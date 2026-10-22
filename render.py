"""Short vertical (1080x1920) do Mente Secreta: pinturas escuras com tom dourado, zoom lento,
fade pro preto entre cenas, legendas de 2-3 palavras com uma palavra colorida, trilha escura.
Uso: python3 tts.py r.json out && python3 musica.py out && python3 render.py r.json out -> out/final.mp4
Cena: {"text", "src", "focus": 0..1 (0=esquerda), "destaque": ["PALAVRA"], "foco_y": 0..1}"""
import sys, os, json, subprocess, math, hashlib, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get('MS_CACHE', '/tmp/ms_cache')
OURO = (232, 168, 64); VERM = (235, 40, 70); CIANO = (60, 225, 215); MAG = (225, 60, 200); BRANCO = (255, 255, 255)
CORES = [VERM, CIANO, OURO, MAG]

def fpath(n):
    for p in (os.path.join(HERE, 'fonts', n), os.path.join(HERE, n)):
        if os.path.exists(p): return p
    raise FileNotFoundError(n)
M9 = {s: ImageFont.truetype(fpath('Mont900.ttf'), s) for s in (60, 70, 78)}
M8 = ImageFont.truetype(fpath('Mont800.ttf'), 30)

def run(cmd): subprocess.run(cmd, check=True)

def source_file(src):
    if os.path.exists(src): return src
    os.makedirs(CACHE, exist_ok=True)
    base = re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(src.split('?')[0]))[-60:] or 'img'
    p = os.path.join(CACHE, hashlib.md5(src.encode()).hexdigest()[:8] + '_' + base)
    if not os.path.exists(p) or os.path.getsize(p) < 1000:
        print('baixando', src)
        run(['curl', '-fsSL', '--retry', '3', '--retry-delay', '5', '-m', '90', '-A', 'MenteSecretaBot/1.0 (https://github.com/aupontocortes-tech)', '-o', p, src])
    # normaliza para JPG (alguns servidores mandam sem extensão)
    j = p + '.jpg'
    if not os.path.exists(j): Image.open(p).convert('RGB').save(j, quality=95)
    return j

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3

def cena_mp4(i, sc, dur, out):
    p = source_file(sc['src']); im = Image.open(p); iw, ih = im.size
    if iw * 16 >= ih * 9:   # mais larga que 9:16: corta laterais
        cw, ch = int(ih * 9 / 16), ih; x = int((iw - cw) * float(sc.get('focus', 0.5))); y = 0
    else:                   # mais alta: corta em cima/embaixo
        cw, ch = iw, int(iw * 16 / 9); x = 0; y = int((ih - ch) * float(sc.get('foco_y', 0.3)))
    cw -= cw % 2; ch -= ch % 2
    z = 1.10; n = max(1, int(dur * FPS))
    dx = ['iw/2-(iw/zoom/2)', 'iw/2-(iw/zoom/2)+on*0.4', 'iw/2-(iw/zoom/2)-on*0.4'][i % 3]
    vf = (f"crop={cw}:{ch}:{x}:{y},scale={int(W*1.3)//2*2}:{int(H*1.3)//2*2}:flags=lanczos,"
          f"zoompan=z='1+({z}-1)*on/{n}':x='{dx}':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
          f"eq=contrast=1.10:brightness=-0.06:saturation=0.62,"
          f"colorbalance=rs=0.07:gs=0.02:bs=-0.09:rm=0.06:gm=0.01:bm=-0.07:rh=0.04:bh=-0.05,"
          f"vignette=PI/3.6,fade=t=in:st=0:d=0.35,setsar=1")
    o = os.path.join(out, f'part{i:02d}.mp4')
    run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', p, '-t', f'{dur:.3f}', '-an', '-vf', vf,
         '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', o])
    return o

def blocos(words):
    ch, cur = [], []
    for w in words:
        cur.append(w); txt = ' '.join(x['w'] for x in cur)
        if len(cur) >= 3 or len(txt) >= 16 or w['w'][-1] in '.,:?!;' or (cur and w is words[-1]):
            ch.append(cur); cur = []
    if cur: ch.append(cur)
    return ch

def limpa(w): return w.strip('.,:?!;"“”()').upper()

_CACHE_LEG = {}
def desenha_legenda(base, chunk, cor, alvo, k):
    """chunk = lista de palavras; alvo = índice da palavra colorida; k = animação 0..1"""
    k = min(1.0, round(k * 6) / 6)
    chave = (id(chunk), k)
    if chave not in _CACHE_LEG:
        _CACHE_LEG.clear() if len(_CACHE_LEG) > 40 else None
        _CACHE_LEG[chave] = _camada_legenda(chunk, cor, alvo, k)
    L, pos = _CACHE_LEG[chave]; base.alpha_composite(L, pos)

