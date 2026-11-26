"""Orrery: brass arms carry planets round a glowing sun, over a star map in blue enamel. Made for the Orbit layout too."""
from skinkit import *

K = Kit('orrery', 'Orrery', 'Planets on brass arms round a glowing sun', ['space', 'brass', 'elegant'], 'Font Cinzel: SIL Open Font License, see OFL.txt')
K.flag(planets=dict(cols=4, rows=2), corona='light', halo='light', rays='light', comet='light', twinkle='light')


def plate():
    c = K.canvas(1080, 2)
    H = lathe(c, [(0, 0.012), (0.872, 0.012), (0.880, 0.034), (0.900, 0.040), (0.960, 0.040), (0.972, 0.055), (0.992, 0.050), (1.0, 0.01)], 0.003)
    neb = fbm(c.shape, 4, 5, 6)
    alb = mix(flat('#0A1338', c.shape), flat('#1C2F78', c.shape), clamp(0.45 + 0.45 * neb)[..., None])
    alb = mix(alb, flat('#3B2470', c.shape), clamp(0.5 * fbm(c.shape, 3, 9, 4))[..., None])
    st = stars(c, 420, 3, 0.1, 0.865, 0.0030)
    ink = Ink(c)
    g = rng(8)
    for k in range(13):             # constellations that do not exist
        a0, r0 = g.random() * TAU, 0.46 + 0.38 * g.random()
        p = [(math.sin(a0) * r0, -math.cos(a0) * r0)]
        for _ in range(3 + int(g.random() * 3)):
            a0 += (g.random() - 0.4) * 0.28
            r0 = min(0.85, max(0.42, r0 + (g.random() - 0.5) * 0.16))
            p.append((math.sin(a0) * r0, -math.cos(a0) * r0))
        ink.line(p, 0.0022, 150)
        for x, y in p:
            ink.dot(x, y, 0.0062)
    for r, w in ((0.865, 0.004), (0.655, 0.0022), (0.44, 0.0022)):
        ink.line(arcpts(r, 0, TAU, 400), w, 190)
    ink.line(arcpts(0.60, 0, TAU, 400, 0.10, 0.13), 0.0018, 120)
    for k in range(24):
        ink.line([c.polar(k * TAU / 24, 0.44), c.polar(k * TAU / 24, 0.865)], 0.0012, 70)
    col = surface(c, H, alb, COOL, rough=0.3, clear=0.7, reach=0.1)
    gold = metal(c, H, GOLD, rough=0.25, grime=0.2, studio=WARM)
    col = mix(col, gold, (ink.arr(0.0004) * 0.9)[..., None])
    col = col + (st * 0.9)[..., None] * rgb('#E8F0FF')
    ring = smooth(0.874, 0.878, c.R)
    tick = Ink(c)
    for k in range(180):
        r0 = 0.905 if k % 5 else 0.892
        tick.line([c.polar(k * TAU / 180, r0), c.polar(k * TAU / 180, 0.922)], 0.0022 if k % 5 else 0.0040)
    H2 = H - 0.004 * tick.arr(0.0006)
    brass = metal(c, H2 + 0.0004 * circular_streaks(c, 4, 1300), BRASS, rough=0.22, grime=0.55, aniso=(np.cos(c.A), np.sin(c.A), 0.4))
    brass = brass * (1 - 0.6 * tick.arr())[..., None]
    g2 = rng(21)
    sg = Ink(c)
    for k in range(12):             # made-up signs of the houses
        a = (k + 0.5) * TAU / 12
        x, y = c.polar(a, 0.943)
        s = 0.013
        kind = k % 6
        if kind == 0:
            sg.line(arcpts(s, 0, TAU, 20, x, y), 0.004); sg.dot(x, y, 0.004)
        elif kind == 1:
            sg.line(turned(arcpts(1, -1.9, 1.9, 14), a, s, x, y), 0.004); sg.line(turned([(-1, 0.3), (1, 0.3)], a, s, x, y), 0.004)
        elif kind == 2:
            sg.line(turned([(-1, 0.8), (0, -0.9), (1, 0.8)], a, s, x, y), 0.004, closed=True)
        elif kind == 3:
            sg.line(turned([(0, -1), (0, 1)], a, s, x, y), 0.004); sg.line(turned(arcpts(0.7, 1.2, 5.1, 14), a, s, x, y), 0.004)
        elif kind == 4:
            for j in (-0.5, 0.5):
                sg.line(turned(bez((-1, j), (-0.3, j - 0.8), (0.3, j + 0.8), (1, j), 12), a, s, x, y), 0.004)
        else:
            sg.line(turned([(-0.8, -0.8), (0.8, 0.8)], a, s, x, y), 0.004); sg.line(turned([(0.8, -0.8), (-0.8, 0.8)], a, s, x, y), 0.004)
    brass = brass * (1 - 0.7 * sg.arr(0.0005))[..., None]
    col = mix(col, brass, ring[..., None])
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'plate', exposure=0.95)
    c = K.canvas(40, 4, 1.0, 5.0)            # an arm
    d = np.abs(c.X) - 0.34
    H = 0.4 * np.sqrt(clamp(1 - (c.X / 0.36) ** 2))
    bead = np.abs(((c.Y + 5) % 3.3) - 1.65) < 0.35
    H = np.where(bead, H * 1.2 + 0.1, H)
    c.put(metal(c, H, BRASS, rough=0.2, grime=0.3, shadows=False) if False else metal(c, H, BRASS, rough=0.2, grime=0.3, reach=0.3), np.where(bead, c.cover(np.abs(c.X) - 0.62), c.cover(d)) * c.cover(np.abs(c.Y) - 4.95))
    K.put(c, 'arm', how='png')


