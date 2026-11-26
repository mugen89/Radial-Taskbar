"""Compass: a ship's brass compass with its card floating in oil; the needle swings round to your choice."""
from lineup import *

K = Kit('compass', 'Compass', "A ship's brass compass with its card floating in oil; the needle swings round to your choice", ['sea', 'brass', 'precise'])
K.flag(halo='light')
BRASS = '#C8964A'


def bowl():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    card = mix(flat('#F2E8D0', c.shape), flat('#E0D2B0', c.shape), smooth(0.0, 0.9, c.R)[..., None])
    rose = c.cover(c.star(16, 0.80, 0.10)) * 0.35 + c.cover(c.star(8, 0.86, 0.12)) * 0.45 + c.cover(c.star(4, 0.90, 0.14)) * 0.6
    card = mix(card, flat('#2A3A5A', c.shape), clamp(rose * 0.6)[..., None])
    marks = np.zeros(c.shape, F)
    for k in range(72):
        a = k * TAU / 72
        x0, y0 = c.polar(a, 0.86)
        x1, y1 = c.polar(a, 0.84 if k % 3 else 0.82)
        marks = np.maximum(marks, gauss(c.capsule(x0, y0, x1, y1, 0), 0.0025))
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    f = load_font('georgiab.ttf', 0.05 / c.px)
    for k, s in enumerate(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']):
        x, y = c.polar(k * TAU / 8, 0.90)
        dr.text(((x + 1) * c.w / 2, (y + 1) * c.h / 2), s, font=f, fill=255, anchor='mm')
    letters = np.asarray(im, F) / 255
    card = mix(card, flat('#B8202A', c.shape), (marks + letters * 0.95)[..., None] * 0.9)
    rimz = smooth(0.93, 0.935, c.R)
    H = 0.04 * np.sqrt(clamp(1 - ((c.R - 0.965) / 0.035) ** 2)) * rimz
    col = mix(card * (1 - 0.3 * gauss(c.R - 0.93, 0.015))[..., None], metal(c, H, flat(BRASS, c.shape), rough=0.22, grime=0.5, seed=4, studio=WARM), rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'bowl')
    K.save(glass_dome(1080 if K.draft == 1 else 540, 2, strength=0.55), 'dome', how='png')


def needle():
    c = K.canvas(80, 4, 1.0, 10.0)
    north = c.poly([(0, -9.6), (0.9, 0), (-0.9, 0)])
    south = c.poly([(0, 9.6), (0.9, 0), (-0.9, 0)])
    H = 0.3 * clamp(1 - np.abs(c.X) / 0.9)
    col = np.where((c.Y < 0)[..., None], rgb('#B8202A'), rgb('#2A3A5A')) * np.ones(c.shape + (3,), F)
    c.put(surface(c, H, col.astype(F), WARM, rough=0.3, metal=0.3), c.cover(np.minimum(north, south)), H)
    K.put(c, 'needle', how='png')


def chips():
    def one(c, k):
        d = c.R - 0.84
        rimz = smooth(0.70, 0.72, c.R)
        H = 0.05 * np.sqrt(clamp(1 - ((c.R - 0.78) / 0.07) ** 2)) * rimz
        face = flat('#F6F0E0' if k == 0 else '#E8DCC0', c.shape)
        col = mix(face, metal(c, H, flat(BRASS, c.shape), rough=0.22, grime=0.4, seed=8 + k, studio=WARM), rimz[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'chips', 2, one)


def cap():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.82, 0.84, c.R)
    H = 0.05 * np.sqrt(clamp(1 - ((c.R - 0.90) / 0.07) ** 2)) * rimz
    face = mix(flat('#F6F0E0', c.shape), flat('#E4D8BC', c.shape), smooth(0.0, 0.8, c.R)[..., None])
    col = mix(face, metal(c, H, flat(BRASS, c.shape), rough=0.22, grime=0.4, seed=5, studio=WARM), rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'cap')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE8B0')


K.run([bowl, needle, chips, cap])
P = dict(base='#2A1E12', accent=BRASS, accent2='#B8202A', text='#2A1E12', sub='#5A4A32', panel=('#F2E8D0', '#E0D2B0'), stroke=BRASS, tile=('#F6F0E0', '#E4D8BC'), tilestroke='#8A6A32',
         ink='#2A1E12', paneltext='#2A1E12', dim=0.3, font='Georgia', badge='#B8202A', badgeink='#F6F0E0')
swing = 'sel+6*sin(time*2.2)*exp(-0.0*time)'
finish(K, P, sounds='watch',
       back=[soft(1.08, 0.03, 60), img('bowl', 1.0, rotate='(1-open)*-30', intro=intro(0.45, 'out', scale=0.94)), img('needle', [0.07, 0.70], rotate=swing, opacity='sat(open)')],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('chips', '0.96*(1+0.04*hot-0.03*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.58, zoom=1.14, shadow=dict(x=0, y=1, blur=2, color='black/35')),
       hub=[img('cap', 1.0, intro=intro(0.45, 'back', scale=0.7))],
       front=[img('dome', 1.0, opacity='0.8*sat(open)')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=2, color='#F6F0E0')),
       tabs=dict(inset=13, text='#F6F0E0', fill='#00000030', on='#C8964A/85'),
       style=dict(open='spin', speed=0.9, tilt=0.3),
       onlaunch=[dict(color='#F2D88A', count=14, area='slot', life=[0.4, 0.8], size=[1.2, 2.4], speed=[50, 180], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.5)])
