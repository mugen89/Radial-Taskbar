"""Terrarium: moss, ferns and log slices under a glass lid with drops on it; a ladybird and a butterfly live there."""
from skinkit import *

K = Kit('terrarium', 'Terrarium', 'Moss, ferns and log slices under glass, with a ladybird and a butterfly', ['nature', 'green', 'glass'])
K.flag(slices=dict(cols=4), leaves=dict(cols=4), fly=dict(cols=2), shaft='light', halo='light', mote='light')
DAY = Studio(lights=[((-0.48, -0.70, 0.54), 0.45, '#FFF8E2', 4.0), ((0.72, -0.40, 0.50), 0.35, '#E2F4D8', 1.4), ((0.10, 0.85, 0.45), 0.5, '#C8D8A0', 0.7)], sky='#E6F2E0', floor='#2A3A1E', ambient=0.55)


def moss_tex(c, seed, scale=1.0):
    a = fbm(c.shape, 8 * scale, seed, 4)
    b = fbm(c.shape, 70 * scale, seed + 3, 3)
    f = fbm(c.shape, 240 * scale, seed + 5, 2)
    alb = ramp(clamp(0.5 + 0.35 * a + 0.28 * b + 0.15 * f), '#22380F', '#3F6A1C', '#6A9A2E', '#A8C84E')
    return alb, 0.018 * a + 0.010 * b + 0.006 * f


def fern(ink, x, y, a, s, hang=1.0):
    """One frond from (x, y) in direction a."""
    n = 15
    for k in range(n):
        t = k / (n - 1)
        bend = a + 0.35 * t * hang
        px, py = x + math.sin(bend) * s * t, y - math.cos(bend) * s * t
        L = s * 0.34 * (math.sin(math.pi * (0.12 + 0.86 * t)) ** 0.8)
        for side in (-1, 1):
            q = bend + side * (1.25 - 0.45 * t)
            ink.brush(bez((px, py), (px + math.sin(q) * L * 0.5, py - math.cos(q) * L * 0.5), (px + math.sin(q + side * -0.25) * L * 0.8, py - math.cos(q + side * -0.25) * L * 0.8), (px + math.sin(q - side * 0.35) * L, py - math.cos(q - side * 0.35) * L), 8), s * 0.060)
    ink.line([(x + math.sin(a + 0.35 * t * hang) * s * t, y - math.cos(a + 0.35 * t * hang) * s * t) for t in np.linspace(0, 1, 14)], s * 0.018)


def ground():
    c = K.canvas(1100, 2)
    alb, h = moss_tex(c, 3)
    H = 0.05 + h
    # bare earth and pebbles between the cushions
    e = clamp(fbm(c.shape, 5, 14, 5) * 1.6 - 0.15)
    soil = ramp(clamp(0.5 + 0.5 * fbm(c.shape, 60, 15, 3)), '#1E140C', '#3A281A', '#5A4029')
    alb = mix(alb, soil, smooth(0.15, 0.45, e)[..., None])
    H = H - 0.030 * smooth(0.15, 0.45, e)
    d1, d2, v = worley(c.X, c.Y, 26, 9, True)
    peb = smooth(0.34, 0.27, d1) * smooth(0.05, 0.25, e) * (v > 0.45)
    alb = mix(alb, mix(flat('#6E6A62', c.shape), flat('#C2BAA8', c.shape), v[..., None]), peb[..., None])
    H = H + peb * 0.030 * np.sqrt(clamp(1 - (d1 / 0.36) ** 2))
    g = rng(6)
    col = surface(c, H, alb, DAY, rough=0.8, reach=0.07, ao_r=(0.006, 0.015, 0.04), ao_s=1.3)
    # ferns growing in from the edge, darker ones first
    for layer, (n, tone, s0) in enumerate(((20, ('#1E3A12', '#35601C'), 0.30), (17, ('#2F5A18', '#5A8A2A'), 0.26), (12, ('#467A22', '#86B43E'), 0.21))):
        ink = Ink(c)
        for k in range(n):
            a = (k + 0.6 * g.random()) * TAU / n
            x, y = c.polar(a, 0.965)
            fern(ink, x, y, a + math.pi + 0.5 * g.standard_normal(), s0 * (0.8 + 0.4 * g.random()), -1 if g.random() < 0.5 else 1)
        cov = ink.arr(0.0006)
        sh = blur(shift(cov, int(0.010 / c.px), int(0.016 / c.px)), 0.008 / c.px)
        col = col * (1 - 0.55 * sh * (1 - cov))[..., None]
        leafc = ramp(clamp(0.5 + 0.5 * fbm(c.shape, 30, 20 + layer, 3)), *tone) * (0.70 + 0.5 * smooth(0.95, 0.65, c.R))[..., None]
        col = mix(col, leafc, (cov * 0.97)[..., None])
    for k in range(9):              # little red mushrooms
        a, r = g.random() * TAU, 0.80 + 0.10 * g.random()
        x, y, s = math.sin(a) * r, -math.cos(a) * r, 0.016 + 0.010 * g.random()
        q = np.hypot(c.X - x, c.Y - y)
        col = col * (1 - 0.5 * gauss(np.maximum(0, np.hypot(c.X - x - 0.008, c.Y - y - 0.012) - s * 0.9), 0.010) * (q > s))[..., None]
        z = np.sqrt(clamp(1 - (q / s) ** 2))
        cap = rgb('#C82A1E') * (0.45 + 0.75 * clamp(0.6 * z - 0.4 * (c.X - x) / s - 0.5 * (c.Y - y) / s))[..., None]
        for j in range(5):
            ja = j * 1.3 + k
            cap = mix(cap, flat('#FFF6E6', c.shape), smooth(s * 0.17, s * 0.12, np.hypot(c.X - x - math.sin(ja) * s * 0.55, c.Y - y + math.cos(ja) * s * 0.55))[..., None])
        col = mix(col, cap, c.cover(q - s)[..., None])
    c.put(col, c.cover(c.R - 0.975))
    K.put(c, 'ground', exposure=1.02, quality=86)