def sphere(c, fn, r=0.80, atmo=None):
    q = c.R / r
    z = np.sqrt(clamp(1 - q * q))
    x, y = c.X / r, c.Y / r
    # tilted so the bands do not lie flat
    ca, sa = math.cos(0.35), math.sin(0.35)
    lat = np.arcsin(clamp(-x * sa + y * ca, -1, 1))
    lon = np.arctan2(x * ca + y * sa, np.maximum(z, 1e-4))
    col = fn(lon, lat, x, y, z)
    li = clamp(-0.52 * x - 0.60 * y + 0.60 * z)
    k = 0.10 + 1.15 * np.power(li, 0.9)
    col = col * k[..., None]
    rim = np.power(clamp(1 - z), 3) * clamp(0.3 - 0.5 * x - 0.6 * y)
    if atmo:
        col = col + rgb(atmo) * (0.9 * rim)[..., None]
    c.put(col, c.cover(c.R - r))
    if atmo:
        g = 0.50 * gauss(np.maximum(0, c.R - r), 0.06) * clamp(0.35 - 0.4 * x - 0.5 * y) * (c.R > r - 0.01)
        c.put(rgb(atmo), g.astype(F) * (c.alpha < 0.98))
    return c


def planets():
    def noise(c, s, cells=6, sx=1.0, sy=1.0):
        f = fbm((c.h, c.w), cells, s, 5)
        return f

    def bands(cols, seed, n=7, turb=0.35):
        def fn(lon, lat, x, y, z):
            t = np.sin(lat * n + turb * fbm(lat.shape, 5, seed, 4) + 0.25 * np.sin(lon * 3 + lat * 9)) * 0.5 + 0.5
            t2 = np.sin(lat * n * 2.3 + 1.0) * 0.5 + 0.5
            return ramp(clamp(0.7 * t + 0.3 * t2), *cols)
        return fn

    def rock(cols, seed, cr=0):
        def fn(lon, lat, x, y, z):
            n = fbm(lat.shape, 5, seed, 6) * 0.5 + 0.5
            col = ramp(clamp(n * 1.15 - 0.05), *cols)
            if cr:
                d1 = worley(x * 1.0 + 3, y + 3, cr, seed)
                col = col * (1 - 0.35 * smooth(0.30, 0.18, d1) + 0.25 * gauss(d1 - 0.33, 0.05))[..., None]
            return col
        return fn

    def earthy(lon, lat, x, y, z):
        n = fbm(lat.shape, 4, 14, 6)
        land = smooth(0.02, 0.10, n)
        col = mix(ramp(clamp(0.5 + n), '#0B2A6B', '#1E66B8', '#3FA0D8'), ramp(clamp(n * 1.2), '#2F7A3A', '#7FA24A', '#C2A66A'), land[..., None])
        cloud = smooth(0.15, 0.55, fbm(lat.shape, 6, 33, 5))
        ice = smooth(1.05, 1.22, np.abs(lat))
        return mix(col, flat('#F4F8FF', lat.shape), clamp(cloud * 0.8 + ice)[..., None])

    def lava(lon, lat, x, y, z):
        n = np.abs(fbm(lat.shape, 6, 44, 5))
        crack = gauss(n, 0.045)
        return ramp(clamp(n * 2), '#2A0E0A', '#55221A', '#3A1810') + rgb('#FF6A1A') * (2.4 * crack)[..., None]

    specs = [(rock(('#5A1E10', '#A8481F', '#D98850', '#F0C49A'), 3), '#FFB48A'), (bands(('#8A5A34', '#D9B27C', '#F4E3C0', '#B8753E'), 5), '#FFE7C0'), (earthy, '#8FD0FF'), (bands(('#1E5FB8', '#3F9AE0', '#8AD0F4', '#2A78CC'), 8, 5, 0.25), '#9FE0FF'),
             (rock(('#4A4A50', '#86868C', '#B9B9BC', '#E0E0E0'), 12, 6), None), (lava, '#FF8A4A'), (bands(('#5A2A9A', '#9A5AD8', '#D9A8F4', '#6A34B4'), 17, 6, 0.6), '#E0B8FF'), (bands(('#C9A86A', '#E9D3A0', '#FFF4D8', '#B8935A'), 21, 9, 0.15), '#FFF0CC')]
    ims = []
    for k, (fn, at) in enumerate(specs):
        c = K.canvas(250, 3)
        sphere(c, fn, 0.80 if k != 7 else 0.66, at)
        if k == 7:                  # rings, half behind and half in front
            x, y = c.X * math.cos(0.38) + c.Y * math.sin(0.38), (-c.X * math.sin(0.38) + c.Y * math.cos(0.38)) / 0.30
            r = np.hypot(x, y)
            ringcov = smooth(0.74, 0.76, r) * smooth(0.985, 0.96, r) * (0.65 + 0.35 * np.sin(r * 90)) * (1 - 0.8 * gauss(r - 0.865, 0.012))
            front = y > 0
            inside = c.R < 0.66
            cov = ringcov * (front | ~inside)
            c.put(ramp(clamp((r - 0.74) / 0.24), '#8A6A3A', '#E9D3A0', '#B8935A') * (0.75 + 0.25 * clamp(-x))[..., None], (cov * 0.95).astype(F))
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'planets')
    c = K.canvas(60, 4)
    sphere(c, rock(('#6A6A70', '#A0A0A6', '#D8D8DA'), 5, 4), 0.86, None)
    K.put(c, 'moon', how='png', tone=False)


