"""Veil Frequency — monta um Short a partir de um episódio (serie/fila/NN_slug.json).

python3 veil/vf.py veil/serie/fila/01_x.json out
Gera: out/final.mp4 e grava os créditos das imagens dentro do próprio JSON (campo "creditos").

Passos: imagens grátis (Openverse: CC0 / domínio público / CC BY) -> voz Edge TTS em inglês
(mesmo ajuste grave do Mente Secreta) com filtro de rádio -> visual de fita VHS -> som -> vídeo 1080x1920.
"""
import asyncio, json, os, subprocess, sys, random, datetime, urllib.request, urllib.parse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts

W, H, FPS = 1080, 1920, 30
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
MONOB = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
ANTON = os.path.join(RAIZ, 'Anton.ttf')
VOZES = {
    'narrador': ('en-US-ChristopherNeural', '+6%', '-14Hz'),
    'transmissao': ('en-US-JennyNeural', '-8%', '-6Hz'),
}
UA = 'Mozilla/5.0 (VeilFrequencyBot/1.0; github.com/aupontocortes-tech)'
TINTAS = {'fogo': (1.25, 0.75, 0.6), 'frio': (0.8, 0.95, 1.1), 'verde': (0.8, 1.1, 0.85), 'normal': (0.9, 0.95, 1.0)}


def run(*a):
    r = subprocess.run(a, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        raise RuntimeError(' '.join(a[:6]) + '\n' + r.stderr[-800:])


def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


# ---------------------------------------------------------------- imagens
def openverse(q):
    u = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(
        {'q': q, 'license': 'cc0,pdm,by', 'page_size': 20, 'mature': 'false'})
    for _ in range(3):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            return json.load(urllib.request.urlopen(req, timeout=60)).get('results', [])
        except Exception as e:
            print('openverse falhou:', e)
    return []


PROIBIDAS = ('logo', 'brand', 'advert', 'poster', 'sign', 'text', 'iphone', 'case', 'restaurant', 'menu', 'garden', 'flower', 'wedding', 'selfie', 'tdk', 'sony', 'maxell', 'demagnetizer', 'mix')


def relevante(r, q):
    """A foto precisa ter no título/tags pelo menos uma palavra importante da busca (evita foto aleatória)."""
    chaves = [w for w in q.lower().split() if len(w) > 3 and w not in ('dark', 'night', 'old', 'empty', 'vintage')] or q.lower().split()
    texto = ' '.join([(r.get('title') or '')] + [t.get('name', '') for t in (r.get('tags') or [])]).lower()
    if any(p in (r.get('title') or '').lower() for p in PROIBIDAS):
        return False
    return any(c in texto for c in chaves)


def baixar_imagem(q, destino, usados):
    for r in openverse(q):
        if r['url'] in usados or (r.get('width') or 0) < 700 or not relevante(r, q):
            continue
        subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, '-o', destino, r['url']])
        try:
            im = Image.open(destino); im.load()
            if min(im.size) < 450:
                continue
        except Exception:
            continue
        usados.add(r['url'])
        lic = r['license'].upper()
        lic = 'Public Domain' if lic in ('PDM', 'CC0') else f"CC {lic} {r.get('license_version') or ''}".strip()
        return f"\"{r.get('title') or 'Untitled'}\" by {r.get('creator') or 'unknown'} ({lic}) {r.get('foreign_landing_url') or ''}".strip()
    return None


