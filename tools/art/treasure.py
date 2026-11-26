"""Treasure Map: burnt parchment, islands, a compass, and a red X where you point."""
from skinkit import *

K = Kit('treasure', 'Treasure Map', 'Burnt parchment, islands and a compass; X marks your choice', ['map', 'adventure', 'paper'])
K.flag(islands=dict(cols=4), coin=dict(cols=8))
INK, RUST, SEA = '#3A2412', '#9E2A16', '#7FA39A'


def parchment(c, seed, light='#E9CF98', dark='#C49A58'):
    n = fbm(c.shape, 5, seed, 6) * 0.5 + 0.5
    m = fbm(c.shape, 40, seed + 3, 4)
    alb = mix(flat(light, c.shape), flat(dark, c.shape), clamp(n * 0.75 + 0.10 * m)[..., None])
    stains = clamp(fbm(c.shape, 3, seed + 9, 4) - 0.35)
    return mix(alb, flat('#8A5F2C', c.shape), (0.5 * stains)[..., None]) * (1 + 0.03 * fbm(c.shape, 220, seed + 1, 2))[..., None]


def island_shape(g, r, wild=0.16, n=90):
    ph = g.random(6) * TAU
    am = g.random(6) * wild * np.array([1, 0.8, 0.6, 0.4, 0.3, 0.2])
    return [(math.sin(a) * r * (1 + sum(am[k] * math.sin((k + 2) * a + ph[k]) for k in range(6))), -math.cos(a) * r * (1 + sum(am[k] * math.sin((k + 2) * a + ph[k]) for k in range(6)))) for a in np.linspace(0, TAU, n, endpoint=False)]


def mountain(ink, x, y, s):
    ink.line(wob([(x - s, y + s * 0.6), (x - s * 0.1, y - s * 0.6), (x + s * 0.25, y - s * 0.15), (x + s, y + s * 0.6)], s * 0.04, 3, 1), s * 0.09)
    for k in range(4):
        t = 0.15 + k * 0.2
        ink.line([(x - s * 0.1 + s * 0.35 * t, y - s * 0.6 + s * 1.0 * t), (x + s * 0.02 + s * 0.12 * t, y - s * 0.6 + s * 1.2 * t + s * 0.1)], s * 0.05)


def palm(ink, x, y, s):
    ink.line(bez((x, y), (x + s * 0.1, y - s * 0.4), (x - s * 0.1, y - s * 0.7), (x + s * 0.1, y - s), 10), s * 0.10)
    for a in (-1.9, -1.1, -0.3, 0.5, 1.3, 2.0):
        ink.brush(turned(bez((0, 0), (0.1, -0.3), (0.3, -0.45), (0.42, -0.2), 10), a, s, x + s * 0.1, y - s), s * 0.12)


def wave(ink, x, y, s):
    for k in range(3):
        ink.line(arcpts(s * 0.34, -1.35, 1.35, 10, x + (k - 1) * s * 0.66, y + s * 0.2), s * 0.07)