def sun():
    c = K.canvas(460, 2)
    n = fbm(c.shape, 7, 4, 6)
    q = clamp(c.R / 0.94)
    z = np.sqrt(1 - q * q)
    col = ramp(clamp(0.30 + 0.55 * z + 0.22 * n), '#E8640C', '#FF9A1F', '#FFC94A', '#FFE48A')
    cell = worley(c.X, c.Y, 9, 5)
    col = col * (1 - 0.10 * smooth(0.25, 0.55, cell))[..., None]
    c.put(col, c.cover(c.R - 0.94))
    K.put(c, 'sun', tone=False)
    light(K, 'corona', 420, lambda q: 0.85 * gauss(np.maximum(0, q.R - 0.50), 0.16) + 0.35 * gauss(np.maximum(0, q.R - 0.50), 0.40), '#FFA030')

    def rays(q):
        g = rng(6)
        n = 260
        prof = blur1(np.abs(g.standard_normal((1, n))).astype(F), 1.0, 1)[0]
        u = (q.A / TAU + 0.5) * (n - 1)
        i = np.floor(u).astype(int)
        p = prof[i] * (1 - (u - i)) + prof[(i + 1) % n] * (u - i)
        return 0.75 * p * np.power(clamp(1 - (q.R - 0.45) / 0.53), 1.8) * smooth(0.40, 0.52, q.R)
    light(K, 'rays', 520, rays, '#FFC46A')
    halo(K, 'halo', 220, 2.0, 0.15)
    light(K, 'twinkle', 64, lambda q: gauss(q.R, 0.16) + 0.6 * gauss(q.X, 0.05) * smooth(0.9, 0, np.abs(q.Y)) + 0.6 * gauss(q.Y, 0.05) * smooth(0.9, 0, np.abs(q.X)))
    light(K, 'comet', 200, lambda q: gauss(np.hypot(q.X + 0.72, q.Y * 1.0), 0.10) * 1.2 + 0.7 * gauss(q.Y / (0.04 + 0.10 * clamp(q.X + 0.75)), 1.0) * smooth(0.95, -0.72, q.X) * (q.X > -0.75), '#CFE6FF')


