"""Veil Frequency — VÍDEO LONGO (deitado, 16:9) a partir de veil/longos/fila/NN_slug.json.
python3 veil/longo.py veil/longos/fila/01_x.json out   ->  out/longo.mp4 e out/capa.jpg

Formato do arquivo: {"titulo", "titulo_pt", "resumo_pt", "descricao", "tags", "capa_parte", "capa_texto",
  "partes": [{"visual": "imagem em inglês", "falas": [{"text": "...", "voz": "dan" (opcional), "pausa": 1.0}]}]}
Cada PARTE = uma imagem fixa (zoom bem lento). A imagem só troca quando muda a parte (momentos importantes).
Narração: Edge TTS (narrador fixo do canal; vozes de personagem nas falas). Fundo: chuva + drone grave."""
import json, os, sys, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import historia   # gera imagem (Cloudflare FLUX, reserva Pollinations)

W, H, FPS = 1920, 1080, 30
VOZES = {
    'narrador': ('en-US-AndrewMultilingualNeural', '-10%', '-3Hz'),
    'dan':      ('en-US-GuyNeural', '-2%', '+0Hz'),
    'eco':      ('en-US-GuyNeural', '-14%', '-10Hz'),
    'mulher':   ('en-US-AvaMultilingualNeural', '-4%', '+0Hz'),
    'sussurro': ('en-US-AvaMultilingualNeural', '-14%', '-6Hz'),
    'homem':    ('en-US-GuyNeural', '-2%', '+0Hz'),
    'idosa':    ('en-US-JennyNeural', '-12%', '-6Hz'),
    'idoso':    ('en-US-GuyNeural', '-12%', '-8Hz'),
    'crianca':  ('en-US-AnaNeural', '-6%', '+0Hz'),
    'sombria':  ('en-US-JennyNeural', '-20%', '-20Hz'),
    'sombrio':  ('en-US-GuyNeural', '-20%', '-20Hz'),
}
ESTILO = ('cinematic horror film still, wide 16:9 composition, dim moody low-key lighting, desaturated cold tones, film grain, '
          'photorealistic, unsettling atmosphere, no text, no watermark, no blood, no gore')

def imagem_16x9(prompt, seed, destino):
    """Gera (quadrada ou vertical) e recorta o meio em 16:9, 1920x1080."""
    tmp = destino + '.tmp.jpg'
    historia.ESTILO = ESTILO
    if not historia.gerar_imagem(prompt, seed, tmp):
        return False
    im = Image.open(tmp).convert('RGB'); w, h = im.size
    alvo_h = int(w * 9 / 16)
    if alvo_h <= h:
        y = (h - alvo_h) // 2; im = im.crop((0, y, w, y + alvo_h))
    im = im.resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=3))
    im.save(destino, quality=94); os.remove(tmp)
    return True

def musica(dur, destino, sr=44100):
    n = int(dur * sr); t = np.arange(n) / sr; rng = np.random.default_rng(13)
    chuva = rng.standard_normal(n)
    chuva = chuva - np.convolve(chuva, np.ones(8) / 8, mode='same')          # tira o grave: chiado de chuva
    chuva = np.convolve(chuva, np.ones(3) / 3, mode='same') * (0.75 + 0.25 * np.sin(2 * np.pi * t / 19))
    gotas = np.zeros(n); pos = rng.integers(0, n, int(dur * 6))
    for p in pos: gotas[p:p + 200] += rng.uniform(0.2, 0.6) * np.exp(-np.arange(min(200, n - p)) / 25)
    drone = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (41.2, 55, 61.7)) / 3
    drone *= 0.6 + 0.4 * np.sin(2 * np.pi * t / 37)
    y = 0.10 * chuva / np.max(np.abs(chuva)) + 0.05 * gotas / max(1e-6, np.max(np.abs(gotas))) + 0.16 * drone
    f = int(3 * sr); y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    sf.write(destino, np.stack([y, np.roll(y, 300)], 1).astype(np.float32), sr)

