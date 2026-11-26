"""Sunflower: seeds in a golden spiral, petals that open with the wheel; little flowers carry the apps."""
from lineup import *

K = Kit('sunflower', 'Sunflower', 'Seeds in a golden spiral and petals that open with the wheel; little flowers carry the apps', ['nature', 'bright', 'summer'])
K.flag(halo='light')


def petals(c, n, r0, r1, w, seed):
    ink = Ink(c)
    g = rng(seed)
    for k in range(n):
        a = k * TAU / n + g.uniform(-0.03, 0.03)
        l = r1 + g.uniform(-0.03, 0.03)
        pts = [c.polar(a + 0.04 * math.sin(t * 3), r0 + (l - r0) * t) for t in np.linspace(0, 1, 16)]
        ink.brush(pts, w, 255, 'leaf')
    return ink.arr(0.003)


def head():
    c = K.canvas(1080, 2)
    cov = petals(c, 34, 0.70, 1.0, 0.11, 3)
    t = clamp(cov)
    vein = 0.5 + 0.5 * np.sin(c.A * 34 * 2)
    alb = mix(flat('#E8A00A', c.shape), flat('#FFD23A', c.shape), clamp(0.3 + 0.5 * (c.R - 0.7) / 0.3 + 0.2 * vein)[..., None])
    H = 0.02 * t
    col = surface(c, H, alb, WARM, rough=0.6, reach=0.06)
    c.put(col, t, H)
    disc = c.R - 0.74
    n = np.arange(1, 2200)
    rr, aa = 0.72 * np.sqrt(n / 2200), n * 2.39996323
    seeds = np.zeros(c.shape, F)
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    for r_, a_ in zip(rr, aa):
        x, y = math.sin(a_) * r_, -math.cos(a_) * r_
        px, py = (x + 1) * c.w / 2, (y + 1) * c.h / 2
        s = (0.007 + 0.012 * r_) / c.px
        dr.ellipse([px - s, py - s, px + s, py + s], fill=255)
    seeds = np.asarray(im, F) / 255
    Hs = 0.03 * blur(seeds, 1.2 * c.ss) + 0.02 * smooth(0.74, 0.5, c.R)
    salb = mix(flat('#2A1606', c.shape), flat('#6A3A10', c.shape), (seeds * (0.6 + 0.4 * smooth(0.0, 0.74, c.R)))[..., None])
    scol = surface(c, Hs, salb, WARM, rough=0.7, reach=0.08)
    c.put(scol, c.cover(disc), Hs)
    K.put(c, 'head')


def flowers():
    def one(c, k):
        cov = petals(c, 12, 0.40, 0.92, 0.26, 10 + k)
        alb = mix(flat('#F2B81E', c.shape), flat('#FFE06A', c.shape), clamp((c.R - 0.4) / 0.5)[..., None])
        if k % 2:
            alb = mix(alb, flat('#FF9A1E', c.shape), 0.35)
        col = surface(c, 0.03 * cov, alb, WARM, rough=0.6)
        c.put(col, cov)
        cen = c.R - 0.52
        c.put(surface(c, 0.05 * clamp(-cen / 0.5), flat('#4A2A0A', c.shape) * (0.8 + 0.3 * fbm(c.shape, 30, 5 + k, 2))[..., None], WARM, rough=0.7), c.cover(cen))
        return c
    plate(K, 'flowers', 2, one)


def middle():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    n = np.arange(1, 700)
    rr, aa = 0.94 * np.sqrt(n / 700), n * 2.39996323
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    for r_, a_ in zip(rr, aa):
        x, y = math.sin(a_) * r_, -math.cos(a_) * r_
        px, py = (x + 1) * c.w / 2, (y + 1) * c.h / 2
        s = (0.012 + 0.016 * r_) / c.px
        dr.ellipse([px - s, py - s, px + s, py + s], fill=255)
    seeds = np.asarray(im, F) / 255
    alb = mix(flat('#1E1004', c.shape), flat('#5A3410', c.shape), (seeds * 0.7)[..., None])
    col = surface(c, 0.02 * blur(seeds, 1.2 * c.ss), alb, WARM, rough=0.7)
    col = col * (1 - 0.35 * smooth(0.6, 0.0, c.R))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'middle')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE08A')
    c = K.canvas(40, 4, 1.0, 1.6)
    cov = Ink(c).brush([(0, 1.5), (0, -1.5)], 0.9, 255, 'leaf').arr(0.02)
    c.col[:] = rgb('#FFD23A')
    c.alpha = cov
    K.put(c, 'petal', how='png', tone=False)


K.run([head, flowers, middle])
P = dict(base='#2A1A08', accent='#F2C21E', accent2='#FFE08A', text='#FFF4D8', sub='#E8D08A', panel=('#4A2E10', '#2A1A08'), stroke='#F2C21E', tile=('#FFF4D8', '#F2DCA0'), tilestroke='#B8801A',
         ink='#2A1A08', dim=0.3, font='Candara, Segoe UI', badge='#F2C21E', badgeink='#2A1A08')
finish(K, P, sounds='celesta',
       back=[soft(1.10, 0.04, 55), img('head', 1.04, scale='0.72+0.28*outback(sat(open))', rotate='(1-sat(open))*-40+time*0.5', intro=intro(0.5, 'out', scale=0.8))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('flowers', '1.08*(1+0.06*hot-0.04*press)', frame='(i+ring)%2', rotate='time*4*hot+seed*90')],
       icon=dict(size=0.48, zoom=1.2, shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('middle', 1.0, rotate='time*-1', intro=intro(0.5, 'back', scale=0.6))],
       over=[img('petal', [0.05, 0.08], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=1, blur=4, color='black/90')),
       style=dict(open='bloom', tilt=0.3),
       onlaunch=[dict(image='petal', count=22, area='slot', life=[0.7, 1.3], size=[6, 11], speed=[80, 260], outward=True, dir=[-100, 100], gravity=160, drag=1.6, spin=[-260, 260], sway=20, swayhz=1, fadein=0, fadeout=0.5)],
       screen=dict(effect='petals', color='#F2C21E', color2='#FFE08A', density=0.6, speed=0.7, size=1.0))