def glass():
    """The rim of the jar and the lid's reflections, with drops on the inside."""
    c = K.canvas(1100, 2)
    u = (c.R - 0.972) / 0.028
    inside = np.abs(u) < 1
    toward = -(np.sin(c.A) * 0.5 - np.cos(c.A) * 0.86 * 1.0)
    li = inside * (0.16 + 0.55 * gauss(u + 0.45, 0.22) * (0.35 + 0.65 * np.abs(toward)) + 0.35 * gauss(u - 0.6, 0.18) * (0.3 + 0.7 * clamp(-toward)))
    dk = inside * 0.30 * gauss(np.abs(u) - 0.95, 0.16)
    ax, ay = c.X + 0.04, c.Y + 0.07
    rr = np.hypot(ax, ay)
    win = smooth(0.80, 0.84, rr) * (1 - smooth(0.915, 0.95, rr)) * smooth(0.60, 0.97, -(ax * 0.5 + ay * 0.86) / np.maximum(rr, 1e-4))
    li = li + 0.30 * win * (c.R < 0.945)
    g = rng(12)
    drop_l, drop_d = np.zeros(c.shape, F), np.zeros(c.shape, F)
    for _ in range(150 if K.draft == 1 else 60):
        a, r = g.random() * TAU, 0.945 - abs(g.standard_normal()) * 0.055
        x, y, s = math.sin(a) * r, -math.cos(a) * r, 0.0035 + 0.010 * g.random() ** 2
        px, py = int((x + 1) * c.w / 2), int((y + 1) * c.h / 2)
        k = int(s / c.px * 1.6) + 3
        sl = (slice(max(0, py - k), py + k), slice(max(0, px - k), px + k))
        lx, ly = (c.X[sl] - x) / s, (c.Y[sl] - y) / s
        q = np.hypot(lx, ly)
        m = clamp((1 - q) * s / c.px + 0.5)
        drop_l[sl] = np.maximum(drop_l[sl], m * (0.80 * gauss(np.hypot(lx + 0.36, ly + 0.40), 0.26) + 0.45 * gauss(np.hypot(lx - 0.38, ly - 0.42), 0.34) + 0.06))
        drop_d[sl] = np.maximum(drop_d[sl], m * 0.28 * smooth(0.5, 1.0, q))
    li = clamp(li + drop_l)
    dk = clamp(dk + drop_d)
    a = clamp(li + dk * (1 - li))
    c.col = from_srgb(np.ones(c.shape + (3,), F) * (li / np.maximum(li + dk * (1 - li), 1e-4))[..., None] * np.array([0.95, 1.0, 0.96], F))
    c.alpha = (a * c.cover(c.R - 1.0)).astype(F)
    K.put(c, 'glass', tone=False)


