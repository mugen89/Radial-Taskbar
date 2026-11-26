"""Pumpkin Night: a carved pumpkin by candlelight, gravestones, bats, fog and a big moon."""
from skinkit import *

K = Kit('pumpkin', 'Pumpkin Night', 'A carved pumpkin by candlelight, gravestones, bats and fog under a big moon', ['season', 'spooky', 'night'], 'Font Metamorphous: SIL Open Font License, see OFL.txt')
K.flag(bat=dict(cols=2), glow='light', warm='light', halo='light', face='light', stones=dict(cols=3))
MOON = Studio(lights=[((-0.50, -0.72, 0.50), 0.40, '#D6DEFF', 3.2), ((0.70, 0.30, 0.50), 0.40, '#FF8A2A', 1.0), ((0.1, 0.9, 0.4), 0.4, '#6A4AA8', 0.5)], sky='#5A5A8A', floor='#0A0812', ambient=0.42)


def night():
    c = K.canvas(1100, 2)
    t = clamp((c.Y + 1) / 2)
    col = ramp(t, '#120A2E', '#2A1450', '#5A2468', '#8A3A5A')
    col = col + (stars(c, 200, 4, 0.2, 0.96, 0.0032) * smooth(0.2, -0.5, c.Y))[..., None]
    m = np.hypot(c.X + 0.02, c.Y + 0.30)        # the moon, behind everything
    mc = flat('#F6E7B8', c.shape) * (0.90 + 0.10 * fbm(c.shape, 5, 3, 5))[..., None]
    d1 = worley(c.X, c.Y, 5.5, 4)
    mc = mc * (1 - 0.12 * smooth(0.30, 0.20, d1))[..., None]
    col = col + rgb('#FFD98A') * (0.50 * gauss(np.maximum(0, m - 0.56), 0.20))[..., None]
    col = mix(col, mc, c.cover(m - 0.56)[..., None])
    # clouds
    cl = smooth(0.15, 0.6, fbm(c.shape, 3, 9, 5) + 0.25 - 2.2 * np.abs(c.Y + 0.15))
    col = mix(col, flat('#2A1450', c.shape), (0.6 * cl)[..., None])
    # bare trees, reaching in from the sides
    g = rng(5)
    ink = Ink(c)
    def branch(x, y, a, L, w, n):
        if n == 0 or L < 0.015:
            return
        pts = [(x, y)]
        q = a
        for _ in range(5):
            q += 0.22 * g.standard_normal()
            x, y = x + math.sin(q) * L / 5, y - math.cos(q) * L / 5
            pts.append((x, y))
        for i in range(5):
            ink.line(pts[i:i + 2], w * (1 - 0.10 * i))
        for k in range(2 + int(g.random() * 2)):
            branch(x, y, q + (0.75 * (g.random() - 0.5) * 2), L * (0.62 + 0.2 * g.random()), w * 0.62, n - 1)
        if n > 2:
            px, py = pts[3]
            branch(px, py, q + (0.9 if g.random() < 0.5 else -0.9), L * 0.6, w * 0.5, n - 2)
    for x, a in ((-0.80, 0.28), (0.82, -0.25), (-0.60, -0.1), (0.62, 0.15)):
        branch(x, 0.62, a, 0.34, 0.050 if abs(x) > 0.7 else 0.030, 6)
    # hills and a crooked fence
    hill = 0.60 + 0.05 * np.sin(c.X * 3.1 + 0.6) + 0.02 * fbm(c.shape, 8, 12, 3) + 0.10 * c.X ** 2 * 0
    land = c.cover(hill - c.Y)
    for k in range(34):
        x = -0.97 + k * 1.94 / 33
        h = 0.13 + 0.03 * g.random()
        t2 = 0.10 * (g.random() - 0.5)
        y0 = 0.64 + 0.05 * math.sin(x * 3.1 + 0.6)
        ink.poly([(x - 0.008, y0), (x + 0.008, y0), (x + 0.008 + t2 * h, y0 - h), (x + t2 * h, y0 - h - 0.025), (x - 0.008 + t2 * h, y0 - h)])
    for dy in (0.05, 0.10):
        ink.line([(x, 0.64 + 0.05 * math.sin(x * 3.1 + 0.6) - dy) for x in np.linspace(-0.98, 0.98, 60)], 0.008)
    sil = np.maximum(ink.arr(0.0005), land)
    ground = ramp(clamp((c.Y - 0.5) / 0.5), '#0E0820', '#1A1024', '#100A18')
    col = mix(col, ground, sil[..., None])
    rim = smooth(0.945, 0.965, c.R)
    col = mix(col, flat('#0A0612', c.shape) * (0.8 + 0.6 * fbm(c.shape, 40, 3, 3))[..., None], rim[..., None])
    col = col * (1 - 0.35 * smooth(0.75, 1.0, c.R))[..., None]
    c.put(col, c.cover(c.R - 0.99))
    K.put(c, 'night', tone=False, quality=87)
    for name, seed in (('fog', 8),):
        c = K.canvas(520, 1, 1.0, 0.42)
        n = fbm(c.shape, 5, seed, 5) * 0.5 + 0.5
        c.col[:] = rgb('#CFC6E6')
        c.alpha = (clamp(n * 1.2 - 0.25) * smooth(1.0, 0.45, np.abs(c.X)) * smooth(1.0, 0.2, np.abs(c.Y / 0.42)) * 0.75).astype(F)
        K.put(c, name, how='png', tone=False)


