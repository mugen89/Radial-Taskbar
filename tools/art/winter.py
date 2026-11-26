"""Winter Wreath: fir, baubles, blinking lights, a ribbon and falling snow."""
from skinkit import *

K = Kit('winter', 'Winter Wreath', 'A fir wreath with glass baubles, blinking lights and falling snow', ['season', 'winter', 'festive'])
K.flag(balls=dict(cols=6), glow='light', halo='light', twinkle='light', flake=dict(cols=3))
COLS = ('#C8102E', '#E0A526', '#1E7A3E', '#2A6FD6', '#C9D2DC', '#8A2BB8')
FROST = Studio(lights=[((-0.45, -0.70, 0.58), 0.34, '#FFFFFF', 4.4), ((0.75, -0.35, 0.50), 0.26, '#FFD9A0', 2.2), ((0.10, 0.86, 0.45), 0.4, '#9AC0FF', 1.0), ((-0.92, 0.2, 0.28), 0.18, '#BFD6FF', 1.2)], sky='#CFE0F6', floor='#12182A', ambient=0.50)


def night():
    c = K.canvas(900, 2)
    col = ramp(clamp(0.5 + 0.5 * c.Y + 0.1 * fbm(c.shape, 4, 3, 4)), '#0A1A4A', '#143A7A', '#2A6AA8')
    col = col + (stars(c, 240, 5, 0.0, 0.95, 0.0035))[..., None]
    fr = smooth(0.45, 0.98, c.R + 0.10 * fbm(c.shape, 7, 8, 5))       # frost on the window
    cry = np.abs(fbm(c.shape, 40, 9, 4, ridged=True))
    col = mix(col, flat('#E6F2FF', c.shape), clamp(fr * (0.30 + 0.5 * cry))[..., None])
    c.put(col, c.cover(c.R - 0.98))
    K.put(c, 'night', tone=False, quality=86)


