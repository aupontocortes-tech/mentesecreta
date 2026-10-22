"""Narração do Mente Secreta (voz grave e calma, Microsoft Edge TTS, grátis).
Uso: python3 tts.py roteiro.json out
Gera out/narr.wav e out/timing.json (início/fim de cada cena e de cada palavra)."""
import sys, os, json, asyncio, ssl, subprocess, time
import numpy as np, soundfile as sf

# Se existir um certificado extra (proxy), confia nele também
_extra = os.environ.get('EXTRA_CA')
if _extra and os.path.exists(_extra):
    _orig = ssl.create_default_context
    def _ctx(*a, **k):
        c = _orig(*a, **k); c.load_verify_locations(_extra); return c
    ssl.create_default_context = _ctx
import edge_tts

VOZ = os.environ.get('MS_VOZ', 'pt-BR-AntonioNeural')
RATE = os.environ.get('MS_RATE', '+6%')
PITCH = os.environ.get('MS_PITCH', '-14Hz')
SR = 24000
PRON = {'Greene': 'Grím', 'Cornell': 'Cornél', 'Stanford': 'Stênford', 'Harvard': 'Rárvard', 'Shorts': 'Xórts'}

async def falar(texto, mp3):
    c = edge_tts.Communicate(texto, VOZ, rate=RATE, pitch=PITCH, boundary='WordBoundary')
    marcas = []
    with open(mp3, 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                marcas.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7))
    return marcas

def para_wav(mp3):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', mp3, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()

def main():
    spec = json.load(open(sys.argv[1], encoding='utf-8')); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    pron = dict(PRON); pron.update(spec.get('pron', {}))
    audio = [np.zeros(int(SR * 0.2), np.float32)]; t = 0.2; words = []; segs = []
    for i, sc in enumerate(spec['scenes']):
        texto = sc['text']; falado = texto
        for k, v in pron.items(): falado = falado.replace(k, v)
        mp3 = os.path.join(out, f'v{i:02d}.mp3')
        for tent in range(4):
            try: marcas = asyncio.run(falar(falado, mp3)); break
            except Exception as e:
                print('TTS falhou, tentando de novo:', e); time.sleep(3 + tent * 3)
        else: sys.exit('ERRO: TTS não respondeu')
        x = para_wav(mp3)
        nz = np.where(np.abs(x) > 0.01)[0]; ini = max(0, nz[0] - 300); x = x[ini:nz[-1] + 600]; dur = len(x) / SR
        ws = texto.split(); off = ini / SR
        if len(marcas) == len(ws):
            for w, (s, e) in zip(ws, marcas):
                words.append({'w': w, 's': round(t + s - off, 3), 'e': round(t + e - off, 3), 'seg': i})
        else:  # número de palavras diferente: distribui pelo tamanho
            tot = sum(len(w) + 1 for w in ws); cur = t
            for w in ws:
                wd = dur * (len(w) + 1) / tot; words.append({'w': w, 's': round(cur, 3), 'e': round(cur + wd, 3), 'seg': i}); cur += wd
        segs.append([t, t + dur]); audio.append(x); t += dur
        pausa = float(sc.get('pausa', 0.22)); audio.append(np.zeros(int(SR * pausa), np.float32)); t += pausa
    audio.append(np.zeros(int(SR * 0.8), np.float32)); t += 0.8
    y = np.concatenate(audio); y = y / np.max(np.abs(y)) * 0.89
    sf.write(os.path.join(out, 'narr.wav'), y, SR)
    json.dump({'words': words, 'segs': segs, 'dur': len(y) / SR}, open(os.path.join(out, 'timing.json'), 'w'), ensure_ascii=False)
    print('narração', round(len(y) / SR, 2), 's,', len(segs), 'cenas')

if __name__ == '__main__':
    main()