def sheet():
    c = K.canvas(1150, 2, 1.12)
    edge = c.R - 1.06 + 0.014 * fbm(c.shape, 9, 4, 5) + 0.008 * fbm(c.shape, 40, 6, 3)
    for a, r, s in ((0.75, 1.09, 0.07), (2.8, 1.085, 0.055), (4.1, 1.10, 0.085), (5.4, 1.085, 0.05)):      # bites
        x, y = c.polar(a, r)
        edge = smax(edge, -(np.hypot(c.X - x, c.Y - y) - s + 0.03 * fbm(c.shape, 14, 8, 3)), 0.02)
    alb = parchment(c, 3)
    ink = Ink(c)
    for r, w in ((0.975, 0.0042), (0.955, 0.0018), (0.905, 0.0022)):
        ink.line(wob(arcpts(r, 0, TAU, 400), 0.0012, int(r * 900), 10), w)
    for k in range(72):             # the scale round the map
        if k % 2:
            ink.poly(arcpts(0.955, k * TAU / 72, (k + 1) * TAU / 72, 4) + arcpts(0.943, k * TAU / 72, (k + 1) * TAU / 72, 4)[::-1])
    rh = Ink(c)
    for k in range(32):             # courses
        a = k * TAU / 32
        rh.line([c.polar(a, 0.30), c.polar(a, 0.905)], 0.0020 if k % 2 else 0.0032)
    g = rng(5)
    for k in range(16):
        a = (k + 0.5) * TAU / 16 + 0.1 * g.standard_normal()
        r = 0.50 if k % 2 else 0.885
        x, y = c.polar(a, r)
        if k % 5 == 0:
            mountain(ink, x, y, 0.036)
        elif k % 5 == 2 and r > 0.8:
            palm(ink, x, y, 0.060)
        else:
            wave(ink, x, y, 0.040)
    # a sea serpent
    for k, (dx, s) in enumerate(((0, 1.0), (0.062, 0.8), (0.112, 0.6))):
        x, y = c.polar(3.55, 0.855)
        ink.line(arcpts(0.026 * s, -1.5, 1.5, 16, x - dx, y), 0.0085 * s)
        ink.line(arcpts(0.026 * s, -1.5, 1.5, 16, x - dx, y - 0.0005), 0.004)
    x, y = c.polar(3.55, 0.855)
    ink.brush(bez((x + 0.026, y), (x + 0.045, y - 0.03), (x + 0.03, y - 0.06), (x + 0.062, y - 0.062), 16), 0.020, shape='tail')
    cov = np.maximum(ink.arr(0.0006), 0.42 * rh.arr(0.0006))
    worn = clamp(1.05 - 0.6 * clamp(fbm(c.shape, 24, 11, 3)))
    alb = mix(alb, flat(INK, c.shape), (cov * worn * 0.85)[..., None])
    # shallow water tinted along the border
    tint = smooth(0.42, 0.80, c.R) * smooth(0.92, 0.80, c.R) * clamp(0.5 + fbm(c.shape, 8, 14, 4))
    alb = mix(alb, alb * rgb('#B5D2C4') * 1.15, (0.42 * tint)[..., None])
    burn = smooth(0.0, -0.055, edge)
    char = smooth(-0.012, -0.001, edge + 0.006 * fbm(c.shape, 60, 2, 3))
    alb = alb * mix(flat('#5A3313', c.shape), np.ones(c.shape + (3,), F), clamp(burn * 1.05)[..., None])
    alb = mix(alb, flat('#120A05', c.shape), char[..., None])
    H = 0.010 * fbm(c.shape, 5, 21, 4) + 0.0012 * fbm(c.shape, 120, 22, 3)
    for v, at in ((c.X * 0.96 + c.Y * 0.1, -0.34), (c.X * 0.97 - c.Y * 0.08, 0.40), (c.Y + c.X * 0.05, 0.05)):
        H += 0.016 * np.exp(-np.abs(v - at) / 0.012)
        alb = mix(alb, flat('#F2DFB4', c.shape), (0.22 * gauss(v - at, 0.003) * clamp(0.5 + fbm(c.shape, 60, 9, 2)))[..., None])
    H += 0.018 * smooth(-0.05, 0.0, edge)                # the edge curls up
    col = surface(c, H, alb, WARM, rough=0.85, reach=0.08, strength=0.9)
    c.put(col, c.cover(edge), H)
    K.put(c, 'sheet', exposure=1.10)


