"""Film Reel: a metal reel turns behind a strip of film; every app is a frame, the picture flickers and gathers dust."""
from lineup import *

K = Kit('film', 'Film Reel', 'A metal reel turns behind a strip of film; every app is a frame, and the picture flickers with dust', ['cinema', 'vintage', 'warm'])
K.flag(halo='light', lamplight='light', dust=dict(cols=4))


def reel():
    c = K.canvas(1080, 2)
    holes = np.full(c.shape, 9.0, F)
    for k in range(6):
        x, y = c.polar(k * TAU / 6, 0.52)
        holes = np.minimum(holes, c.circle(0.20, x, y))
    d = np.maximum(c.R - 0.98, -holes)
    d = np.maximum(d, 0.07 - c.R)
    H = 0.02 * clamp(-d / 0.02) + 0.01 * gauss(c.R - 0.95, 0.01)
    tx, ty = -np.sin(c.A), np.cos(c.A)
    col = metal(c, H, flat('#8A8E94', c.shape), rough=0.3, aniso=(tx, ty, V(0.4)), grime=0.6, seed=5, studio=WARM, scratch=100)
    c.put(col, c.cover(d), H)
    K.put(c, 'reel', how='png')


def strip():
    c = K.canvas(1080, 2)
    r0, half = 0.715, 0.165
    d = np.abs(c.R - r0) - half
    edge = np.abs(c.R - r0) > half * 0.72
    sprocket = (np.abs(((c.A / TAU * 72) % 1) - 0.5) < 0.18) & edge & (np.abs(np.abs(c.R - r0) - half * 0.86) < half * 0.08)
    col = flat('#1A1410', c.shape) * (0.9 + 0.1 * fbm(c.shape, 40, 3, 2))[..., None]
    col = mix(col, flat('#C8B080', c.shape), (sprocket * 0.9)[..., None])
    c.put(col, c.cover(d) * (1 - sprocket * 0.85))
    K.put(c, 'strip', how='png')


def frames():
    def one(c, k):
        d = c.box(0.80, 0.66, r=0.06)
        sep = c.box(0.84, 0.70, r=0.04)
        col = mix(flat('#F2E2BA', c.shape), flat('#C8A878', c.shape), smooth(0.0, 1.2, c.R)[..., None]) * (0.85 + 0.15 * fbm(c.shape, 20, 3 + k, 2))[..., None]
        col = col * (1 - 0.35 * smooth(0.3, 1.1, c.R))[..., None]
        c.put(flat('#1A1410', c.shape), c.cover(sep))
        c.put(col, c.cover(d))
        return c
    plate(K, 'frames', 2, one)


def lamp():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.80, 0.82, c.R)
    H = 0.06 * np.sqrt(clamp(1 - ((c.R - 0.89) / 0.08) ** 2)) * rimz
    col = metal(c, H, flat('#6A6E74', c.shape), rough=0.3, grime=0.6, seed=4, studio=WARM)
    face = mix(flat('#3A2A18', c.shape), flat('#120C06', c.shape), smooth(0.0, 0.8, c.R)[..., None])
    col = mix(face, col, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'lamp')
    light(K, 'lamplight', 300, lambda c: (1 - smooth(0.0, 1.0, c.R)) ** 2.2, tint='#FFD89A')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE0A8')
    ims = []
    for k in range(4):
        c = K.canvas(300, 1)
        g = rng(80 + k)
        a = np.zeros(c.shape, F)
        for _ in range(26):
            x, y = g.uniform(-1, 1), g.uniform(-1, 1)
            a = np.maximum(a, smooth(0.012, 0.004, np.hypot(c.X - x, c.Y - y)) * g.uniform(0.4, 1))
        for _ in range(2):
            x = g.uniform(-0.9, 0.9)
            a = np.maximum(a, gauss(c.X - x - 0.02 * c.Y, 0.003) * g.uniform(0.3, 0.7))
        c.col[:] = rgb('#E8E0D0')
        c.alpha = a
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'dust', how='png')
    c = K.canvas(40, 4, 1.0, 1.3)
    d = c.poly([(0, -1.2), (0.75, 1.0), (-0.75, 1.0)])
    c.col[:] = rgb('#E8C27A')
    c.alpha = c.cover(d)
    K.put(c, 'pointer', how='png', tone=False)


K.run([reel, strip, frames, lamp])
P = dict(base='#1A1612', accent='#E8C27A', accent2='#F4E6C4', text='#F4E6C4', sub='#C8B48A', panel=('#2A221A', '#1A1612'), stroke='#8A7A5A', tile=('#F2E2BA', '#D8C498'), tilestroke='#6A5A3A',
         ink='#1A1612', dim=0.55, font='Georgia', badge='#E8C27A', badgeink='#1A1612')
finish(K, P, sounds='projector',
       back=[soft(1.08, 0.03, 70), img('reel', 1.0, rotate='time*18+(1-open)*-90', intro=intro(0.4, 'out', scale=0.92)), img('strip', 1.0, rotate='time*-3')],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('frames', '0.98*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0', rotate='a')],
       icon=dict(size=0.56, zoom=1.16, tone='original', shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('lamp', 1.0, intro=intro(0.4, 'back', scale=0.6)), img('lamplight', 1.25, opacity='0.16+0.05*noise(time*20)')],
       front=[img('dust', 1.0, frame='floor(time*12)%4', opacity='0.55', rotate='floor(time*12)*37')],
       over=[img('pointer', [0.05, 0.065], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       style=dict(open='fade', speed=0.9, tilt=0.25),
       onlaunch=[dict(color='#FFE8B0', count=1, area='slot', life=[0.2, 0.2], size=[70, 70], grow=1.5, speed=[0, 0], opacity=0.45, fadein=0, fadeout=1)])
