"""Short interface sounds, synthesised. Each skin gets open, move, launch and close."""
import numpy as np

RATE = 24000
TAU = 2 * np.pi


def t_(sec):
    return np.arange(int(sec * RATE)) / RATE


def env(t, attack, decay):
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-np.maximum(0, t - attack) / decay)


def sine(t, f, f1=None):
    f1 = f if f1 is None else f1
    ph = np.cumsum(f + (f1 - f) * (t / max(t[-1], 1e-6))) / RATE
    return np.sin(TAU * ph)


def noise(t, seed=1):
    return np.random.default_rng(seed).standard_normal(len(t))


def low(x, fc):
    a = np.exp(-TAU * fc / RATE)
    y = np.empty_like(x)
    s = 0.0
    for i, v in enumerate(x):
        s = a * s + (1 - a) * v
        y[i] = s
    return y


def high(x, fc):
    return x - low(x, fc)


def band(x, f0, f1):
    return low(high(x, f0), f1)


def square(t, f, f1=None, duty=0.5):
    f1 = f if f1 is None else f1
    ph = np.cumsum(f + (f1 - f) * (t / max(t[-1], 1e-6))) / RATE
    return np.where((ph % 1) < duty, 1.0, -1.0)


def tri(t, f):
    return 2 * np.abs(2 * ((t * f) % 1) - 1) - 1


def ring(t, parts, decay):
    """Struck metal or glass: inharmonic partials."""
    out = 0
    for k, (f, a) in enumerate(parts):
        out = out + a * np.sin(TAU * f * t + k) * np.exp(-t / (decay / (1 + 0.5 * k)))
    return out


def mixat(total, items):
    out = np.zeros(int(total * RATE))
    for at, x in items:
        i = int(at * RATE)
        n = min(len(x), len(out) - i)
        if n > 0:
            out[i:i + n] += x[:n]
    return out


def fade(x, n=0.004):
    k = int(n * RATE)
    x = x.copy()
    x[-k:] *= np.linspace(1, 0, k)
    return x


def norm(x, peak=0.8):
    return fade(x * (peak / max(1e-6, np.abs(x).max())))


def click(seed, f=2600, q=0.004):
    t = t_(0.03)
    return band(noise(t, seed), f * 0.6, f * 1.7) * env(t, 0.0004, q) + 0.4 * np.sin(TAU * f * t) * env(t, 0.0003, q * 0.8)


