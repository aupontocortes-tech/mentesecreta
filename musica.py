"""Trilha escura + efeitos gerados por código (100% original, sem direitos autorais).
Uso: python3 musica.py out  (precisa de out/timing.json) -> out/trilha.wav"""
import sys, os, json
import numpy as np, soundfile as sf

SR = 48000

def env_adsr(n, a, r):
    e = np.ones(n, np.float32); ai = int(a * SR); ri = int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e

def lowpass(x, k):
    """Passa-baixa simples (média móvel repetida)."""
    ker = np.ones(k, np.float32) / k
    for _ in range(3): x = np.convolve(x, ker, mode='same')
    return x

def trilha(dur, seed):
    rng = np.random.default_rng(seed); n = int(dur * SR); t = np.arange(n) / SR
    raiz = rng.choice([55.0, 58.27, 61.74, 49.0])  # A1, A#1, B1, G1
    # drone grave com batimento lento
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    drone = (np.sin(2 * np.pi * raiz * t) + 0.6 * np.sin(2 * np.pi * raiz * 1.5 * t + 1) +
             0.4 * np.sin(2 * np.pi * (raiz * 2 + 0.3) * t)) * lfo
    # "vento" escuro
    ar = lowpass(rng.standard_normal(n).astype(np.float32), 60) * 3
    # notas de piano menor, espaçadas
    pi = np.zeros(n, np.float32); escala = [0, 3, 7, 10, 12, 15]
    p = 1.5
    while p < dur - 2:
        f = raiz * 4 * 2 ** (rng.choice(escala) / 12); m = int(min(4, dur - p) * SR)
        tt = np.arange(m) / SR
        nota = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2 * tt)) * np.exp(-tt * 1.4)
        s = int(p * SR); pi[s:s + m] += nota[:n - s] * 0.5
        p += rng.uniform(2.2, 3.8)
    y = 0.35 * drone + 0.25 * ar + 0.45 * pi
    y *= env_adsr(n, 1.5, 2.5)
    return y / (np.max(np.abs(y)) + 1e-9)

def whoosh(dur=0.6):
    n = int(dur * SR); x = np.random.default_rng(1).standard_normal(n).astype(np.float32)
    x = lowpass(x, 12) * np.sin(np.linspace(0, np.pi, n)) ** 2
    return x / np.max(np.abs(x))

def batida(n_batidas=3):
    """Batida de coração (tum-tum)."""
    um = int(0.9 * SR); y = np.zeros(um * n_batidas, np.float32); tt = np.arange(int(0.18 * SR)) / SR
    thump = np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 28)
    for b in range(n_batidas):
        for d, g in ((0, 1.0), (0.22, 0.7)):
            s = b * um + int(d * SR); y[s:s + len(thump)] += thump * g
    return y / np.max(np.abs(y))

def main():
    out = sys.argv[1]; T = json.load(open(os.path.join(out, 'timing.json')))
    dur = T['dur']; n = int(dur * SR)
    seed = int(os.environ.get('MS_SEED', '0')) or int(dur * 1000)
    y = trilha(dur, seed) * 0.16
    w = whoosh() * 0.10
    for s, _ in T['segs'][1:]:
        i = max(0, int((s - 0.45) * SR)); y[i:i + len(w)] += w[:max(0, n - i)]
    b = batida() * 0.5; s = T['segs'][-1][0]; i = int(max(0, s - 0.3) * SR)
    y[i:i + len(b)] += b[:max(0, n - i)]
    sf.write(os.path.join(out, 'trilha.wav'), np.clip(y, -1, 1), SR)
    print('trilha ok')

if __name__ == '__main__':
    main()
