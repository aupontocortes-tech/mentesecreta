"""Capa chamativa 1080x1920 (Mente Secreta e Veil Frequency).
Uso: python3 capa.py roteiro.json saida.jpg [imagem1 imagem2 ...]
- Escolhe, entre as imagens (ou as "src" das 4 primeiras cenas do roteiro), a mais forte (contraste + cor + rosto bem iluminado).
- Texto: campo "capa" do roteiro (["LINHA 1", "LINHA 2"]); se não houver, usa o título sem #Shorts e emojis.
- Veil (roteiro com "titulo_pt"): última linha vermelha. Mente Secreta: última linha amarela.
"""
import sys, os, json, re, io, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

AQUI = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

def abre(src):
    try:
        if src.startswith('http'):
            req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
            return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert('RGB')
        return Image.open(src).convert('RGB')
    except Exception as e:
        print('  capa: não abriu', src[:80], e); return None

def nota(im):
    a = np.asarray(im.resize((180, 320)), np.float32)
    sat = (a.max(2) - a.min(2)).mean(); con = a.mean(2).std(); lum = a.mean()
    meio = a[100:220, 45:135].mean()        # centro bem iluminado (rosto/assunto)
    return sat * 0.6 + con + meio * 0.25 - abs(lum - 105) * 0.3

def cobre(im):
    r = max(W / im.width, H / im.height); im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))

def linhas_do(r):
    if r.get('capa'): return [str(l).strip().upper() for l in r['capa'] if str(l).strip()][:3]
    t = re.sub(r'#\w+', '', r.get('titulo', '')); t = re.sub(r'[^\w\s\'?!.,:-]', '', t).strip()
    t = t.split('|')[-1].strip() if '|' in t else t
    pal = t.upper().split()[:6]   # capa curta: no máximo 6 palavras
    if len(pal) <= 3: return [' '.join(pal)]
    meio = (len(pal) + 1) // 2
    return [' '.join(pal[:meio]), ' '.join(pal[meio:])][:2]

def main():
    r = json.load(open(sys.argv[1], encoding='utf-8')); saida = sys.argv[2]
    fontes = sys.argv[3:] or [s.get('src') for s in r.get('scenes', [])[:4] if s.get('src')]
    cands = [(nota(im), im) for im in (abre(s) for s in fontes if s) if im is not None]
    if not cands: print('capa: nenhuma imagem'); return
    im = cobre(max(cands, key=lambda c: c[0])[1])
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.2)).enhance(1.12).convert('RGBA')
    g = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        a = int(205 * (1 - y / 880) ** 1.3) if y < 880 else 0
        if y > 1560: a = max(a, int(150 * (y - 1560) / 360))
        g[y, :, 3] = a
    im.alpha_composite(Image.fromarray(g, 'RGBA')); d = ImageDraw.Draw(im)
    veil = 'titulo_pt' in r
    destaque = (235, 35, 45) if veil else (255, 212, 0)
    linhas = linhas_do(r); y = 250
    for j, ln in enumerate(linhas):
        tam = 210
        while tam > 80:
            f = ImageFont.truetype(os.path.join(AQUI, 'Anton.ttf'), tam)
            if d.textlength(ln, font=f) <= W - 90: break
            tam -= 8
        cor = destaque if j == len(linhas) - 1 else (255, 255, 255)
        d.text((W / 2, y + tam / 2), ln, font=f, fill=cor, anchor='mm', stroke_width=max(9, tam // 11), stroke_fill=(0, 0, 0))
        y += tam + 16
    im.convert('RGB').save(saida, quality=90); print('capa', saida, linhas)

if __name__ == '__main__':
    main()
