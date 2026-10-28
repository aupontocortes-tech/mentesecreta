"""Narrador do Veil com a VOZ DO THIAGO clonada (Chatterbox, licença MIT, roda no processador).
Uso: python3 veil/voz_clone.py out/spec.json out
- A gravação dele fica CRIPTOGRAFADA em veil/voz/narrador.enc; a senha vem do Secret VF_VOZ_CHAVE.
- Gera out/clone_NN.wav para cada cena com "clone": true. O tts.py usa esses arquivos no lugar da voz padrão.
- Se faltar a senha ou der erro, sai sem gerar nada (o vídeo sai com a voz padrão)."""
import os, sys, json, subprocess, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))

def main(spec_path, out):
    chave = os.environ.get('VF_VOZ_CHAVE', '').strip()
    if not chave:
        print('voz clonada: sem VF_VOZ_CHAVE, usando voz padrão'); return
    spec = json.load(open(spec_path, encoding='utf-8'))
    alvo = [(i, sc['text']) for i, sc in enumerate(spec['scenes']) if sc.get('clone')]
    if not alvo:
        return
    tmp = tempfile.mkdtemp()
    ref_opus, ref_wav = os.path.join(tmp, 'r.opus'), os.path.join(tmp, 'r.wav')
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write(chave); senha = f.name
    try:
        subprocess.run(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-iter', '200000', '-in',
                        os.path.join(AQUI, 'voz', 'narrador.enc'), '-out', ref_opus, '-pass', f'file:{senha}'], check=True)
    finally:
        os.remove(senha)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', ref_opus, '-ac', '1', '-ar', '24000', ref_wav], check=True)
    import torch, torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    torch.manual_seed(7)
    m = ChatterboxTTS.from_pretrained(device='cpu')
    m.prepare_conditionals(ref_wav, exaggeration=0.45)   # aprende a voz 1 vez só (mais rápido)
    for i, texto in alvo:
        w = m.generate(texto, exaggeration=0.45, cfg_weight=0.4, temperature=0.7)
        ta.save(os.path.join(out, f'clone_{i:02d}.wav'), w, m.sr)
        print(f'voz clonada: cena {i} ok', flush=True)
    for f in (ref_opus, ref_wav):
        os.remove(f)

if __name__ == '__main__':
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:   # nunca derruba o vídeo: cai na voz padrão
        print('voz clonada falhou, usando voz padrão:', e)
        for f in os.listdir(sys.argv[2]):
            if f.startswith('clone_'): os.remove(os.path.join(sys.argv[2], f))
