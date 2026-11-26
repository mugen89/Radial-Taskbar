"""Jukebox: chrome, cherry wood, tubes of coloured light with bubbles in them, and backlit keys."""
from skinkit import *

K = Kit('jukebox', 'Jukebox', 'Chrome, cherry wood and bubbling tubes of coloured light that dance to the sound', ['retro', 'music', 'colourful'], 'Font Righteous: SIL Open Font License, see OFL.txt')
K.flag(colors='light', halo='light', bubble='light', notes=dict(cols=2), keys=dict(cols=2), shine='light')
DINER = Studio(lights=[((-0.45, -0.72, 0.56), 0.30, '#FFFFFF', 4.6), ((0.80, -0.25, 0.48), 0.20, '#FFD6E8', 2.4), ((0.15, 0.88, 0.40), 0.32, '#FFB060', 1.5), ((-0.92, 0.22, 0.28), 0.16, '#BFE6FF', 1.6)], sky='#C8BED2', floor='#120A0E', ambient=0.45)


def cabinet():
    c = K.canvas(1100, 2)
    H = lathe(c, [(0, 0.02), (0.700, 0.02), (0.712, 0.050), (0.735, 0.058), (0.745, 0.030), (0.752, 0.012), (0.822, 0.012), (0.830, 0.030), (0.838, 0.066), (0.866, 0.070), (0.874, 0.030), (0.880, 0.012), (0.950, 0.012), (0.957, 0.030), (0.964, 0.062), (0.990, 0.056), (1.0, 0.0)], 0.002)
    tex, g = wood(c, 6, 1.6, '#8E3018', '#2A0B06', rot=0.3)
    fan = np.abs(((c.A / TAU + 0.5) * 40) % 1 - 0.5)                # sunburst veneer
    tex = tex * (0.75 + 0.5 * fan)[..., None]
    col = surface(c, H + 0.001 * g, tex, DINER, rough=0.3, clear=0.9, reach=0.1)
    chrome = metal(c, H, CHROME, rough=0.08, grime=0.08, studio=DINER, reach=0.05, dirt='#1A1418')
    bands = np.maximum(np.maximum(smooth(0.703, 0.707, c.R) * smooth(0.750, 0.747, c.R), smooth(0.824, 0.828, c.R) * smooth(0.879, 0.876, c.R)), smooth(0.952, 0.956, c.R))
    col = mix(col, chrome, bands[..., None])
    groove = np.maximum(smooth(0.748, 0.752, c.R) * smooth(0.826, 0.822, c.R), smooth(0.876, 0.880, c.R) * smooth(0.954, 0.950, c.R))
    col = mix(col, flat('#1A0608', c.shape), (groove * 0.95)[..., None])
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'cabinet', exposure=0.95)

    def colours(q):                 # the light inside both tubes
        t = (q.A / TAU + 0.5) % 1
        ring = [rgb(x) for x in ('#FF2A1E', '#FF8A14', '#FFD21E', '#3AD05A', '#18B8E8', '#8A3AF0', '#FF2A8A', '#FF2A1E')]
        u = t * 7
        i = np.clip(np.floor(u).astype(int), 0, 6)
        f = smooth(0, 1, u - i)
        lut = np.stack(ring)
        col = lut[i] * (1 - f[..., None]) + lut[i + 1] * f[..., None]
        a = 1.0 * gauss(q.R - 0.787, 0.020) + 0.35 * gauss(q.R - 0.787, 0.050)
        col2 = lut[(i + 3) % 7] * (1 - f[..., None]) + lut[(i + 4) % 7] * f[..., None]
        b = 1.0 * gauss(q.R - 0.915, 0.020) + 0.35 * gauss(q.R - 0.915, 0.050)
        return col * a[..., None] + col2 * b[..., None]
    light(K, 'colors', 700, colours)
    c = K.canvas(1000, 2)            # the glass of the tubes
    li = np.zeros(c.shape, F)
    for r0 in (0.787, 0.915):
        u = (c.R - r0) / 0.036
        inside = np.abs(u) < 1
        nx = u
        sx, sy = np.sin(c.A), -np.cos(c.A)
        toward = -(sx * 0.5 + sy * 0.82)
        li += inside * (0.75 * gauss(u * np.sign(1) + 0.45 * np.sign(-toward + 1e-6), 0.16) * np.abs(toward) ** 0.7 + 0.10)
    c.col[:] = 1
    c.alpha = clamp(li * 0.75).astype(F)
    K.put(c, 'tubeglass', tone=False)