def stones():
    ims = []
    for k in range(3):
        c = K.canvas(250, 3)
        top = [c.box(0.66, 0.62, 0, 0.18, r=0.06), None, None]
        if k == 0:
            d = smin(c.box(0.64, 0.56, 0, 0.26, r=0.05), np.hypot(c.X, c.Y + 0.20) - 0.64, 0.02)
        elif k == 1:
            d = np.minimum(c.box(0.64, 0.70, 0, 0.12, r=0.05), np.minimum(c.box(0.50, 0.10, 0, -0.62, r=0.04), c.box(0.34, 0.08, 0, -0.76, r=0.04)))
        else:
            d = c.poly([(-0.66, 0.82), (-0.66, -0.42), (-0.40, -0.72), (0, -0.84), (0.40, -0.72), (0.66, -0.42), (0.66, 0.82)]) - 0.02
        n = fbm(c.shape, 14, 20 + k, 5)
        d = d + 0.010 * n
        H = bevel(d, 0.10, 0.13) + 0.010 * n + 0.005 * fbm(c.shape, 90, 30 + k, 3)
        inner = smooth(0.012, 0.004, np.abs(d + 0.12))
        H = H - 0.030 * inner
        crack = gauss(c.X * 0.8 + c.Y * 0.3 - 0.35 + 0.10 * fbm(c.shape, 6, 40 + k, 3), 0.010) * (c.Y < 0.2)
        H = H - 0.04 * crack
        alb = ramp(clamp(0.5 + 0.5 * n), '#3E3F4C', '#62647A', '#8A8AA0')
        moss = clamp(fbm(c.shape, 5, 50 + k, 4) * 1.4 + 0.9 * smooth(0.3, 0.95, c.Y) - 0.35)
        alb = mix(alb, ramp(clamp(0.5 + fbm(c.shape, 90, 60 + k, 2)), '#2A3A1E', '#5A7A34'), clamp(moss)[..., None] * 0.8)
        sh = 0.55 * gauss(np.maximum(0, np.hypot(c.X * 0.8, (c.Y - 0.88) * 3) - 0.5), 0.2)
        c.put(np.zeros(3, F), (sh * smooth(1.0, 0.9, np.abs(c.Y))).astype(F))
        c.put(surface(c, H, alb, MOON, rough=0.7, reach=0.2), c.cover(d), H)
        ims.append(c.image(exposure=1.1))
    K.sheet(ims, 3, 'stones', how='jpg')


