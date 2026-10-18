"""Generate the test signals: 48 kHz mono float WAVs.

    impulse   one unit sample at 0.1 s, then silence
    sweep     exponential sine sweep 20 Hz – 20 kHz, -6 dBFS
    noise     white noise, -12 dBFS RMS, fixed seed
    bass_di   SYNTHETIC placeholder for a bass DI: additive plucked-string notes
              B0 E1 A1 D2 G2 C3. Replace with a real recording when available.
              (Karplus-Strong was tried first: SC's Pitch does not lock onto it.)

Every signal is preceded by 100 ms of silence: scsynth computes one sample in each
UGen constructor, so a signal starting at full level would be processed twice at
sample 0 and the comparison would measure that start-up artifact.

Run: .venv/bin/python signals/make_signals.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000
PREROLL = int(0.1 * SR)
HERE = Path(__file__).parent


def impulse(dur=1.0):
    x = np.zeros(int(dur * SR))
    x[int(0.1 * SR)] = 1.0
    return x


def sweep(dur=5.0, f0=20.0, f1=20000.0, level_db=-6.0):
    t = np.arange(int(dur * SR)) / SR
    k = np.log(f1 / f0)
    x = np.sin(2 * np.pi * f0 * dur / k * (np.exp(t / dur * k) - 1))
    fade = int(0.01 * SR)
    ramp = np.linspace(0, 1, fade)
    x[:fade] *= ramp
    x[-fade:] *= ramp[::-1]
    return x * 10 ** (level_db / 20)


def noise(dur=3.0, level_db=-12.0):
    x = np.random.default_rng(1).standard_normal(int(dur * SR))
    return x * 10 ** (level_db / 20)


def pluck(freq, dur, rng, position=0.2, inharmonicity=1e-4):
    """Additive plucked string: 1/k partials, comb from the pluck position,
    higher partials decaying faster, slight stiffness inharmonicity."""
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    k = 1
    while (fk := k * freq * np.sqrt(1 + inharmonicity * k * k)) < 5000:
        amp = abs(np.sin(np.pi * k * position)) / k
        tau = 1.2 / (1 + 0.3 * (k - 1))
        x += amp * np.exp(-t / tau) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 2 * np.pi))
        k += 1
    attack = np.minimum(t / 0.003, 1)
    return x * attack


def bass_di(note_dur=1.0, level_db=-6.0):
    rng = np.random.default_rng(2)
    midi = [23, 28, 33, 38, 43, 48]  # B0 E1 A1 D2 G2 C3
    x = np.concatenate([pluck(440 * 2 ** ((m - 69) / 12), note_dur, rng) for m in midi])
    return x / np.max(np.abs(x)) * 10 ** (level_db / 20)


if __name__ == "__main__":
    for name, fn in [("impulse", impulse), ("sweep", sweep), ("noise", noise), ("bass_di", bass_di)]:
        x = np.concatenate([np.zeros(PREROLL), fn()])
        sf.write(HERE / f"{name}.wav", x.astype(np.float32), SR, subtype="FLOAT")
        print(f"signals/{name}.wav")
