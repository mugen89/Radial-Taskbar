"""Crypt: worn flagstones under a wrought-iron gate; violet soul flames burn over stone plaques, and the gate
in the middle swings open when the wheel does."""
from lineup import *

K = Kit('crypt', 'Crypt', 'Worn flagstones under wrought iron; violet soul flames burn over stone plaques and the gate swings open', ['gothic', 'dark', 'violet'])
K.flag(halo='light', flame=dict(light=True, cols=4), aura='light')
K.font('metamorphous', 'Metamorphous-Regular.ttf')
VIOLET = '#A66BFF'


def floor():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    f1, f2, _ = worley(c.X, c.Y, 5, 4, True)
    seam = smooth(0.0, 0.03, f2 - f1)
    H = 0.03 * seam + 0.01 * fbm(c.shape, 20, 5, 3)
    alb = mix(flat('#2A2630', c.shape), flat('#4A4450', c.shape), clamp(0.4 + 0.5 * fbm(c.shape, 8, 6, 4))[..., None])
    col = surface(c, H, alb, COOL, rough=0.85, reach=0.1)
    bars = np.full(c.shape, 9.0, F)
    for k in range(20):
        a = k * TAU / 20
        x, y = c.polar(a, 0.98)
        bars = np.minimum(bars, c.capsule(0, 0, x, y, 0.010))
    bars = np.maximum(bars, 0.40 - c.R)
    rings = np.minimum(np.abs(c.R - 0.95) - 0.018, np.abs(c.R - 0.42) - 0.014)
    iron = np.minimum(bars, rings)
    Hi = 0.04 * clamp(-iron / 0.015)
    icol = metal(c, Hi, flat('#1A1A20', c.shape), rough=0.4, grime=0.3, seed=7, studio=COOL)
    c.put(col, c.cover(d), H)
    c.put(icol, c.cover(iron), Hi)
    K.put(c, 'floor')


def plaques():
    def one(c, k):
        d = c.regular(8, 0.86, rot=TAU / 16)
        t = clamp(-d / 0.2)
        H = 0.06 * np.sqrt(t) - 0.01 * gauss(c.R - 0.62, 0.012) + 0.008 * fbm(c.shape, 18, 3 + k, 3)
        alb = mix(flat('#5A5462', c.shape), flat('#3A3442', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 6, 4 + k, 3))[..., None])
        col = surface(c, H, alb, COOL, rough=0.85, reach=0.1)
        col = col + rgb(VIOLET) * (0.25 * gauss(c.R - 0.62, 0.02))[..., None]
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'plaques', 2, one)


def gate():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = mix(flat('#1E1828', c.shape), flat('#0A0810', c.shape), smooth(0.0, 0.95, c.R)[..., None])
    col = col + rgb(VIOLET) * (0.25 * gauss(c.R, 0.5))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'well')
    for side, name in ((-1, 'gateL'), (1, 'gateR')):
        c = K.canvas(240, 2, 1.0, 2.0)
        bars = np.full(c.shape, 9.0, F)
        for x in (-0.6, -0.2, 0.2, 0.6):
            bars = np.minimum(bars, c.capsule(x, -1.7, x, 1.7, 0.05))
        bars = np.minimum(bars, np.minimum(np.abs(c.Y + 1.2) - 0.05, np.abs(c.Y - 1.2) - 0.05) + 0 * c.X)
        bars = np.maximum(bars, np.abs(c.X) - 0.85)
        spear = np.full(c.shape, 9.0, F)
        for x in (-0.6, -0.2, 0.2, 0.6):
            spear = np.minimum(spear, c.poly([(x, -1.98), (x + 0.12, -1.72), (x - 0.12, -1.72)]))
        iron = np.minimum(bars, spear)
        Hi = 0.05 * clamp(-iron / 0.05)
        c.put(metal(c, Hi, flat('#24222C', c.shape), rough=0.4, grime=0.3, seed=8, studio=COOL), c.cover(iron), Hi)
        K.put(c, name, how='png')
    flames(K, 'flame', 12, 96, 1.8, hot='#F4E6FF', mid='#B07CFF', out='#5A2AB8', seed=9)
    light(K, 'aura', 200, lambda c: (1 - smooth(0.0, 1.0, c.R)) ** 2, tint=VIOLET)
    halo(K, 'halo', 220, 2.0, 0.2, tint='#C8A0FF')


K.run([floor, plaques, gate])
P = dict(base='#14101C', accent=VIOLET, accent2='#D9C2FF', text='#EEE6FA', sub='#B8A8D8', panel=('#241C30', '#14101C'), stroke='#7A6A8A', tile=('#3A3442', '#24202C'), tilestroke='#7A6A8A',
         ink='#EEE6FA', dim=0.58, font=dict(file='Metamorphous-Regular.ttf', family='Metamorphous'), badge=VIOLET, badgeink='#14101C')
flick = '(1+0.10*sin(time*11+seed*9)+0.06*sin(time*17+seed*3))'
finish(K, P, sounds='spooky',
       back=[soft(1.10, 0.03, 70), img('floor', 1.0, intro=intro(0.4, 'out', scale=0.92))],
       under=[img('aura', '1.8*' + flick, opacity='0.35+0.4*hot'), img('plaques', '0.98*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0', rotate='a'),
              img('flame', [0.34, 0.61], y=-0.88, pivot=[0.5, 0.75], frame='floor(time*14+seed*12)%12', opacity='0.75+0.25*hot', scale=flick)],
       icon=dict(size=0.58, zoom=1.16, shadow=dict(x=0, y=0, blur=5, color='#A66BFF/60')),
       hub=[img('well', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       front=[img('gateL', [0.5, 1.0], **{'in': 'hub'}, x='-0.25-0.9*open', opacity='1-sat(open*1.4)'), img('gateR', [0.5, 1.0], **{'in': 'hub'}, x='0.25+0.9*open', opacity='1-sat(open*1.4)')],
       style=dict(open='fade', speed=0.85, tilt=0.3),
       onlaunch=[dict(color='#C8A0FF', count=24, area='slot', life=[0.6, 1.2], size=[2, 4], speed=[40, 160], outward=True, dir=[-60, 60], gravity=-160, drag=1.2, fadein=0, fadeout=0.5)],
       screen=dict(effect='fireflies', color='#8A5ADF', color2='#E8D8FF', density=0.8, speed=0.5, size=1.1))