def pumpkin():
    c = K.canvas(560, 2)
    # ribs: a squashed ball of eight lobes seen from the front
    ry = c.Y - 0.06
    u = clamp(c.X / 0.97, -1, 1)
    lat = clamp(ry / 0.84, -1, 1)
    edge = np.hypot(c.X / 0.97, ry / 0.84) - 1 + 0.020 * np.cos(np.arctan2(c.X, -ry) * 1.0)
    z = np.sqrt(clamp(1 - (c.X / 0.97) ** 2 - (ry / 0.84) ** 2))
    th = np.arctan2(c.X / 0.97, z * 0.9 + 0.12 * (1 - lat ** 2))
    k = (th / math.pi * 9 + 0.5) % 1
    lobe = np.sqrt(clamp(1 - ((k - 0.5) * 2) ** 2 * 0.92))
    H = 0.40 * z + 0.075 * lobe
    alb = ramp(clamp(0.25 + 0.55 * lobe + 0.12 * fbm(c.shape, 30, 4, 3)), '#8A2E04', '#E0620A', '#FF9A2A')
    col = surface(c, H, alb, MOON, rough=0.45, clear=0.25, reach=0.1) * 1.15 + alb * 0.14
    col = col * (1 - 0.55 * smooth(0.20, 0.0, np.minimum(k, 1 - k) * 1.2) * 0.7)[..., None]
    c.put(col, c.cover(edge * 0.8), H)
    st = c.poly(bez((-0.13, -0.70), (-0.06, -0.80), (-0.10, -0.92), (0.06, -0.99), 14) + [(0.20, -0.95)] + bez((0.20, -0.95), (0.08, -0.88), (0.12, -0.78), (0.14, -0.70), 14))
    sc = ramp(clamp(0.5 + 0.5 * np.sin(c.X * 70 + c.Y * 8)), '#2E3A12', '#5E7028', '#8AA048')
    c.put(sc * 0.8, c.cover(st - 0.01))
    K.put(c, 'pumpkin', exposure=1.0)
    # the light that comes out of the cuts: two eyes above the words, a grin below
    def face(q):
        s = q
        cov = Ink(q)
        for sx in (-1, 1):
            cov.poly([(sx * 0.16, -0.40), (sx * 0.52, -0.50), (sx * 0.40, -0.26)])
        top = [(x, 0.47 + 0.14 * (1 - (x / 0.62) ** 2) * 0.55) for x in np.linspace(-0.62, 0.62, 21)]
        top = [(x, y + (0.0 if i % 4 else 0.0) - (0.075 if i % 4 == 2 else 0)) for i, (x, y) in enumerate(top)]
        bot = [(x, 0.53 + 0.23 * (1 - (x / 0.62) ** 2) + (0.065 if i % 4 == 0 else 0) * 0) for i, x in enumerate(np.linspace(0.62, -0.62, 21))]
        cov.poly(top + bot)
        a = cov.arr()
        inner = 0.55 + 0.45 * gauss(np.hypot(q.X, q.Y - 0.1), 0.55)
        return a * inner, a
    c = Canvas(K.px(460), 1, 1.0)
    li, a = face(c)
    gl = blur(a, 0.035 / c.px) * 0.55 + blur(a, 0.11 / c.px) * 0.55
    c.col = (rgb('#FFC23A') * (li * 1.15)[..., None] + rgb('#FF7A14') * gl[..., None]).astype(F)
    c.alpha[:] = 1
    K.save(c.image(tone=False, dither=False), 'face', 88, 'jpg')
    halo(K, 'glow', 256, 1.8, 0.0, '#FF8A1E')
    halo(K, 'halo', 220, 2.0, 0.1)
    light(K, 'warm', 256, lambda q: (1 - smooth(0.0, 1.0, q.R)) ** 1.8, '#FF7A1E')


