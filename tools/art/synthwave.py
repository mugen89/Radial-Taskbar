"""Synthwave: a striped sun, dark hills and a glowing grid that rolls toward you."""
from skinkit import *

K = Kit('synthwave', 'Synthwave', 'A striped sun, dark hills and a glowing grid that rolls toward you', ['retro', 'neon', 'eighties'], 'Fonts Monoton and Russo One: SIL Open Font License, see OFL.txt')
K.flag(grid=dict(light=True, cols=2, rows=4), halo='light', streak='light', rimlight='light')
P, C = '#FF3FA4', '#2FE6FF'
HZ = 0.12                   # height of the horizon


def scene():
    c = K.canvas(1050, 2)
    t = clamp((c.Y + 1) / (1 + HZ))
    col = ramp(t, '#0B0426', '#2A0A52', '#7A1480', '#E0337F', '#FF8A4A')
    col = col + (stars(c, 260, 5, 0.0, 0.98, 0.0032) * smooth(0.0, -0.45, c.Y))[..., None]
    # sun
    y0 = HZ - 0.30
    r = np.hypot(c.X, c.Y - y0)
    v = clamp((c.Y - (y0 - 0.50)) / 1.0)
    sun = ramp(v, '#FFF06A', '#FFB03A', '#FF5C7A', '#D81E9A')
    bars = np.zeros(c.shape, bool)
    for k in range(7):
        yy = y0 - 0.05 + k * 0.078
        bars |= np.abs(c.Y - yy) < (0.006 + 0.0045 * k)
    m = smooth(0.002, -0.002, r - 0.50) * (~bars) * (c.Y < HZ)
    col = col + rgb('#FF4F9A') * (0.55 * gauss(np.maximum(0, r - 0.45), 0.22) * (c.Y < HZ + 0.02))[..., None]
    col = mix(col, sun, m[..., None])
    # hills
    for seed, base, amp, tone, line in ((4, 0.06, 0.20, '#2A0B4A', '#8A2BC2'), (9, 0.02, 0.13, '#12052B', '#FF3FA4')):
        prof = np.abs(lattice((1, c.w), 15, seed)[0]) * 0.6 + np.abs(lattice((1, c.w), 34, seed + 3)[0]) * 0.28
        side = smooth(0.10, 0.75, np.abs(c.X[0]))
        top = HZ - base - amp * prof * (0.25 + 0.95 * side)
        d = top[None, :] - c.Y
        cov = clamp(0.5 - d / c.px) * (c.Y < HZ)
        facet = 0.5 + 0.5 * np.sign(np.gradient(prof))[None, :]
        col = mix(col, mix(flat(tone, c.shape), flat(line, c.shape), (0.16 * facet)[0][None, :, None] * np.ones(c.shape + (1,), F)), cov[..., None])
        col = mix(col, flat(line, c.shape), (0.9 * gauss(d, 0.0035) * (c.Y < HZ))[..., None])
    # floor
    fl = clamp((c.Y - HZ) / (1 - HZ))
    floor = ramp(fl, '#2A0838', '#14042A', '#070116')
    floor = floor + rgb('#FF3F8A') * (0.40 * np.exp(-fl / 0.10))[..., None]
    col = np.where((c.Y >= HZ)[..., None], floor, col)
    col = col + rgb('#FFB0D8') * (0.9 * gauss(c.Y - HZ, 0.004))[..., None]
    c.col = clamp(col).astype(F)
    c.alpha = c.cover(c.R - 0.995)
    K.put(c, 'scene', tone=False, quality=90)


def grid():
    ims = []
    for f in range(8):
        c = K.canvas(620, 2, 1.0, (1 - HZ) / 2)
        y = (c.Y / c.aspect + 1) / 2 * (1 - HZ)                # distance below the horizon
        z = 0.16 / np.maximum(y, 1e-3)
        u = c.X * z * 9.0
        v = z * 5.0 + f / 8
        dy = np.maximum(np.abs(np.gradient(z * 5.0, c.px, axis=0)), 1e-3)
        lv = np.abs(((v + 0.5) % 1) - 0.5) / dy
        lu = np.abs(((u + 0.5) % 1) - 0.5) / np.maximum(z * 9.0, 1e-3)
        w = 0.0032 + 0.010 * y
        a = np.maximum(gauss(lv, w), gauss(lu, w)) + 0.35 * np.maximum(gauss(lv, w * 3.2), gauss(lu, w * 3.2))
        a = a * smooth(0.0, 0.10, y) * (np.hypot(c.X, c.Y / c.aspect * (1 - HZ) / 2 + HZ + (1 - HZ) / 2) < 0.985)
        far = clamp(1 - y / (1 - HZ))
        col = mix(flat(C, c.shape), flat(P, c.shape), far[..., None])
        c.col = clamp(col * (a * 1.05)[..., None]).astype(F)
        c.alpha[:] = 1
        ims.append(c.image(tone=False, dither=False))
    K.sheet(ims, 2, 'grid', how='jpg')