def make(kind):
    if kind == 'clockwork':
        tick = click(3, 3100, 0.0035)
        clunk = click(5, 900, 0.010)
        t = t_(0.42)
        hiss = high(noise(t, 9), 2200) * env(t, 0.03, 0.10)
        bell = ring(t_(0.42), [(1180, 0.6), (2630, 0.35), (4100, 0.2)], 0.14)
        wind = mixat(0.30, [(0.030 * i, tick * (0.5 + 0.05 * i)) for i in range(8)] + [(0.245, clunk * 1.2)])
        return {'open': norm(wind, 0.7), 'move': norm(tick, 0.5), 'launch': norm(mixat(0.42, [(0, clunk), (0.03, hiss * 0.5), (0.02, bell * 0.35)]), 0.8),
                'close': norm(mixat(0.14, [(0, clunk * 0.8), (0.05, tick * 0.6), (0.08, tick * 0.4)]), 0.5)}
    if kind == 'vinyl':
        t = t_(0.26)
        thump = np.sin(TAU * 70 * t) * env(t, 0.004, 0.06)
        crack = (np.random.default_rng(4).random(len(t)) > 0.994) * noise(t, 5) * 0.8
        needle = band(noise(t, 6), 300, 3000) * env(t, 0.01, 0.06)
        s = t_(0.05)
        mv = band(noise(s, 8), 900, 4200) * env(s, 0.008, 0.010)
        l = t_(0.36)
        scratch = band(noise(l, 10), 500, 5200) * np.abs(np.sin(TAU * 4.2 * l)) * env(l, 0.02, 0.16)
        return {'open': norm(thump * 0.9 + crack * 0.5 + needle * 0.4, 0.7), 'move': norm(mv, 0.35), 'launch': norm(scratch + mixat(0.36, [(0.17, np.sin(TAU * 62 * t) * env(t, 0.004, 0.07))]), 0.7),
                'close': norm(needle[:3600] * np.linspace(1, 0, 3600), 0.4)}
    if kind == 'reactor':
        t = t_(0.40)
        rise = sine(t, 90, 420) * env(t, 0.12, 0.14) + 0.4 * sine(t, 180, 840) * env(t, 0.14, 0.10) + 0.15 * band(noise(t, 2), 800, 3000) * env(t, 0.10, 0.08)
        s = t_(0.05)
        mv = sine(s, 1500, 1100) * env(s, 0.002, 0.012) + 0.4 * sine(s, 3000, 2200) * env(s, 0.001, 0.006)
        l = t_(0.45)
        zap = sine(l, 900, 160) * env(l, 0.004, 0.10) + 0.5 * sine(l, 1350, 240) * env(l, 0.004, 0.08) + 0.25 * low(noise(l, 4), 900) * env(l, 0.01, 0.12)
        c = t_(0.24)
        return {'open': norm(rise, 0.7), 'move': norm(mv, 0.35), 'launch': norm(zap, 0.75), 'close': norm(sine(c, 420, 90) * env(c, 0.01, 0.07), 0.5)}
    if kind == 'stone':
        t = t_(0.34)
        grind = low(noise(t, 3), 420) * (0.6 + 0.4 * np.sin(TAU * 23 * t)) * env(t, 0.06, 0.12)
        thud = np.sin(TAU * 58 * t) * env(t, 0.003, 0.07)
        s = t_(0.06)
        mv = band(noise(s, 4), 300, 1500) * env(s, 0.001, 0.012)
        l = t_(0.60)
        chime = ring(l, [(523, 0.5), (784, 0.4), (1175, 0.25), (1568, 0.2)], 0.30)
        return {'open': norm(grind * 1.6 + mixat(0.34, [(0.2, thud)]), 0.75), 'move': norm(mv, 0.45), 'launch': norm(mixat(0.6, [(0, thud), (0.02, chime * 0.5)]), 0.7), 'close': norm(grind[:4800] * np.linspace(1, 0, 4800), 0.5)}
    if kind == 'water':
        def drop(f, d=0.10):
            t = t_(0.22)
            return np.sin(TAU * np.cumsum(f * (1 + 1.2 * (1 - np.exp(-t / 0.03)))) / RATE) * env(t, 0.004, d * 0.35)
        l = t_(0.5)
        splash = band(noise(l, 5), 600, 4000) * env(l, 0.02, 0.10)
        return {'open': norm(mixat(0.45, [(0, drop(420)), (0.09, drop(560) * 0.7), (0.20, drop(700) * 0.5)]), 0.6), 'move': norm(drop(760, 0.06)[:2600], 0.35),
                'launch': norm(mixat(0.5, [(0, splash * 0.5), (0.03, drop(380)), (0.12, drop(620) * 0.6), (0.2, drop(900) * 0.35)]), 0.65), 'close': norm(drop(330)[:4000], 0.45)}
    if kind == 'pixel':
        def bl(f, d, duty=0.5):
            t = t_(d)
            return square(t, f, None, duty) * np.exp(-t / (d * 0.6))
        return {'open': norm(np.concatenate([bl(392, 0.05), bl(523, 0.05), bl(784, 0.10)]), 0.4), 'move': norm(bl(660, 0.030, 0.25), 0.28),
                'launch': norm(np.concatenate([bl(988, 0.06), bl(1319, 0.22, 0.25)]), 0.4), 'close': norm(np.concatenate([bl(523, 0.04), bl(330, 0.07)]), 0.35)}
    if kind == 'neon':
        t = t_(0.40)
        hum = (np.sin(TAU * 100 * t) + 0.6 * np.sin(TAU * 200 * t) + 0.4 * np.sin(TAU * 300 * t)) * env(t, 0.02, 0.16)
        gate = np.ones(len(t))
        for a, b in ((0.03, 0.05), (0.08, 0.13), (0.17, 0.19)):
            gate[int(a * RATE):int(b * RATE)] = 0.1
        buzz = (hum * 0.6 + 0.4 * band(noise(t, 4), 1500, 5000) * env(t, 0.01, 0.08)) * gate
        s = t_(0.04)
        mv = band(noise(s, 6), 2500, 7000) * env(s, 0.0006, 0.008)
        l = t_(0.34)
        return {'open': norm(buzz, 0.55), 'move': norm(mv, 0.3), 'launch': norm(band(noise(l, 7), 1200, 6000) * env(l, 0.002, 0.05) + 0.5 * ring(l, [(1760, 0.5), (2637, 0.4)], 0.15), 0.6),
                'close': norm(band(noise(t_(0.12), 9), 1000, 5000) * env(t_(0.12), 0.002, 0.025), 0.4)}
    if kind == 'page':
        t = t_(0.40)
        rustle = band(noise(t, 3), 1200, 5500) * (0.3 + 0.7 * np.abs(np.sin(TAU * 5 * t))) * env(t, 0.05, 0.14)
        l = t_(0.7)
        magic = sum(ring(t_(0.5), [(f, 0.5), (f * 2.01, 0.2)], 0.18) * a for f, a in ((880, 0.5),))
        arp = mixat(0.7, [(0.05 * i, ring(t_(0.4), [(f, 0.5), (f * 2.7, 0.12)], 0.16)) for i, f in enumerate((659, 880, 1109, 1319))])
        s = t_(0.05)
        return {'open': norm(rustle, 0.6), 'move': norm(band(noise(s, 6), 1500, 5000) * env(s, 0.006, 0.010), 0.3), 'launch': norm(arp, 0.6), 'close': norm(rustle[:5000] * np.linspace(1, 0, 5000), 0.45)}
    if kind == 'watch':
        tick = click(11, 4300, 0.0025)
        l = t_(0.5)
        chime = ring(l, [(2093, 0.5), (4186, 0.2), (3136, 0.25)], 0.22)
        return {'open': norm(mixat(0.22, [(0.026 * i, tick * (0.35 + 0.08 * i)) for i in range(7)]), 0.5), 'move': norm(tick, 0.38), 'launch': norm(mixat(0.5, [(0, tick), (0.01, chime * 0.6)]), 0.6),
                'close': norm(mixat(0.1, [(0, tick), (0.04, tick * 0.7)]), 0.4)}
    if kind == 'comic':
        t = t_(0.22)
        boing = sine(t, 240, 620) * env(t, 0.005, 0.08) * (1 + 0.5 * np.sin(TAU * 26 * t))
        s = t_(0.05)
        pop = sine(s, 900, 300) * env(s, 0.001, 0.012)
        l = t_(0.4)
        pow_ = low(noise(l, 5), 1500) * env(l, 0.002, 0.07) + 0.9 * sine(l, 180, 50) * env(l, 0.002, 0.09)
        return {'open': norm(boing, 0.55), 'move': norm(pop, 0.4), 'launch': norm(pow_, 0.8), 'close': norm(sine(t, 520, 200) * env(t, 0.004, 0.05), 0.45)}
    if kind == 'vault':
        clunk = click(5, 520, 0.018)
        tick = click(3, 2300, 0.003)
        l = t_(0.7)
        boom = np.sin(TAU * 46 * l) * env(l, 0.004, 0.16) + 0.5 * low(noise(l, 8), 300) * env(l, 0.004, 0.14)
        bolt = ring(l, [(310, 0.5), (517, 0.4), (873, 0.3), (1420, 0.2)], 0.12)
        return {'open': norm(mixat(0.42, [(0.045 * i, tick * 0.6) for i in range(5)] + [(0.25, clunk)]), 0.7), 'move': norm(tick, 0.4), 'launch': norm(mixat(0.7, [(0, clunk), (0.02, bolt * 0.6), (0.06, boom * 0.8)]), 0.8),
                'close': norm(mixat(0.2, [(0, clunk * 0.9)]), 0.5)}
    if kind == 'glass':
        t = t_(0.6)
        chord = mixat(0.6, [(0.04 * i, ring(t_(0.5), [(f, 0.5), (f * 2.76, 0.16), (f * 5.4, 0.06)], 0.22)) for i, f in enumerate((1047, 1319, 1568))])
        s = t_(0.12)
        mv = ring(s, [(2093, 0.5), (5772, 0.15)], 0.03)
        return {'open': norm(chord, 0.5), 'move': norm(mv, 0.28), 'launch': norm(mixat(0.6, [(0, ring(t, [(1568, 0.5), (4327, 0.2)], 0.25)), (0.06, ring(t_(0.5), [(2093, 0.5), (5772, 0.15)], 0.25))]), 0.55),
                'close': norm(ring(t_(0.25), [(784, 0.5), (2163, 0.2)], 0.08), 0.4)}
    if kind == 'term':
        def bp(f, d):
            t = t_(d)
            return (np.sin(TAU * f * t) + 0.3 * np.sin(TAU * 2 * f * t)) * np.minimum(1, (d - t) / 0.01)
        key = click(21, 3500, 0.003) + 0.0
        return {'open': norm(np.concatenate([bp(880, 0.05), np.zeros(600), bp(1175, 0.07)]), 0.35), 'move': norm(key, 0.35), 'launch': norm(np.concatenate([bp(1175, 0.05), bp(1568, 0.10)]), 0.35), 'close': norm(bp(660, 0.06), 0.3)}
    if kind == 'paper':
        def flick(seed, d, f0, f1):
            t = t_(d)
            return band(noise(t, seed), f0, f1) * env(t, d * 0.12, d * 0.22)
        l = t_(0.45)
        chime = mixat(0.45, [(0.05 * i, ring(t_(0.35), [(f, 0.5), (f * 3.0, 0.10)], 0.10)) for i, f in enumerate((784, 988, 1175))])
        return {'open': norm(mixat(0.30, [(0.045 * i, flick(3 + i, 0.09, 900, 5200) * (0.6 + 0.1 * i)) for i in range(4)]), 0.5), 'move': norm(flick(9, 0.05, 1600, 6000), 0.28),
                'launch': norm(mixat(0.45, [(0, flick(11, 0.16, 900, 5000)), (0.04, chime * 0.7)]), 0.55), 'close': norm(flick(13, 0.10, 800, 4200), 0.38)}
    if kind == 'wood':
        def knock(f):
            t = t_(0.12)
            return ring(t, [(f, 0.7), (f * 2.3, 0.3), (f * 3.9, 0.15)], 0.025) + 0.3 * band(noise(t, 3), 500, 3000) * env(t, 0.0005, 0.006)
        return {'open': norm(mixat(0.3, [(0, knock(240)), (0.07, knock(300)), (0.14, knock(360))]), 0.6), 'move': norm(knock(520), 0.38), 'launch': norm(mixat(0.35, [(0, knock(200)), (0.05, knock(400)), (0.1, knock(600))]), 0.65),
                'close': norm(knock(180), 0.5)}
    if kind == 'casino':
        t = t_(0.5)
        def clack(f, a=1.0):
            q = t_(0.04)
            return a * (ring(q, [(f, 0.6), (f * 2.4, 0.3), (f * 4.1, 0.12)], 0.010) + 0.4 * band(noise(q, int(f)), 1500, 6000) * env(q, 0.0004, 0.004))
        roll = low(noise(t, 4), 700) * (0.5 + 0.5 * np.sin(TAU * 34 * t)) * env(t, 0.04, 0.16) * 0.6
        hops = mixat(0.5, [(0.02, clack(1500)), (0.10, clack(1720, 0.8)), (0.165, clack(1430, 0.65)), (0.215, clack(1630, 0.5)), (0.25, clack(1520, 0.4)), (0.275, clack(1580, 0.3))])
        return {'open': norm(roll + mixat(0.5, [(0.0, clack(900, 0.7))]), 0.6), 'move': norm(clack(1650), 0.38), 'launch': norm(hops + mixat(0.5, [(0.30, ring(t_(0.2), [(2350, 0.4), (3700, 0.25)], 0.06))]), 0.65), 'close': norm(clack(1100), 0.4)}
    if kind == 'dial':
        tick = click(3, 1900, 0.004)
        clunk = click(8, 520, 0.014)
        t = t_(0.5)
        spring = mixat(0.5, [(0.032 * i, tick * 0.7) for i in range(9)] + [(0.31, clunk)])
        bell = ring(t_(0.5), [(1318, 0.5), (1660, 0.4), (2640, 0.25), (3950, 0.12)], 0.20)
        return {'open': norm(spring[:9000], 0.55), 'move': norm(tick, 0.42), 'launch': norm(mixat(0.5, [(0, clunk), (0.02, bell * 0.8), (0.10, bell[:9000] * 0.6)]), 0.6), 'close': norm(mixat(0.15, [(0, clunk), (0.05, tick * 0.5)]), 0.5)}
    if kind == 'holo':
        t = t_(0.45)
        sh = sum(np.sin(TAU * f * t + 2 * np.sin(TAU * 7 * t)) * a for f, a in ((620, 0.5), (930, 0.35), (1860, 0.2))) * env(t, 0.10, 0.12)
        s = t_(0.06)
        mv = sine(s, 2300, 3000) * env(s, 0.003, 0.012) * 0.6 + 0.2 * high(noise(s, 5), 4000) * env(s, 0.001, 0.006)
        l = t_(0.5)
        arp = mixat(0.5, [(0.035 * i, sine(t_(0.2), f, f * 1.01) * env(t_(0.2), 0.003, 0.05)) for i, f in enumerate((1046, 1568, 2093, 3136))])
        return {'open': norm(sh + 0.12 * high(noise(t, 3), 3000) * env(t, 0.05, 0.08), 0.5), 'move': norm(mv, 0.3), 'launch': norm(arp + 0.2 * sine(l, 300, 1800) * env(l, 0.05, 0.10), 0.5), 'close': norm(sine(t, 1400, 200) * env(t, 0.005, 0.06), 0.35)}
    if kind == 'jelly':
        def blip(f, d=0.16, w=18):
            t = t_(d)
            return sine(t, f * 0.7, f) * (1 + 0.35 * np.sin(TAU * w * t)) * env(t, 0.004, d * 0.35)
        return {'open': norm(mixat(0.4, [(0, blip(240)), (0.07, blip(320)), (0.14, blip(430))]), 0.55), 'move': norm(blip(520, 0.07, 30), 0.38), 'launch': norm(mixat(0.5, [(0, blip(300, 0.25, 14)), (0.05, blip(600, 0.22, 20) * 0.6)]), 0.6), 'close': norm(sine(t_(0.16), 420, 160) * env(t_(0.16), 0.004, 0.05), 0.45)}
    if kind == 'sand':
        t = t_(0.5)
        rake = band(noise(t, 3), 1400, 6500) * (0.35 + 0.65 * np.abs(np.sin(TAU * 3.0 * t)) ** 2) * env(t, 0.08, 0.16)
        bowl = ring(t_(1.0), [(392, 0.6), (1086, 0.22), (2090, 0.08)], 0.55)
        s = t_(0.07)
        return {'open': norm(rake, 0.4), 'move': norm(band(noise(s, 6), 1800, 5200) * env(s, 0.010, 0.016), 0.25), 'launch': norm(mixat(1.0, [(0, bowl)]), 0.5), 'close': norm(rake[:6000] * np.linspace(1, 0, 6000), 0.3)}
    if kind == 'flask':
        def bub(f):
            t = t_(0.09)
            return sine(t, f, f * 2.2) * env(t, 0.003, 0.02)
        g = np.random.default_rng(3)
        boil = mixat(0.5, [(0.02 + 0.045 * i, bub(300 + 420 * g.random()) * (0.4 + 0.6 * g.random())) for i in range(9)])
        ting = ring(t_(0.35), [(2489, 0.5), (5980, 0.2)], 0.12)
        l = t_(0.6)
        fizz = high(noise(l, 4), 3500) * env(l, 0.03, 0.14) * 0.5
        return {'open': norm(boil, 0.5), 'move': norm(ting[:3600], 0.28), 'launch': norm(mixat(0.6, [(0, ting), (0.02, fizz), (0.05, boil * 0.7)]), 0.55), 'close': norm(bub(260), 0.4)}
    if kind == 'sleigh':
        def jing(seed, d=0.25):
            t = t_(d)
            return sum(ring(t, [(f, 0.4)], 0.07) for f in (3120 + seed * 37, 4170 - seed * 23, 5230 + seed * 11)) * (0.6 + 0.4 * np.sin(TAU * 31 * t))
        l = t_(0.9)
        chime = mixat(0.9, [(0.07 * i, ring(t_(0.6), [(f, 0.5), (f * 2.76, 0.15)], 0.25)) for i, f in enumerate((1047, 1319, 1568, 2093))])
        return {'open': norm(mixat(0.45, [(0.0, jing(1)), (0.09, jing(2)), (0.18, jing(3))]), 0.45), 'move': norm(jing(5, 0.09), 0.25), 'launch': norm(mixat(0.9, [(0, chime), (0.0, jing(4) * 0.4)]), 0.55), 'close': norm(jing(2, 0.16), 0.3)}
    if kind == 'spooky':
        t = t_(0.7)
        wind = band(noise(t, 4), 250, 1100) * env(t, 0.22, 0.20)
        creak = (np.sin(TAU * np.cumsum(180 + 90 * np.sin(TAU * 3.1 * t) + 40 * noise(t, 6).clip(-1, 1)) / RATE) > 0.6) * env(t, 0.05, 0.14)
        s = t_(0.06)
        l = t_(0.8)
        ghost = sine(l, 700, 420) * (1 + 0.5 * np.sin(TAU * 6 * l)) * env(l, 0.08, 0.22)
        return {'open': norm(wind * 1.2 + low(creak, 1400) * 0.5, 0.5), 'move': norm(band(noise(s, 8), 500, 2200) * env(s, 0.002, 0.014), 0.35), 'launch': norm(ghost + 0.5 * wind[:len(l)] if len(wind) >= len(l) else ghost, 0.5), 'close': norm(low(creak, 1200)[:6000], 0.35)}
    if kind == 'firework':
        t = t_(0.5)
        whistle = sine(t, 700, 2400) * env(t, 0.02, 0.13) * 0.6
        l = t_(0.9)
        boom = low(noise(l, 3), 500) * env(l, 0.003, 0.09) * 1.4 + np.sin(TAU * 62 * l) * env(l, 0.002, 0.10)
        crack = (np.random.default_rng(9).random(len(l)) > 0.988) * noise(l, 7) * env(l, 0.12, 0.22)
        s = t_(0.04)
        return {'open': norm(whistle, 0.4), 'move': norm(band(noise(s, 6), 2000, 7000) * env(s, 0.0005, 0.007), 0.28), 'launch': norm(boom + high(crack, 1500) * 0.6, 0.75), 'close': norm(high(crack, 1500)[2000:8000], 0.3)}
    if kind == 'arcade':
        def bl(f, d, duty=0.5, f1=None):
            t = t_(d)
            return square(t, f, f1, duty) * np.exp(-t / (d * 0.55))
        coin = np.concatenate([bl(988, 0.07, 0.5), bl(1319, 0.30, 0.5)])
        return {'open': norm(np.concatenate([bl(262, 0.04), bl(330, 0.04), bl(392, 0.04), bl(523, 0.12)]), 0.35), 'move': norm(click(4, 1500, 0.006) + 0.3 * mixat(0.03, [(0, bl(880, 0.02, 0.25))]), 0.35), 'launch': norm(coin, 0.4), 'close': norm(bl(440, 0.14, 0.5, 110), 0.32)}
    if kind == 'synth':
        t = t_(0.5)
        saw = lambda f, d: sum(np.sin(TAU * f * k * t_(d)) / k for k in range(1, 9))
        sweep = low(saw(110, 0.5), 900) * env(t, 0.12, 0.16) + 0.4 * sine(t, 220, 880) * env(t, 0.15, 0.10)
        stab = low(sum(saw(f, 0.5) for f in (220, 277, 330, 440)), 2600) * env(t, 0.004, 0.14)
        s = t_(0.05)
        return {'open': norm(sweep, 0.5), 'move': norm(square(s, 660, 880, 0.25) * env(s, 0.001, 0.012), 0.22), 'launch': norm(stab, 0.5), 'close': norm(sine(t_(0.2), 600, 110) * env(t_(0.2), 0.004, 0.06), 0.4)}
    if kind == 'cockpit':
        sw = click(3, 1300, 0.006)
        def bp(f, d):
            t = t_(d)
            return np.sin(TAU * f * t) * np.minimum(1, (d - t) / 0.01) * np.minimum(1, t / 0.004)
        l = t_(0.5)
        turb = band(noise(l, 4), 300, 2600) * env(l, 0.10, 0.14) + 0.3 * sine(l, 400, 1500) * env(l, 0.12, 0.12)
        return {'open': norm(mixat(0.4, [(0, sw), (0.06, sw * 0.8), (0.12, sw * 0.9), (0.2, bp(1046, 0.09) * 0.4)]), 0.5), 'move': norm(sw, 0.35), 'launch': norm(mixat(0.5, [(0, sw), (0.02, turb)]), 0.55), 'close': norm(mixat(0.2, [(0, sw), (0.05, bp(523, 0.08) * 0.3)]), 0.4)}
    if kind == 'jukebox':
        clunk = click(5, 420, 0.016)
        t = t_(0.8)
        crack = (np.random.default_rng(4).random(len(t)) > 0.996) * noise(t, 5) * 0.4
        chord = mixat(0.8, [(0.0, ring(t_(0.7), [(f, 0.4), (f * 2, 0.2), (f * 3, 0.08)], 0.30)) for f in (261, 329, 392, 466)])
        return {'open': norm(mixat(0.4, [(0, clunk), (0.10, click(7, 900, 0.008)), (0.2, clunk * 0.7)]) + crack[:int(0.4 * RATE)], 0.55), 'move': norm(click(9, 1100, 0.006), 0.4), 'launch': norm(mixat(0.8, [(0, clunk), (0.03, chord)]), 0.6), 'close': norm(clunk, 0.45)}
    if kind == 'celesta':
        def note(f, d=0.6):
            return ring(t_(d), [(f, 0.6), (f * 2, 0.25), (f * 4.2, 0.08)], 0.22)
        return {'open': norm(mixat(0.8, [(0.06 * i, note(f)) for i, f in enumerate((523, 659, 784, 1047, 1319))]), 0.45), 'move': norm(note(1568, 0.16), 0.26), 'launch': norm(mixat(0.9, [(0, note(1047)), (0.06, note(1568)), (0.12, note(2093))]), 0.5), 'close': norm(note(392, 0.3), 0.4)}
    if kind == 'clay':
        def squish(seed, d, f):
            t = t_(d)
            return low(noise(t, seed), f) * env(t, 0.006, d * 0.25) * 1.6 + 0.5 * sine(t, f * 0.35, f * 0.16) * env(t, 0.004, d * 0.2)
        return {'open': norm(mixat(0.36, [(0, squish(3, 0.14, 700)), (0.09, squish(4, 0.14, 850)), (0.18, squish(5, 0.14, 1000))]), 0.6), 'move': norm(squish(6, 0.06, 1300), 0.4), 'launch': norm(mixat(0.4, [(0, squish(7, 0.3, 600)), (0.06, sine(t_(0.2), 260, 520) * env(t_(0.2), 0.004, 0.05) * 0.5)]), 0.7), 'close': norm(squish(8, 0.12, 500), 0.5)}
    if kind == 'pencil':
        def scr(seed, d, f0=1800, f1=6500):
            t = t_(d)
            return band(noise(t, seed), f0, f1) * (0.5 + 0.5 * np.sin(TAU * 38 * t)) * env(t, 0.012, d * 0.45)
        t = t_(0.35)
        stamp = np.sin(TAU * 92 * t) * env(t, 0.002, 0.045) + 0.5 * low(noise(t, 4), 1200) * env(t, 0.001, 0.02)
        return {'open': norm(mixat(0.45, [(0, scr(3, 0.16)), (0.14, scr(4, 0.14)), (0.26, scr(5, 0.16))]), 0.4), 'move': norm(scr(6, 0.05), 0.25), 'launch': norm(stamp, 0.7), 'close': norm(scr(7, 0.10, 1200, 4500), 0.3)}
    if kind == 'drip':
        def dr(f):
            t = t_(0.16)
            return np.sin(TAU * np.cumsum(f * (1 + 1.6 * np.exp(-t / 0.012))) / RATE) * env(t, 0.002, 0.03)
        t = t_(0.6)
        leaves = band(noise(t, 4), 1500, 5000) * (0.3 + 0.7 * np.abs(np.sin(TAU * 4 * t))) * env(t, 0.1, 0.14)
        chirp = mixat(0.5, [(0.0, sine(t_(0.07), 2600, 3600) * env(t_(0.07), 0.01, 0.02)), (0.10, sine(t_(0.07), 2500, 3500) * env(t_(0.07), 0.01, 0.02)), (0.19, sine(t_(0.1), 3000, 2300) * env(t_(0.1), 0.01, 0.03))])
        return {'open': norm(leaves * 0.6 + mixat(0.6, [(0.1, dr(900)), (0.28, dr(1200) * 0.6)]), 0.42), 'move': norm(dr(1300), 0.3), 'launch': norm(mixat(0.6, [(0, dr(700)), (0.06, chirp)]), 0.5), 'close': norm(dr(600), 0.4)}
    if kind == 'nixie':
        t = t_(0.4)
        hum = (np.sin(TAU * 120 * t) + 0.5 * np.sin(TAU * 240 * t)) * env(t, 0.03, 0.14)
        relay = click(6, 1500, 0.007)
        zing = ring(t_(0.45), [(3300, 0.4), (4700, 0.25), (7100, 0.1)], 0.12)
        return {'open': norm(mixat(0.4, [(0, relay), (0.05, relay * 0.7)]) + hum * 0.5, 0.5), 'move': norm(click(8, 2700, 0.004), 0.35), 'launch': norm(mixat(0.45, [(0, relay), (0.01, zing * 0.7)]), 0.5), 'close': norm(mixat(0.12, [(0, relay * 0.8)]), 0.4)}
    if kind == 'western':
        tick = click(31, 2400, 0.004)
        t = t_(0.5)
        spin = mixat(0.46, [(0.026 * i + 0.0013 * i * i, tick * (0.35 + 0.05 * i)) for i in range(12)])
        cock = mixat(0.12, [(0, click(33, 1700, 0.006)), (0.05, click(34, 2600, 0.004) * 0.8)])
        thump = low(noise(t, 35), 300) * env(t, 0.002, 0.08)
        ric = sine(t_(0.35), 2400, 900) * env(t_(0.35), 0.01, 0.2) * 0.25
        spur = ring(t_(0.5), [(3100, 0.5), (4400, 0.3), (5900, 0.2)], 0.16)
        return {'open': norm(spin, 0.55), 'move': norm(tick, 0.4), 'launch': norm(mixat(0.5, [(0, cock), (0.07, thump), (0.09, ric)]), 0.7), 'close': norm(mixat(0.4, [(0, spur), (0.09, spur * 0.6)]), 0.4)}
    if kind == 'cafe':
        clink = ring(t_(0.5), [(2100, 0.5), (5300, 0.3), (7900, 0.15)], 0.18)
        tap = ring(t_(0.2), [(1600, 0.4), (3400, 0.2)], 0.05)
        t = t_(0.6)
        pour = band(noise(t, 41), 500, 2500) * (0.6 + 0.4 * np.sin(TAU * 9 * t)) * env(t, 0.08, 0.25)
        return {'open': norm(mixat(0.6, [(0, pour * 0.6), (0.05, clink * 0.6)]), 0.45), 'move': norm(tap, 0.3), 'launch': norm(clink, 0.55), 'close': norm(mixat(0.3, [(0, tap), (0.06, tap * 0.6)]), 0.35)}
    if kind == 'shutter':
        a1, b1 = click(51, 3000, 0.003), click(52, 2200, 0.005)
        t = t_(0.3)
        wind = band(noise(t, 53), 800, 3000) * env(t, 0.02, 0.12)
        return {'open': norm(mixat(0.3, [(0, a1), (0.035, b1), (0.05, wind * 0.4)]), 0.55), 'move': norm(click(54, 2600, 0.003), 0.3),
                'launch': norm(mixat(0.25, [(0, b1), (0.06, a1)]), 0.6), 'close': norm(mixat(0.2, [(0, a1 * 0.7), (0.03, b1 * 0.5)]), 0.4)}
    if kind == 'projector':
        tick = click(61, 2000, 0.004)
        clatter = mixat(0.5, [(i * 0.042, tick * (0.5 + 0.3 * (i % 2))) for i in range(11)])
        t = t_(0.5)
        whir = band(noise(t, 62), 300, 1200) * env(t, 0.08, 0.2) * (0.7 + 0.3 * np.sin(TAU * 24 * t))
        return {'open': norm(clatter + whir[:len(clatter)] * 0.5, 0.5), 'move': norm(tick, 0.3), 'launch': norm(mixat(0.3, [(0, click(63, 1200, 0.008)), (0.02, tick)]), 0.55),
                'close': norm(mixat(0.25, [(0, tick), (0.05, tick * 0.6), (0.1, tick * 0.3)]), 0.35)}
    if kind == 'billiard':
        clack = mixat(0.12, [(0, ring(t_(0.12), [(3800, 0.6), (5200, 0.3), (7100, 0.15)], 0.02)), (0, click(71, 1800, 0.004) * 0.6)])
        t = t_(0.3)
        roll = low(noise(t, 72), 600) * env(t, 0.05, 0.12) * 0.5
        return {'open': norm(mixat(0.4, [(0, clack), (0.09, clack * 0.7), (0.15, clack * 0.5), (0.05, roll)]), 0.55), 'move': norm(clack * 0.5, 0.3),
                'launch': norm(mixat(0.3, [(0, clack), (0.04, roll)]), 0.6), 'close': norm(mixat(0.25, [(0, clack * 0.6), (0.08, clack * 0.4)]), 0.4)}
    raise SystemExit('no sounds called ' + kind)