def islands():
    ims = []
    for k in range(4):
        c = K.canvas(260, 3)
        g = rng(40 + k)
        d = c.poly(island_shape(g, 0.74, 0.12))
        alb = np.zeros(c.shape + (3,), F)
        land = smooth(0.012, -0.012, d)
        shore = smooth(0.20, 0.0, d) * (1 - land)
        col = mix(flat('#E7C98B', c.shape), flat('#A9B072', c.shape), clamp(smooth(-0.04, -0.30, d) * (0.65 + 0.35 * fbm(c.shape, 7, k, 3)))[..., None])
        col = mix(col, flat('#D8B878', c.shape), clamp(0.4 * fbm(c.shape, 12, k + 5, 3))[..., None])
        sea = flat('#5E9A93', c.shape)
        rings = np.maximum(gauss(d - 0.10, 0.011), 0.7 * gauss(d - 0.175, 0.009)) * (0.6 + 0.4 * (fbm(c.shape, 20, k + 2, 2) > -0.3))
        out = mix(sea, col, land[..., None])
        edge = smooth(0.026, 0.010, np.abs(d + 0.004 * fbm(c.shape, 60, k, 2)))
        hat = (np.abs(((c.X + c.Y) * 14) % 1 - 0.5) < 0.10) * smooth(0.0, -0.03, d) * smooth(-0.13, -0.07, d) * ((c.X + c.Y) > 0)
        lines = np.maximum(edge, np.maximum(hat * 0.55, rings * 0.75))
        out = mix(out, flat(INK, c.shape), lines[..., None])
        a = clamp(np.maximum(land, np.maximum(0.55 * shore, lines)))
        c.col, c.alpha = out.astype(F), a.astype(F)
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'islands', how='png')


def compass():
    c = K.canvas(560, 2)
    ink, red, pale = Ink(c), Ink(c), Ink(c)
    for k in range(16):
        a = k * TAU / 16
        L = 0.985 if k % 4 == 0 else 0.86 if k % 2 == 0 else 0.76
        w = 0.15 if k % 4 == 0 else 0.11 if k % 2 == 0 else 0.07
        tip, l, r, o = turned([(0, -L)], a)[0], turned([(-w, -0.52)], a)[0], turned([(w, -0.52)], a)[0], (0, 0)
        (red if k % 4 == 0 else ink).poly([tip, l, o])
        pale.poly([tip, r, o])
        ink.line([tip, l, r], 0.008, closed=True)
    d = c.R - 0.665
    star = np.maximum(np.maximum(ink.arr(), red.arr()), pale.arr())
    col = flat('#EBD3A0', c.shape)
    col = mix(col, flat('#EFDDB2', c.shape), pale.arr(0.002)[..., None])
    col = mix(col, flat(RUST, c.shape), (red.arr(0.002) * 0.92)[..., None])
    col = mix(col, flat(INK, c.shape), (ink.arr(0.002) * 0.9)[..., None])
    disc = parchment(c, 31, '#F0DCAD', '#D9B678')
    col = mix(col, disc, smooth(0.006, -0.006, d)[..., None])
    for r, w in ((0.665, 0.013), (0.615, 0.006)):
        col = mix(col, flat(INK, c.shape), smooth(w, w * 0.4, np.abs(c.R - r))[..., None] * 0.9)
    tick = Ink(c)
    for k in range(48):
        tick.line([turned([(0, -0.622)], k * TAU / 48)[0], turned([(0, -0.658)], k * TAU / 48)[0]], 0.007 if k % 4 else 0.014)
    col = mix(col, flat(INK, c.shape), (0.85 * tick.arr())[..., None])
    worn = 1 + 0.05 * fbm(c.shape, 30, 4, 3)
    c.put(col * worn[..., None], clamp(np.maximum(star, smooth(0.006, -0.006, d))))
    K.put(c, 'compass', tone=False)
    c = K.canvas(120, 3, 1.0, 1.3)          # the pointer on its rim
    red = Ink(c).poly([(0, -1.25), (0.62, 0.9), (0, 0.45), (-0.62, 0.9)]).arr(0.01)
    c.col = mix(flat('#C23A20', c.shape), flat('#7C1B0C', c.shape), smooth(-0.02, 0.02, c.X)[..., None])
    c.alpha = red
    K.put(c, 'needle', how='png', tone=False)


