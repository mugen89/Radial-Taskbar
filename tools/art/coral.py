"""Coral Reef: blue water in a ring of corals, bubbles that hold your apps, small fish, and a pearl."""
from skinkit import *

K = Kit('coral', 'Coral Reef', 'Blue water in a ring of corals, small fish, and a pearl in the middle', ['nature', 'sea', 'colourful'])
K.flag(fish1=dict(cols=2), fish2=dict(cols=2), caustic='light', halo='light', drop='light', anemone=dict(cols=1))
SEA = Studio(lights=[((-0.40, -0.74, 0.58), 0.45, '#E6FBFF', 3.8), ((0.72, -0.40, 0.50), 0.35, '#9AE8FF', 1.5), ((0.12, 0.85, 0.45), 0.5, '#2A9AC8', 0.7)], sky='#BFF2FF', floor='#0A4A66', ambient=0.60)


def water():
    c = K.canvas(1000, 2)
    n = fbm(c.shape, 5, 3, 5)
    col = ramp(clamp(c.R * 0.85 + 0.12 * n), '#4FD3E6', '#1E9AC4', '#0C5A94', '#08386B')
    sand = smooth(0.72, 0.98, c.R + 0.07 * n)
    s = flat('#E0CFA0', c.shape) * (0.82 + 0.12 * fbm(c.shape, 60, 5, 3) + 0.05 * white(c.shape, 4))[..., None] * rgb('#A8E6E0')
    col = mix(col, s, (0.55 * sand)[..., None])
    c.put(col, c.cover(c.R - 0.985))
    K.put(c, 'water', tone=False, quality=86)

    def caustic(q):
        u = fbm(q.shape, 7, 5, 2) * 0.07
        d1 = worley(q.X + u, q.Y - u, 7.5, 3)
        d2 = worley(q.X - u + 5, q.Y + u, 10.5, 8)
        k = np.power(clamp(d1 * 1.05), 4) * 0.8 + np.power(clamp(d2 * 1.05), 4) * 0.55
        return 0.75 * k * smooth(1.0, 0.80, q.R)
    light(K, 'caustic', 460, caustic, '#CFFBFF')


def coral_branch(c, x, y, a, s, g, H, idm, k, depth=0):
    """Staghorn: a little tree of tapering fingers."""
    L = s * (0.55 + 0.35 * g.random())
    x1, y1 = x + math.sin(a) * L, y - math.cos(a) * L
    d = c.taper(x, y, s * 0.17, x1, y1, s * 0.115)
    h = 0.06 + 0.10 * depth + bevel(d, s * 0.14, s * 0.22)
    m = d < 0
    H[:] = np.where(m & (h > H), h, H)
    idm[:] = np.where(m, k, idm)
    if depth < 3:
        for da in (-0.55, 0.45) if depth else (-0.7, 0.0, 0.7):
            coral_branch(c, x1, y1, a + da + (g.random() - 0.5) * 0.35, s * 0.72, g, H, idm, k, depth + 1)