def wood_slice(c, seed, r=0.86, bark=0.10, moss=0.0, calm=0.0):
    g = rng(seed)
    ph = g.random(3) * TAU
    rr = r * (1 + 0.020 * np.sin(2 * c.A + ph[0]) + 0.014 * np.sin(3 * c.A + ph[1]) + 0.010 * np.sin(7 * c.A + ph[2]))
    d = c.R - rr
    q = c.R / rr
    warp = 0.04 * fbm(c.shape, 5, seed + 3, 3)
    rings = 0.5 + 0.5 * np.sin((q + warp) * 46)
    rings = rings * (1 - calm * smooth(0.82, 0.60, q))
    alb = mix(flat('#E3C08A', c.shape), flat('#B07E46', c.shape), (0.55 * rings ** 2 + 0.12)[..., None])
    alb = mix(alb, flat('#8A5A30', c.shape), (0.35 * gauss(q, 0.18))[..., None])
    for k in range(3):
        ca = ph[k]
        crack = gauss(((c.A - ca + math.pi) % TAU - math.pi) * c.R, 0.010 + 0.006 * q) * smooth(0.15, 0.4, q) * smooth(0.96, 0.8, q)
        alb = alb * (1 - 0.55 * crack)[..., None]
    isb = smooth(1 - bark * 1.0, 1 - bark * 0.75, q)
    b = fbm(c.shape, 22, seed + 8, 4)
    alb = mix(alb, ramp(clamp(0.5 + 0.6 * b), '#24160C', '#4A3220', '#6E5238'), isb[..., None])
    H = np.where(q < 1 - bark * 0.8, 0.14 - 0.02 * rings, 0.15 + 0.05 * b) * smooth(0.0, -0.05, d)
    if moss:
        mm = clamp(fbm(c.shape, 4, seed + 11, 4) * 1.6 + moss - 0.5) * smooth(0.80, 0.94, q)
        ma, mh = moss_tex(c, seed + 13, 0.6)
        alb = mix(alb, ma, clamp(mm * 1.3)[..., None])
        H = H + 0.05 * clamp(mm) + mh * clamp(mm)
    return alb, H, d


def slices():
    ims = []
    for k in range(4):
        c = K.canvas(250, 3)
        alb, H, d = wood_slice(c, 30 + k * 5, 0.86, 0.11, 0.45 if k % 2 else 0.15)
        sh = 0.55 * gauss(np.maximum(0, np.hypot(c.X - 0.05, c.Y - 0.08) - 0.86), 0.08) * smooth(1.0, 0.95, np.maximum(np.abs(c.X), np.abs(c.Y)))
        c.put(np.zeros(3, F), sh.astype(F))
        c.put(surface(c, H, alb, DAY, rough=0.7, reach=0.2), c.cover(d), H)
        ims.append(c.image())
    K.sheet(ims, 4, 'slices', how='jpg')
    c = K.canvas(500, 2)
    alb, H, d = wood_slice(c, 77, 0.93, 0.10, 0.75, 0.85)
    alb = mix(alb, flat('#F0DCB4', c.shape), (0.45 * smooth(0.80, 0.55, c.R))[..., None])
    c.put(surface(c, H, alb, DAY, rough=0.7, reach=0.14), c.cover(d), H)
    K.put(c, 'stump', exposure=0.97)


