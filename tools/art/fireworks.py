"""Fireworks: a city by the water at night; every launch is a rocket."""
from skinkit import *

K = Kit('fireworks', 'Fireworks', 'A city by the water at night, where every launch is a rocket', ['season', 'night', 'festive'], 'Font Righteous: SIL Open Font License, see OFL.txt')
K.flag(burst1='light', burst2='light', burst3='light', sparkler='light', halo='light', twinkle='light')


def city():
    c = K.canvas(1080, 2)
    WL = 0.42                                     # waterline
    t = clamp((c.Y + 1) / (1 + WL))
    col = ramp(t, '#050A24', '#0C1742', '#26235E', '#5A2E6A')
    col = col + (stars(c, 260, 6, 0.1, 0.96, 0.0028) * smooth(0.2, -0.4, c.Y))[..., None]
    g = rng(8)
    def skyline(seed, base, hmin, hmax, tone, lit, wcol, scale):
        nonlocal col
        g2 = rng(seed)
        x = -1.05
        while x < 1.05:
            w = (0.05 + 0.07 * g2.random()) * scale
            h = hmin + (hmax - hmin) * g2.random() ** 1.5
            y0, y1 = base - h, base
            m = (c.X >= x) & (c.X < x + w) & (c.Y >= y0) & (c.Y < y1)
            col = np.where(m[..., None], rgb(tone) * (0.85 + 0.3 * g2.random()), col)
            if g2.random() < 0.3:             # a mast
                mm = (np.abs(c.X - x - w / 2) < 0.0025) & (c.Y >= y0 - 0.05) & (c.Y < y0)
                col = np.where(mm[..., None], rgb(tone), col)
            nx, ny = max(2, int(w / 0.014)), max(2, int(h / 0.020))
            u, v = (c.X - x) / w * nx, (c.Y - y0) / h * ny
            on = g2.random((ny + 1, nx + 1)) < lit
            iu, iv = np.clip(np.floor(u), 0, nx).astype(int), np.clip(np.floor(v), 0, ny).astype(int)
            win = m & on[iv, iu] & (np.abs(u % 1 - 0.5) < 0.30) & (np.abs(v % 1 - 0.5) < 0.28)
            warm = rgb(wcol)
            col = np.where(win[..., None], warm * (0.6 + 0.4 * g2.random()), col)
            x += w + 0.004 * g2.random()
    skyline(3, WL, 0.16, 0.52, '#1A1A46', 0.30, '#B08ACF', 0.9)
    skyline(5, WL, 0.10, 0.36, '#10103A', 0.42, '#FFC46A', 1.0)
    skyline(9, WL, 0.04, 0.20, '#080828', 0.50, '#FFE2A0', 1.1)
    # the water mirrors it, broken by ripples
    h, w = c.shape
    wl = int((WL + 1) * h / 2)
    rows = np.arange(h)
    src = np.clip(wl - (rows - wl), 0, h - 1)
    mir = col[src]
    jig = (0.010 * np.sin(c.Y * 190) + 0.006 * np.sin(c.Y * 420 + c.X * 9)) / c.px
    xi = np.clip(np.arange(w)[None, :] + jig, 0, w - 1).astype(int)
    mir = np.take_along_axis(mir, np.repeat(xi[..., None], 3, 2), axis=1)
    mir = mir * 0.55 * (1 - 0.35 * (0.5 + 0.5 * np.sin(c.Y * 260 + 3 * fbm(c.shape, 14, 4, 3))))[..., None] + rgb('#0A1440') * 0.35
    col = np.where((c.Y > WL)[..., None], mir, col)
    col = col + rgb('#FFC46A') * (0.5 * gauss(c.Y - WL, 0.004))[..., None]
    H = lathe(c, [(0, 0), (0.925, 0.0), (0.935, 0.030), (0.96, 0.042), (0.985, 0.034), (1.0, 0.0)], 0.003)
    rim = metal(c, H, V([0.30, 0.28, 0.40]), rough=0.22, grime=0.2, studio=COOL, dirt='#05060F')
    ln = np.maximum(smooth(0.004, 0.001, np.abs(c.R - 0.945)), smooth(0.004, 0.001, np.abs(c.R - 0.978)))
    rim = mix(rim, metal(c, H, GOLD, rough=0.2, grime=0.1), ln[..., None])
    col = mix(col, rim, smooth(0.922, 0.928, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.996))
    K.put(c, 'city', tone=False, quality=88)