def wreath():
    c = K.canvas(1180, 2, 1.16)
    g = rng(7)
    total = np.zeros(c.shape, F)
    col = np.zeros(c.shape + (3,), F)
    R0 = 0.955
    layers = ((700, '#0C2412', '#163A1C', 0.085), (760, '#14401E', '#25602C', 0.078), (640, '#1E5A2A', '#3E8A40', 0.070), (360, '#2E7A38', '#6AB45A', 0.060))
    for k, (n, c0, c1, L) in enumerate(layers):
        if K.draft != 1:
            n = n // 2
        ink = Ink(c)
        for _ in range(n):
            a = g.random() * TAU
            r = R0 + 0.055 * g.standard_normal()
            x, y = math.sin(a) * r, -math.cos(a) * r
            t = a + math.pi / 2 + (g.random() - 0.5) * 2.2
            l = L * (0.7 + 0.6 * g.random())
            bx, by = x + math.sin(t) * l, y - math.cos(t) * l
            ink.line([(x, y), (bx, by)], 0.0055)
            m = 9
            for j in range(m):
                q = (j + 0.5) / m
                px, py = x + (bx - x) * q, y + (by - y) * q
                for s in (-1, 1):
                    w = t + s * (0.75 - 0.25 * q)
                    nl = l * 0.42 * (1 - 0.45 * q)
                    ink.line([(px, py), (px + math.sin(w) * nl, py - math.cos(w) * nl)], 0.0038)
        cov = ink.arr(0.0004)
        sh = blur(shift(cov, int(0.008 / c.px), int(0.012 / c.px)), 0.008 / c.px)
        col = col * (1 - 0.55 * sh * (1 - cov))[..., None]
        lit = clamp(0.55 - 0.35 * (np.sin(c.A) * 0.5 * 0 + c.X * 0.35 + c.Y * 0.5) + 0.18 * fbm(c.shape, 60, 30 + k, 3))
        leaf = mix(flat(c0, c.shape), flat(c1, c.shape), lit[..., None])
        # snow lies on the upper sides
        snow = smooth(0.35, 0.8, fbm(c.shape, 22, 50 + k, 4) + 0.10 - 0.36 * (c.Y - 0.02)) * (k >= 2)
        leaf = mix(leaf, flat('#F4F9FF', c.shape), (0.75 * snow)[..., None])
        col = mix(col, leaf, cov[..., None])
        total = np.maximum(total, cov)
    sh = 0.0
    c.put(col, clamp(total))
    # cones and berries
    for i in range(22):
        a = (i + 0.4 * g.random()) * TAU / 22
        if abs(((a - math.pi + math.pi) % TAU) - math.pi) < 0.30:
            continue
        x, y = c.polar(a, R0 + 0.030 * g.standard_normal())
        if i % 4 == 1:
            s = 0.036
            q = np.hypot(c.X - x, c.Y - y)
            t = np.arctan2(c.X - x, -(c.Y - y))
            sc = ((t / TAU * 8 + np.floor(q / s * 4) * 0.5) % 1)
            cc = mix(flat('#3A2010', c.shape), flat('#9A6A3A', c.shape), (clamp(1 - np.abs(sc - 0.5) * 2) * (0.5 + 0.5 * ((q / s * 4) % 1)))[..., None])
            c.put(np.zeros(3, F), (0.5 * gauss(np.maximum(0, np.hypot(c.X - x - 0.008, c.Y - y - 0.012) - s), 0.012)).astype(F) * (q > s))
            c.put(cc, c.cover(q - s))
        else:
            for j in range(3):
                bx, by, s = x + 0.020 * math.sin(j * 2.1 + i), y + 0.020 * math.cos(j * 2.1 + i), 0.0135
                q = np.hypot(c.X - bx, c.Y - by)
                z = np.sqrt(clamp(1 - (q / s) ** 2))
                li = clamp(0.35 + 0.65 * z - 0.35 * (c.X - bx) / s - 0.4 * (c.Y - by) / s)
                c.put(rgb('#D8142C') * li[..., None] + (0.9 * gauss(np.hypot(c.X - bx + s * 0.35, c.Y - by + s * 0.4), s * 0.28))[..., None], c.cover(q - s))
    # ribbon with a bow, below
    for s in (-1, 1):
        tail = c.poly([(s * 0.02, 0.98), (s * 0.10, 0.99), (s * 0.20, 1.13), (s * 0.15, 1.11), (s * 0.11, 1.145)])
        c.put(rgb('#8E0A1E') * (0.8 + 0.4 * np.sin(c.X * 60) * 0.3)[..., None], c.cover(tail))
        loop = c.poly(bez((0, 0.955), (s * 0.10, 0.80), (s * 0.30, 0.82), (s * 0.275, 0.96), 18) + bez((s * 0.275, 0.96), (s * 0.28, 1.09), (s * 0.10, 1.06), (0, 0.985), 18))
        u = clamp((np.abs(c.X)) / 0.28)
        fold = 0.55 + 0.45 * np.cos(u * 9 + (c.Y - 0.96) * 20)
        c.put(np.zeros(3, F), (0.45 * gauss(np.maximum(0, loop), 0.016) * (loop > 0)).astype(F) * (c.alpha > 0.2))
        c.put(mix(flat('#7A0818', c.shape), flat('#E5283E', c.shape), (0.25 + 0.75 * fold)[..., None]), c.cover(loop))
        hole = c.poly(bez((s * 0.06, 0.955), (s * 0.12, 0.90), (s * 0.21, 0.90), (s * 0.20, 0.965), 12) + bez((s * 0.20, 0.965), (s * 0.20, 1.02), (s * 0.12, 1.02), (s * 0.06, 0.985), 12))
        c.put(flat('#6A0614', c.shape) * (0.6 + 0.6 * smooth(0.06, 0.2, np.abs(c.X)))[..., None], c.cover(hole))
    k = c.box(0.045, 0.050, 0, 0.97, r=0.02)
    c.put(mix(flat('#8E0A1E', c.shape), flat('#F04A5C', c.shape), clamp(0.6 - c.X * 8 - (c.Y - 0.97) * 8)[..., None]), c.cover(k))
    K.put(c, 'wreath', tone=False, quality=87)


def ball(c, base, r=0.86, cap=True):
    d = c.R - r
    z = np.sqrt(clamp(1 - (c.R / r) ** 2))
    nx, ny = c.X / r, c.Y / r
    b = rgb(base)
    li = 0.16 + 0.62 * clamp(-0.45 * nx - 0.60 * ny + 0.62 * z)
    col = b * li[..., None] + FROST.reflect(nx, ny, z, 0.05) * (0.05 * 1 + 0.75 * np.power(clamp(1 - z), 4) + 0.10 * b.mean())[..., None]
    col = col + b * (0.35 * gauss(np.hypot(nx - 0.35, ny - 0.45), 0.35))[..., None]
    # a window mirrored in the glass
    wx, wy = nx + 0.36, ny + 0.42
    bend = wx * 0.94 - wy * 0.35, wx * 0.35 + wy * 0.94
    win = smooth(0.20, 0.17, np.abs(bend[0])) * smooth(0.24, 0.21, np.abs(bend[1])) * (np.abs(bend[0]) > 0.015) * (np.abs(bend[1]) > 0.015)
    col = col + (0.80 * win)[..., None]
    if cap:
        capd = c.box(0.15, 0.085, 0, -r - 0.03, r=0.03)
        c.put(flat(GOLD, c.shape) * (0.35 + 0.9 * gauss(c.X + 0.05, 0.07))[..., None], c.cover(capd))
    sh = 0.42 * gauss(np.maximum(0, np.hypot(c.X - 0.05, c.Y - 0.08) - r * 0.98), 0.08) * smooth(1.0, 0.95, np.maximum(np.abs(c.X), np.abs(c.Y)))
    c.put(np.zeros(3, F), (sh * (c.alpha < 0.5)).astype(F))
    c.put(col, c.cover(d))
    return c