def metal_():
    c = K.canvas(900, 2)
    H = lathe(c, [(0, 0), (0.925, 0.0), (0.932, 0.028), (0.955, 0.040), (0.985, 0.034), (1.0, 0.0)], 0.003)
    nx, ny, nz = normals(H, c.px)
    # chrome: a horizon painted into the reflection
    t = clamp(0.5 - 0.5 * ny * 1.5)
    chrome = ramp(t, '#1A0636', '#FF4FA4', '#FFE9F6', '#7FD8FF', '#0E1C56')
    chrome = chrome * (0.75 + 0.5 * nz)[..., None] + (0.6 * np.power(clamp(nx * -0.4 + ny * -0.66 + nz * 0.64), 40))[..., None]
    c.put(chrome, c.cover(c.R - 0.995) * smooth(0.922, 0.928, c.R))
    K.put(c, 'rim', tone=False)
    c = K.canvas(300, 3)
    H = lathe(c, [(0, 0), (0.80, 0.0), (0.83, 0.10), (0.89, 0.14), (0.96, 0.10), (1.0, 0.0)], 0.01)
    nx, ny, nz = normals(H, c.px)
    t = clamp(0.5 - 0.5 * ny * 1.4)
    chrome = ramp(t, '#1A0636', '#FF4FA4', '#FFF2FA', '#7FD8FF', '#0E1C56') * (0.70 + 0.5 * nz)[..., None]
    well = ramp(clamp(0.5 + 0.5 * c.Y), '#1B0838', '#3A0F5E')
    col = mix(well, chrome, smooth(0.800, 0.815, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985) * mix(0.90, 1.0, smooth(0.80, 0.815, c.R)))
    K.put(c, 'slot', tone=False)
    halo(K, 'halo', 256, 2.0, 0.05)
    light(K, 'streak', 220, lambda q: 0.9 * gauss(q.Y, 0.022) * smooth(1.0, 0.0, np.abs(q.X)) + 0.7 * gauss(q.X, 0.022) * smooth(0.6, 0.0, np.abs(q.Y)) + 0.6 * gauss(q.R, 0.10))
    light(K, 'rimlight', 420, lambda q: 0.9 * gauss(q.R - 0.80, 0.018) + 0.4 * gauss(q.R - 0.80, 0.07))