def bursts():
    def peony(q, n, seed, fall, trail):
        g = rng(seed)
        out = np.zeros(q.shape, F)
        for k in range(n):
            a = g.random() * TAU
            r = 0.92 * (0.45 + 0.55 * math.sqrt(g.random()))
            x, y = math.sin(a) * r, -math.cos(a) * r + fall * r * r
            for j in range(7):
                t = 1 - j * trail
                px, py = math.sin(a) * r * t, -math.cos(a) * r * t + fall * (r * t) ** 2
                i, jx = int((py + 1) * q.h / 2), int((px + 1) * q.w / 2)
                s = 0.016 * (1 - 0.09 * j)
                w = int(s / q.px * 3) + 2
                sl = (slice(max(0, i - w), i + w), slice(max(0, jx - w), jx + w))
                out[sl] += gauss(np.hypot(q.X[sl] - px, q.Y[sl] - py), s) * (1.0 if j == 0 else 0.45 * (1 - j / 7))
        return clamp(out, 0, 1.6)
    light(K, 'burst1', 420, lambda q: peony(q, 120, 3, 0.06, 0.030))
    light(K, 'burst2', 420, lambda q: peony(q, 70, 7, 0.16, 0.060))

    def ringed(q):
        out = np.zeros(q.shape, F)
        for k in range(36):
            a = k * TAU / 36
            for r, s in ((0.90, 0.020), (0.86, 0.016), (0.82, 0.012), (0.55, 0.014)):
                out += gauss(np.hypot(q.X - math.sin(a) * r, q.Y + math.cos(a) * r), s)
        return clamp(out, 0, 1.4)
    light(K, 'burst3', 360, ringed)

    def sparkler(q):
        g = rng(5)
        out = np.zeros(q.shape, F)
        for k in range(90):
            a = k * TAU / 90 + 0.05 * g.standard_normal()
            L = 0.10 + 0.24 * g.random()
            r0 = 0.66
            dx, dy = math.sin(a), -math.cos(a)
            u = q.X * dx + q.Y * dy
            v = np.abs(-q.X * dy + q.Y * dx)
            m = (u > r0) & (u < r0 + L)
            out += m * gauss(v, 0.0065) * (1 - clamp((u - r0) / L)) ** 1.2 * (0.6 + 0.8 * g.random())
        return clamp(out + 0.5 * gauss(q.R - 0.66, 0.025), 0, 1.5)
    light(K, 'sparkler', 420, sparkler, '#FFE2A0')
    halo(K, 'halo', 256, 2.0, 0.05)
    light(K, 'twinkle', 64, lambda q: gauss(q.R, 0.16) + 0.6 * gauss(q.X, 0.05) * smooth(0.9, 0, np.abs(q.Y)) + 0.6 * gauss(q.Y, 0.05) * smooth(0.9, 0, np.abs(q.X)))


def glass():
    c = K.canvas(260, 3)
    H = lathe(c, [(0, 0), (0.82, 0.0), (0.85, 0.09), (0.90, 0.13), (0.96, 0.09), (1.0, 0.0)], 0.01)
    rim = metal(c, H, GOLD, rough=0.18, grime=0.15, reach=0.2)
    well = ramp(clamp(0.5 + 0.5 * c.Y), '#0A1030', '#1E1A4E') + rgb('#8FA8FF') * (0.16 * smooth(0.5, 0.62, np.hypot(c.X + 0.05, c.Y + 0.1)) * (1 - smooth(0.72, 0.82, np.hypot(c.X + 0.05, c.Y + 0.1))) * smooth(0.5, 0.95, -((c.X + 0.05) * 0.5 + (c.Y + 0.1) * 0.86) / np.maximum(np.hypot(c.X + 0.05, c.Y + 0.1), 1e-3)))[..., None]
    col = mix(well, rim, smooth(0.825, 0.835, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985) * mix(0.86, 1.0, smooth(0.82, 0.835, c.R)))
    K.put(c, 'slot')
    c = K.canvas(420, 2)
    H = lathe(c, [(0, 0), (0.84, 0.0), (0.86, 0.05), (0.91, 0.08), (0.97, 0.06), (1.0, 0.0)], 0.006)
    rim = metal(c, H, GOLD, rough=0.18, grime=0.2, reach=0.15)
    well = ramp(clamp(c.R / 0.85), '#141A4A', '#0A0E2E', '#05081E')
    col = mix(well, rim, smooth(0.845, 0.852, c.R)[..., None])
    n = 60
    k = np.abs(((c.A / TAU + 0.5) * n) % 1 - 0.5)
    col = col + rgb('#FFD27A') * (0.8 * smooth(0.10, 0.04, k) * smooth(0.012, 0.004, np.abs(c.R - 0.80)))[..., None]
    c.put(col, c.cover(c.R - 0.985))
    K.put(c, 'hub')


K.run([city, bursts, glass])

