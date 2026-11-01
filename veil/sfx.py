"""Efeitos sonoros do Veil Frequency, gerados por código (100% originais, sem direitos autorais).
Uso: python3 veil/sfx.py out   (depois do musica.py; precisa de out/spec.json, out/timing.json e out/trilha.wav)
Mistura na trilha:
 - "ambiente" do roteiro (vento, chuva, grilos, rio, floresta) baixinho o vídeo todo;
 - "efeito" de cada cena (batida, arranhao, passos, grito, estalo, rangido, respiracao, pingo, telefone, sussurro,
   choro, chiado, freada, trovao, coracao, porta) no começo da cena;
 - "impacto": true -> pancada grave + silêncio da trilha na hora da virada."""
import sys, os, json
import numpy as np, soundfile as sf

SR = 48000
R = np.random.default_rng(7)

def t(d): return np.arange(int(d * SR)) / SR
def ruido(d): return R.standard_normal(int(d * SR)).astype(np.float32)
def banda(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x)).astype(np.float32)
def norm(x, g=1.0): return (x / (np.max(np.abs(x)) + 1e-9) * g).astype(np.float32)
def env(n, a, r):
    e = np.ones(n, np.float32); ai, ri = int(a * SR), int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e
def eco(x, atraso=0.09, g=0.45, n=5):
    y = np.concatenate([x, np.zeros(int(atraso * n * SR), np.float32)])
    for k in range(1, n + 1):
        s = int(atraso * k * SR); y[s:s + len(x)] += x * g ** k
    return y
def junta(partes):   # [(inicio_s, som)]
    fim = max(s + len(x) / SR for s, x in partes); y = np.zeros(int(fim * SR) + 1, np.float32)
    for s, x in partes: i = int(s * SR); y[i:i + len(x)] += x
    return y

def batida():
    um = lambda: norm(np.sin(2 * np.pi * 150 * t(0.25)) * np.exp(-t(0.25) * 30) + banda(ruido(0.25), 200, 2000) * np.exp(-t(0.25) * 60) * 0.6)
    return norm(eco(junta([(0, um()), (0.42, um()), (0.84, um())]), 0.06, 0.3, 3))
def arranhao():
    p = []
    for k in range(3):
        d = 0.5; x = banda(ruido(d), 1500, 6000) * (0.5 + 0.5 * np.sin(2 * np.pi * 38 * t(d))) * env(int(d * SR), 0.05, 0.15)
        p.append((k * 0.62, x))
    return norm(junta(p))
def passos():
    um = lambda: norm(np.sin(2 * np.pi * 65 * t(0.35)) * np.exp(-t(0.35) * 14) + banda(ruido(0.35), 80, 600) * np.exp(-t(0.35) * 25) * 0.7)
    return norm(junta([(k * 0.75, um()) for k in range(4)]))
def grito():
    d = 1.6; f = 520 + 280 * np.sin(np.linspace(0, np.pi, int(d * SR))) + 18 * np.sin(2 * np.pi * 6 * t(d))
    ph = 2 * np.pi * np.cumsum(f) / SR; x = (2 * (ph / (2 * np.pi) % 1) - 1).astype(np.float32)
    x = banda(x, 300, 2500) * env(int(d * SR), 0.15, 0.6)
    return norm(eco(x, 0.13, 0.5, 6))   # longe, com eco
def estalo():
    crack = banda(ruido(0.08), 1000, 9000) * np.exp(-t(0.08) * 50)
    ring = np.sin(2 * np.pi * 1180 * t(1.2)) * np.exp(-t(1.2) * 4) * 0.4
    queda = banda(ruido(0.9), 60, 400) * np.linspace(1, 0, int(0.9 * SR)) * 0.6
    return norm(junta([(0, crack), (0, ring), (0.1, queda)]))
def rangido():
    d = 1.4; f = 95 + 30 * np.sin(2 * np.pi * 1.3 * t(d)) + 8 * R.standard_normal(int(d * SR)).cumsum() / 400
    ph = 2 * np.pi * np.cumsum(f) / SR; x = (2 * (ph / (2 * np.pi) % 1) - 1).astype(np.float32)
    return norm(banda(x, 400, 3000) * env(int(d * SR), 0.1, 0.3))
def respiracao():
    um = lambda d: banda(ruido(d), 300, 1800) * np.sin(np.linspace(0, np.pi, int(d * SR))) ** 2
    return norm(junta([(0, um(1.1)), (1.3, um(1.4) * 0.8)]))
def pingo():
    um = lambda: np.sin(2 * np.pi * np.linspace(1400, 800, int(0.12 * SR)) * t(0.12)) * np.exp(-t(0.12) * 35)
    return norm(eco(junta([(0, um()), (0.9, um()), (1.8, um())]), 0.07, 0.35, 4))