def balls():
    K.sheet([ball(K.canvas(230, 3), b, 0.83).image(exposure=0.98) for b in COLS], 6, 'balls')
    c = K.canvas(470, 2)
    d = c.R - 0.94
    z = np.sqrt(clamp(1 - (c.R / 0.94) ** 2))
    nx, ny = c.X / 0.94, c.Y / 0.94
    b = rgb('#B80E26')
    col = b * (0.22 + 0.60 * clamp(-0.45 * nx - 0.60 * ny + 0.62 * z))[..., None] + FROST.reflect(nx, ny, z, 0.08) * (0.04 + 0.6 * np.power(clamp(1 - z), 4))[..., None] + b * (0.30 * gauss(np.hypot(nx - 0.35, ny - 0.45), 0.35))[..., None]
    ink = Ink(c)
    for yy in (-0.62, 0.64):        # painted gold bands
        ink.line([(x, yy + 0.16 * x * x * (1 if yy > 0 else -1) * -1) for x in np.linspace(-0.9, 0.9, 60)], 0.022)
        ink.line([(x, yy * 0.90 + 0.14 * x * x * (1 if yy > 0 else -1) * -1) for x in np.linspace(-0.9, 0.9, 60)], 0.010)
        for j in range(-5, 6):
            x = j * 0.15
            ink.dot(x, yy * 1.10 + 0.17 * x * x * (1 if yy > 0 else -1) * -1, 0.020)
    col = mix(col, rgb('#F0C860') * (0.40 + 0.8 * clamp(-0.45 * nx - 0.60 * ny + 0.62 * z))[..., None], (ink.arr(0.002) * 0.95)[..., None])
    col = col + (0.55 * smooth(0.52, 0.60, np.hypot(nx + 0.04, ny + 0.06)) * (1 - smooth(0.76, 0.84, np.hypot(nx + 0.04, ny + 0.06))) * smooth(0.6, 0.97, -(nx * 0.5 + ny * 0.86) / np.maximum(np.hypot(nx, ny), 1e-3)))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'hub', exposure=0.97)
    ims = []
    for k in range(3):
        c = K.canvas(48, 4)
        ink = Ink(c)
        for j in range(6):
            a = j * TAU / 6
            ink.line([(0, 0), c.polar(a, 0.9)], 0.10)
            for q in (0.42, 0.66):
                x, y = c.polar(a, q)
                for s in (-1, 1):
                    ink.line([(x, y), (x + math.sin(a + s * 0.95) * 0.26, y - math.cos(a + s * 0.95) * 0.26)], 0.08) if k else None
        c.col[:] = 1
        c.alpha = (ink.arr(0.02) if k else gauss(c.R, 0.5) * smooth(1, 0.8, c.R)).astype(F)
        ims.append(c.image(tone=False))
    K.sheet(ims, 3, 'flake')
    c = K.canvas(120, 4)
    d = c.star(5, 0.95, 0.44)
    H = bevel(d, 0.30, 0.30, 'chamfer')
    c.put(metal(c, H, GOLD, rough=0.16, grime=0.1, reach=0.2), c.cover(d), H)
    K.put(c, 'star', how='png')
    halo(K, 'glow', 96, 1.8, 0.0)
    halo(K, 'halo', 220, 2.0, 0.15)
    light(K, 'twinkle', 64, lambda q: gauss(q.R, 0.16) + 0.6 * gauss(q.X, 0.05) * smooth(0.9, 0, np.abs(q.Y)) + 0.6 * gauss(q.Y, 0.05) * smooth(0.9, 0, np.abs(q.X)))


K.run([night, wreath, balls])

K.sounds('sleigh')
T = 'title'
lights = []
for k, col in enumerate(('#FF4A4A', '#FFD24A', '#4AFF7A', '#5AA8FF')):
    lights.append(dict(shape='circle', copies=9, angle='j*40+%d' % (k * 10), radius='0.95+0.030*sin(j*2.4+%d)' % k, size=0.030, fill=col))
    lights.append(img('glow', 0.17, copies=9, angle='j*40+%d' % (k * 10), radius='0.95+0.030*sin(j*2.4+%d)' % k, tint=col, opacity='0.04+0.34*smooth(0.35,0.75,wave(time*0.55+j*0.37+%g))' % (k * 0.25)))
