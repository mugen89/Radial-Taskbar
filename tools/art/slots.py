"""Slot Machine: a red and chrome cabinet face with chasing bulbs; every app sits in a reel window, coins burst on launch."""
from lineup import *

K = Kit('slots', 'Slot Machine', 'A red and chrome cabinet with chasing bulbs; every app sits in a reel window and coins burst on a win', ['casino', 'bright', 'game'])
K.flag(halo='light', bulbs=dict(cols=2, light=True))
SYMS = ['star', 'diamond', 'bar', 'bell']


def cabinet():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    t = clamp(-d / 0.99)
    H = 0.02 * smooth(0.90, 0.91, c.R) + 0.03 * np.sqrt(clamp(1 - ((c.R - 0.95) / 0.04) ** 2)) * smooth(0.90, 0.91, c.R)
    paint = mix(flat('#8A0A14', c.shape), flat('#C81E2A', c.shape), clamp(0.5 + 0.5 * np.sin(c.A * 16))[..., None] * 0.35)
    chrome = smooth(0.90, 0.91, c.R)
    col = surface(c, H, paint, WARM, rough=0.25, clear=1.0, reach=0.1)
    col = mix(col, metal(c, H, flat('#E0E4EA', c.shape), rough=0.12, grime=0.2, seed=3, studio=COOL), chrome[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'cabinet')
    ims = []
    for phase in range(2):
        c = K.canvas(1080, 1)
        v = np.zeros(c.shape, F)
        n = 40
        for k in range(n):
            x, y = c.polar(k * TAU / n, 0.955)
            on = 1.0 if (k + phase) % 2 == 0 else 0.25
            v = v + on * (gauss(np.hypot(c.X - x, c.Y - y), 0.010) * 1.4 + 0.3 * gauss(np.hypot(c.X - x, c.Y - y), 0.03))
        c.col = (rgb('#FFE08A') * v[..., None]).astype(F)
        c.alpha[:] = 1
        ims.append(c.image(tone=False, dither=False))
    K.sheet(ims, 2, 'bulbs', how='jpg')


def reels():
    def one(c, k):
        d = c.box(0.74, 0.88, r=0.16)
        t = clamp(-d / 0.3)
        roll = 0.75 + 0.25 * np.sqrt(clamp(1 - (c.Y / 0.9) ** 2))
        col = flat('#FAF6EC', c.shape) * roll[..., None]
        sym = {'star': c.star(5, 0.40, 0.17), 'diamond': c.regular(4, 0.40), 'bar': c.box(0.40, 0.14, r=0.04), 'bell': np.minimum(c.circle(0.30, 0, -0.05), c.box(0.36, 0.06, y=0.28, r=0.03))}[SYMS[k]]
        col = mix(col, flat('#E8D8B8', c.shape), (0.6 * c.cover(sym))[..., None])
        frame = smooth(-0.06, -0.04, d)
        H = 0.04 * frame
        chrome = metal(c, H, flat('#E0E4EA', c.shape), rough=0.15, grime=0.2, seed=9 + k, studio=COOL)
        col = mix(col, chrome, frame[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'reels', 4, one)


def jackpot():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.80, 0.82, c.R)
    H = 0.06 * np.sqrt(clamp(1 - ((c.R - 0.89) / 0.08) ** 2)) * rimz
    gold = metal(c, H, flat('#E8B83A', c.shape), rough=0.18, grime=0.3, seed=5, studio=WARM)
    glass = mix(flat('#5A0610', c.shape), flat('#20020A', c.shape), smooth(0.0, 0.8, c.R)[..., None])
    glass = glass + rgb('#FF6A4A') * (0.2 * gauss(np.hypot(c.X + 0.2, c.Y + 0.3), 0.25))[..., None]
    col = mix(glass, gold, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'jackpot')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE08A')
    c = K.canvas(48, 4)
    d = c.R - 0.88
    H = 0.2 * clamp(-d / 0.3) + 0.03 * gauss(c.R - 0.65, 0.04)
    c.put(metal(c, H, flat('#E8B83A', c.shape), rough=0.2, grime=0.2, seed=6, studio=WARM), c.cover(d), H)
    K.put(c, 'coin', how='png')
    c = K.canvas(48, 4, 1.0, 1.4)
    d = c.poly([(0, -1.3), (0.8, 1.1), (-0.8, 1.1)])
    c.col[:] = rgb('#FFE08A')
    c.alpha = c.cover(d)
    K.put(c, 'arrow', how='png', tone=False)


K.run([cabinet, reels, jackpot])
P = dict(base='#2A0A0E', accent='#FFD23A', accent2='#FF3A3A', text='#FFE9A0', sub='#E8C27A', panel=('#5A0A14', '#2A0A0E'), stroke='#E8B83A', tile=('#FAF6EC', '#E8DCC0'), tilestroke='#B8902A',
         ink='#2A0A0E', dim=0.42, font='Impact, Bahnschrift', badge='#FFD23A', badgeink='#2A0A0E')
finish(K, P, sounds='casino',
       back=[soft(1.10, 0.03, 65), img('cabinet', 1.0, intro=intro(0.35, 'back', scale=0.9)), img('bulbs', 1.0, frame='floor(time*5)%2')],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), soft(0.95, 0.06, 40), img('reels', '0.96*(1+0.05*hot-0.04*press)', frame='floor(i+ring+time*20*hot)%4')],
       icon=dict(size=0.56, zoom=1.16, shadow=dict(x=0, y=1, blur=2, color='black/40')),
       hub=[img('jackpot', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('arrow', [0.06, 0.084], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=18, clockpx=34, shadow=dict(x=0, y=1, blur=4, color='black/90')),
       style=dict(open='bloom', speed=1.1, tilt=0.35),
       onlaunch=[dict(image='coin', count=24, area='slot', life=[0.6, 1.1], size=[7, 11], speed=[150, 380], outward=True, dir=[-70, 70], gravity=900, spin=[-500, 500], fadein=0, fadeout=0.3)])
