"""Veil Frequency — uma história de terror completa por vídeo.

python3 veil/historia.py veil/historias/fila/NN_slug.json out
Gera out/final.mp4.

Passos: imagem de IA por cena (Pollinations, grátis, sem conta) -> voz em inglês (Edge TTS, narrador grave)
-> trilha escura -> montagem com zoom lento, legenda palavra a palavra e marca VEIL FREQUENCY.
Reaproveita tts.py, musica.py e render.py do Mente Secreta (raiz do repositório)."""
import json, os, sys, time, random, subprocess, urllib.parse, urllib.request
from PIL import Image, ImageFilter
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ESTILO = ('cinematic horror film still, 35mm photo, dim moody low-key lighting, desaturated cold tones, '
          'film grain, shallow depth of field, photorealistic, unsettling atmosphere, vertical composition, '
          'no text, no watermark, no blood, no gore')
UA = 'Mozilla/5.0 (VeilFrequencyBot/1.0; github.com/aupontocortes-tech)'


def gerar_imagem(prompt, seed, destino):
    """Pollinations: grátis e sem conta. Corta a marca d'água de baixo e entrega 1080x1920."""
    texto = f'{prompt}, {ESTILO}'
    url = ('https://image.pollinations.ai/prompt/' + urllib.parse.quote(texto) + '?' +
           urllib.parse.urlencode({'width': 768, 'height': 1344, 'seed': seed, 'nologo': 'true'}))
    for tent in range(20):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            dados = urllib.request.urlopen(req, timeout=100).read()
            im = Image.open(__import__('io').BytesIO(dados)).convert('RGB')
            if min(im.size) < 300:
                raise ValueError('imagem pequena')
            w, h = im.size
            im = im.crop((0, 0, w, int(h * 0.94)))               # remove a marca d'água no rodapé
            im = im.resize((1080, int(1080 * im.height / im.width)), Image.LANCZOS)
            if im.height < 1920:                                    # completa a altura sem distorcer
                im = im.resize((int(1920 * im.width / im.height), 1920), Image.LANCZOS)
                x = (im.width - 1080) // 2
                im = im.crop((x, 0, x + 1080, 1920))
            else:
                y = (im.height - 1920) // 2
                im = im.crop((0, y, 1080, y + 1920))
            im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
            im.save(destino, quality=94)
            return True
        except Exception as e:
            espera = 12 + 3 * min(tent, 6)
            print(f'  imagem falhou ({e}); nova tentativa em {espera}s')
            time.sleep(espera)
    return False


def main(caminho, out):
    os.makedirs(out, exist_ok=True)
    hist = json.load(open(caminho, encoding='utf-8'))
    base = random.Random(hist.get('titulo', '')).randint(1, 10**6)
    spec = {'scenes': [], 'pron': hist.get('pron', {})}
    for i, sc in enumerate(hist['scenes']):
        img = os.path.abspath(f'{out}/cena{i:02d}.jpg')
        if not os.path.exists(img):
            print(f'cena {i}: gerando imagem')
            if not gerar_imagem(sc['visual'], base + i, img):
                sys.exit(f'ERRO: não consegui gerar a imagem da cena {i}')
            time.sleep(3)
        spec['scenes'].append({'text': sc['text'], 'src': img, 'focus': 0.5, 'foco_y': 0.5,
                               'destaque': sc.get('destaque', []), 'pausa': sc.get('pausa', 0.3)})
    json.dump(spec, open(f'{out}/spec.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    env = dict(os.environ, MS_VOZ=os.environ.get('VF_VOZ', 'en-US-AndrewMultilingualNeural'),
               MS_RATE=os.environ.get('VF_RATE', '-4%'), MS_PITCH=os.environ.get('VF_PITCH', '-8Hz'),
               MS_MARCA='VEIL FREQUENCY')
    for cmd in (['tts.py', f'{out}/spec.json', out], ['musica.py', out], ['render.py', f'{out}/spec.json', out]):
        subprocess.run(['python3', os.path.join(RAIZ, cmd[0]), *cmd[1:]], check=True, env=env)
    print('OK', out + '/final.mp4')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'out')
