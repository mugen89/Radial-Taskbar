"""Grimoire: an open spellbook by candlelight. The signs are made up; they mean nothing in any alphabet."""
from skinkit import *

K = Kit('grimoire', 'Grimoire', 'An open spellbook by candlelight, with a circle that wakes up', ['magic', 'book', 'fantasy'], 'Font MedievalSharp: SIL Open Font License, see OFL.txt')
K.flag(flame=dict(light=True, cols=4), glowrunes='light', glowstar='light', seal='light', warm='light', halo='light', signs=dict(cols=4, rows=2, light=True))
INK = '#2B170B'
CANDLE = Studio(lights=[((-0.62, -0.62, 0.48), 0.50, '#FFD9A0', 3.6), ((0.70, -0.60, 0.42), 0.40, '#FFC27A', 2.0), ((0.1, 0.9, 0.4), 0.4, '#8A93C8', 0.35)], sky='#8A6A4A', floor='#120A06', ambient=0.42)


def sign(g):
    """One made-up letter: strokes in a box from -0.5 to 0.5."""
    s = [[(-0.22 if g.random() < 0.5 else 0.0, -0.5), (-0.22 if g.random() < 0.5 else 0.0, 0.5)]]
    ys = [-0.5, -0.25, 0.0, 0.25, 0.5]
    for _ in range(2 + int(g.random() * 2)):
        a, b = ys[int(g.random() * 5)], ys[int(g.random() * 5)]
        s.append([(-0.22, a), (0.26, b)])
        if g.random() < 0.4:
            s.append([(0.26, b), (-0.02, min(0.5, b + 0.35))])
    if g.random() < 0.35:
        s.append(arcpts(0.14, 0, TAU, 12, 0.10, ys[int(g.random() * 5)] * 0.6))
    return s


def ring_signs(ink, n, r, size, seed, w):
    g = rng(seed)
    for k in range(n):
        a = k * TAU / n
        x, y = math.sin(a) * r, -math.cos(a) * r
        for st in sign(g):
            ink.line(turned(st, a, size, x, y), w)


def book():
    asp = 0.80
    c = K.canvas(1250, 2, 1.30, asp)
    W, HH = 1.26, 0.985
    cover = c.box(W, HH, r=0.05)
    n = fbm(c.shape, 30, 5, 4)
    leather = mix(flat('#4A2313', c.shape), flat('#2A120A', c.shape), clamp(0.5 + 0.6 * fbm(c.shape, 5, 3, 4))[..., None])
    H = bevel(cover, 0.03, 0.035) + 0.0035 * n
    # tooled border
    H = H - 0.006 * smooth(0.007, 0.002, np.abs(cover + 0.030)) - 0.004 * smooth(0.005, 0.001, np.abs(cover + 0.044))
    col = surface(c, H, leather, CANDLE, rough=0.5, clear=0.12)
    # brass corners
    cd = np.minimum(np.abs(c.X) - (W - 0.20), 9)
    q = smax(-(np.abs(c.X) + np.abs(c.Y) * 1.0 - (W + HH - 0.23)), cover + 0.004, 0.01)
    hb = bevel(q, 0.012, 0.03) + H
    r = np.hypot(np.abs(c.X) - (W - 0.075), np.abs(c.Y) - (HH - 0.075))
    hb = np.where(r < 0.026, hb + dome(r, 0.027, 0.025), hb)
    br = metal(c, hb, OLD_BRASS, rough=0.3, grime=0.7, studio=CANDLE)
    col = mix(col, br, c.cover(q)[..., None])
    H = np.where(q < 0, hb, H)
    c.put(col, c.cover(cover), H)
    # the pages: a block on each side, rising toward the fold
    x = np.abs(c.X)
    page = np.maximum(c.box(W - 0.085, HH - 0.085, r=0.012) + 0.003 * fbm(c.shape, 60, 8, 2), -9)
    u = clamp(x / (W - 0.085))
    hp = 0.10 * np.sqrt(clamp(u * 6)) * (1 - 0.25 * u) + 0.02
    edge = smooth(0.0, 0.03, -page)
    leaves = 0.004 * np.sin(x * 900) * smooth(W - 0.17, W - 0.11, x)
    Hp = 0.03 + hp * edge + leaves * 0.4 + 0.006 * fbm(c.shape, 4, 12, 3)
    tint = fbm(c.shape, 6, 15, 5) * 0.5 + 0.5
    alb = mix(flat('#E3CB98', c.shape), flat('#B58E55', c.shape), clamp(tint * 0.8 + 0.5 * smooth(0.10, 0.0, -page))[..., None])
    alb = alb * (1 - 0.10 * (np.sin(x * 620) > 0.2) * smooth(W - 0.16, W - 0.12, x))[..., None]
    alb = mix(alb, flat('#8A5A28', c.shape), (0.6 * clamp(fbm(c.shape, 4, 19, 4) - 0.45))[..., None])
    # writing in the margins
    ink = Ink(c)
    g = rng(7)
    for side in (-1, 1):
        for row in range(26):
            yy = -0.80 + row * 0.064
            lo = math.sqrt(max(0, 0.96 ** 2 - yy * yy)) + 0.05
            hi = 1.10
            xx = lo
            while xx < hi - 0.02:
                ll = 0.02 + 0.05 * g.random()
                if xx + ll > hi:
                    break
                pts = [(side * (xx + ll * t / 8), yy + 0.005 * g.standard_normal()) for t in range(9)]
                ink.line(pts, 0.0036, 200)
                xx += ll + 0.014
    alb = mix(alb, flat(INK, c.shape), (0.62 * ink.arr(0.0012))[..., None])
    fold = gauss(c.X, 0.045)
    col = surface(c, Hp, alb, CANDLE, rough=0.85, reach=0.12, strength=0.9) * (1 - 0.55 * fold)[..., None]
    c.put(col, c.cover(page), Hp)
    # a ribbon
    rb = c.poly([(0.015, -HH + 0.06), (0.045, -HH + 0.06), (0.05, HH + 0.02), (0.033, HH - 0.02), (0.016, HH + 0.02)])
    c.put(mix(flat('#8E1420', c.shape), flat('#5A0A12', c.shape), clamp(0.5 + 0.5 * np.sin(c.X * 300))[..., None]) * 0.8, c.cover(np.maximum(rb, -(np.abs(c.Y) - HH * 0.93))))
    K.put(c, 'book', exposure=1.02, quality=88)