# ---------------------------------------------------------------- visual
def wrap(d, text, font, maxw):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def fundo(foto, tinta, zoom, seed):
    if foto and os.path.exists(foto):
        ph = Image.open(foto).convert('RGB')
        sw, sh = ph.size
        ch = sh / zoom; cw = ch * W / H
        if cw > sw:
            cw = sw / zoom; ch = cw * H / W
        x0, y0 = (sw - cw) / 2, (sh - ch) / 2
        ph = ph.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
        a = np.asarray(ph).astype('float32')
        a = a.mean(-1, keepdims=True) * 0.75 + a * 0.25
        a = a * np.array(TINTAS.get(tinta, TINTAS['normal']))
        a = (a / 255).clip(0, 1) ** 1.25 * 255 * 0.78
        return Image.fromarray(a.clip(0, 255).astype('uint8'))
    arr = (np.random.default_rng(seed).random((H // 4, W // 4)) * 60).astype('uint8')
    return Image.fromarray(np.stack([arr] * 3, -1)).resize((W, H), Image.NEAREST)


def quadro(sc, foto, seed, saida, amanha):
    img = fundo(foto, sc.get('tinta', 'normal'), sc.get('zoom', 1.0), seed)
    d = ImageDraw.Draw(img)
    verde = (120, 255, 160)
    if sc.get('alerta'):
        d.rectangle([110, 300, W - 110, 520], fill=(0, 0, 0))
        d.text((W / 2, 380), sc['alerta'], font=ImageFont.truetype(MONOB, 80), fill=(255, 40, 40), anchor='mm')
        if sc.get('alerta_sub'):
            d.text((W / 2, 470), sc['alerta_sub'], font=ImageFont.truetype(MONO, 40), fill=(220, 220, 220), anchor='mm')
    if sc.get('caixa'):
        f = ImageFont.truetype(MONO, 46)
        largura = max(d.textlength(l, font=f) for l in sc['caixa'])
        if largura > W - 200:
            f = ImageFont.truetype(MONO, int(46 * (W - 200) / largura))
        d.rectangle([70, 300, W - 70, 340 + 80 * len(sc['caixa'])], fill=(0, 0, 0))
        for k, ln in enumerate(sc['caixa']):
            cor = (255, 70, 70) if ln.startswith('!') else verde
            d.text((100, 320 + k * 80), ln.lstrip('!'), font=f, fill=cor)
    if sc.get('etiqueta'):
        txt = sc['etiqueta'].replace('{amanha}', amanha)
        d.rectangle([160, 330, W - 160, 470], fill=(214, 204, 180))
        d.text((W / 2, 400), txt, font=ImageFont.truetype(MONOB, 70), fill=(200, 0, 0) if sc.get('vermelho') else (20, 20, 20), anchor='mm')
    # canto VHS
    fv = ImageFont.truetype(MONOB, 46)
    d.text((70, 90), 'PLAY ►', font=fv, fill=(235, 235, 235))
    d.text((70, 150), '1.317 MHz', font=fv, fill=(235, 235, 235))
    d.text((W - 70, 90), '03:17 AM', font=fv, fill=(235, 235, 235), anchor='ra')
    # legenda (palavras-chave em vermelho)
    fa = ImageFont.truetype(ANTON, 84)
    dest = {w.upper().strip(".,!?'\"") for w in sc.get('destaque', [])}
    y = 1380
    for ln in wrap(d, sc['text'].upper(), fa, W - 160):
        x = (W - d.textlength(ln, font=fa)) / 2
        for w in ln.split(' '):
            cor = (255, 45, 45) if w.strip('.,!?"') in dest else (255, 255, 255)
            d.text((x, y), w, font=fa, fill=cor, stroke_width=6, stroke_fill=(0, 0, 0))
            x += d.textlength(w + ' ', font=fa)
        y += 104
    a = np.asarray(img).astype('float32')
    a[::4] *= 0.72
    yy, xx = np.mgrid[0:H, 0:W]
    a *= (1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2)[..., None]
    Image.fromarray(a.clip(0, 255).astype('uint8')).save(saida)


def clipe(png, d_seg, saida, onda_audio=None, onda_ini=0.0, direcao=1):
    flick = "eq=brightness='0.04*sin(t*37)+0.02*sin(t*91)':eval=frame"
    noise = 'noise=alls=14:allf=t+u'
    z0, z1 = (1.0, 1.07) if direcao > 0 else (1.07, 1.0)
    zp = (f"zoompan=z='{z0}+({z1}-{z0})*on/({d_seg}*{FPS})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
    if onda_audio:
        fc = (f"[0:v]{zp}[b];[1:a]atrim={onda_ini:.3f},asetpts=PTS-STARTPTS,showwaves=s={W}x500:mode=cline:colors=0x66ffa0:rate={FPS},format=rgba[w];"
              f"[b][w]overlay=0:820:shortest=1,{noise},{flick},format=yuv420p[v]")
        run('ffmpeg', '-y', '-loop', '1', '-i', png, '-i', onda_audio, '-filter_complex', fc, '-map', '[v]',
            '-t', f'{d_seg:.3f}', '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', saida)
    else:
        run('ffmpeg', '-y', '-loop', '1', '-i', png, '-vf', f'scale={W}:{H},{zp},{noise},{flick},format=yuv420p',
            '-t', f'{d_seg:.3f}', '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', saida)


# ---------------------------------------------------------------- som
async def falar(sc, destino):
    voz, rate, pitch = VOZES.get(sc.get('voz', 'narrador'), VOZES['narrador'])
    await edge_tts.Communicate(sc['text'], voz, rate=rate, pitch=pitch).save(destino)


def audio_cena(sc, raw, d_total, saida):
    if sc.get('voz') == 'transmissao':
        af = 'highpass=f=350,lowpass=f=3200,acrusher=bits=8:mix=0.35,aecho=0.8:0.6:120:0.3,volume=2.2'
    else:
        af = 'highpass=f=110,lowpass=f=7000,aecho=0.8:0.5:60:0.18,volume=1.6'
    run('ffmpeg', '-y', '-i', raw, '-af', f'{af},apad', '-t', f'{d_total:.3f}', '-ar', '44100', '-ac', '2', saida)


def main(caminho, out):
    os.makedirs(out, exist_ok=True)
    ep = json.load(open(caminho, encoding='utf-8'))
    S = ep['scenes']
    amanha = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime('%m/%d/%y')

    async def vozes():
        for i, sc in enumerate(S):
            await falar(sc, f'{out}/raw{i}.mp3')
    asyncio.run(vozes())

    usados, creditos, dts, clipes, cortes_extra = set(), [], [], [], []
    t = 0.0
    for i, sc in enumerate(S):
        dt = dur(f'{out}/raw{i}.mp3') + 0.25 + float(sc.get('pausa', 0))
        dts.append(dt)
        audio_cena(sc, f'{out}/raw{i}.mp3', dt, f'{out}/a{i}.wav')
        buscas = sc.get('imagens') or []
        if isinstance(buscas, str):
            buscas = [buscas]
        fotos = []
        for k, q in enumerate(buscas[:3]):
            dest = f'{out}/img{i}_{k}.jpg'
            cred = baixar_imagem(q, dest, usados) or baixar_imagem('abandoned dark room', dest, usados)
            if cred:
                fotos.append(dest); creditos.append(cred)
        if not fotos:
            fotos = [None]
        seg = dt / len(fotos)
        for k, foto in enumerate(fotos):
            png = f'{out}/q{i}_{k}.png'
            quadro(sc, foto, i * 10 + k, png, amanha)
            mp4 = f'{out}/v{i}_{k}.mp4'
            clipe(png, seg, mp4, f'{out}/a{i}.wav' if sc.get('onda') else None, k * seg, 1 if (i + k) % 2 == 0 else -1)
            clipes.append(mp4)
            if k:
                cortes_extra.append(t + k * seg)
        t += dt
    total = sum(dts)

    with open(f'{out}/lista.txt', 'w') as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clipes)
    run('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', f'{out}/lista.txt', '-c', 'copy', f'{out}/video.mp4')
    run('ffmpeg', '-y', *sum([['-i', f'{out}/a{i}.wav'] for i in range(len(S))], []), '-filter_complex',
        ''.join(f'[{i}:a]' for i in range(len(S))) + f'concat=n={len(S)}:v=0:a=1[a]', '-map', '[a]', f'{out}/voz.wav')

    # respiração na pausa da cena marcada com "respiracao": true
    resp_t = None
    for i, sc in enumerate(S):
        if sc.get('respiracao'):
            resp_t = sum(dts[:i]) + dur(f'{out}/raw{i}.mp3') + 0.3
    run('ffmpeg', '-y', '-f', 'lavfi', '-i', 'anoisesrc=color=pink:amplitude=0.6:d=2', '-af',
        "lowpass=f=900,highpass=f=150,volume='0.9*pow(sin(PI*t/1.0),2)':eval=frame", f'{out}/resp.wav')
    cortes = sorted([sum(dts[:k]) for k in range(len(S))] + cortes_extra)
    n = len(cortes)
    rt = int((resp_t or total + 5) * 1000)
    fc = (f"[0:a]volume=1[voz];[1:a]volume=0.05[drone];[2:a]highpass=f=1500,volume=0.035[hiss];"
          f"[3:a]adelay={rt}|{rt},volume={0.5 if resp_t else 0}[resp];"
          f"[4:a]asplit={n}" + ''.join(f'[s{k}]' for k in range(n)) + ';'
          + ''.join(f"[s{k}]atrim=0:0.12,asetpts=PTS-STARTPTS,volume=0.25,adelay={int(c*1000)}|{int(c*1000)}[n{k}];" for k, c in enumerate(cortes))
          + "[voz][drone][hiss][resp]" + ''.join(f'[n{k}]' for k in range(n))
          + f"amix=inputs={4+n}:normalize=0,alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5[a]")
    run('ffmpeg', '-y', '-i', f'{out}/voz.wav', '-f', 'lavfi', '-i', f'sine=f=55:d={total}',
        '-f', 'lavfi', '-i', f'anoisesrc=color=white:amplitude=0.5:d={total}', '-i', f'{out}/resp.wav',
        '-f', 'lavfi', '-i', 'anoisesrc=color=white:amplitude=1:d=1',
        '-filter_complex', fc, '-map', '[a]', '-t', f'{total:.3f}', '-ar', '44100', f'{out}/mix.wav')
    run('ffmpeg', '-y', '-i', f'{out}/video.mp4', '-i', f'{out}/mix.wav', '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-maxrate', '4200k', '-bufsize', '8400k', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{out}/final.mp4')

    ep['creditos'] = list(dict.fromkeys(creditos))
    json.dump(ep, open(caminho, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    palavras = sum(len(s['text'].split()) for s in S)
    print(f'OK {total:.1f}s, {palavras} palavras, {len(clipes)} imagens, {os.path.getsize(out + "/final.mp4") // 1024} KB')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'out')
