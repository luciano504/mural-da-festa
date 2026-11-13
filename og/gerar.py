# Gera a prévia (imagem + título) do link de cada festa, para o WhatsApp mostrar a arte do convite.
# Sem meta refresh nem canonical: o robô do WhatsApp seguia o redirecionamento e perdia a prévia.
# Roda no GitHub Actions a cada 10 minutos. Escreve c/<slug>/index.html e c/<slug>/og.jpg.
import os, io, json, hashlib, html, urllib.request
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageOps

SUPA = 'https://dcddaxipusfthklmmhxq.supabase.co'
KEY = 'sb_publishable_jonZ2Lq8W33xfCpDxLvJqQ_OLcG87eV'   # chave pública do app (a mesma do index.html)
TOKEN = os.environ.get('OG_TOKEN', '')
SITE = 'https://luciano504.github.io/mural-da-festa/'
W, H = 1200, 630

def rpc(nome, args):
    req = urllib.request.Request(f'{SUPA}/rest/v1/rpc/{nome}', data=json.dumps(args).encode(), method='POST',
        headers={'apikey': KEY, 'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())

def baixar(path):
    url = f'{SUPA}/storage/v1/object/public/fe-midia/' + '/'.join(urllib.parse.quote(p) for p in path.split('/'))
    with urllib.request.urlopen(url, timeout=60) as r: return Image.open(io.BytesIO(r.read())).convert('RGB')

def cor(h, padrao):
    try:
        h = (h or '').lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception: return padrao

def arte(img, W=W, H=H):
    fundo = ImageOps.fit(img, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    fundo = Image.blend(fundo, Image.new('RGB', (W, H), (255, 255, 255)), .25)
    a = ImageOps.contain(img, (W - 80, H - 50), Image.LANCZOS)
    x, y = (W - a.width) // 2, (H - a.height) // 2
    sombra = Image.new('L', (a.width + 60, a.height + 60), 0); ImageDraw.Draw(sombra).rectangle([30, 34, a.width + 30, a.height + 34], fill=110)
    sombra = sombra.filter(ImageFilter.GaussianBlur(14))
    fundo.paste((0, 0, 0), (x - 30, y - 30), sombra); fundo.paste(a, (x, y))
    return fundo

def cartao(f):
    bg = cor(f.get('bg'), (246, 241, 244)); ac = cor(f.get('accent'), (150, 60, 95))
    im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
    def fonte(n, tam):
        for p in [f'/usr/share/fonts/truetype/dejavu/{n}', '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf']:
            if os.path.exists(p): return ImageFont.truetype(p, tam)
        return ImageFont.load_default()
    nome = f.get('homenageado') or f.get('titulo') or 'Mural da Festa'
    tam = 92
    while tam > 40 and d.textlength(nome, font=fonte('DejaVuSerif-Bold.ttf', tam)) > W - 160: tam -= 6
    d.rectangle([24, 24, W - 24, H - 24], outline=ac, width=3)
    d.text((W / 2, H / 2 - 30), nome, font=fonte('DejaVuSerif-Bold.ttf', tam), fill=ac, anchor='mm')
    sub = f.get('titulo') if f.get('titulo') and f.get('titulo') != nome else ''
    if sub: d.text((W / 2, H / 2 + 60), sub, font=fonte('DejaVuSerif.ttf', 40), fill=(60, 50, 70), anchor='mm')
    return im

def pagina(f, ver, quadrado=False):
    slug = f['slug']; corp = f.get('categoria') == 'corporativo'
    titulo = f.get('titulo') or f.get('homenageado') or 'Mural da Festa'
    desc = ('Confirme sua presença pelo link. No dia, é por ele que você participa: perguntas, mensagens e muito mais.' if corp
            else f"Confirme sua presença e deixe sua homenagem para {f.get('homenageado') or 'o homenageado'}: foto, recado, áudio ou vídeo.")
    destino = f'{SITE}?f={slug}'; img = f'{SITE}c/{slug}/' + ('og_q.jpg' if quadrado else 'og.jpg') + f'?v={ver}'; LA, AL = (1200, 1200) if quadrado else (W, H)
    e = html.escape
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)}</title>
<meta property="og:type" content="website"><meta property="og:site_name" content="Mural da Festa">
<meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{SITE}c/{slug}/"><meta property="og:image" content="{img}">
<meta property="og:image:width" content="{LA}"><meta property="og:image:height" content="{AL}"><meta property="og:image:type" content="image/jpeg">
<meta name="twitter:card" content="summary_large_image"><meta name="description" content="{e(desc)}">
<meta property="og:image:secure_url" content="{img}"><meta property="og:locale" content="pt_BR">
<script>location.replace({json.dumps(destino)} + location.hash);</script>
</head><body style="font-family:system-ui;text-align:center;padding:40px"><p><a href="{destino}">Abrir o convite</a></p></body></html>
'''

def main():
    if not TOKEN: print('Falta a senha OG_TOKEN nos Secrets do repositório.'); return
    festas = rpc('fe_og_lista', {'p_token': TOKEN}); mudou = 0
    for f in festas:
        slug = f.get('slug')
        if not slug or '/' in slug or '..' in slug: continue
        fonte_img = f.get('convite') or f.get('fundo') or f.get('enfeite') or f.get('logo')
        chave = hashlib.md5(json.dumps([fonte_img, f.get('titulo'), f.get('homenageado'), f.get('categoria'), f.get('bg'), f.get('accent'), 6]).encode()).hexdigest()[:10]
        pasta = os.path.join('c', slug); os.makedirs(pasta, exist_ok=True)
        marca = os.path.join(pasta, '.versao')
        if os.path.exists(marca) and open(marca).read().strip() == chave: continue
        try: im = arte(baixar(fonte_img)) if fonte_img else cartao(f)
        except Exception as ex: print('sem imagem', slug, ex); im = cartao(f)
        try: imq = arte(baixar(fonte_img), 1200, 1200) if fonte_img else None
        except Exception: imq = None
        def salvar(im, nome):
            q = 85
            while True:
                buf = io.BytesIO(); im.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
                if buf.tell() < 280_000 or q <= 55: break
                q -= 8
            open(os.path.join(pasta, nome), 'wb').write(buf.getvalue())
        salvar(im, 'og.jpg')
        if imq: salvar(imq, 'og_q.jpg')   # quadrado: no WhatsApp o convite aparece grande (aprovado em 13/11/2026)
        open(os.path.join(pasta, 'index.html'), 'w', encoding='utf-8').write(pagina(f, chave, bool(imq)))
        open(marca, 'w').write(chave); mudou += 1; print('atualizada', slug)
    print(len(festas), 'festas,', mudou, 'atualizadas')

if __name__ == '__main__': main()