def bits():
    ims = []
    for f in range(2):
        c = K.canvas(130, 4, 1.0, 0.6)
        up = -0.34 if f == 0 else 0.22
        for s in (-1, 1):
            w = [(0, -0.08), (s * 0.30, up * 0.6 - 0.06), (s * 0.62, up - 0.08), (s * 0.97, up * 0.4 + 0.02), (s * 0.72, up * 0.2 + 0.16), (s * 0.60, 0.10 + up * 0.15), (s * 0.44, 0.24 + up * 0.1), (s * 0.30, 0.14), (s * 0.14, 0.28), (0, 0.18)]
            c.put(rgb('#120A20') * (0.8 + 0.7 * smooth(0.2, 0.9, np.abs(c.X)))[..., None], c.cover(c.poly(w)))
        c.put(rgb('#1E1230'), c.cover(np.hypot(c.X / 0.12, c.Y / 0.22) * 0.12 - 0.12))
        for s in (-1, 1):
            c.put(rgb('#1E1230'), c.cover(c.poly([(s * 0.02, -0.14), (s * 0.11, -0.16), (s * 0.09, -0.32)])))
            c.put(rgb('#FFB03A'), c.cover(np.hypot(c.X - s * 0.045, c.Y + 0.09) - 0.020))
        ims.append(c.image(tone=False))
    K.sheet(ims, 2, 'bat')
    c = K.canvas(160, 3, 1.0, 1.2)            # a ghost
    d = smin(np.hypot(c.X, c.Y + 0.45) - 0.56, c.box(0.56, 0.62, 0, 0.18), 0.02)
    d = np.maximum(d, c.Y - 0.80 - 0.16 * np.cos(c.X * 11))
    col = flat('#EAF4FF', c.shape) * (0.75 + 0.25 * clamp(0.6 - c.X * 0.5 - c.Y * 0.4))[..., None]
    for s in (-1, 1):
        col = mix(col, flat('#1A1430', c.shape), c.cover(np.hypot((c.X - s * 0.21) / 0.8, (c.Y + 0.46) / 1.2) - 0.11)[..., None])
    col = mix(col, flat('#1A1430', c.shape), c.cover(np.hypot(c.X / 0.9, (c.Y + 0.12) / 1.3) - 0.12)[..., None])
    c.put(col, c.cover(d) * (0.92 - 0.55 * smooth(0.1, 0.95, c.Y)))
    K.put(c, 'ghost', how='png', tone=False)
    c = K.canvas(90, 4)                      # a little pumpkin
    q = np.hypot(c.X / 0.90, (c.Y - 0.10) / 0.76)
    z = np.sqrt(clamp(1 - q * q))
    k = (np.arctan2(c.X / 0.9, z + 0.1) / math.pi * 7 + 0.5) % 1
    li = clamp(0.30 + 0.6 * z - 0.25 * c.X - 0.35 * c.Y)
    c.put(rgb('#FF8A1E') * (li * (0.55 + 0.45 * np.sqrt(clamp(1 - ((k - 0.5) * 2) ** 2))))[..., None] * 1.25, c.cover((q - 1) * 0.8))
    c.put(rgb('#4E6A22'), c.cover(c.capsule(0, -0.62, 0.10, -0.88, 0.09)))
    K.put(c, 'little', how='png', tone=False)


K.run([night, stones, pumpkin, bits])


K.font('metamorphous', 'Metamorphous-Regular.ttf')
K.sounds('spooky')
T = 'title'
fl = '(0.80+0.14*noise(time*6)+0.08*noise(time*17))'
def bat(s, sp, r, ph):
    return img('bat', [s, s * 0.6], angle='time*%g+%g' % (sp, ph), radius='%g+0.06*sin(time*1.3+%g)' % (r, ph), y='0.02*sin(time*5+%g)' % ph, frame='floor(time*9+%g)%%2' % ph, rotate='10*sin(time*2+%g)' % ph, opacity='smooth(0.3,0.6,time)')