swing = '5*sin(time*3.2+seed*6)*sat(hot)'
K.write(
    style=dict(shape='orb', material='solid', base='#123A22', accent='#E5283E', accent2='#E0A526', text='#FFF8EA', border='#E0A526', opacity=0.97, corner=14, font='Palatino Linotype', open='bloom', speed=1, hoverGrow=3,
               iconZoom=1.12, glow=0.4, tilt=0.5, pointer=False, burst=False, shadow=0.55, dim=0.34),
    wheel=dict(hub=90, thickness=92, gap=5, ringgap=12, rim=44, icon=40, crowd=1.5, area=[1.18, 1.18, 1.18, 1.24], hubkeep=0.70),
    colors=dict(cream='#FFF8EA', gold='#FFD98A'), fonts=dict(title='Palatino Linotype, Georgia'),
    back=[soft(1.10, 0.03, 55), img('night', 0.97, intro=intro(0.28, 'out', scale=0.7)), img('wreath', 1.16, rotate='0', intro=intro(0.36, 'back', scale=0.80, rotate=-12))] + lights + [img('star', 0.17, y=-0.955, rotate='6*sin(time*1.1)', intro=intro(0.4, 'back', 0.15, scale=0.0)), img('halo', 0.42, y=-0.955, opacity='0.35+0.15*wave(time*0.6)', tint='#FFD98A')],
    slot=dict(intro=intro(0.42, 'bounce', 0.08, scale=0.2, y=-0.8, stagger=0.02, order='both'),
              under=[img('halo', 1.9, opacity='0.45*hot+launch*1.5', tint='#FFE9B0'), img('balls', '1.14*(1+0.04*hot-0.03*press)', frame='(i+ring*2)%6', rotate=swing, pivot=[0.5, 0.06], y='-1.0*(1+0.04*hot)', detail=1.06)],
              icon=dict(size=0.90, zoom=1.14, shadow=dict(y=2, blur=3, color='black/55')),
              over=[img('twinkle', '0.55*wave(time*0.8+seed*3)', x=-0.40, y=-0.46, opacity='0.35+0.65*hot', rotate='time*20')] + running('#FFD98A', '#FFFFFF', 0.90, 0.15) + badge('#123A22', 'cream', T, stroke='#E0A526') + groupmark('cream', -0.66, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.14, 0.06, 55, 0.80, **{'in': 'hub'}), img('star', 0.25, **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel+time*20', opacity='on', scale='0.4+0.6*on')],
    hub=[img('hub', 1.0, intro=intro(0.42, 'bounce', scale=0.4))] + words('cream', 'gold', T, px=17, y=-0.06, box=(1.30, 0.50), clockpx=31, datepx=12, shadow=dict(x=0, y=1, blur=3, color='#3A0410')),
    draw=dict(clock=False, shadow=False, text='cream'), tabs=dict(inset=14, text='cream', fill='#FFFFFF/16', on='#1E7A3E'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#1E5A34'], [1, '#0C2E1A']]}, stroke={'type': 'linear', 'stops': [[0, '#FFE9B0'], [0.5, '#B07A1E'], [1, '#FFD98A']]}, width=3, corner=14, text='cream'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#C8102E'], [1, '#8E0A1E']]}, stroke='#FFD98A', width=1.6, corner=10, text='cream'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#C8102E'], [1, '#8E0A1E']]}, stroke='#FFD98A', width=2.2, corner=10, text='cream'),
    particles=[dict(image='flake', rate=11, max=70, area='stage', life=[3, 5.5], size=[3, 9], speed=[14, 34], dir=[165, 195], sway=18, swayhz=0.4, spin=[-60, 60], fadein=0.2, fadeout=0.3, opacity=0.85)],
    onlaunch=[dict(image='flake', count=40, area='slot', life=[0.6, 1.2], size=[5, 13], speed=[80, 360], outward=True, dir=[-120, 120], gravity=140, drag=2.2, sway=16, swayhz=1, spin=[-160, 160], fadein=0, fadeout=0.5), dict(color='#FFE9B0', light=True, count=24, area='slot', life=[0.3, 0.8], size=[1.5, 3.5], speed=[90, 380], outward=True, dir=[-120, 120], drag=2.4, fadein=0, fadeout=0.6)],
    onhover=[dict(image='flake', count=3, area='slot', life=[0.5, 0.9], size=[3, 6], speed=[20, 60], outward=True, dir=[-90, 90], gravity=60, spin=[-90, 90], fadein=0, fadeout=0.5)])