def reef():
    c = K.canvas(1160, 2, 1.10)
    g = rng(9)
    H = np.full(c.shape, 0.0, F)
    idm = np.zeros(c.shape, F)
    alb = np.zeros(c.shape + (3,), F)
    cov = np.zeros(c.shape, F)
    # rock below everything
    rr = 0.955 + 0.035 * fbm(c.shape, 10, 4, 4)
    d = np.abs(c.R - rr) - 0.055 - 0.018 * fbm(c.shape, 14, 7, 4)
    h = 0.05 * np.sqrt(clamp(1 - (1 - clamp(-d / 0.06)) ** 2)) + 0.012 * fbm(c.shape, 40, 8, 4) * (d < 0)
    H = np.where(d < 0, h, H)
    alb = np.where((d < 0)[..., None], ramp(clamp(0.5 + 0.5 * fbm(c.shape, 18, 9, 4)), '#5A6A72', '#8E8A92', '#B8A6A8'), alb)
    cov = np.maximum(cov, c.cover(d))
    cols = ('#FF6A5E', '#FF9A3A', '#FFD24A', '#FF5CA8', '#B46AF0', '#3AD0A8', '#F0F0E0')
    spots = 44
    for i in range(spots):
        a = (i + 0.5 * g.random()) * TAU / spots
        r = 0.955 + 0.030 * g.standard_normal()
        x, y = math.sin(a) * r, -math.cos(a) * r
        base = rgb(cols[int(g.random() * len(cols))])
        kind = i % 5
        s = 0.050 + 0.030 * g.random()
        px, py = c.X - x, c.Y - y
        box = (np.abs(px) < 0.17) & (np.abs(py) < 0.17)
        ys, xs = np.where(box.any(1))[0], np.where(box.any(0))[0]
        sl = (slice(ys[0], ys[-1] + 1), slice(xs[0], xs[-1] + 1))

        class Sub:                  # only the neighbourhood is worked on
            pass
        q = Sub()
        q.X, q.Y, q.px = c.X[sl], c.Y[sl], c.px
        q.taper = lambda x0, y0, r0, x1, y1, r1, q=q: Canvas.taper(q, x0, y0, r0, x1, y1, r1)
        lx, ly = q.X - x, q.Y - y
        R = np.hypot(lx, ly)
        if kind == 0:               # brain
            dd = R - s * (1 + 0.06 * np.sin(3 * np.arctan2(lx, -ly) + i))
            hh = 0.07 + s * 0.9 * np.sqrt(clamp(1 - (R / (s * 1.05)) ** 2))
            m = np.sin((lx + 0.02 * np.sin(ly * 90 + i)) * 190 + 5 * np.sin(ly * 60 + lx * 40))
            hh = hh + 0.006 * m
            cc = base * (0.80 + 0.25 * (m > 0))[..., None]
        elif kind == 1 or kind == 3:            # branches
            hh = np.full(R.shape, -1.0, F)
            idd = np.zeros(R.shape, F)
            for t in range(3):
                coral_branch(q, x, y, a + (t - 1) * 0.75 + (0 if kind == 1 else 3.1) * 0, s * 0.85, g, hh, idd, 1)
            dd = np.where(idd > 0, -0.01, 0.01)
            cc = mix(flat(base, R.shape), np.ones(R.shape + (3,), F), clamp((hh - 0.22) * 2.2)[..., None])
        elif kind == 2:             # tubes
            dd, hh = np.full(R.shape, 9.0, F), np.zeros(R.shape, F)
            cc = flat(base, R.shape)
            for t in range(5):
                ta, tr = g.random() * TAU, s * 0.75 * math.sqrt(g.random())
                qx, qy, qs = x + math.sin(ta) * tr, y - math.cos(ta) * tr, s * (0.28 + 0.16 * g.random())
                w = np.hypot(q.X - qx, q.Y - qy)
                hole = w < qs * 0.52
                dd = np.minimum(dd, w - qs)
                top = 0.10 + 0.03 * t
                hh = np.where(w < qs, np.where(hole, top - 0.07, top + bevel(w - qs, qs * 0.3, 0.02)), hh)
                cc = np.where(hole[..., None], base * 0.25, cc)
        else:                       # a fan with ribs
            ang = np.arctan2(lx, -ly) - a
            ang = (ang + math.pi) % TAU - math.pi
            rib = np.sin(ang * 34) * 0.5 + 0.5
            dd = np.maximum(R - s * 1.7, (np.abs(ang) - 1.0) * R)
            hh = 0.10 + 0.012 * rib + 0.02 * R / s
            cc = base * (0.70 + 0.40 * rib)[..., None]
        m = dd < 0
        up = m & (hh > H[sl] - 0.04)
        H[sl] = np.where(up, hh, H[sl])
        alb[sl] = np.where(up[..., None], cc, alb[sl])
        cov[sl] = np.maximum(cov[sl], np.clip(0.5 - dd / c.px, 0, 1) if kind in (0, 2, 4) else blur(m.astype(F), 0.6))
    H = blur(H, 0.8)
    alb = alb * (1 + 0.06 * fbm(c.shape, 160, 3, 2))[..., None]
    col = surface(c, H, alb, SEA, rough=0.5, clear=0.12, reach=0.10, slope=0.7, ao_r=(0.008, 0.02, 0.05), ao_s=1.3)
    c.put(col, clamp(cov), H)
    K.put(c, 'reef', exposure=1.02, quality=87)