K.write(
    style=dict(shape='orb', material='solid', base='#1A1030', accent='#FF8A1E', accent2='#8A5AE0', text='#FFE9C8', border='#6A4A9A', opacity=0.97, corner=10, font='Metamorphous', open='bloom', speed=1, hoverGrow=3,
               iconZoom=1.12, glow=0.5, tilt=0.5, pointer=False, burst=False, shadow=0.65, dim=0.46),
    wheel=dict(hub=104, thickness=92, gap=5, ringgap=10, rim=34, icon=40, crowd=1.5, area=1.14, hubkeep=0.50),
    colors=dict(lit='#FFD24A', pale='#FFE9C8'), fonts=dict(title=dict(file='Metamorphous-Regular.ttf', family='Metamorphous')),
    back=[soft(1.08, 0.025, 70), img('night', 1, intro=intro(0.30, 'out', scale=0.88)), img('warm', 1.10, opacity='0.35*' + fl), img('fog', [0.95, 0.40], x='0.10*sin(time*0.25)', y=0.50, opacity='0.50'), img('fog', [0.90, 0.36], x='-0.12*sin(time*0.2+1)', y=0.66, opacity='0.55', scale=['-1', '1']),
          bat(0.10, 13, 0.66, 10), bat(0.075, 13, 0.74, 34), bat(0.085, -10, 0.82, 200)],
    ring=[dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringout+5', to=360, stroke='#8A5AE0/40', width=1.4)],
    slot=dict(intro=intro(0.36, 'out', 0.08, scale=0.9, y=0.7, stagger=0.025, order='random'),
              under=[img('halo', 1.9, opacity='0.50*hot+launch*1.5', tint='#7CFF9A'), img('ghost', [0.95, 1.14], y='-0.30-0.55*outback(sat(hot))-1.2*launch', x='0.06*sin(time*3+seed*6)', opacity='sat(hot*1.5)*0.92', when='hot>0.01'), img('stones', '1.16*(1+0.02*hot-0.03*press)', frame='(i+ring)%3', rotate='5*(seed-0.5)+1.5*sin(time*14)*launch', detail=1.04)],
              icon=dict(size=0.92, y=0.05, zoom=1.12, shadow=dict(y=2, blur=3, color='black/65')),
              over=[img('little', 0.34, x=-0.62, y=0.74, when='running', opacity='active ? 1 : 0.85'), img('glow', 0.8, x=-0.62, y=0.76, when='active', opacity='0.6*' + fl), img('fog', [1.3, 0.5], y=0.82, x='0.1*sin(time*0.6+seed*6)', opacity=0.35)] + badge('#1A1030', 'pale', T, x=0.62, y=-0.62, stroke='#FF8A1E') + groupmark('lit', -0.94, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.20, 0.07, 70, 0.80, **{'in': 'hub'}), img('glow', 0.50, **{'in': 'hub'}, angle='sel', radius=1.02, opacity='on*' + fl)],
    hub=[img('glow', 1.7, opacity='0.30*' + fl), img('pumpkin', 1.06, rotate='2*sin(time*0.8)', intro=intro(0.40, 'back', scale=0.3, rotate=-30)), img('face', 0.98, rotate='2*sin(time*0.8)', opacity='0.85*' + fl), dict(shape='rect', y=0.075, size=[0.74, 0.215], corner=10, fill='#170802/82', stroke='#FFB03A/70', width=1.4, glow=4, glowcolor='#FF7A14')]
    + words('lit', '#FFB84A', T, px=14, y=0.035, box=(1.38, 0.40), subpx=9, suby=0.225, clockpx=25, clocky=0.035, datey=0.225, datepx=10, weight=400, shadow=dict(x=0, y=0, blur=6, color='#FF6A0A')),
    draw=dict(clock=False, shadow=False, text='#FFE9C8'), tabs=dict(inset=40, text='#FFE9C8', fill='#000000/35', on='#8A5AE0'),
    pinbutton={'in': 'hub', 'x': -0.80, 'y': 0.70, 'size': 10}, settingsbutton={'in': 'hub', 'x': 0.80, 'y': 0.70, 'size': 10},
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#2E1A50'], [1, '#140A26']]}, stroke='#FF8A1E', width=2.4, corner=12, text='pale'), tag=dict(fill={'type': 'linear', 'stops': [[0, '#2E1A50'], [1, '#140A26']]}, stroke='#FF8A1E', width=1.6, corner=9, text='pale'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#6A6C82'], [1, '#3E3F4C']]}, stroke='#1A1030', width=2.4, corner=16, text='pale'),
    onlaunch=[dict(image='bat', count=16, area='slot', life=[0.6, 1.2], size=[14, 30], speed=[140, 460], outward=True, dir=[-120, 120], gravity=-80, drag=1.2, sway=20, swayhz=3, fadein=0, fadeout=0.4), dict(color='#FF8A1E', light=True, count=20, area='slot', life=[0.3, 0.7], size=[2, 4], speed=[80, 320], outward=True, dir=[-120, 120], gravity=-80, drag=2, fadein=0, fadeout=0.6)],
    particles=[dict(color='#FF9A3A', light=True, rate=2, max=16, area='hub', life=[1.2, 2.2], size=[1.5, 3], speed=[10, 30], dir=[-30, 30], gravity=-30, sway=10, swayhz=1, fadein=0.2, fadeout=0.5)])