def capa(img, texto, destino):
    im = Image.open(img).convert('RGB').resize((1280, 720)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(os.path.join(RAIZ, 'veil', 'Anton.ttf') if os.path.exists(os.path.join(RAIZ, 'veil', 'Anton.ttf')) else os.path.join(RAIZ, 'Mont900.ttf'), 120)
    w = d.textlength(texto, font=f); x, y = (1280 - w) / 2, 520
    if w > 1220:
        f = ImageFont.truetype(os.path.join(RAIZ, 'Mont900.ttf'), 80); w = d.textlength(texto, font=f); x = (1280 - w) / 2; y = 560
    for dx in range(-7, 8, 3):
        for dy in range(-7, 8, 3): d.text((x + dx, y + dy), texto, font=f, fill='black')
    d.text((x, y), texto, font=f, fill='#E8E8E8')
    im.save(destino, quality=92)

def main(caminho, out):
    os.makedirs(out, exist_ok=True)
    h = json.load(open(caminho, encoding='utf-8'))
    # 1) imagens (uma por parte)
    imgs = []
    for i, p in enumerate(h['partes']):
        img = os.path.abspath(f'{out}/parte{i:02d}.jpg')
        if not os.path.exists(img):
            print('imagem da parte', i, flush=True)
            if not imagem_16x9(p['visual'], 900 + i, img):
                sys.exit(f'ERRO: imagem da parte {i}')
        imgs.append(img)
    # 2) narração
    cenas, parte_de = [], []
    for i, p in enumerate(h['partes']):
        for k, f in enumerate(p['falas']):
            v, r, pi = VOZES.get(f.get('voz') or 'narrador', VOZES['narrador'])
            ultima = k == len(p['falas']) - 1
            cenas.append({'text': f['text'], 'voz_edge': v, 'rate': r, 'pitch': pi,
                          'pausa': f.get('pausa', 1.1 if ultima else 0.55)})
            parte_de.append(i)
    json.dump({'scenes': cenas}, open(f'{out}/spec.json', 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.run(['python3', os.path.join(RAIZ, 'tts.py'), f'{out}/spec.json', out], check=True)
    T = json.load(open(f'{out}/timing.json'))
    segs, total = T['segs'], T['dur']
    # início/fim de cada parte (a imagem troca junto com a fala que abre a parte)
    ini = []
    for i in range(len(h['partes'])):
        s = segs[parte_de.index(i)][0]
        ini.append(0.0 if i == 0 else max(0.0, s - 0.6))
    ini.append(total + 6.0)   # 6 s de respiro no final
    # 3) vídeo: uma cena por imagem, zoom lento, fade nas trocas
    lista = []
    for i, img in enumerate(imgs):
        d = ini[i + 1] - ini[i]; nfr = int(round(d * FPS))
        z = f"1+0.10*on/{max(1, nfr)}"            # 10% de zoom ao longo da parte inteira
        vf = (f"scale=2880:1620,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nfr}:s={W}x{H}:fps={FPS},"
              f"eq=contrast=1.06:brightness=-0.03:saturation=0.85,vignette=PI/4,"
              f"fade=t=in:st=0:d=0.8,fade=t=out:st={max(0, d - 0.8):.2f}:d=0.8,format=yuv420p")
        if i == 0:   # título no começo
            tit = h['titulo'].split('|')[0].strip().upper()
            open(f'{out}/titulo.txt', 'w').write(tit)
            vf = vf.replace(',format=yuv420p', f",drawtext=fontfile={os.path.join(RAIZ, 'Mont900.ttf')}:textfile={out}/titulo.txt:"
                            f"x=(w-tw)/2:y=h*0.42:fontsize=96:fontcolor=white:alpha='if(lt(t,1),t,if(lt(t,5),1,max(0,6-t)))':"
                            f"shadowcolor=black:shadowx=4:shadowy=4,format=yuv420p")
        cena = f'{out}/cena{i:02d}.mp4'; tmp = f'{out}/tmp{i:02d}.mp4'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-loop', '1', '-framerate', '1', '-t', '1', '-i', img,
                        '-vf', vf, '-frames:v', str(nfr), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
                        '-pix_fmt', 'yuv420p', tmp], check=True)
        os.replace(tmp, cena); lista.append(cena); print('cena', i, round(d, 1), 's', flush=True)
    open(f'{out}/lista.txt', 'w').write(''.join(f"file '{os.path.abspath(c)}'\n" for c in lista))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{out}/lista.txt', '-c', 'copy', f'{out}/video.mp4'], check=True)
    musica(ini[-1], f'{out}/fundo.wav')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f'{out}/video.mp4', '-i', f'{out}/narr.wav', '-i', f'{out}/fundo.wav',
                    '-filter_complex', "[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,apad[n];[2:a]aresample=48000,volume=0.55[m];"
                    "[n][m]amix=inputs=2:duration=shortest:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11[a]",
                    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart',
                    f'{out}/longo.mp4'], check=True)
    capa(imgs[h.get('capa_parte', 0)], h.get('capa_texto', h['titulo'].split('|')[0].strip().upper()), f'{out}/capa.jpg')
    print('OK', f'{out}/longo.mp4', round(ini[-1] / 60, 1), 'min')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'out')