def _camada_legenda(chunk, cor, alvo, k):
    ws = [limpa(x['w']) for x in chunk]
    linhas = [ws] if len(' '.join(ws)) <= 11 or len(ws) == 1 else [ws[:len(ws) // 2 or 1], ws[len(ws) // 2 or 1:]]
    if len(ws) == 3 and len(linhas) == 2: linhas = [ws[:2], ws[2:]] if len(ws[0] + ws[1]) <= len(ws[1] + ws[2]) else [ws[:1], ws[1:]]
    lay = Image.new('RGBA', (W, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); idx = 0; y = 120
    for li, ln in enumerate(linhas):
        f = M9[78] if li == len(linhas) - 1 and len(linhas) == 2 else M9[70]
        if sum(d.textlength(w, font=f) for w in ln) > 940: f = M9[60]
        sp = 22; larg = [d.textlength(w, font=f) for w in ln]; x = W / 2 - (sum(larg) + sp * (len(ln) - 1)) / 2
        for w, lw in zip(ln, larg):
            c = cor if idx == alvo else BRANCO
            d.text((x, y), w, font=f, fill=c, stroke_width=7, stroke_fill=(0, 0, 0), anchor='lm')
            x += lw + sp; idx += 1
        y += f.size + 16
    sombra = lay.split()[3].filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.75))
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0)); sh.putalpha(sombra)
    sh.alpha_composite(lay); s = 0.88 + 0.12 * ease(k)
    L2 = sh.resize((int(W * s), int(420 * s)), Image.BICUBIC) if s != 1 else sh
    if k < 1: L2.putalpha(L2.split()[3].point(lambda v: int(v * ease(k * 1.4))))
    return L2, (int(W / 2 - L2.width / 2), int(1330 - L2.height / 2))

def main():
    spec = json.load(open(sys.argv[1], encoding='utf-8')); out = sys.argv[2]
    T = json.load(open(os.path.join(out, 'timing.json'), encoding='utf-8'))
    DUR, SEGS, WORDS, SC = T['dur'], T['segs'], T['words'], spec['scenes']
    assert len(SC) == len(SEGS), 'número de cenas diferente da narração'
    bounds = [0.0] + [SEGS[i][0] - 0.25 for i in range(1, len(SEGS))] + [DUR]
    parts = [cena_mp4(i, sc, bounds[i + 1] - bounds[i], out) for i, sc in enumerate(SC)]
    lst = os.path.join(out, 'parts.txt'); open(lst, 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    base = os.path.join(out, 'base.mp4')
    run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', base])

    CH = []; ncor = 0
    for c in blocos(WORDS):
        sc = SC[c[0]['seg']]; dest = [limpa(x) for x in sc.get('destaque', [])]
        ws = [limpa(x['w']) for x in c]
        alvo = next((j for j, w in enumerate(ws) if w in dest), None)
        if alvo is None: alvo = max(range(len(ws)), key=lambda j: len(ws[j]))
        cor = OURO if ws[alvo] in dest else CORES[ncor % len(CORES)]; ncor += 1
        CH.append((c[0]['s'] - 0.05, c[-1]['e'] + 0.12, c, cor, alvo))
    for j in range(len(CH) - 1):  # emenda blocos próximos para não piscar
        if CH[j + 1][0] - CH[j][1] < 0.35: CH[j] = (CH[j][0], CH[j + 1][0], *CH[j][2:])

    grad = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        a = int(150 * (1 - y / 420) ** 1.6) if y < 420 else 0
        if y > 1050: a = max(a, int(200 * ((y - 1050) / 870) ** 1.2))
        grad[y, :, 3] = a
    GRAD = Image.fromarray(grad, 'RGBA')
    final = os.path.join(out, 'final.mp4')
    dec = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', base, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-i', os.path.join(out, 'narr.wav'), '-i', os.path.join(out, 'trilha.wav'),
                            '-filter_complex', '[1:a]aresample=48000[n];[2:a]aresample=48000[m];[n][m]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]',
                            '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '4200k',
                            '-bufsize', '8000k', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                            '-shortest', '-movflags', '+faststart', final], stdin=subprocess.PIPE)
    n = int(math.ceil(DUR * FPS)); fs = W * H * 3; last = None
    for i in range(n):
        raw = dec.stdout.read(fs)
        if len(raw) < fs: raw = last
        last = raw; t = i / FPS
        im = Image.frombytes('RGB', (W, H), raw).convert('RGBA'); im.alpha_composite(GRAD); d = ImageDraw.Draw(im)
        d.text((W / 2, 120), 'MENTE SECRETA', font=M8, fill=OURO + (200,), anchor='mm')
        for (cs, ce, c, cor, alvo) in CH:
            if cs <= t < ce: desenha_legenda(im, c, cor, alvo, (t - cs) / 0.18); break
        d.rectangle((0, H - 10, W * t / DUR, H), fill=OURO)
        enc.stdin.write(im.convert('RGB').tobytes())
    enc.stdin.close(); enc.wait(); dec.terminate()
    print('ok', final, round(os.path.getsize(final) / 1e6, 1), 'MB', round(DUR, 1), 's')

if __name__ == '__main__':
    main()