def magic():
    """The circle, once in ink and once in light."""
    for name, fn, size in (('runes', lambda ink: [ring_signs(ink, 40, 0.925, 0.072, 5, 0.0075)] + [ink.line(arcpts(r, 0, TAU, 300), w) for r, w in ((0.985, 0.0075), (0.870, 0.005), (0.968, 0.003))], 900),
                           ('star', lambda ink: _star(ink), 800)):
        c = K.canvas(size, 2)
        ink = Ink(c)
        fn(ink)
        a = ink.arr(0.0008)
        dry = clamp(1.12 - 0.55 * clamp(fbm(c.shape, 50, 4, 3)))
        c.col[:] = rgb(INK)
        c.alpha = (a * dry * 0.88).astype(F)
        K.put(c, name, how='png', tone=False)
        light(K, 'glow' + name, size * 2 // 3, lambda q, f=fn: _lit(q, f), '#FFB648')


def _lit(q, fn):
    ink = Ink(q)
    fn(ink)
    a = ink.arr()
    return clamp(1.2 * a + 0.9 * blur(a, 0.008 / q.px) + 1.1 * blur(a, 0.025 / q.px))


def _star(ink):
    R = 0.955
    for n, step in ((7, 3), (7, 2)):
        pts = [(math.sin(k * step * TAU / n) * R, -math.cos(k * step * TAU / n) * R) for k in range(n)]
        ink.line(pts, 0.0062, closed=True)
    ink.line(arcpts(R, 0, TAU, 240), 0.006)
    for k in range(7):
        x, y = math.sin(k * TAU / 7) * R, -math.cos(k * TAU / 7) * R
        ink.line(arcpts(0.042, 0, TAU, 24, x, y), 0.006)
        ink.dot(x, y, 0.014)


def seals():
    c = K.canvas(320, 3)                     # the drawn ring round every entry
    ink = Ink(c)
    for r, w in ((0.93, 0.022), (0.80, 0.011)):
        ink.line(wob(arcpts(r, 0, TAU, 160), 0.004, int(r * 100), 8), w)
    for k in range(24):
        a = k * TAU / 24
        if k % 3 == 0:
            ink.dot(*turned([(0, -0.865)], a)[0], 0.026)
        else:
            ink.line(turned([(0, -0.835), (0, -0.895)], a), 0.012)
    a = ink.arr(0.004)
    disc = smooth(0.80, 0.76, c.R)
    c.col = mix(flat('#F3E2B8', c.shape), flat(INK, c.shape), a[..., None])
    c.alpha = np.maximum(a * 0.92, disc * 0.62).astype(F)
    K.put(c, 'ring', how='png', tone=False)
    light(K, 'seal', 320, lambda q: _seal(q), '#FFC25A')
    # what is under the words
    c = K.canvas(460, 2)
    ink = Ink(c)
    for r, w in ((0.975, 0.016), (0.93, 0.007), (0.745, 0.009)):
        ink.line(wob(arcpts(r, 0, TAU, 260), 0.002, int(r * 70), 10), w)
    ring_signs(ink, 22, 0.838, 0.125, 11, 0.0165)
    a = ink.arr(0.003)
    alb = mix(flat('#F2DFB2', c.shape), flat('#D3AE70', c.shape), clamp(0.4 + 0.5 * fbm(c.shape, 5, 2, 5) + 0.5 * smooth(0.5, 1.0, c.R))[..., None])
    c.put(mix(alb, flat(INK, c.shape), (0.9 * a)[..., None]) * 0.92, c.cover(c.R - 0.985))
    K.put(c, 'hub', tone=False)


def _seal(q):
    ink = Ink(q)
    for r, w in ((0.90, 0.03), (0.76, 0.014)):
        ink.line(arcpts(r, 0, TAU, 160), w)
    pts = [(math.sin(k * 2 * TAU / 5) * 0.76, -math.cos(k * 2 * TAU / 5) * 0.76) for k in range(5)]
    ink.line(pts, 0.016, closed=True)
    for k in range(10):
        ink.dot(*turned([(0, -0.83)], k * TAU / 10)[0], 0.03)
    a = ink.arr()
    return clamp((1.1 * a + 0.8 * blur(a, 0.03 / q.px) + 0.8 * blur(a, 0.09 / q.px)) * smooth(1.0, 0.94, q.R))


def candle():
    c = K.canvas(260, 3)
    H = lathe(c, [(0, 0.22), (0.10, 0.20), (0.34, 0.22), (0.40, 0.26), (0.46, 0.20), (0.50, 0.05), (0.56, 0.05), (0.84, 0.03), (0.92, 0.10), (0.97, 0.10), (1.0, 0.03)], 0.02)
    H = H + 0.015 * fbm(c.shape, 8, 3, 3) * (c.R < 0.5)
    wax = smooth(0.505, 0.49, c.R + 0.02 * fbm(c.shape, 9, 2, 3))
    col = mix(metal(c, H, OLD_BRASS, rough=0.28, grime=0.6, studio=CANDLE), surface(c, H, flat('#F1DFB9', c.shape), CANDLE, rough=0.5, clear=0.3) + rgb('#FF9A3A') * (0.55 * gauss(c.R, 0.26))[..., None], wax[..., None])
    c.put(col, c.cover(c.R - 0.97), H)
    K.put(c, 'candle')
    flames(K, 'flame', 12, 110, 1.8)
    light(K, 'warm', 256, lambda q: (1 - smooth(0.0, 1.0, q.R)) ** 1.6, '#FFA54A')
    halo(K, 'halo', 220, 2.2, 0.1, '#FFC25A')
    ims = []
    g = rng(3)
    for k in range(8):
        c = K.canvas(64, 3)
        ink = Ink(c)
        for st in sign(g):
            ink.line(turned(st, 0, 1.5), 0.15)
        a = ink.arr(0.02)
        c.col = (rgb('#FFC25A') * clamp(a + 0.7 * blur(a, 0.12 / c.px))[..., None]).astype(F)
        c.alpha[:] = 1
        ims.append(c.image(tone=False, dither=False))
    K.sheet(ims, 4, 'signs', how='jpg')


def shade_():
    boxshadow(K, 'shadow', 1.0, 0.78, 0.05, 1.22, 0.08, 0.66, 192, 0.82)


K.run([book, magic, seals, candle, shade_])
K.font('medievalsharp', 'MedievalSharp.ttf')
K.sounds('page')
T = 'title'
flick = '(0.82+0.18*noise(time*7+%d))'
def candle_at(x, y, s):
    return [soft(0.20, y + 0.03, 60, 0.75, x=x + 0.02), img('candle', 0.17, x=x, y=y), img('warm', 0.52, x=x, y=y, opacity='0.34*sat(open)*' + flick % s), img('flame', [0.085, 0.153], x=x, y=y - 0.045, pivot=[0.5, 0.72], frame='floor(time*15+%d)%%12' % (s * 5), opacity='1.15*sat(open)', scale=flick % s)]
K.write(
    style=dict(shape='orb', material='solid', base='#2A150B', accent='#FFB648', accent2='#C4501E', text='#F6E3B8', border='#A8783A', opacity=0.97, corner=8, font='MedievalSharp', open='bloom', speed=1, hoverGrow=3,
               iconZoom=1.14, glow=0.5, tilt=0.3, pointer=False, burst=False, shadow=0.6, dim=0.44),
    wheel=dict(hub=94, thickness=92, gap=6, ringgap=10, rim=30, icon=43, crowd=1.5, area=[1.72, 1.36, 1.72, 1.36], hubkeep=0.66),
    colors=dict(ink=INK, flame='#FFB648', page='#F2DFB2'), fonts=dict(title=dict(file='MedievalSharp.ttf', family='MedievalSharp')),
    back=[img('shadow', [1.54, 1.263], x=0.015, y=0.05, opacity='sat(open)'),
          img('book', [1.30, 1.04], intro=intro(0.30, 'out', scale=0.80)),
          img('star', 0.90, rotate='time*-3', opacity='0.32*smooth(0.1,0.4,time)'), img('glowstar', 0.90, rotate='time*-3', opacity='0.04+0.16*on*(0.7+0.3*wave(time*0.7))+launch*0.9'),
          img('runes', 1.0, rotate='time*4+(1-open)*70', opacity='smooth(0.05,0.35,time)'), img('glowrunes', 1.0, rotate='time*4+(1-open)*70', opacity='(1-smooth(0.15,0.8,time))*0.9+0.06+0.22*on+launch')],
    ring=[dict(shape='arc', **{'in': 'px', 'from': 0}, r='(ringin+ringout)/2', to='360*outcubic(sat(time*2))', stroke=INK + '/45', width=1.4)],
    slot=dict(intro=intro(0.32, 'back', 0.08, scale=0.3, rotate=-90, stagger=0.022, order='ring'),
              under=[img('halo', 1.8, opacity='0.30*hot+launch'), img('ring', '1.06*(1+0.03*hot)', rotate='i*31-time*4', opacity=1), img('seal', '1.12+0.06*hot', rotate='time*40', opacity='sat(hot)*(0.85+0.15*noise(time*8))+launch*2')],
              icon=dict(size=1.04, zoom=1.16, tone='ink', hot='original', ink='#24120A', paper='#F0DDB0'),
              over=running('#8E3B16', '#FFB648', 0.90, 0.15) + badge(INK, '#F6E3B8', T, stroke='#A8783A') + groupmark(INK, -0.96, 0.13), marks=False, chevron=False, badge=False),
    over=[img('halo', 0.36, **{'in': 'hub'}, angle='sel', radius=1.02, opacity='on*(0.9+0.1*noise(time*9))'), dict(shape='poly', **{'in': 'hub'}, angle='sel', radius=1.03, turns=True, points=[[-0.065, 0.05], [0, -0.07], [0.065, 0.05]], closed=True, fill='#FFD27A', opacity='on', glow=5, glowcolor='#FFB648')],
    hub=[img('hub', 1.0, rotate='sel*0.1', intro=intro(0.36, 'back', scale=0.4, rotate=-120))] + words('ink', '#8E3B16', T, px=19, y=-0.05, box=(1.18, 0.50), subpx=12.5, suby=0.28, clockpx=32, clocky=-0.07, datey=0.22, datepx=13.5, weight=400),
    front=candle_at(-1.18, -0.80, 1) + candle_at(1.18, 0.78, 2) + [img('warm', 0.95, x=-0.4, y=-0.3, opacity='0.06*' + flick % 3)],
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=20, text='ink', fill='#C9A263/70', on='#A8481A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#3A1D10'], [1, '#1E0E07']]}, stroke={'type': 'linear', 'stops': [[0, '#E0B565'], [0.5, '#6B4A1E'], [1, '#C79A4E']]}, width=2.4, corner=9, text='#F6E3B8'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#F2DFB2'], [1, '#D3AE70']]}, stroke='#5A3313', width=1.8, corner=5, text='ink'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#F2DFB2'], [1, '#CDA76A']]}, stroke='#5A3313', width=2, corner=6, text='ink'),
    particles=[dict(color='#FFB648', light=True, rate=3, max=26, area='wheel', life=[1.6, 3.2], size=[1.5, 3], speed=[4, 16], dir=[-30, 30], gravity=-14, sway=14, swayhz=0.6, fadein=0.3, fadeout=0.5)],
    onlaunch=[dict(image='signs', light=True, count=26, area='slot', life=[0.6, 1.2], size=[12, 24], speed=[80, 360], outward=True, dir=[-110, 110], drag=2.4, gravity=-60, spin=[-120, 120], fadein=0.05, fadeout=0.6)],
    onhover=[dict(image='signs', light=True, count=3, area='slot', life=[0.5, 0.9], size=[8, 13], speed=[20, 70], outward=True, dir=[-70, 70], gravity=-30, drag=1.5, fadein=0.1, fadeout=0.6, opacity=0.8)])