K.run([scene, grid, metal_])
K.font('monoton', 'Monoton-Regular.ttf')
K.font('russoone', 'RussoOne-Regular.ttf')
K.sounds('synth')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#1A0636', accent=P, accent2=C, text='#FFF0FA', border='#B05CFF', opacity=0.97, corner=8, font='Russo One', open='zoom', speed=1.1, hoverGrow=3,
               iconZoom=1.12, glow=0.8, tilt=0.8, pointer=False, burst=False, shadow=0.7, dim=0.40),
    wheel=dict(hub=88, thickness=94, gap=6, ringgap=10, rim=30, icon=44, crowd=1.5, area=1.12, hubkeep=0.80),
    colors=dict(p=P, c=C, white='#FFF6FC'), fonts=dict(title=dict(file='RussoOne-Regular.ttf', family='Russo One'), neon=dict(file='Monoton-Regular.ttf', family='Monoton')),
    back=[soft(1.09, 0.025, 66), img('rimlight', 1.30, tint=P, opacity='0.20+0.30*sound+0.06*wave(time*0.4)'), img('scene', 1.0, intro=intro(0.26, 'out', scale=0.86)), img('grid', [1.0, (1 - HZ) / 2], y=HZ + (1 - HZ) / 2, frame='7-floor(time*14)%8', opacity='(0.85+0.4*beat)*smooth(0.1,0.35,time)'),
          img('rim', 1.0, rotate='0')],
    ring=[dict(shape='arc', **{'in': 'px', 'from': 0}, r='(ringin+ringout)/2', to='360*outcubic(sat(time*2))', stroke='c/30', width=1.2)],
    slot=dict(intro=intro(0.34, 'out', 0.06, scale=0.05, y=0.6, stagger=0.02, order='both'),
              under=[img('halo', 1.9, tint=P, opacity='0.55*hot+launch*2'), img('halo', 1.5, tint=C, opacity='0.10+0.45*hot'), img('slot', '1.04*(1+0.06*hot-0.04*press)', detail=1.06),
                     {'shape': 'arc', 'r': 0.90, 'from': 'time*80', 'to': 'time*80+200', 'stroke': 'c', 'width': 2.4, 'opacity': 'sat(hot)', 'glow': 6, 'glowcolor': 'c', 'caps': True}, {'shape': 'arc', 'r': 0.90, 'from': 'time*80+200', 'to': 'time*80+360', 'stroke': 'p', 'width': 2.4, 'opacity': 'sat(hot)', 'glow': 6, 'glowcolor': 'p', 'caps': True}],
              icon=dict(size=1.04, zoom=1.16, shadow=dict(y=2, blur=3, color='black/60')),
              over=[img('streak', '0.9+0.5*launch', x=-0.48, y=-0.58, opacity='0.35*wave(time*0.4+seed)+0.8*hot*wave(time*1.1)+launch*2', rotate=12)] + running('p', '#FFD6F0', 0.90, 0.15) + badge('#1A0636', 'white', T, stroke=C) + groupmark('c', -0.94, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.20, 0.04, 70, 0.78, **{'in': 'hub'}), dict(shape='poly', **{'in': 'hub'}, angle='sel', radius=1.10, turns=True, points=[[-0.10, 0.07], [0, -0.09], [0.10, 0.07]], closed=True, fill='c', opacity='on', glow=7, glowcolor='c')],
    hub=[dict(shape='circle', size=0.98, fill={'type': 'linear', 'stops': [[0, '#14042E'], [0.55, '#3B0D5E'], [1, '#8A1F74']]}), {'shape': 'arc', 'r': 0.965, 'from': 0, 'to': 360, 'stroke': {'type': 'linear', 'stops': [[0, C], [1, P]]}, 'width': 3, 'glow': 7, 'glowcolor': 'p'}, {'shape': 'arc', 'r': 0.89, 'from': 'sel-40', 'to': 'sel+40', 'stroke': 'c', 'width': 2, 'opacity': 'on', 'glow': 4, 'glowcolor': 'c'},
         dict(shape='rect', y='0.48+0.09*j', size=['sqrt(max(0,0.80-(0.48+0.09*j)*(0.48+0.09*j)))*0.92', 0.018], copies=5, fill='p/55')]
    + [l if i != 2 else dict(l, font='neon', px=30, weight=400) for i, l in enumerate(words('white', '#FFB3E0', T, px=16.5, y=-0.10, box=(1.36, 0.52), subpx=11, suby=0.24, clockpx=30, clocky=-0.10, datey=0.25, datepx=11.5, weight=400, shadow=dict(x=0, y=0, blur=6, color=P)))],
    draw=dict(clock=False, shadow=False, text='white'), tabs=dict(inset=12, text='white', fill='#2FE6FF/14', on='#FF3FA4/85'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#14042E'], [0.6, '#3B0D5E'], [1, '#7A1C6E']]}, stroke={'type': 'linear', 'stops': [[0, C], [1, P]]}, width=2, corner=10, text='white'), tag=dict(fill={'type': 'linear', 'stops': [[0, '#1A0636'], [1, '#3B0D5E']]}, stroke=P, width=1.6, corner=8, text='white'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#14042E'], [0.55, '#4A1070'], [1, '#B02A7E']]}, stroke=C, width=1.6, corner=9, text='white'),
    onlaunch=[dict(color=C, light=True, count=28, area='slot', life=[0.25, 0.6], size=[1.5, 3], speed=[200, 720], outward=True, dir=[-90, 90], drag=2.5, stretch=1, fadein=0, fadeout=0.6), dict(color=P, light=True, count=28, area='slot', life=[0.25, 0.6], size=[1.5, 3], speed=[160, 620], outward=True, dir=[-90, 90], drag=2.5, stretch=1, fadein=0, fadeout=0.6)],
    particles=[dict(color='#FFD6F0', light=True, rate=2.5, max=16, area='wheel', life=[1.2, 2.6], size=[1, 2], speed=[2, 8], dir=[-30, 30], gravity=-6, fadein=0.3, fadeout=0.5)])