def bits():
    # a bubble
    c = K.canvas(260, 3)
    z = np.sqrt(clamp(1 - (c.R / 0.94) ** 2))
    rim = np.power(clamp(1 - z), 2.2)
    win = smooth(0.50, 0.60, np.hypot(c.X + 0.06, c.Y + 0.10)) * (1 - smooth(0.74, 0.84, np.hypot(c.X + 0.06, c.Y + 0.10))) * smooth(0.50, 0.95, -((c.X + 0.06) * 0.5 + (c.Y + 0.10) * 0.86) / np.maximum(np.hypot(c.X + 0.06, c.Y + 0.10), 1e-3))
    low = smooth(0.62, 0.90, c.R) * smooth(0.45, 1.0, (c.X * 0.5 + c.Y * 0.86) / np.maximum(c.R, 1e-3)) * (1 - smooth(0.90, 0.96, c.R))
    li = clamp(0.65 * rim + 0.70 * win + 0.35 * low + 0.8 * gauss(np.hypot(c.X + 0.42, c.Y + 0.46), 0.07))
    hue = 0.5 + 0.5 * np.sin(c.A * 2 + c.R * 4)
    c.col = mix(flat('#BFF6FF', c.shape), flat('#FFD6F4', c.shape), hue[..., None]) * (0.7 + 0.3 * li)[..., None]
    c.alpha = clamp(li * 0.95 + 0.10).astype(F) * c.cover(c.R - 0.94)
    K.put(c, 'bubble', how='png', tone=False)
    # anemone
    c = K.canvas(340, 2)
    g = rng(4)
    for ringk, (n, r0, r1, w, col0, col1) in enumerate(((34, 0.34, 0.96, 0.058, '#7A1450', '#E8408A'), (28, 0.30, 0.82, 0.060, '#A8205E', '#FF5FA0'), (20, 0.24, 0.66, 0.060, '#C83060', '#FF7A8A'))):
        for k in range(n):
            a = (k + 0.5 * ringk + 0.3 * g.standard_normal()) * TAU / n
            L = r0 + (r1 - r0) * (0.86 + 0.14 * g.random())
            b = 0.16 * g.standard_normal()
            pts = bez(c.polar(a, r0), c.polar(a + b, (r0 + L) / 2), c.polar(a - b, (r0 + L) / 2 + 0.1), c.polar(a + b * 0.6, L), 10)
            d = np.full(c.shape, 9.0, F)
            for i in range(len(pts) - 1):
                d = np.minimum(d, c.capsule(*pts[i], *pts[i + 1], w * (1.0 - 0.35 * i / len(pts))))
            t = clamp((c.R - r0) / max(0.01, L - r0))
            cc = mix(flat(col0, c.shape), flat(col1, c.shape), t[..., None]) * (0.75 + 0.45 * np.sqrt(clamp(-d / w)))[..., None]
            tip = np.hypot(c.X - pts[-1][0], c.Y - pts[-1][1]) - w * 0.80
            c.put(np.zeros(3, F), (0.25 * gauss(np.maximum(0, d - 0.004), 0.02)).astype(F) * (c.alpha > 0.5))
            c.put(cc, c.cover(d))
            c.put(flat('#FFB45A', c.shape) * (0.75 + 0.4 * np.sqrt(clamp(-tip / w)))[..., None], c.cover(tip))
    c.put(flat('#7A1E56', c.shape) * (0.8 + 0.4 * smooth(0.3, 0, c.R))[..., None], c.cover(c.R - 0.36))
    K.put(c, 'anemone')
    # fish, heads to the right
    for name, body, stripe, fin in (('fish1', '#FF8A1E', '#FFFFFF', '#E0560A'), ('fish2', '#2E6BFF', '#FFE14A', '#163AA8')):
        ims = []
        for f in (0, 1):
            c = K.canvas(150, 4, 1.0, 0.62)
            sw = 0.10 if f else -0.10
            tail = c.poly([(-0.50, 0), (-0.96, -0.36 + sw), (-0.82, sw), (-0.96, 0.36 + sw)])
            c.put(flat(fin, c.shape) * (0.85 + 0.3 * np.sin(c.Y * 60) * 0.3)[..., None], c.cover(tail))
            top = c.poly([(-0.35, -0.20), (-0.15, -0.52), (0.30, -0.42), (0.40, -0.20)])
            c.put(flat(fin, c.shape), c.cover(np.minimum(top, c.poly([(-0.2, 0.22), (-0.1, 0.48), (0.18, 0.40), (0.2, 0.2)]))))
            d = np.hypot((c.X - 0.12) / 0.74, c.Y / 0.36) - 1
            shadev = 0.75 + 0.35 * clamp(-c.Y / 0.36)
            col = flat(body, c.shape) * shadev[..., None]
            if name == 'fish1':
                for sx, w in ((0.42, 0.075), (-0.02, 0.085), (-0.44, 0.06)):
                    e = np.abs(c.X - sx - 0.06 * np.cos(c.Y * 5))
                    col = mix(col, flat('#101010', c.shape), smooth(w + 0.045, w + 0.030, e)[..., None])
                    col = mix(col, flat(stripe, c.shape) * shadev[..., None], smooth(w, w - 0.02, e)[..., None])
            else:
                col = mix(col, flat(stripe, c.shape), smooth(0.02, -0.02, np.abs(c.Y + 0.02) - 0.07 - 0.05 * c.X)[..., None])
            c.put(col, c.cover(d * 0.36))
            e = np.hypot(c.X - 0.60, c.Y + 0.07)
            c.put(np.ones(3, F), c.cover(e - 0.085))
            c.put(np.zeros(3, F), c.cover(e - 0.052))
            ims.append(c.image(tone=False))
        K.sheet(ims, 2, name)
    # scallop and pearl
    c = K.canvas(520, 2)
    n = 22
    a = (c.A / TAU + 0.5) * n
    k = np.abs((a % 1) - 0.5) * 2
    edge = 0.955 + 0.030 * np.cos((a % 1 - 0.5) * TAU)
    d = c.R - edge
    H = 0.045 * (1 - k) * smooth(0.3, 0.9, c.R) + lathe(c, [(0, 0), (0.6, 0.02), (0.9, 0.12), (1.0, 0.08)])
    band = 0.5 + 0.5 * np.sin(c.R * 34)
    alb = mix(flat('#FFC4B0', c.shape), flat('#F0705E', c.shape), (0.60 * band * smooth(0.5, 0.9, c.R) + 0.20)[..., None])
    c.put(surface(c, H, alb, SEA, rough=0.35, clear=0.45), c.cover(d), H)
    K.put(c, 'shell')
    c = K.canvas(420, 2)
    r = 0.95
    z = np.sqrt(clamp(1 - (c.R / r) ** 2))
    nx, ny = c.X / r, c.Y / r
    irid = np.stack([0.5 + 0.5 * np.sin(6.0 * z + k2 + 2.0 * nx) for k2 in (0.0, 2.1, 4.2)], -1)
    li = 0.62 + 0.38 * clamp(-0.45 * nx - 0.62 * ny + 0.64 * z)
    col = (flat('#FBF6F2', c.shape) * 0.86 + irid * 0.14) * li[..., None] + (0.55 * np.power(clamp(-0.42 * nx - 0.60 * ny + 0.68 * z), 50))[..., None] + rgb('#9AE0FF') * (0.20 * np.power(clamp(1 - z), 2) * clamp(0.2 + 0.6 * ny))[..., None]
    c.put(col, c.cover(c.R - r))
    K.put(c, 'pearl', tone=False)
    light(K, 'drop', 64, lambda q: 0.8 * gauss(q.R - 0.66, 0.14) + 1.0 * gauss(np.hypot(q.X + 0.28, q.Y + 0.32), 0.17) + 0.14 * (q.R < 0.66), '#D6FBFF')
    halo(K, 'halo', 220, 2.0, 0.1)


