"""Arcade: a control panel with lit buttons, running bulbs and a joystick that leans toward the pointer."""
from skinkit import *

K = Kit('arcade', 'Arcade', 'Lit buttons, running bulbs and a joystick that leans toward the pointer', ['game', 'retro', 'bright'], 'Font Press Start 2P: SIL Open Font License, see OFL.txt')
K.flag(buttons=dict(cols=6, rows=2), bulb_on='light', halo='light', coin=dict(cols=6))
COLS = ('#FF2E3E', '#FFC21A', '#2FD05A', '#2E9BFF', '#F4F4F8', '#B24CFF')
SHOP = Studio(lights=[((-0.42, -0.72, 0.58), 0.30, '#FFFFFF', 4.6), ((0.75, -0.30, 0.50), 0.22, '#FFD6F4', 2.2), ((0.12, 0.88, 0.42), 0.36, '#9AD8FF', 1.3)], sky='#CBC4E6', floor='#0E0A1A', ambient=0.45)


def panel():
    c = K.canvas(1080, 2)
    H = lathe(c, [(0, 0.02), (0.875, 0.02), (0.885, 0.045), (0.955, 0.052), (0.965, 0.030), (0.972, 0.060), (0.992, 0.055), (1.0, 0.01)], 0.003)
    alb = flat('#15121F', c.shape).copy()
    g = rng(12)
    ink = {k: Ink(c) for k in ('#FF2E8A', '#22D3EE', '#FACC15', '#7C3AED', '#34D399')}
    names = list(ink)
    for k in range(120):            # confetti of shapes
        a, r = g.random() * TAU, 0.30 + 0.56 * math.sqrt(g.random())
        x, y, s, t, col = math.sin(a) * r, -math.cos(a) * r, 0.016 + 0.020 * g.random(), g.random() * TAU, ink[names[k % 5]]
        kind = k % 6
        if kind == 0:
            col.poly(turned([(0, -1), (0.9, 0.7), (-0.9, 0.7)], t, s, x, y))
        elif kind == 1:
            col.line(turned([(-1.6, 0), (-0.8, -0.7), (0, 0), (0.8, -0.7), (1.6, 0)], t, s, x, y), 0.0075)
        elif kind == 2:
            col.line(arcpts(s, 0, TAU, 24, x, y), 0.0065)
        elif kind == 3:
            col.poly(turned([(-0.8, -0.8), (0.8, -0.8), (0.8, 0.8), (-0.8, 0.8)], t, s * 0.8, x, y))
        elif kind == 4:
            for j in range(3):
                col.line(turned([(-1, (j - 1) * 0.6), (1, (j - 1) * 0.6)], t, s, x, y), 0.0055)
        else:
            col.dot(x, y, s * 0.45)
    for k, i in ink.items():
        alb = paint(alb, i.arr() * 0.9, k)
    # a band for the bulbs, and the plastic strip round the edge
    alb = np.where((c.R > 0.880)[..., None], rgb('#B3122E'), alb)
    alb = np.where((c.R > 0.960)[..., None], rgb('#FFC21A'), alb)
    col = surface(c, H, alb, SHOP, rough=0.32, clear=0.75, reach=0.12)
    n = 36
    for i in range(n):              # bulb sockets
        x, y = c.polar((i + 0.5) * TAU / n, 0.920)
        r = np.hypot(c.X - x, c.Y - y)
        m = metal(c, np.where(r < 0.026, 0.05 + bevel(np.maximum(r - 0.025, 0.016 - r), 0.004, 0.008), H), CHROME, rough=0.2, grime=0.2, reach=0.03) if i == 0 else None
        col = np.where(((r < 0.0245) & (r > 0.0165))[..., None], rgb('#B9BEC8') * (0.35 + 0.75 * clamp(0.5 - (c.X - x) * 14 - (c.Y - y) * 18))[..., None], col)
        col = np.where((r <= 0.0165)[..., None], rgb('#4A2410'), col)
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'panel', exposure=0.95)