def bits():
    c = K.canvas(260, 3)
    ink = Ink(c)
    ink.brush(wob(lerpts((-0.78, -0.82), (0.80, 0.78), 24), 0.02, 3), 0.30, shape='head', seed=4, rough=0.05)
    ink.brush(wob(lerpts((0.80, -0.80), (-0.76, 0.80), 24), 0.02, 5), 0.28, shape='head', seed=6, rough=0.05)
    a = ink.arr(0.006) * clamp(1.15 - 0.7 * clamp(fbm(c.shape, 30, 3, 4)))
    c.col = mix(flat('#B3200F', c.shape), flat('#D8472C', c.shape), clamp(0.5 + fbm(c.shape, 10, 2, 3))[..., None])
    c.alpha = a.astype(F)
    K.put(c, 'cross', how='png', tone=False)
    c = K.canvas(150, 4)                     # a little ship
    ink, pale = Ink(c), Ink(c)
    hull = bez((-0.72, 0.30), (-0.5, 0.75), (0.4, 0.78), (0.74, 0.22), 16) + [(0.70, 0.20), (-0.70, 0.28)]
    pale.poly(hull)
    ink.line(hull, 0.06, closed=True)
    for x, h in ((-0.25, 0.85), (0.22, 0.95)):
        ink.line([(x, 0.3), (x, 0.3 - h)], 0.05)
        sail = bez((x - 0.02, 0.22 - h * 0.15), (x + 0.42, 0.1 - h * 0.2), (x + 0.42, -h * 0.5), (x - 0.02, 0.30 - h), 14)
        pale.poly(sail)
        ink.line(sail, 0.05, closed=True)
    ink.poly([(0.22, -0.65), (0.22, -0.88), (0.52, -0.76)])
    for y in (0.40, 0.52):
        ink.line(wob([(-0.62, y), (0, y + 0.06), (0.6, y - 0.03)], 0.01, 2, 1), 0.03)
    for k in range(4):
        ink.line(arcpts(0.17, -1.4, 1.4, 8, -0.6 + k * 0.4, 0.82), 0.05)
    a1, a2 = ink.arr(0.004), pale.arr(0.004)
    c.col = mix(flat('#EFDDB2', c.shape), flat(INK, c.shape), a1[..., None])
    c.alpha = np.maximum(a1, a2 * 0.95).astype(F)
    K.put(c, 'ship', how='png', tone=False)
    ims = []
    for k in range(8):
        c = K.canvas(64, 3)
        w = abs(math.cos(k * math.pi / 8)) * 0.90 + 0.08
        r = np.hypot(c.X / w, c.Y)
        H = np.where(r < 0.74, 0.10 + 0.02 * np.cos(np.arctan2(c.X / w, -c.Y) * 5), 0.16) * smooth(0.96, 0.88, r)
        c.put(metal(c, H, GOLD, rough=0.22, grime=0.4, reach=0.2), c.cover((r - 0.92) * w), H)
        ims.append(c.image())
    K.sheet(ims, 8, 'coin')


