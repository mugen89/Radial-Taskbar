"""Aperture: the front of a camera lens; coated glass for every app, numbers on the barrel, and an iris
that opens around the name."""
from lineup import *

K = Kit('aperture', 'Aperture', 'The front of a camera lens: coated glass for every app, numbers on the barrel, an iris that opens around the name', ['photo', 'dark', 'precise'])
K.flag(halo='light')


def barrel():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    knurl = (np.abs(((c.A / TAU * 180) % 1) - 0.5) < 0.25) * smooth(0.90, 0.905, c.R)
    H = 0.03 * smooth(0.90, 0.905, c.R) + 0.006 * knurl + 0.015 * smooth(0.56, 0.57, c.R)
    alb = flat('#141418', c.shape) * (0.9 + 0.1 * fbm(c.shape, 40, 3, 2))[..., None]
    col = metal(c, H, alb, rough=0.55, grime=0.2, seed=3, studio=COOL, met=0.2)
    marks = np.zeros(c.shape, F)
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    f = load_font('segoeuib.ttf', 0.035 / c.px)
    for k, s in enumerate(['1.4', '2', '2.8', '4', '5.6', '8', '11', '16', '22']):
        a = -1.3 + k * 2.6 / 8
        x, y = c.polar(a, 0.83)
        dr.text(((x + 1) * c.w / 2, (y + 1) * c.h / 2), s, font=f, fill=255, anchor='mm')
    marks = np.asarray(im, F) / 255
    for k in range(60):
        a = k * TAU / 60
        x0, y0 = c.polar(a, 0.86)
        marks = np.maximum(marks, gauss(c.capsule(x0, y0, *c.polar(a, 0.875 if k % 5 else 0.885), 0), 0.0015))
    col = mix(col, flat('#E8E8EE', c.shape), (marks * 0.9)[..., None])
    col = mix(col, flat('#D02A2A', c.shape), (0.9 * gauss(c.R - 0.78, 0.003) * smooth(0.2, 0.0, np.abs(c.A)))[..., None])
    glass = smooth(0.565, 0.555, c.R)
    coat = mix(flat('#1A1428', c.shape), flat('#0A1A14', c.shape), clamp(0.5 + 0.5 * c.X)[..., None])
    refl = gauss(np.hypot(c.X + 0.18, c.Y + 0.20) - 0.30, 0.03) * 0.5 + gauss(np.hypot(c.X - 0.15, c.Y - 0.18) - 0.18, 0.02) * 0.3
    coat = coat + rgb('#B48CFF') * (0.5 * refl)[..., None] + rgb('#6AE0A0') * (0.25 * gauss(np.hypot(c.X, c.Y) - 0.45, 0.02))[..., None]
    col = mix(col, coat, glass[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'barrel')


def elements():
    def one(c, k):
        d = c.R - 0.88
        rimz = smooth(0.74, 0.76, c.R)
        H = 0.05 * np.sqrt(clamp(1 - ((c.R - 0.81) / 0.07) ** 2)) * rimz
        col = metal(c, H, flat('#202026', c.shape), rough=0.45, grime=0.2, seed=8 + k, studio=COOL, met=0.3)
        tint = rgb('#B48CFF' if k else '#6AE0A0')
        glass = flat('#0A0A12', c.shape) + tint * (0.35 * gauss(c.R - 0.55, 0.06) + 0.25 * gauss(np.hypot(c.X + 0.25, c.Y + 0.3) - 0.25, 0.04))[..., None]
        col = mix(glass, col, rimz[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'elements', 2, one)


def iris():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = mix(flat('#121218', c.shape), flat('#050508', c.shape), smooth(0.0, 0.9, c.R)[..., None])
    col = col + rgb('#B48CFF') * (0.3 * gauss(c.R - 0.90, 0.01))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'well')
    c = K.canvas(460, 2)
    n = 8
    blades = np.zeros(c.shape, F)
    for k in range(n):
        a = k * TAU / n
        u = c.X * math.cos(a) + c.Y * math.sin(a)
        blades = np.maximum(blades, (u > 0.20).astype(F) * 0.0 + smooth(0.19, 0.21, u))
    hole = c.regular(n, 0.21, rot=TAU / 16)
    cov = c.cover(-hole) * c.cover(c.R - 0.96)
    seams = np.zeros(c.shape, F)
    for k in range(n):
        a = k * TAU / n + 0.35
        u = c.X * math.cos(a) + c.Y * math.sin(a) - 0.2
        seams = np.maximum(seams, gauss(u, 0.004) * smooth(0.2, 0.3, c.R))
    col = flat('#2A2A32', c.shape) * (0.8 + 0.25 * smooth(-1, 1, -c.Y - c.X))[..., None] - V([0.1, 0.1, 0.1]) * seams[..., None]
    c.col, c.alpha = col.astype(F), cov.astype(F)
    K.put(c, 'iris', how='png')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#D8C8FF')
    c = K.canvas(40, 4, 1.0, 1.5)
    d = c.poly([(0, -1.4), (0.7, 1.2), (-0.7, 1.2)])
    c.col[:] = rgb('#D02A2A')
    c.alpha = c.cover(d)
    K.put(c, 'index', how='png', tone=False)


K.run([barrel, elements, iris])
P = dict(base='#0E0E12', accent='#E0E0E8', accent2='#B48CFF', text='#F4F4F8', sub='#B8B8C4', panel=('#1E1E24', '#0E0E12'), stroke='#5A5A66', tile=('#E8E8EE', '#C8C8D0'), tilestroke='#5A5A66',
         ink='#0E0E12', dim=0.5, font='Bahnschrift, Segoe UI', badge='#E0E0E8', badgeink='#0E0E12')
finish(K, P, sounds='shutter',
       back=[soft(1.08, 0.03, 70), img('barrel', 1.0, rotate='(1-open)*-40', intro=intro(0.45, 'out', scale=0.92))],
       under=[img('halo', '1.6*hot', opacity='hot*0.5', when='hot>0.02'), img('elements', '1.0*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.60, zoom=1.16, shadow=dict(x=0, y=1, blur=3, color='black/50')),
       hub=[img('well', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       front=[img('iris', '1.0+1.8*sat(open)', **{'in': 'hub'}, rotate='sat(open)*70', opacity='1-sat(open*1.15)')],
       over=[img('index', [0.05, 0.075], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       style=dict(open='zoom', speed=0.85, tilt=0.3),
       onlaunch=[dict(color='#FFFFFF', count=1, area='slot', life=[0.18, 0.18], size=[80, 80], grow=1.4, speed=[0, 0], opacity=0.5, fadein=0, fadeout=1)])