def telefone():
    tom = (np.sin(2 * np.pi * 440 * t(0.4)) + np.sin(2 * np.pi * 480 * t(0.4))) * env(int(0.4 * SR), 0.01, 0.05)
    return norm(junta([(0, tom), (0.6, tom), (2.0, tom), (2.6, tom)]))
def sussurro():
    p = []
    for k in range(6):
        d = R.uniform(0.15, 0.3); p.append((k * 0.27, banda(ruido(d), 1800, 7000) * np.sin(np.linspace(0, np.pi, int(d * SR)))))
    return norm(eco(junta(p), 0.11, 0.4, 4))
def choro():
    p = []
    for k in range(3):
        d = 0.7; f = 330 - 60 * np.linspace(0, 1, int(d * SR)) + 10 * np.sin(2 * np.pi * 7 * t(d))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(int(d * SR), 0.08, 0.4); p.append((k * 0.95, x))
    return norm(eco(banda(junta(p), 200, 2000), 0.15, 0.5, 5))
def chiado(): return norm(banda(ruido(1.5), 2000, 9000) * (0.7 + 0.3 * np.sin(2 * np.pi * 9 * t(1.5))) * env(int(1.5 * SR), 0.05, 0.3))
def freada():
    d = 1.3; x = banda(ruido(d), 1500, 5000) * (1 + 0.6 * np.sin(2 * np.pi * 23 * t(d)))
    return norm(x * env(int(d * SR), 0.05, 0.4))
def trovao():
    d = 3.0; x = banda(ruido(d), 30, 300) * np.exp(-t(d) * 1.3) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t(d)))
    return norm(x)
def coracao():
    thump = np.sin(2 * np.pi * 52 * t(0.18)) * np.exp(-t(0.18) * 28)
    return norm(junta([(b * 0.85 + d, thump * g) for b in range(4) for d, g in ((0, 1), (0.22, 0.7))]))
def porta():   # porta batendo
    return norm(np.sin(2 * np.pi * 70 * t(0.5)) * np.exp(-t(0.5) * 9) + banda(ruido(0.5), 100, 3000) * np.exp(-t(0.5) * 20))
def impacto():
    d = 2.5; f = np.linspace(70, 28, int(d * SR)); boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t(d) * 1.6)
    hit = banda(ruido(0.3), 60, 4000) * np.exp(-t(0.3) * 15)
    return norm(junta([(0, boom), (0, hit * 0.8)]))

EFEITOS = dict(batida=batida, arranhao=arranhao, passos=passos, grito=grito, estalo=estalo, rangido=rangido,
               respiracao=respiracao, pingo=pingo, telefone=telefone, sussurro=sussurro, choro=choro, chiado=chiado,
               freada=freada, trovao=trovao, coracao=coracao, porta=porta)
VOL = dict(grito=0.22, choro=0.28, sussurro=0.25, respiracao=0.3, telefone=0.25, chiado=0.06, trovao=0.5)

def ambiente(tipo, n):
    d = n / SR; x = ruido(d)
    if tipo == 'vento': y = banda(x, 80, 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t(d)))
    elif tipo == 'chuva': y = banda(x, 1500, 9000)
    elif tipo == 'rio': y = banda(x, 200, 1500) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.3 * t(d)))
    elif tipo in ('grilos', 'floresta'):   # noite calma: vento leve (o grilo sintético soava como bipe)
        y = banda(x, 100, 500) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.08 * t(d)))
    else: return np.zeros(n, np.float32)
    y = norm(y); return np.pad(y, (0, max(0, n - len(y))))[:n]

def main():
    out = sys.argv[1]
    spec = json.load(open(os.path.join(out, 'spec.json'), encoding='utf-8'))
    T = json.load(open(os.path.join(out, 'timing.json'), encoding='utf-8'))
    y, sr = sf.read(os.path.join(out, 'trilha.wav'), dtype='float32')
    if y.ndim > 1: y = y.mean(axis=1)
    assert sr == SR, sr
    n = len(y)
    if spec.get('ambiente'): y += ambiente(spec['ambiente'], n) * 0.05 * env(n, 2, 2)
    for k, (sc, (s, e)) in enumerate(zip(spec['scenes'], T['segs'])):
        if k == 0: continue   # o gancho (1ª frase) fica limpo, só a voz e a trilha
        if sc.get('impacto'):   # silêncio na trilha + pancada logo antes da frase da virada
            i = int(max(0, s - 0.15) * SR); k = int(1.2 * SR)
            y[i:i + k] *= np.linspace(0.15, 1, len(y[i:i + k]))
            b = impacto() * 0.55; y[i:i + len(b)] += b[:max(0, n - i)]
        nome = sc.get('efeito')
        if nome in EFEITOS:
            fx = EFEITOS[nome]() * VOL.get(nome, 0.35)
            i = int(max(0, s - 0.1) * SR); y[i:i + len(fx)] += fx[:max(0, n - i)]
    sf.write(os.path.join(out, 'trilha.wav'), np.clip(y, -1, 1), SR)
    print('efeitos ok')

if __name__ == '__main__':
    main()