K.run([plate, planets, sun])
K.font('cinzel', 'Cinzel[wght].ttf')
K.sounds('celesta')
T = 'title'
both = ['radial', 'orbit']
glow = [img('corona', 1.9, **{'in': 'hub'}, only=both, opacity='0.42+0.06*noise(time*3)+launch'), img('rays', 2.1, **{'in': 'hub'}, only=both, rotate='time*5', opacity='0.30'), img('rays', 1.9, **{'in': 'hub'}, only=both, rotate='-time*7+40', opacity='0.20')]
sunny = [img('sun', 1.02, only=both, rotate='time*2', intro=intro(0.4, 'back', scale=0.2))]
K.write(
    style=dict(shape='orb', material='solid', base='#0E1640', accent='#FFC94A', accent2='#8FD0FF', text='#F4EBD2', border='#C99A45', opacity=0.97, corner=10, font='Cinzel', open='bloom', speed=0.95, hoverGrow=3,
               iconZoom=1.14, glow=0.5, tilt=0.6, pointer=False, burst=False, shadow=0.6, dim=0.40),
    wheel=dict(hub=90, thickness=98, gap=5, ringgap=10, rim=40, icon=42, crowd=1.5, area=1.10, hubkeep=0.74),
    colors=dict(ink='#4A1E04', deep='#8A3A08', pale='#F4EBD2', gold='#FFC94A'), fonts=dict(title=dict(file='Cinzel[wght].ttf', family='Cinzel', weight=700)),
    back=[soft(1.09, 0.025, 66), img('plate', 1, rotate='(1-open)*-20', intro=intro(0.34, 'out', scale=0.86)), img('twinkle', 0.05, copies=12, angle='rnd(j)*360', radius='0.45+0.4*rnd(j+50)', opacity='smooth(0.6,1,wave(time*0.35+rnd(j+9)))')] + glow,
    ring=[dict(shape='arc', **{'in': 'px', 'from': 0}, r='(ringin+ringout)/2', to='360*outcubic(sat(time*2))', stroke={'type': 'linear', 'stops': [[0, '#FFE7A6'], [0.5, '#8A6427'], [1, '#E0B565']]}, width=3.2),
          dict(shape='line', **{'in': 'px'}, points=[['sin(rad(a+j*span))*(ringin-16)', '-cos(rad(a+j*span))*(ringin-16)'], ['sin(rad(a+j*span))*((ringin+ringout)/2-20)', '-cos(rad(a+j*span))*((ringin+ringout)/2-20)']], copies='n', stroke={'type': 'linear', 'stops': [[0, '#F0C97A'], [1, '#8A6427']]}, width=4)],
    slot=dict(intro=intro(0.55, 'out', 0.04, angle=-200, scale=0.5, stagger=0.02, order='ring'),
              under=[img('halo', 1.8, opacity='0.50*hot+launch*1.5', tint='item'), soft(1.02, 0.10, 50, 0.6, x=0.07), img('planets', '1.16*(1+0.05*hot-0.03*press)', frame='(i*3+ring*2)%8', rotate='0', detail=1.06)],
              icon=dict(size=0.84, zoom=1.20, shadow=dict(y=2, blur=4, color='black/70')),
              over=[img('moon', 0.17, angle='time*(40+60*rnd(i+3))+i*70', radius='1.02', opacity='0.4+0.6*hot', when='!kid'), dict(shape='arc', r=1.04, **{'from': 'time*30'}, to='time*30+300', stroke='gold', width=1.6, opacity='sat(hot)', glow=4, glowcolor='gold'),
                    img('comet', [1.6, 1.6], rotate='a-60', radius='2.0*launch', angle='a', opacity='launch*(1-launch)*4', when='launch>0.01')]
              + running('#FFC94A', '#FFF6D8', 0.94, 0.14) + badge('#0E1640', 'pale', T, stroke='#C99A45') + groupmark('gold', -0.98, 0.12), marks=False, chevron=False, badge=False),
    over=[img('twinkle', 0.42, **{'in': 'hub'}, angle='sel', radius=1.12, opacity='on*(0.8+0.2*noise(time*8))', rotate='time*30')],
    hub=sunny + words('ink', 'deep', T, px=16.5, box=(1.34, 0.52), clockpx=29, datepx=11.5, subpx=10.5),
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=13, text='ink', fill='#FFF0B8/40', on='#C9480C/80'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#1A2968'], [1, '#0A1030']]}, stroke={'type': 'linear', 'stops': [[0, '#FFE7A6'], [0.5, '#8A6427'], [1, '#E0B565']]}, width=2.6, corner=12, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#16225A'], [1, '#0A1030']]}, stroke='#C99A45', width=1.6, corner=9, text='pale'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#1C2F78'], [1, '#0A1030']]}, stroke='#C99A45', width=2, corner=9, text='pale'),
    particles=[dict(color='#FFE7A6', light=True, rate=2, max=16, area='wheel', life=[1.5, 3], size=[1, 2.2], speed=[1, 5], dir=[0, 360], fadein=0.4, fadeout=0.5)],
    onlaunch=[dict(color='#FFE7A6', light=True, count=40, area='slot', life=[0.3, 0.8], size=[1.5, 3.5], speed=[100, 480], outward=True, dir=[-100, 100], drag=2.5, fadein=0, fadeout=0.6)])