def button(base, lit):
    c = K.canvas(230, 3)
    H = np.where(c.R > 0.70, lathe(c, [(0.70, 0.02), (0.735, 0.13), (0.84, 0.19), (0.93, 0.15), (1.0, 0.0)]), 0.10 - 0.10 * (c.R / 0.70) ** 2 * 0 + 0.07 * (c.R / 0.70) ** 2)
    b = rgb(base)
    nx, ny, nz = normals(blur(H, 0.01 / c.px), c.px)
    rimcol = surface(c, H, flat(base, c.shape) * 0.85, SHOP, rough=0.25, clear=1.0, reach=0.2)
    glow = gauss(c.R, 0.55)
    if lit:
        face = b * (0.75 + 0.9 * glow)[..., None] + np.ones(3, F) * (0.35 * gauss(c.R, 0.30))[..., None]
        rimcol = rimcol * 0.8 + b * 0.35
    else:
        face = b * (0.28 + 0.26 * glow)[..., None]
    face = face + SHOP.reflect(nx, ny, nz, 0.08) * (0.045 + 0.5 * np.power(clamp(1 - nz), 4))[..., None]
    gap = smooth(0.026, 0.010, np.abs(c.R - 0.705))
    col = mix(face, rimcol, smooth(0.695, 0.715, c.R)[..., None]) * (1 - 0.8 * gap)[..., None]
    sh = 0.5 * gauss(np.maximum(0, np.hypot(c.X - 0.05, c.Y - 0.08) - 0.88), 0.07)
    c.put(np.zeros(3, F), (sh * smooth(1.0, 0.93, np.maximum(np.abs(c.X), np.abs(c.Y)))).astype(F))
    c.put(col, c.cover(c.R - 0.90), H)
    return c.image(exposure=0.97)


def buttons():
    K.sheet([button(b, lit) for lit in (0, 1) for b in COLS], 6, 'buttons', how='jpg')