def bits():
    ims = []
    for k, tone in enumerate((('#2F5A18', '#7FB23A'), ('#3F7A22', '#A8D05A'), ('#5A7A1E', '#C8D46A'), ('#2A6A3A', '#6AC07A'))):
        c = K.canvas(72, 4)
        a = k * 0.9
        pts = turned(bez((0, 0.92), (0.72, 0.35), (0.55, -0.55), (0, -0.94), 16) + bez((0, -0.94), (-0.55, -0.55), (-0.72, 0.35), (0, 0.92), 16), a, 0.96)
        cov = Ink(c).poly(pts).arr(0.01)
        u, v = c.X * math.cos(a) + c.Y * math.sin(a), -c.X * math.sin(a) + c.Y * math.cos(a)
        vein = np.maximum(gauss(u, 0.035), 0.6 * smooth(0.12, 0.04, np.abs(((v + np.abs(u) * 0.8) * 4) % 1 - 0.5)) * (np.abs(u) > 0.05))
        col = ramp(clamp(0.5 - 0.35 * v + 0.25 * np.sign(u) * 0.4), *tone)
        c.col = mix(col, flat('#E6F2C0', c.shape), (0.35 * vein)[..., None]).astype(F)
        c.alpha = cov
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'leaves')
    c = K.canvas(220, 3)             # a pair of seed leaves that unfolds under what is selected
    for s in (-1, 1):
        for rot, sc in ((0.95, 1.0), (1.75, 0.72)):
            pts = turned(bez((0, 0), (0.28, -0.25), (0.26, -0.72), (0, -0.98), 16) + bez((0, -0.98), (-0.26, -0.72), (-0.28, -0.25), (0, 0), 16), s * rot, sc)
            cov = Ink(c).poly(pts).arr(0.006)
            q = s * rot
            u, v = c.X * math.cos(q) + c.Y * math.sin(q), -c.X * math.sin(q) + c.Y * math.cos(q)
            col = ramp(clamp(-v), '#2F6A1C', '#5AA02E', '#A8DC5A') * (0.88 + 0.12 * np.sign(u))[..., None]
            col = mix(col, flat('#E6F7B8', c.shape), (0.5 * gauss(u, 0.018))[..., None])
            c.put(col, cov)
    K.put(c, 'sprout', how='png', tone=False)
    c = K.canvas(110, 4)             # ladybird, walking up
    for s in (-1, 1):
        for y in (-0.25, 0.1, 0.42):
            c.put(rgb('#141414'), c.cover(c.capsule(0, y, s * 0.86, y - 0.18, 0.045)))
    c.put(rgb('#161616'), c.cover(np.hypot(c.X, c.Y + 0.56) - 0.30))
    d = np.hypot(c.X / 0.62, (c.Y - 0.10) / 0.70) - 1
    z = np.sqrt(clamp(1 - (d + 1) ** 2))
    col = rgb('#E0241A') * (0.40 + 0.75 * clamp(0.6 * z - 0.35 * c.X - 0.45 * c.Y))[..., None] + (0.6 * gauss(np.hypot(c.X + 0.22, c.Y + 0.20), 0.14))[..., None]
    spots = np.minimum.reduce([np.hypot(c.X - x, c.Y - y) - r for x, y, r in ((-0.30, -0.10, 0.12), (0.30, -0.10, 0.12), (-0.26, 0.34, 0.13), (0.26, 0.34, 0.13), (0, -0.40, 0.12))])
    col = mix(col, flat('#141414', c.shape), np.maximum(c.cover(spots), smooth(0.030, 0.012, np.abs(c.X)))[..., None])
    c.put(col, c.cover(d * 0.62))
    for s in (-1, 1):
        c.put(np.ones(3, F), c.cover(np.hypot(c.X - s * 0.16, c.Y + 0.66) - 0.055))
    K.put(c, 'bug', how='png', tone=False)
    ims = []
    for f in range(2):
        c = K.canvas(130, 4)
        sq = 1.0 if f == 0 else 0.45
        for s in (-1, 1):
            for pts, cc in ((bez((0, -0.05), (0.5, -1.1), (1.15, -0.75), (0.75, 0.0), 16) + bez((0.75, 0.0), (0.4, 0.12), (0.2, 0.1), (0, 0.05), 8), '#4A8AFF'), (bez((0, 0.0), (0.6, 0.0), (0.95, 0.5), (0.5, 0.82), 14) + bez((0.5, 0.82), (0.2, 0.8), (0.1, 0.4), (0, 0.1), 8), '#2E5FE0')):
                q = [(x * s * sq * 0.92, y * 0.92) for x, y in pts]
                d = c.poly(q)
                col = mix(flat(cc, c.shape), flat('#0E1430', c.shape), smooth(-0.10, -0.02, d)[..., None])
                col = mix(col, flat('#CFE6FF', c.shape), (0.6 * gauss(np.hypot(c.X - s * 0.45 * sq, c.Y + 0.35), 0.13))[..., None])
                c.put(col, c.cover(d))
        c.put(rgb('#141018'), c.cover(c.capsule(0, -0.35, 0, 0.45, 0.06)))
        for s in (-1, 1):
            c.put(rgb('#141018'), c.cover(c.capsule(0, -0.36, s * 0.2, -0.72, 0.018)))
        ims.append(c.image(tone=False))
    K.sheet(ims, 2, 'fly')
    light(K, 'shaft', 420, lambda q: 0.55 * np.maximum.reduce([gauss(q.X * 0.80 + q.Y * 0.60 - o, w) * k for o, w, k in ((-0.45, 0.10, 1.0), (-0.12, 0.06, 0.7), (0.20, 0.13, 0.8), (0.52, 0.05, 0.5))]) * smooth(0.98, 0.5, q.R), '#FFF6C8')
    halo(K, 'halo', 200, 2.0, 0.1, '#FFF2B0')
    halo(K, 'mote', 32, 1.6, 0.0, '#FFF6C8')