K.run([water, reef, bits])
K.sounds('water')
T = 'title'
def swim(name, s, sp, r, ph, fl=1):
    return img(name, [s, s * 0.62], angle='time*%g+%g' % (sp, ph), radius='%g+0.05*sin(time*0.9+%g)+0.10*on*sin(time*3+%g)' % (r, ph, ph), rotate='time*%g+%g+%g+8*sin(time*1.7+%g)' % (sp, ph, 0 if sp > 0 else 180, ph), frame='floor(time*6+%g)%%2' % ph, opacity='smooth(0.25,0.6,time)')
K.write(
    style=dict(shape='orb', material='solid', base='#0C4A78', accent='#FF7A9A', accent2='#4FE0E6', text='#F0FCFF', border='#8FE6F4', opacity=0.96, corner=16, font='Candara', open='bloom', speed=0.95, hoverGrow=4,
               iconZoom=1.14, glow=0.3, tilt=0.7, pointer=False, burst=False, shadow=0.55, dim=0.32),
    wheel=dict(hub=88, thickness=94, gap=5, ringgap=10, rim=46, icon=43, crowd=1.48, area=1.16, hubkeep=0.78),
    colors=dict(deep='#0A3A66', teal='#1E7A9A', pale='#F0FCFF'), fonts=dict(title='Candara, Segoe UI'),
    back=[soft(1.12, 0.03, 60), img('water', 0.985, intro=intro(0.30, 'out', scale=0.5)), img('caustic', 0.98, rotate='time*3', opacity='0.40', scale='1.02+0.03*sin(time*0.8)'), img('caustic', 0.98, rotate='-time*4+60', opacity='0.28', scale='1.05+0.03*sin(time*0.7+2)'),
          swim('fish1', 0.085, 9, 0.46, 20), swim('fish1', 0.065, 9, 0.50, 2), swim('fish2', 0.060, -12, 0.80, 200), swim('fish2', 0.050, -12, 0.83, 214), swim('fish2', 0.046, -12, 0.78, 226),
          img('reef', 1.10, rotate='(1-open)*12', intro=intro(0.34, 'out', scale=0.86))],
    slot=dict(intro=intro(0.45, 'out', 0.06, scale=0.2, y=0.9, stagger=0.02, order='random'),
              under=[img('anemone', '1.46*(0.30+0.70*outback(sat(hot)))', rotate='8*sin(time*1.6+seed*6)', opacity='sat(hot*3)', when='hot>0.01'), img('anemone', '1.10*(0.30+0.70*outback(sat(hot)))', rotate='-10*sin(time*1.9+seed*6)+9', opacity='sat(hot*3)', when='hot>0.01'),
                     dict(shape='circle', size=0.92, y='0.03*sin(time*1.6+seed*6)', fill={'type': 'radial', 'from': [-0.2, -0.3], 'radius': 1.2, 'stops': [[0, '#6AE0F4/30'], [1, '#0A3A66/55']]})],
              icon=dict(size=1.0, zoom=1.14, y='0.03*sin(time*1.6+seed*6)', shadow=dict(y=2, blur=3, color='#04203A/60')),
              over=[img('bubble', '1.0*(1+0.05*hot-0.05*press+launch*0.5)', y='0.03*sin(time*1.6+seed*6)', scale=['1+0.012*sin(time*3+seed*9)', '1-0.012*sin(time*3+seed*9)'], opacity='1-launch', detail=1.06)]
              + running('#FF7A9A', '#FFE3EA', 0.94, 0.15) + badge('#0A3A66', 'pale', T, stroke='#8FE6F4') + groupmark('pale', -0.96, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.22, 0.06, 55, 0.80, **{'in': 'hub'}), img('drop', 0.22, **{'in': 'hub'}, angle='sel', radius=1.14, opacity='on', scale='0.6+0.4*on+0.06*sin(time*6)')],
    hub=[img('shell', 1.14, rotate='sel*0.2+4*sin(time*0.6)', intro=intro(0.42, 'back', scale=0.3, rotate=-90)), soft(0.92, 0.05, 40, 0.80), img('pearl', 0.84, intro=intro(0.40, 'back', 0.06, scale=0.2))] + words('deep', 'teal', T, px=17, y=-0.04, box=(1.18, 0.48), subpx=11, suby=0.26, clockpx=30, clocky=-0.07, datey=0.21, datepx=12),
    draw=dict(clock=False, shadow=False, text='deep'), tabs=dict(inset=18, text='deep', fill='#1E7A9A/22', on='#FF7A9A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#1E8FB8'], [1, '#0A3A66']]}, stroke={'type': 'linear', 'stops': [[0, '#FFD6C4'], [0.5, '#F08A7A'], [1, '#FFD6C4']]}, width=4, corner=18, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#1E7AA0'], [1, '#0C4A78']]}, stroke='#8FE6F4', width=1.4, corner=13, text='pale'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#2AA0C8'], [1, '#0C4A78']]}, stroke='#FFD6C4', width=2.4, corner=13, text='pale'),
    particles=[dict(image='drop', light=True, rate=3.5, max=22, area='wheel', life=[1.6, 3.2], size=[3, 8], speed=[14, 34], dir=[-12, 12], gravity=-16, sway=10, swayhz=1.1, fadein=0.2, fadeout=0.3, opacity=0.7)],
    onlaunch=[dict(image='drop', light=True, count=40, area='slot', life=[0.5, 1.1], size=[4, 13], speed=[60, 300], outward=True, dir=[-120, 120], drag=2.4, gravity=-160, sway=14, swayhz=2, fadein=0, fadeout=0.4)],
    onhover=[dict(image='drop', light=True, count=5, area='slot', life=[0.5, 0.9], size=[2, 5], speed=[20, 60], dir=[-40, 40], gravity=-60, sway=8, swayhz=2, fadein=0.1, fadeout=0.4)])