def keys():
    ims = []
    for lit in (0, 1):
        c = K.canvas(250, 3)
        d = c.box(0.86, 0.74, r=0.20)
        d2 = c.box(0.73, 0.61, r=0.13)
        H = np.where(d2 < 0, 0.13 + bevel(d2, 0.10, 0.05, 'ogee'), bevel(d, 0.07, 0.14))
        chrome = metal(c, np.where(d2 < 0, 0.14, H), CHROME, rough=0.08, grime=0.08, studio=DINER, reach=0.1, dirt='#1A1418')
        base = flat('#F6E7C4', c.shape)
        face = surface(c, H, base, DINER, rough=0.25, clear=0.9, shadows=False) * (0.62 if not lit else 0.75)
        if lit:
            face = face + rgb('#FFB23A') * (0.75 * gauss(np.hypot(c.X, c.Y * 1.2), 0.55))[..., None] + rgb('#FFE9B0') * 0.30
        gap = smooth(0.030, 0.010, np.abs(d2 - 0.01))
        col = mix(chrome, face, smooth(0.01, -0.01, d2)[..., None]) * (1 - 0.7 * gap)[..., None]
        sh = 0.5 * gauss(np.maximum(0, c.box(0.84, 0.72, 0.04, 0.07, r=0.2)), 0.07) * smooth(1.0, 0.94, np.maximum(np.abs(c.X), np.abs(c.Y)))
        c.put(np.zeros(3, F), sh.astype(F))
        c.put(col, c.cover(d), H)
        ims.append(c.image(exposure=0.97))
    K.sheet(ims, 2, 'keys', how='jpg')


