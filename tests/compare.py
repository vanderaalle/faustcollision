"""Fidelity metrics, scsynth render (ref) vs Faust render (test). Lower is better.

waveform    RMS(ref - test) / RMS(ref), RMS floored at -80 dBFS. Sample-exact ports.
envelope    10 ms RMS envelopes, mean |dB difference| over frames above -60 dBFS.
spectrum    STFT (4096/1024) in 1/3-octave bands, mean |dB difference| over cells within
            60 dB of the reference maximum. Phase-insensitive, time-resolved.
statistics  long-term (Welch) spectrum in 1/3-octave bands, mean |dB difference| within
            60 dB of the reference maximum; at least the level difference of the total
            power in those bands (31 Hz – 16 kHz): below them, the mean and slowest parts of
            1/f-type noise over a few seconds are mostly chance.
            For noise UGens and trackers, where only distributions can agree.
distribution  Kolmogorov-Smirnov distance between the sample-value distributions (0..1).
            For values drawn once (Rand, IRand, ...): a case cycles many instances through
            one channel, so its sample values are the draws.
"""
import numpy as np
from scipy import signal

SR = 48000
SILENT = 1e-5  # both renders below this peak: nothing to compare
# The first block is the constructor transient: scsynth's K2A (and an ar BinaryOp) ramps
# its first block from the kr source's constructor output, which the port does not
# model (docs/sc-findings.md #13). Comparisons start at the second block.
SKIP = 64
BANDS = 1000 * 2.0 ** (np.arange(-15, 15) / 3)  # 1/3-octave centres, ~31 Hz – 16 kHz


def _db(p, floor=1e-12):
    return 10 * np.log10(np.maximum(p, floor))


def _band_power(freqs, power):
    """Sum power (last axis over freqs) into 1/3-octave bands."""
    lo, hi = BANDS * 2 ** (-1 / 6), BANDS * 2 ** (1 / 6)
    return np.stack([power[..., (freqs >= l) & (freqs < h)].sum(axis=-1) for l, h in zip(lo, hi)], axis=-1)


def _masked_mean(ref_db, test_db, span=60.0):
    floor = ref_db.max() - span
    mask = (ref_db > floor) | (test_db > floor)
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs(np.maximum(ref_db, floor) - np.maximum(test_db, floor))[mask]))


def waveform(ref, test):
    rms = np.sqrt(np.mean(ref ** 2))
    return float(np.sqrt(np.mean((ref - test) ** 2)) / max(rms, 1e-4))


def envelope(ref, test, frame=480):
    n = len(ref) // frame * frame
    env = [_db(np.mean(x[:n].reshape(-1, frame) ** 2, axis=1)) for x in (ref, test)]
    mask = (env[0] > -60) | (env[1] > -60)
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs(np.maximum(env[0], -80) - np.maximum(env[1], -80))[mask]))


def spectrum(ref, test):
    bands = []
    for x in (ref, test):
        f, _, z = signal.stft(x, SR, nperseg=4096, noverlap=3072)
        bands.append(_db(_band_power(f, np.abs(z.T) ** 2)))
    return _masked_mean(*bands)


def statistics(ref, test):
    bands, totals = [], []
    for x in (ref, test):
        f, p = signal.welch(x, SR, nperseg=8192)
        b = _band_power(f, p)
        bands.append(_db(b))
        totals.append(_db(b.sum()))
    level = abs(totals[0] - totals[1])
    return max(_masked_mean(*bands), float(level))


def distribution(ref, test):
    from scipy.stats import ks_2samp
    return float(ks_2samp(ref, test).statistic)


METRICS = {"waveform": waveform, "envelope": envelope, "spectrum": spectrum, "statistics": statistics,
           "distribution": distribution}


def score(mode, ref, test):
    """Per-channel score, worst channel wins. Inputs are (samples, channels).
    NaN or inf at the same sample in both renders count as agreement (scsynth's
    log of a negative input is NaN, and so is the port's); in one render only, inf."""
    n = min(len(ref), len(test))
    ref, test = ref[SKIP:n].astype(np.float64), test[SKIP:n].astype(np.float64)
    bad_r, bad_t = ~np.isfinite(ref), ~np.isfinite(test)
    same = (bad_r & bad_t) & ((np.isnan(ref) & np.isnan(test)) | (ref == test))
    if ((bad_r | bad_t) & ~same).any():
        return float("inf")
    ref, test = np.where(same, 0.0, ref), np.where(same, 0.0, test)
    worst = 0.0
    for c in range(ref.shape[1]):
        r, t = ref[:, c], test[:, c]
        if max(np.abs(r).max(), np.abs(t).max()) < SILENT:
            continue
        worst = max(worst, METRICS[mode](r, t))
    return worst
