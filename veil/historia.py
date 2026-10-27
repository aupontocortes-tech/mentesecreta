"""Veil Frequency — uma história de terror completa por vídeo.

python3 veil/historia.py veil/historias/fila/NN_slug.json out
Gera out/final.mp4.

Passos: imagem de IA por cena (Cloudflare FLUX; reserva: Pollinations) -> voz em inglês (Edge TTS, narrador grave)
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
# Vozes (Edge TTS, grátis). A história escolhe o narrador ("narrador": "mulher" ou "homem")
# e cada fala pode ter a sua ("voz": "idosa", "crianca", "sombria"...).
VOZES = {   # vozes naturais: sem mexer muito no tom (tom forçado deixa a voz com cara de robô)
    'homem':   ('en-US-AndrewMultilingualNeural', '-2%', '+0Hz'),
    'mulher':  ('en-US-AvaMultilingualNeural', '-2%', '+0Hz'),
    'crianca': ('en-US-AnaNeural', '-4%', '+0Hz'),
    'idosa':   ('en-US-JennyNeural', '-8%', '-6Hz'),
    'idoso':   ('en-US-GuyNeural', '-8%', '-6Hz'),
    'sombria': ('en-US-JennyNeural', '-18%', '-20Hz'),
    'sombrio': ('en-US-GuyNeural', '-18%', '-20Hz'),
}
VOZES_PT = {   # versão dublada em português (vídeo não listado, só para o Thiago conferir)
    'homem':   ('pt-BR-AntonioNeural', '+0%', '-4Hz'),
    'mulher':  ('pt-BR-ThalitaMultilingualNeural', '+0%', '+0Hz'),
    'crianca': ('pt-BR-FranciscaNeural', '-2%', '+12Hz'),
    'idosa':   ('pt-BR-FranciscaNeural', '-8%', '-6Hz'),
    'idoso':   ('pt-BR-AntonioNeural', '-8%', '-8Hz'),
    'sombria': ('pt-BR-FranciscaNeural', '-16%', '-18Hz'),
    'sombrio': ('pt-BR-AntonioNeural', '-16%', '-18Hz'),
}
UA = 'Mozilla/5.0 (VeilFrequencyBot/1.0; github.com/aupontocortes-tech)'


def _ajustar(im, destino, cortar_marca):
    """Entrega 1080x1920 sem distorcer (corta as sobras do centro)."""
    im = im.convert('RGB')
    if min(im.size) < 300:
        raise ValueError('imagem pequena')
    w, h = im.size
    if cortar_marca:
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


def _cloudflare(texto, seed, destino):
    """Cloudflare Workers AI (FLUX schnell): grátis até ~150 imagens/dia. Precisa dos Secrets CF_API_TOKEN e CF_ACCOUNT_ID."""
    import re
    tok = os.environ.get('CF_API_TOKEN', '')
    tok = tok.replace('Authorization:', ' ').replace('Bearer', ' ').replace('"', ' ').replace("'", ' ')
    tok = max(tok.split(), key=len, default='')                     # aceita a chave colada com sobras
    m = re.search(r'[0-9a-f]{32}', os.environ.get('CF_ACCOUNT_ID', ''))  # aceita o link inteiro do painel
    conta = m.group(0) if m else ''
    if not (tok and conta):
        return False
    import base64, io
    url = f'https://api.cloudflare.com/client/v4/accounts/{conta}/ai/run/@cf/black-forest-labs/flux-1-schnell'
    corpo = json.dumps({'prompt': texto + ', centered subject, vertical framing', 'steps': 6, 'seed': seed % 2**31}).encode()
    for tent in range(3):
        try:
            req = urllib.request.Request(url, data=corpo, headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=120).read())
            img = base64.b64decode(d['result']['image'])
            return _ajustar(Image.open(io.BytesIO(img)), destino, False)
        except Exception as e:
            msg = getattr(e, 'read', lambda: b'')()[:200]
            print(f'  cloudflare falhou ({e} {msg}); nova tentativa em 10s')
            time.sleep(10)
    return False


def gerar_imagem(prompt, seed, destino):
    """1º Cloudflare (melhor qualidade); se não tiver chave ou falhar, Pollinations (grátis, sem conta)."""
    texto = f'{prompt}, {ESTILO}'
    if _cloudflare(texto, seed, destino):
        return 'cf'
    url = ('https://image.pollinations.ai/prompt/' + urllib.parse.quote(texto) + '?' +
           urllib.parse.urlencode({'width': 768, 'height': 1344, 'seed': seed, 'nologo': 'true'}))
    for tent in range(20):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            dados = urllib.request.urlopen(req, timeout=100).read()
            return _ajustar(Image.open(__import__('io').BytesIO(dados)), destino, True)
        except Exception as e:
            espera = 47 if '402' in str(e) else 12 + 3 * min(tent, 6)   # 402 = limite grátis (1 imagem a cada 45 s)
            print(f'  imagem falhou ({e}); nova tentativa em {espera}s')
            time.sleep(espera)
    return False

def destaque_pt(texto):
    # palavra mais longa da frase em português (fica vermelha na legenda)
    ps = [w.strip('.,!?;:"“”…—-').upper() for w in texto.split()]
    ps = [w for w in ps if len(w) > 3]
    return [max(ps, key=len)] if ps else []


def main(caminho, out, lingua='en'):
    pt = lingua == 'pt'
    imgs = out                      # as imagens ficam em out/ e são as mesmas nas duas versões
    if pt:
        out = os.path.join(out, 'pt')
    os.makedirs(out, exist_ok=True)
    hist = json.load(open(caminho, encoding='utf-8'))
    base = random.Random(hist.get('titulo', '')).randint(1, 10**6)
    spec = {'scenes': [], 'pron': {} if pt else hist.get('pron', {})}
    narr = hist.get('narrador', 'homem')
    img = None
    for i, sc in enumerate(hist['scenes']):
        if sc.get('mesma_imagem') and img:   # fala curta que continua na imagem anterior
            pass
        else:
            img = os.path.abspath(f'{imgs}/cena{i:02d}.jpg')
        if not os.path.exists(img):
            print(f'cena {i}: gerando imagem')
            fonte = gerar_imagem(sc['visual'], base + i, img)
            if not fonte:
                sys.exit(f'ERRO: não consegui gerar a imagem da cena {i}')
            if fonte != 'cf':
                time.sleep(46)   # Pollinations grátis: 1 imagem a cada 45 s
        tabela = VOZES_PT if pt else VOZES
        voz, rate, pitch = tabela.get(sc.get('voz') or narr, tabela['homem'])
        texto = (sc.get('pt') or sc['text']) if pt else sc['text']
        dest = (sc.get('destaque_pt') or destaque_pt(texto)) if pt else sc.get('destaque', [])
        spec['scenes'].append({'text': texto, 'src': img, 'focus': 0.5, 'foco_y': 0.5,
                               'destaque': dest, 'pausa': sc.get('pausa', 0.3),
                               'voz_edge': voz, 'rate': rate, 'pitch': pitch})
    json.dump(spec, open(f'{out}/spec.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    env = dict(os.environ, MS_VOZ=os.environ.get('VF_VOZ', 'en-US-AndrewMultilingualNeural'),
               MS_RATE=os.environ.get('VF_RATE', '-2%'), MS_PITCH=os.environ.get('VF_PITCH', '+0Hz'),
               MS_MARCA='VEIL FREQUENCY', MS_SEED=str(base))   # mesma trilha nas duas versões
    for cmd in (['tts.py', f'{out}/spec.json', out], ['musica.py', out], ['render.py', f'{out}/spec.json', out]):
        subprocess.run(['python3', os.path.join(RAIZ, cmd[0]), *cmd[1:]], check=True, env=env)
    print('OK', out + '/final.mp4')


if __name__ == '__main__':
    # python3 veil/historia.py historia.json out [en|pt]   (pt usa as imagens já geradas e cria out/pt/final.mp4)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'out', sys.argv[3] if len(sys.argv) > 3 else 'en')