def window():
    c = K.canvas(480, 2)
    H = lathe(c, [(0, 0.0), (0.72, 0.0), (0.735, 0.03), (0.77, 0.10), (0.82, 0.11), (0.835, 0.06), (0.855, 0.06), (0.875, 0.12), (0.95, 0.13), (1.0, 0.0)], 0.004)
    col = metal(c, H, CHROME, rough=0.07, grime=0.08, studio=DINER, dirt='#1A1418')
    n = 48
    k = np.abs(((c.A / TAU + 0.5) * n) % 1 - 0.5)
    flute = (np.abs(c.R - 0.91) < 0.035)
    col = np.where(flute[..., None], col * (0.45 + 1.0 * smooth(0.0, 0.5, k))[..., None], col)
    red = smooth(0.010, 0.004, np.abs(c.R - 0.845) - 0.008)
    col = mix(col, surface(c, H, flat('#C81E3A', c.shape), DINER, rough=0.2, clear=1.0), red[..., None])
    glass = flat('#2A0E06', c.shape) + rgb('#FF8A1E') * (0.40 * gauss(c.R, 0.60))[..., None] + rgb('#FFD27A') * (0.25 * gauss(c.R, 0.30))[..., None]
    rays = 0.5 + 0.5 * np.cos(c.A * 24)
    glass = glass * (0.88 + 0.12 * rays)[..., None] * (1 - 0.55 * smooth(0.50, 0.73, c.R))[..., None]
    col = mix(glass, col, smooth(0.720, 0.730, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'window', exposure=0.97)
    light(K, 'shine', 300, lambda q: 0.55 * smooth(0.50, 0.58, np.hypot(q.X + 0.08, q.Y + 0.13)) * (1 - smooth(0.72, 0.82, np.hypot(q.X + 0.08, q.Y + 0.13))) * smooth(0.45, 0.95, -((q.X + 0.08) * 0.5 + (q.Y + 0.13) * 0.86) / np.maximum(np.hypot(q.X + 0.08, q.Y + 0.13), 1e-3)))
    light(K, 'bubble', 64, lambda q: 0.85 * gauss(q.R - 0.62, 0.15) + 1.0 * gauss(np.hypot(q.X + 0.26, q.Y + 0.30), 0.18) + 0.22 * (q.R < 0.62))
    halo(K, 'halo', 220, 2.0, 0.15, '#FFB84A')
    ims = []
    for k in range(2):
        c = K.canvas(96, 4)
        ink = Ink(c)
        if k == 0:
            ink.dot(-0.28, 0.58, 0.30, ry=0.23).line([(-0.02, 0.55), (-0.02, -0.72)], 0.11).brush(bez((-0.02, -0.74), (0.30, -0.45), (0.50, -0.30), (0.34, 0.10), 16), 0.22, shape='tail')
        else:
            ink.dot(-0.52, 0.56, 0.26, ry=0.20).dot(0.40, 0.42, 0.26, ry=0.20).line([(-0.30, 0.54), (-0.30, -0.52)], 0.10).line([(0.62, 0.40), (0.62, -0.68)], 0.10).poly([(-0.35, -0.60), (0.67, -0.80), (0.67, -0.50), (-0.35, -0.30)])
        c.col = flat('#FFD46A', c.shape).copy()
        c.alpha = ink.arr(0.01)
        ims.append(c.image(tone=False))
    K.sheet(ims, 2, 'notes')


K.run([cabinet, keys, window])
K.font('righteous', 'Righteous-Regular.ttf')
K.sounds('jukebox')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#2A0B06', accent='#FFB84A', accent2='#FF2A5E', text='#FFF1D6', border='#C9CDD6', opacity=0.98, corner=14, font='Righteous', open='bloom', speed=1.05, hoverGrow=2,
               iconZoom=1.10, glow=0.5, tilt=0.4, pointer=False, burst=False, shadow=0.65, dim=0.36),
    wheel=dict(hub=94, thickness=90, gap=4, ringgap=12, rim=70, icon=40, crowd=1.52, area=1.10, hubkeep=0.62),
    colors=dict(pale='#FFF1D6', amber='#FFD27A'), fonts=dict(title=dict(file='Righteous-Regular.ttf', family='Righteous')),
    back=[soft(1.07, 0.03, 66), img('cabinet', 1, intro=intro(0.28, 'out', scale=0.88)), img('colors', 1.0, rotate='time*14', opacity='(0.62+0.75*sound+0.35*beat)*smooth(0.05,0.4,time)'),
          img('bubble', 0.034, copies=26, angle='j*13.846+time*(9+5*rnd(j))', radius='0.787+0.012*sin(time*2+j*2)', opacity='0.75', scale='0.5+0.8*rnd(j+3)', when='rings<1.5'), img('bubble', 0.034, copies=30, angle='j*12-time*(7+5*rnd(j+9))', radius='0.915+0.012*sin(time*2.3+j)', opacity='0.75', scale='0.5+0.8*rnd(j+5)'),
          img('tubeglass', 1.0)],
    slot=dict(intro=intro(0.34, 'back', 0.06, scale=0.2, stagger=0.022, order='ring'),
              under=[img('halo', 1.8, opacity='0.60*hot+launch*1.5'), img('keys', '1.12*(1-0.05*press)', frame=0, detail=1.04), img('keys', '1.12*(1-0.05*press)', frame=1, opacity='sat(0.18+0.82*hot)+launch', detail=1.04)],
              icon=dict(size=0.92, zoom=1.10, shadow=dict(y=1, blur=2, color='#3A1606/60')),
              over=[dict(shape='circle', y=0.88, size=0.14, fill='#C81E3A', stroke='#FFFFFF', width=1.2, when='running'), dict(shape='circle', y=0.88, size=0.08, fill='#FFE9B0', when='active', glow=6, glowcolor='#FFB84A'),
                    dict(text='{number}', x=-0.62, y=-0.50, em=0.26, color='#B3122E', font=T, when='numbers && number<10 && !kid')] + groupmark('pale', -0.88, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.18, 0.05, 70, 0.80, **{'in': 'hub'}), dict(shape='rect', **{'in': 'hub'}, copies=40, angle='j*9', radius='1.045+0.5*(0.02+0.10*sound*noise(time*7+j*1.7))', turns=True, size=[0.035, '0.02+0.10*sound*noise(time*7+j*1.7)'], fill='amber', opacity='0.35+0.65*sound', when='sound>0.02'),
          dict(shape='poly', **{'in': 'hub'}, angle='sel', radius=1.09, turns=True, points=[[-0.075, 0.05], [0, -0.075], [0.075, 0.05]], closed=True, fill='#FF2A5E', opacity='on', glow=6, glowcolor='#FF2A5E')],
    hub=[img('window', 1.04, intro=intro(0.34, 'back', scale=0.4))] + words('pale', 'amber', T, px=16.5, y=-0.04, box=(1.16, 0.48), subpx=10.5, suby=0.26, clockpx=30, clocky=-0.07, datey=0.22, datepx=11.5, weight=400, shadow=dict(x=0, y=0, blur=5, color='#FF6A14')) + [img('shine', 0.78)],
    draw=dict(clock=False, shadow=False, text='pale'), tabs=dict(inset=24, text='pale', fill='#FFFFFF/12', on='#C81E3A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#7A2412'], [1, '#3A0E06']]}, stroke={'type': 'linear', 'stops': [[0, '#FFFFFF'], [0.5, '#7E848E'], [1, '#E6E9EE']]}, width=4, corner=16, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#FFF6E0'], [1, '#F2DCA8']]}, stroke='#C81E3A', width=2, corner=11, text='#4A1408'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#FFF6E0'], [1, '#F2DCA8']]}, stroke='#C81E3A', width=2.4, corner=12, text='#4A1408'),
    particles=[dict(image='notes', rate='1.2*step(0.05,sound)', max=8, area='rim', life=[1.6, 2.6], size=[9, 15], speed=[16, 34], outward=True, dir=[-30, 30], sway=14, swayhz=0.8, gravity=-10, fadein=0.15, fadeout=0.4, opacity=0.85)],
    onlaunch=[dict(image='notes', count=18, area='slot', life=[0.6, 1.1], size=[10, 20], speed=[100, 340], outward=True, dir=[-100, 100], gravity=-60, drag=2, sway=18, swayhz=1.4, spin=[-60, 60], fadein=0, fadeout=0.5)])