K.run([sheet, islands, compass, bits])
K.sounds('page')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#E3C48A', accent='#B3200F', accent2='#3A2412', text='#3A2412', border='#7A5426', opacity=0.98, corner=8, font='Palatino Linotype', open='unfold', speed=1, hoverGrow=3,
               iconZoom=1.14, glow=0, tilt=0.3, pointer=False, burst=False, shadow=0.6, dim=0.32),
    wheel=dict(hub=96, thickness=94, gap=5, ringgap=8, rim=34, icon=44, crowd=1.5, area=1.26, hubkeep=0.6),
    colors=dict(ink=INK, rust=RUST, paper='#EBD3A0'), fonts=dict(title='Palatino Linotype, Book Antiqua, Georgia', hand='Gabriola, Palatino Linotype'),
    back=[soft(1.16, 0.03, 62, 0.84), img('sheet', 1.12, rotate='(1-open)*-14', intro=intro(0.32, 'out', scale=0.80, rotate=-10)),
          img('ship', 0.095, angle='time*5', radius=0.965, rotate='6*sin(time*1.3)', y='0.006*sin(time*2.1)', opacity='smooth(0.3,0.7,time)')],
    slot=dict(intro=intro(0.34, 'back', 0.06, scale=0.2, stagger=0.02, order='random'),
              under=[img('islands', 1.28, frame='(i+ring*2)%4', rotate='i*67', opacity=0.96), img('cross', '1.02*outback(sat(hot*1.2))', opacity='sat(hot*3)', rotate='seed*16-8')],
              icon=dict(size=1.04, zoom=1.18, shadow=dict(x=0, y=2, blur=3, color='#2A1608/55')),
              over=[dict(shape='circle', y=0.86, size=0.15, fill=RUST, stroke='#F0DCAD', width=1.4, when='running'), dict(shape='circle', y=0.86, size=0.07, fill='#FFE7B0', when='active')]
              + [dict(shape='circle', x=0.66, y=-0.66, size=0.26, fill='#EFDDB2', stroke=INK, width=1.3, when='numbers && number<10 && !kid'), dict(text='{number}', x=0.66, y=-0.67, em=0.32, color='ink', font=T, weight=700, when='numbers && number<10 && !kid')] + groupmark(INK, -0.92), marks=False, chevron=False, badge=False),
    over=[dict(shape='rect', **{'in': 'px'}, copies=9, angle='sel', radius='hub+5+j*(radius-hub-60)/m', turns=True, size=[3.6, 8], corner=1.6, fill='#A3200F', opacity='on*(0.45+0.55*step(0.45,fract(j/m*1.5-time*1.1)))*step(radius*0+hub+5+j*(radius-hub-60)/m, ringin+8)'),
          img('needle', [0.15, 0.195], **{'in': 'hub'}, angle='sel', radius=1.07, turns=True, opacity='on', scale='0.5+0.5*on')],
    hub=[img('compass', 1.12, rotate='sel*0.12+2*sin(time*0.7)', intro=intro(0.42, 'back', scale=0.4, rotate=-160))] + words('ink', 'rust', T, px=16.5, y=-0.04, box=(1.02, 0.44), subpx=10.5, suby=0.25, clockpx=27, clocky=-0.07, datey=0.20, datepx=11.5),
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=26, text='ink', fill='#C9A263/80', on='#B3200F'),
    pinbutton={'in': 'hub', 'x': -0.17, 'y': 0.45, 'size': 10.5}, settingsbutton={'in': 'hub', 'x': 0.17, 'y': 0.45, 'size': 10.5},
    panel=dict(fill={'type': 'radial', 'radius': 1.4, 'stops': [[0, '#F0DCAD'], [0.7, '#E0C187'], [1, '#B98D4C']]}, stroke='#5A3313', width=2.5, corner=8, text='ink'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#F0DCAD'], [1, '#D9B678']]}, stroke='#5A3313', width=1.8, corner=5, text='ink'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#F0DCAD'], [1, '#D3AE6C']]}, stroke='#5A3313', width=2, corner=5, text='ink'),
    onlaunch=[dict(image='coin', count=26, area='slot', life=[0.6, 1.1], size=[9, 17], speed=[180, 520], outward=True, dir=[-70, 70], gravity=800, drag=1.4, spin=[-300, 300], fadein=0, fadeout=0.25)],
    onhover=[dict(color='#8A5F2C', count=5, area='slot', life=[0.3, 0.6], size=[1.5, 3], speed=[20, 70], outward=True, dir=[-70, 70], drag=2, fadein=0, fadeout=0.7)])