K.run([ground, glass, slices, bits])
K.sounds('drip')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#2A3A1A', accent='#A8DC5A', accent2='#FFD24A', text='#F4F9E6', border='#86B43E', opacity=0.97, corner=14, font='Candara', open='bloom', speed=0.95, hoverGrow=3,
               iconZoom=1.12, glow=0.2, tilt=0.5, pointer=False, burst=False, shadow=0.6, dim=0.30),
    wheel=dict(hub=92, thickness=92, gap=5, ringgap=10, rim=44, icon=42, crowd=1.48, area=1.12, hubkeep=0.72),
    colors=dict(ink='#3A200E', bark='#7A4A1E', pale='#F4F9E6'), fonts=dict(title='Candara, Segoe UI'),
    back=[soft(1.09, 0.03, 60), img('ground', 1, intro=intro(0.30, 'out', scale=0.88, rotate=-8))],
    slot=dict(intro=intro(0.38, 'back', 0.06, scale=0.1, rotate=60, stagger=0.022, order='random'),
              under=[img('halo', 1.8, opacity='0.35*hot+launch'), img('sprout', '1.80*(0.15+0.85*outback(sat(hot)))', rotate='6*sin(time*1.8+seed*6)+a', opacity='sat(hot*4)', when='hot>0.01'), img('slices', '1.06*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='0', detail=1.06)],
              icon=dict(size=1.0, zoom=1.14, shadow=dict(x=1, y=2, blur=3, color='#2A1608/60')),
              over=[img('leaves', 0.30, x=0.64, y=0.56, frame='i%4', rotate='seed*80+6*sin(time*1.5)', when='running'), img('bug', 0.24, x='0.64+0.04*sin(time*2)', y='0.52', rotate='20*sin(time*1.3)', when='active')]
              + badge('#2A3A1A', 'pale', T, x=-0.64, y=-0.64) + groupmark('pale', -0.88, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.16, 0.06, 60, 0.80, **{'in': 'hub'}), img('leaves', 0.26, **{'in': 'hub'}, angle='sel', radius=1.10, frame=1, rotate='sel+180-22+8*sin(time*2)', opacity='on', scale='0.4+0.6*on')],
    hub=[img('stump', 1.0, intro=intro(0.36, 'back', scale=0.4, rotate=-60))] + words('ink', 'bark', T, px=18, y=-0.04, box=(1.22, 0.52), clockpx=31, datepx=12.5, shadow=dict(x=0, y=0, blur=3, color='#F7E9C8'))
    + [img('bug', 0.115, angle='-time*11', radius=0.90, rotate='-time*11-90+6*sin(time*9)', opacity='smooth(0.3,0.6,time)')],
    front=[img('shaft', 0.96, opacity='0.20+0.06*noise(time*0.7)', rotate='3*sin(time*0.2)'), img('glass', 1.0), img('fly', 0.075, x='0.62*sin(time*0.55)+0.05*sin(time*3)', y='0.50*sin(time*0.83+1)-0.1', frame='floor(time*9)%2', rotate='35*sin(time*0.55)', opacity='smooth(0.6,1.0,time)*(0.55+0.45*idle)')],
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=15, text='ink', fill='#86B43E/35', on='#5A8A2A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#3F5A22'], [1, '#22330F']]}, stroke={'type': 'linear', 'stops': [[0, '#EAF6E0'], [0.5, '#7A9A5A'], [1, '#D6ECC0']]}, width=2.6, corner=16, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#E3C08A'], [1, '#C0925A']]}, stroke='#4A3220', width=2, corner=9, text='ink'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#E3C08A'], [1, '#B8884E']]}, stroke='#4A3220', width=3, corner=11, text='ink'),
    particles=[dict(image='mote', light=True, rate=3, max=20, area='wheel', life=[1.8, 3.4], size=[2, 4.5], speed=[3, 10], dir=[0, 360], sway=12, swayhz=0.5, fadein=0.3, fadeout=0.5, opacity=0.7)],
    onlaunch=[dict(image='leaves', count=26, area='slot', life=[0.6, 1.1], size=[8, 17], speed=[90, 340], outward=True, dir=[-110, 110], gravity=260, drag=2, sway=16, swayhz=1.2, spin=[-260, 260], fadein=0, fadeout=0.4), dict(image='fly', count=4, area='slot', life=[0.9, 1.4], size=[12, 20], speed=[80, 200], dir=[-70, 70], gravity=-60, sway=30, swayhz=1.6, fadein=0.05, fadeout=0.4)],
    onhover=[dict(image='leaves', count=2, area='slot', life=[0.5, 0.9], size=[4, 7], speed=[20, 60], outward=True, dir=[-80, 80], gravity=90, spin=[-160, 160], fadein=0, fadeout=0.5)])