def stick():
    c = K.canvas(460, 2)             # the plate and the dust washer
    H = lathe(c, [(0, 0.01), (0.62, 0.01), (0.70, 0.035), (0.90, 0.045), (0.96, 0.05), (1.0, 0.0)], 0.01)
    col = metal(c, H + 0.0007 * circular_streaks(c, 4, 700), V([0.30, 0.31, 0.34]), rough=0.25, grime=0.3, studio=SHOP, dirt='#08080C')
    for k in range(4):
        x, y = c.polar((k + 0.5) * TAU / 4, 0.85)
        r = np.hypot(c.X - x, c.Y - y)
        hs = np.where(r < 0.06, H + dome(r, 0.062, 0.03), H)
        hs = np.where((np.abs(c.X - x) < 0.009) & (r < 0.045) | (np.abs(c.Y - y) < 0.009) & (r < 0.045), H, hs)
        col = mix(col, metal(c, hs, CHROME, rough=0.2, grime=0.3, studio=SHOP, reach=0.05), smooth(0.062, 0.056, r)[..., None])
    washer = surface(c, H + 0.02 * smooth(0.74, 0.70, c.R), flat('#101014', c.shape), SHOP, rough=0.45, clear=0.3)
    col = mix(col, washer, smooth(0.72, 0.71, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'base')
    c = K.canvas(420, 2)             # the ball
    d = c.R - 0.94
    H = 0.85 * np.sqrt(clamp(1 - (c.R / 0.96) ** 2))
    nx, ny, nz = normals(H, c.px)
    col = rgb('#E5142C') * (0.20 + 0.60 * clamp(0.35 - 0.45 * nx - 0.65 * ny + 0.45 * nz))[..., None] + SHOP.reflect(nx, ny, nz, 0.05) * (0.04 + 0.9 * np.power(clamp(1 - nz), 5))[..., None]
    col = col + (0.9 * np.power(clamp(nx * -0.42 + ny * -0.62 + nz * 0.66), 90))[..., None] + rgb('#FF6A7A') * (0.20 * gauss(np.hypot(c.X + 0.22, c.Y + 0.34), 0.34))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'ball')
    c = K.canvas(56, 4)
    d = c.R - 0.8
    H = 0.7 * np.sqrt(clamp(1 - (c.R / 0.82) ** 2))
    c.put(surface(c, H, flat('#7A4A1E', c.shape), SHOP, rough=0.2, clear=1.0, shadows=False), c.cover(d), H)
    K.put(c, 'bulb', how='png')
    light(K, 'bulb_on', 96, lambda q: 1.3 * gauss(q.R, 0.20) + 0.5 * gauss(q.R, 0.45), '#FFE08A')
    halo(K, 'halo', 220, 2.0, 0.1)
    ims = []
    for k in range(6):
        c = K.canvas(20, 1)
        w = [8, 7, 4, 1, 4, 7][k]
        im = Image.new('RGBA', (20, 20), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.ellipse([10 - w, 2, 9 + w, 17], fill=(245, 180, 30, 255), outline=(140, 80, 10, 255))
        if w > 3:
            dr.rectangle([9 - w // 4, 6, 9 + w // 4, 13], fill=(255, 230, 120, 255))
        ims.append(im)
    K.sheet(ims, 6, 'coin')


K.run([panel, buttons, stick])
K.font('pressstart2p', 'PressStart2P-Regular.ttf')
K.sounds('arcade')
T, X = 'title', 'pix'
lx, ly = 'clamp(px*0.34,-0.16,0.16)', 'clamp(py*0.34,-0.16,0.16)'
w = words('#FFFFFF', '#FFE08A', T, px=15.5, y=-0.03, box=(0.94, 0.40), subpx=10, suby=0.21, clockpx=25, clocky=-0.05, datey=0.18, datepx=10, shadow=dict(x=0, y=1, blur=3, color='#4A0008'))
for l in w:
    l['x'], l['y'] = lx, '%s+%g' % (ly, l['y'])
K.write(
    style=dict(shape='orb', material='solid', base='#15121F', accent='#FF2E8A', accent2='#22D3EE', text='#FFFFFF', border='#FFC21A', opacity=0.98, corner=8, font='Segoe UI Semibold', open='bloom', speed=1.1, hoverGrow=0,
               iconZoom=1.08, glow=0.4, tilt=0.3, pointer=False, burst=False, shadow=0.65, dim=0.36),
    wheel=dict(hub=92, thickness=94, gap=4, ringgap=10, rim=44, icon=40, crowd=1.48, area=1.10, hubkeep=0.60),
    colors=dict(white='#FFFFFF', gold='#FFC21A'), fonts=dict(title='Segoe UI Black, Segoe UI Semibold, Segoe UI', pix=dict(file='PressStart2P-Regular.ttf', family='Press Start 2P')),
    back=[soft(1.08, 0.03, 66), img('panel', 1, intro=intro(0.26, 'out', scale=0.88)),
          img('bulb', 0.030, copies=36, angle='(j+0.5)*10', radius=0.920), img('bulb_on', 0.095, copies=36, angle='(j+0.5)*10', radius=0.920, opacity='smooth(0.35,0.75,wave(j/6-time*1.4))*(0.9+0.4*beat)+(1-smooth(0,0.6,time))*step(0.5,fract(time*9+j*0.5))')],
    slot=dict(intro=intro(0.34, 'back', 0.05, scale=0.1, stagger=0.02, order='both'),
              under=[img('halo', 1.75, opacity='0.55*hot+launch*2', tint='#FFF2C0'), img('buttons', '1.08*(1-0.07*press-0.10*launch)', frame='(i+ring*2)%6', opacity=1, detail=1.04), img('buttons', '1.08*(1-0.07*press-0.10*launch)', frame='6+(i+ring*2)%6', opacity='sat(hot+launch+0.35*active)', detail=1.04)],
              icon=dict(size=0.86, zoom=1.10, shadow=dict(y=2, blur=3, color='black/55')),
              over=[dict(shape='circle', y=0.96, size=0.13, fill='#22D3EE', when='running', opacity='active ? 1 : 0.6', glow=6, glowcolor='#22D3EE'), dict(text='{number}', x=0.74, y=-0.76, em=0.24, font=X, color='white', when='numbers && number<10 && !kid', outline=dict(width=2, color='#15121F'))] + groupmark('#FFFFFF', -0.98, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.16, 0.05, 66, 0.80, **{'in': 'hub'}), dict(shape='poly', **{'in': 'hub'}, angle='sel', radius=1.10, turns=True, points=[[-0.09, 0.06], [0, -0.08], [0.09, 0.06]], closed=True, fill='gold', opacity='on', glow=5, glowcolor='gold')],
    hub=[img('base', 1.0, intro=intro(0.3, 'back', scale=0.5)), dict(shape='circle', x=lx + '*0.5', y=ly + '*0.5', size=0.30, fill='#2A2A32'), dict(shape='circle', x=lx + '+0.05', y=ly + '+0.10', size=0.78, fill={'type': 'radial', 'stops': [[0, 'black/75'], [0.7, 'black/55'], [1, 'black/0']]}), img('ball', 0.66, x=lx, y=ly, intro=intro(0.36, 'back', 0.06, scale=0.3))] + w,
    draw=dict(clock=False, shadow=False, text='white'), tabs=dict(inset=26, text='white', fill='#FFFFFF/14', on='#FF2E8A'),
    pinbutton={'in': 'hub', 'x': -0.62, 'y': 0.62, 'size': 10.5}, settingsbutton={'in': 'hub', 'x': 0.62, 'y': 0.62, 'size': 10.5},
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#241C3A'], [1, '#120E1E']]}, stroke='#FFC21A', width=4, corner=10, text='white'), tag=dict(fill='#B3122E', stroke='#FFC21A', width=2, corner=7, text='white'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#3A2A66'], [1, '#15121F']]}, stroke='#22D3EE', width=2.4, corner=8, text='white'),
    onlaunch=[dict(image='coin', count=12, area='slot', life=[0.5, 0.9], size=[9, 13], speed=[200, 460], dir=[-50, 50], gravity=1100, drag=0.4, fadein=0, fadeout=0.2)] + [dict(color=k, count=9, area='slot', life=[0.3, 0.6], size=[3, 6], speed=[120, 420], outward=True, dir=[-90, 90], drag=2.2, fadein=0, fadeout=0.4) for k in ('#FF2E8A', '#22D3EE', '#FACC15')])