K.font('righteous', 'Righteous-Regular.ttf')
K.sounds('firework')
T = 'title'
shows = []
for k, (name, col, sp, rr) in enumerate((('burst1', '#FF5A6A', 0.42, 0.34), ('burst2', '#FFD24A', 0.36, 0.42), ('burst3', '#5AD0FF', 0.46, 0.28), ('burst1', '#B46AFF', 0.39, 0.36), ('burst2', '#6AFF9A', 0.33, 0.38), ('burst3', '#FF9A3A', 0.44, 0.24))):
    t = '(time*%g+%g)' % (sp, k * 0.37 + 0.45)
    n = 'floor%s' % t
    x, y = '(1.3*(rnd(%s*3+%d)-0.5))' % (n, k), '(-0.80+0.75*rnd(%s*7+%d))' % (n, k + 30)
    f = 'fract%s' % t
    shows.append(img(name, '%g*(0.08+0.92*outcubic(sat(%s*2.2)))*(0.75+0.5*rnd(%s+%d))' % (rr, f, n, k), x=x, y=y + '+0.06*%s*%s' % (f, f), tint=col, opacity='1.15*smooth(0,0.04,%s)*(1-smooth(0.32,0.72,%s))*motion' % (f, f), rotate='360*rnd(%s)' % n))
    shows.append(img('halo', 0.8, x='0', y='0.75', tint=col, opacity='0.10*(1-smooth(0,0.25,%s))*motion' % f))
K.write(
    style=dict(shape='orb', material='solid', base='#0A0E2E', accent='#FFD27A', accent2='#FF5A8A', text='#FFF6E0', border='#C99A45', opacity=0.97, corner=10, font='Righteous', open='bloom', speed=1.05, hoverGrow=3,
               iconZoom=1.14, glow=0.6, tilt=0.6, pointer=False, burst=False, shadow=0.65, dim=0.42),
    wheel=dict(hub=88, thickness=94, gap=6, ringgap=10, rim=30, icon=43, crowd=1.5, area=1.14, hubkeep=0.74),
    colors=dict(pale='#FFF6E0', gold='#FFD27A'), fonts=dict(title=dict(file='Righteous-Regular.ttf', family='Righteous')),
    back=[soft(1.09, 0.025, 68), img('city', 1, intro=intro(0.28, 'out', scale=0.88))] + shows,
    slot=dict(intro=intro(0.36, 'out', 0.05, scale=0.1, y=1.4, stagger=0.02, order='random'),
              under=[img('halo', 1.8, opacity='0.35*hot+launch*2', tint='#FFD27A'), img('sparkler', '1.55+0.10*noise(time*9)', rotate='time*50+120*rnd(floor(time*16))', opacity='sat(hot)*(0.75+0.35*noise(time*22+i))'), img('slot', '1.04*(1+0.04*hot-0.03*press)', detail=1.06)],
              icon=dict(size=1.04, zoom=1.16, shadow=dict(y=2, blur=3, color='black/60')),
              over=[img('burst1', '0.4+3.2*outcubic(sat(launch*1.4))', tint='#FFD27A', opacity='launch*(1.2-launch)*3', when='launch>0.01'), img('burst3', '0.3+2.4*outcubic(sat(launch*1.4))', tint='#FF6AB0', opacity='launch*(1.2-launch)*3', when='launch>0.01')]
              + running('#FFD27A', '#FFFFFF', 0.92, 0.15) + badge('#0A0E2E', 'pale', T, stroke='#C99A45') + groupmark('gold', -0.94, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.18, 0.05, 66, 0.80, **{'in': 'hub'}), img('twinkle', 0.46, **{'in': 'hub'}, angle='sel', radius=1.08, opacity='on*(0.7+0.4*noise(time*14))', rotate='time*90')],
    hub=[img('hub', 1.0, intro=intro(0.34, 'back', scale=0.4))] + words('pale', 'gold', T, px=17, box=(1.30, 0.52), clockpx=31, datepx=12, weight=400, shadow=dict(x=0, y=0, blur=5, color='#FF9A2A/70')),
    draw=dict(clock=False, shadow=False, text='pale'), tabs=dict(inset=19, text='pale', fill='#FFFFFF/12', on='#FF5A8A/85'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#1E2260'], [1, '#0A0E2E']]}, stroke={'type': 'linear', 'stops': [[0, '#FFE9B0'], [0.5, '#8A6427'], [1, '#E0B565']]}, width=2.4, corner=12, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#1E2260'], [1, '#0A0E2E']]}, stroke='#C99A45', width=1.6, corner=10, text='pale'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#2A2E7A'], [1, '#0A0E2E']]}, stroke='#C99A45', width=2, corner=10, text='pale'),
    onlaunch=[dict(color=k, light=True, count=26, area='slot', life=[0.6, 1.2], size=[1.8, 3.6], speed=[160, 560], dir=[0, 360], gravity=260, drag=2.2, stretch=0.8, fadein=0, fadeout=0.6) for k in ('#FFD27A', '#FF5A8A', '#7AE0FF')],
    onhover=[dict(color='#FFE2A0', light=True, count=7, area='slot', life=[0.3, 0.6], size=[1.2, 2.4], speed=[60, 180], outward=True, dir=[-90, 90], gravity=260, drag=1.5, stretch=0.6, fadein=0, fadeout=0.6)])
