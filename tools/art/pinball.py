"""Pinball: a playfield under glass with chrome rails; pop bumpers carry the apps and flash, a dot display in the
middle, and the ball shoots off on launch."""
from lineup import *

K = Kit('pinball', 'Pinball', 'A playfield under glass: pop bumpers carry the apps and flash, a dot display sits in the middle', ['game', 'retro', 'bright'])
K.flag(halo='light', flash='light')
K.font('vt323', 'VT323-Regular.ttf')


def field():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    col = mix(flat('#16248A', c.shape), flat('#08103E', c.shape), smooth(0.0, 1.0, c.R)[..., None])
    stars_ = np.zeros(c.shape, F)
    g = rng(5)
    for _ in range(16):
        x, y = c.polar(g.random() * TAU, g.uniform(0.2, 0.85))
        stars_ = np.maximum(stars_, c.cover(c.star(5, g.uniform(0.03, 0.06), 0.4 * g.uniform(0.03, 0.06) / 0.05 * 0.05 * 0 + 0.02, rot=g.random(), x=x, y=y)))
    col = mix(col, flat('#FFD23A', c.shape), (0.8 * stars_)[..., None])
    for k in range(8):
        a = k * TAU / 8
        arrow = c.poly([c.polar(a, 0.40), c.polar(a + 0.06, 0.34), c.polar(a - 0.06, 0.34)])
        col = mix(col, flat('#FF4A2A', c.shape), (0.85 * c.cover(arrow))[..., None])
    lanes = gauss(c.R - 0.88, 0.004) + gauss(c.R - 0.45, 0.003)
    col = col + V([0.9, 0.9, 1.0]) * (0.6 * lanes)[..., None]
    rail = smooth(0.92, 0.93, c.R)
    H = 0.04 * np.sqrt(clamp(1 - ((c.R - 0.96) / 0.035) ** 2)) * rail
    chrome = metal(c, H, flat('#D8DCE2', c.shape), rough=0.12, grime=0.2, seed=4, studio=COOL)
    col = mix(col, chrome, rail[..., None])
    gl = smooth(0.2, 0.9, -(c.X * 0.55 + c.Y * 0.85)) * smooth(0.92, 0.5, c.R) * 0.07
    c.put(col + gl[..., None], c.cover(d), H)
    K.put(c, 'field')


def bumpers():
    caps = ['#E8302A', '#2A8AE8', '#E8C82A', '#2AC86A']
    def one(c, k):
        d = c.R - 0.90
        skirt = smooth(0.66, 0.68, c.R)
        H = 0.05 * skirt * np.sqrt(clamp(1 - ((c.R - 0.79) / 0.11) ** 2)) + (1 - skirt) * lens(clamp(1 - c.R / 0.66), 0.14, 2.2)
        cap = surface(c, H, flat(caps[k], c.shape), SOFT, rough=0.25, clear=0.8, reach=0.1)
        ring_ = smooth(0.50, 0.52, c.R) * smooth(0.62, 0.60, c.R)
        cap = mix(cap, flat('#FFFFFF', c.shape) * 0.95, ring_[..., None])
        chrome = metal(c, H, flat('#D8DCE2', c.shape), rough=0.12, grime=0.2, seed=8 + k, studio=COOL)
        col = mix(cap, chrome, skirt[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'bumpers', 4, one)


def display():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.82, 0.84, c.R)
    H = 0.05 * np.sqrt(clamp(1 - ((c.R - 0.90) / 0.07) ** 2)) * rimz
    chrome = metal(c, H, flat('#D8DCE2', c.shape), rough=0.12, grime=0.2, seed=5, studio=COOL)
    cell = 0.03
    gx, gy = (c.X / cell) % 1, (c.Y / cell) % 1
    dots = gauss(np.hypot(gx - 0.5, gy - 0.5), 0.18)
    face = flat('#140804', c.shape) + rgb('#5A2A08') * (0.35 * dots)[..., None]
    col = mix(face, chrome, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'display')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFD8A0')
    light(K, 'flash', 220, lambda c: (1 - smooth(0.2, 1.0, c.R)) ** 1.5, tint='#FFF2C0')
    c = K.canvas(48, 4)  # the ball
    d = c.R - 0.9
    H = lens(clamp(-d / 0.9), 0.5, 2)
    c.put(metal(c, H, flat('#E8ECF0', c.shape), rough=0.08, grime=0.1, seed=2, studio=COOL), c.cover(d), H)
    K.put(c, 'ball', how='png')
    c = K.canvas(48, 4, 1.0, 1.4)
    d = c.poly([(0, -1.3), (0.8, 1.1), (-0.8, 1.1)])
    c.col[:] = rgb('#FF9A2A')
    c.alpha = c.cover(d)
    K.put(c, 'arrow', how='png', tone=False)


K.run([field, bumpers, display])
P = dict(base='#0A1440', accent='#FF4A2A', accent2='#FFD23A', text='#FF9A2A', sub='#C86A1A', panel=('#16248A', '#08103E'), stroke='#D8DCE2', tile=('#F2F4F8', '#D0D6E0'), tilestroke='#8A96B0',
         ink='#0A1440', paneltext='#FFD23A', dim=0.4, font=dict(file='VT323-Regular.ttf', family='VT323'), badge='#FFD23A', badgeink='#0A1440')
finish(K, P, sounds='arcade',
       back=[soft(1.08, 0.03, 65), img('field', 1.0, intro=intro(0.35, 'out', scale=0.94))],
       under=[img('flash', '1.7*(1+0.4*launch)', opacity='0.25*hot+0.9*launch+0.25*step(0.5,fract(time*2+seed))*hot'), img('bumpers', '0.96*(1+0.06*hot-0.10*press+0.15*launch)', frame='(i+ring)%4')],
       icon=dict(size=0.48, zoom=1.2, shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('display', 1.0, intro=intro(0.35, 'back', scale=0.6))],
       over=[img('arrow', [0.06, 0.084], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=24, clockpx=46, datepx=17, subpx=16, shadow=dict(x=0, y=0, blur=6, color='#FF6A1A/80')),
       tabs=dict(inset=13, text='#FFD23A', fill='#FFFFFF/12', on='#FF4A2A/85'),
       style=dict(open='zoom', speed=1.15, tilt=0.35),
       onlaunch=[dict(image='ball', count=1, area='slot', life=[0.5, 0.5], size=[14, 14], speed=[700, 700], outward=True, dir=[0, 0], drag=0.5, fadein=0, fadeout=0.2),
                 dict(color='#FFD23A', count=24, area='slot', life=[0.3, 0.6], size=[1.5, 3], speed=[100, 340], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.5)],
       onhover=[dict(color='#FFF2C0', count=6, area='slot', life=[0.15, 0.3], size=[1.5, 2.5], speed=[100, 220], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.6)])
