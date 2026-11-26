"""Rotary: an old dial telephone in mint plastic, with a chrome finger wheel."""
from skinkit import *

K = Kit('rotary', 'Rotary', 'An old dial telephone: chrome, cream and mint', ['retro', 'telephone', 'chrome'])
K.flag(halo='light')
MINT, DARK = '#78BFAE', '#2F6E62'
GLOSS = Studio(lights=[((-0.45, -0.70, 0.60), 0.30, '#FFFFFF', 5.0), ((0.75, -0.28, 0.50), 0.22, '#E4EEFF', 2.2), ((0.12, 0.88, 0.45), 0.40, '#FFE9CF', 0.9)], sky='#E9F2FA', floor='#39443F', ambient=0.55)
ROOM = Studio(lights=[((-0.45, -0.72, 0.55), 0.30, '#FFFFFF', 4.6), ((0.80, -0.25, 0.48), 0.20, '#DDE8FF', 2.6), ((0.20, 0.86, 0.40), 0.30, '#FFE2C0', 1.2), ((-0.92, 0.22, 0.28), 0.16, '#FFFFFF', 1.6)], sky='#C9D4E2', floor='#12161A', ambient=0.45)


def body():
    c = K.canvas(1100, 2)
    H = lathe(c, [(0, 0.02), (0.80, 0.02), (0.828, 0.030), (0.842, 0.085), (0.90, 0.112), (0.955, 0.098), (0.985, 0.060), (1.0, 0.0)], 0.010)
    alb = flat(MINT, c.shape) * (1 + 0.015 * fbm(c.shape, 60, 3, 2))[..., None]
    col = surface(c, H, alb, GLOSS, rough=0.3, clear=1.0, reach=0.2)
    # cream number plate below the wheel
    pl = smooth(0.830, 0.826, c.R)
    plate = surface(c, H, flat('#F2E8CF', c.shape), GLOSS, rough=0.5, clear=0.4, reach=0.2)
    col = mix(col, plate, pl[..., None])
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'body', exposure=0.95)


def wheel():
    c = K.canvas(900, 2)
    H = lathe(c, [(0, 0.06), (0.90, 0.06), (0.945, 0.075), (0.975, 0.072), (1.0, 0.03)], 0.006)
    H = H + 0.0007 * circular_streaks(c, 4, 1200)
    tx, ty = -np.cos(c.A) * -1, np.sin(c.A)
    col = metal(c, H, CHROME, rough=0.16, grime=0.12, studio=ROOM, aniso=(np.cos(c.A), np.sin(c.A), 0.85), reach=0.06, dirt='#2A2C2E')
    ln = np.maximum(smooth(0.004, 0.001, np.abs(c.R - 0.895)), smooth(0.003, 0.001, np.abs(c.R - 0.515)))
    col = col * (1 - 0.35 * ln)[..., None]
    c.put(col, c.cover(c.R - 0.992), H)
    K.put(c, 'wheel', exposure=0.90)


def hole():
    c = K.canvas(320, 3)
    d = c.R - 0.82
    # the rim of the hole
    H = np.where(c.R > 0.80, lathe(c, [(0.80, 0.0), (0.83, 0.13), (0.88, 0.16), (0.95, 0.12), (1.0, 0.04)]), -0.25)
    rim = metal(c, H, CHROME, rough=0.12, grime=0.1, studio=ROOM, reach=0.1, dirt='#2A2C2E')
    well = flat('#F4EBD4', c.shape) * 0.93
    sh = smooth(0.0, 0.42, -(c.R - 0.82) + 0.30 * (c.X * 0.5 + c.Y * 0.8))
    well = well * (0.30 + 0.70 * sh)[..., None] * (1 - 0.45 * smooth(0.62, 0.82, c.R))[..., None]
    col = mix(rim, well, c.cover(d)[..., None])
    c.put(col, c.cover(c.R - 0.985))
    K.put(c, 'hole', exposure=0.98)
    # a tinted lens of light for the hovered hole
    c = K.canvas(260, 2)
    k = smooth(0.82, 0.78, c.R)
    c.col = flat('#FF7A4A', c.shape).copy()
    c.alpha = (k * (0.30 + 0.60 * smooth(0.2, 0.82, c.R))).astype(F)
    K.put(c, 'warm', how='png', tone=False)
    # and its rim, enamelled red
    c = K.canvas(320, 3)
    H = np.where(c.R > 0.80, lathe(c, [(0.80, 0.0), (0.83, 0.13), (0.88, 0.16), (0.95, 0.12), (1.0, 0.04)]), -0.25)
    col = surface(c, H, flat('#D8352A', c.shape), GLOSS, rough=0.25, clear=1.0, shadows=False)
    c.put(col, smooth(0.815, 0.825, c.R) * c.cover(c.R - 0.985), H)
    K.put(c, 'redrim', how='png')


def hub():
    c = K.canvas(460, 2)
    H = lathe(c, [(0, 0.05), (0.74, 0.05), (0.77, 0.07), (0.80, 0.12), (0.88, 0.145), (0.95, 0.12), (1.0, 0.03)], 0.008)
    paper = surface(c, H, flat('#F7F0DC', c.shape) * (1 + 0.02 * fbm(c.shape, 160, 4, 2))[..., None], SOFT, rough=0.9)
    ink = Ink(c)
    for y in (-0.40, 0.42):
        ink.line([(-0.52, y), (0.52, y)], 0.006)
    paper = mix(paper, flat('#B03A2A', c.shape), (0.55 * ink.arr())[..., None])
    for r in (0.70, 0.675):
        paper = mix(paper, flat('#2A2C30', c.shape), (0.8 * smooth(0.007 if r > 0.69 else 0.004, 0.002, np.abs(c.R - r)))[..., None])
    rim = metal(c, H, CHROME, rough=0.10, grime=0.12, studio=ROOM, dirt='#2A2C2E')
    col = mix(paper, rim, smooth(0.765, 0.772, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    # a clear cap over the card
    ax, ay = c.X + 0.06, c.Y + 0.10
    rr = np.hypot(ax, ay)
    win = smooth(0.52, 0.58, rr) * (1 - smooth(0.70, 0.76, rr)) * smooth(0.45, 0.95, -(ax * 0.55 + ay * 0.84) / np.maximum(rr, 1e-4))
    c.add(np.ones(3, F), 0.35 * win * (c.R < 0.76))
    K.put(c, 'hub', exposure=0.97)
    # the finger stop: a bent strip of steel, pivot at its foot
    c = K.canvas(190, 3, 1.0, 1.0)
    d = np.minimum(c.taper(0.55, 0.62, 0.20, -0.35, -0.30, 0.135), c.capsule(-0.35, -0.30, -0.62, -0.62, 0.125))
    H = bevel(d, 0.13, 0.16)
    r = np.hypot(c.X - 0.55, c.Y - 0.62)
    H = np.where(r < 0.12, H + dome(r, 0.13, 0.08), H)
    slot = (np.abs((c.X - 0.55) * 0.7 + (c.Y - 0.62) * 0.7) < 0.018) & (r < 0.11)
    H = np.where(slot, H - 0.05, H)
    sh = 0.55 * gauss(np.maximum(0, np.minimum(c.taper(0.60, 0.70, 0.20, -0.30, -0.22, 0.135), c.capsule(-0.30, -0.22, -0.57, -0.54, 0.125))), 0.10)
    c.put(np.zeros(3, F), sh.astype(F))
    c.put(metal(c, H, CHROME, rough=0.14, grime=0.15, studio=ROOM, reach=0.2, dirt='#2A2C2E'), c.cover(d), H)
    K.put(c, 'stop', how='png')


def handset():
    c = K.canvas(900, 2, 1.0, 0.36)
    d = np.minimum(c.box(0.225, 0.185, -0.745, 0.08, rot=-0.12, r=0.15), c.box(0.225, 0.185, 0.745, 0.08, rot=0.12, r=0.15))
    bar = smax(np.hypot(c.X, (c.Y - 1.02)) - 1.16, -(np.hypot(c.X, c.Y - 1.02) - 0.955), 0.03)
    bar = smax(bar, np.abs(c.X) - 0.64, 0.02)
    d = smin(d, bar, 0.07)
    H = 0.17 * np.sqrt(clamp(1 - (1 - clamp(-d / 0.15)) ** 2))
    col = surface(c, H, flat(MINT, c.shape), GLOSS, rough=0.3, clear=1.0, reach=0.16)
    for x in (-0.73, 0.73):
        r = np.hypot(c.X - x, c.Y - 0.07)
        col = col * (1 - 0.35 * smooth(0.010, 0.002, np.abs(r - 0.165)))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'handset', exposure=0.95)
    halo(K, 'halo', 200, 2.2, 0.2, '#FFC9A0')


K.run([body, wheel, hole, hub, handset])
K.sounds('dial')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#F4EBD4', accent='#D8352A', accent2='#2F6E62', text='#2A2C30', border='#9AA4A6', opacity=0.98, corner=12, font='Courier New', open='spin', speed=1, hoverGrow=0,
               iconZoom=1.10, glow=0, tilt=0.4, pointer=False, burst=False, shadow=0.6, dim=0.26),
    wheel=dict(hub=92, thickness=92, gap=5, ringgap=14, rim=48, icon=40, crowd=1.5, area=[1.26, 1.46, 1.26, 1.12], hubkeep=0.66),
    colors=dict(ink='#2A2C30', red='#C22F24', cream='#F4EBD4'), fonts=dict(title='Courier New, Consolas', digits='Segoe UI Semibold, Segoe UI'),
    back=[soft(0.40, -0.88, 55, 0.6, x=-0.84), soft(0.40, -0.88, 55, 0.6, x=0.88), img('handset', [1.20, 0.432], y=-0.99, intro=intro(0.36, 'bounce', y=-0.30)), soft(1.10, 0.03, 64), img('body', 1, intro=intro(0.28, 'out', scale=0.9))],
    ring=[dict(img('wheel', 1), **{'in': 'px', 'size': '2*(ringout+6)'}, rotate='0', intro=intro(0.3, 'out', scale=0.92))],
    slot=dict(intro=intro(0.46, 'out', 0.04, angle=-150, scale=1, opacity=0, stagger=0.0, order='ring'),
              under=[img('hole', 1.08), img('warm', 1.0, opacity='sat(hot)*0.85'), img('redrim', 1.08, opacity='sat(hot*1.4)')],
              icon=dict(size=0.98, zoom=1.12, shadow=dict(x=1, y=2, blur=2, color='black/40')),
              over=[dict(text='{number}', y=0.0, x=0, radius=1.13, angle='a', em=0.24, color='#3A3E42', font='digits', weight=700, when='!kid', opacity=0.8),
                    {'shape': 'arc', 'r': '1.05+1.1*launch', 'from': 0, 'to': 360, 'stroke': '#D8352A', 'width': 3, 'opacity': 'launch*(1-launch)*3'}, {'shape': 'arc', 'r': '1.0+0.6*launch', 'from': 0, 'to': 360, 'stroke': '#D8352A', 'width': 2, 'opacity': 'launch*(1-launch)*3'}]
              + running('#2F6E62', '#9CF0DC', 0.70, 0.15) + groupmark('#2A2C30', -0.74, 0.11), marks=False, chevron=False, badge=False),
    over=[soft(1.22, 0.05, 60, 0.78, **{'in': 'hub'}), dict(shape='poly', **{'in': 'hub'}, angle='sel', radius=1.08, turns=True, points=[[-0.07, 0.05], [0, -0.07], [0.07, 0.05]], closed=True, fill='#D8352A', opacity='on')],
    hub=[img('hub', 1.0, intro=intro(0.34, 'back', scale=0.5))] + words('ink', 'red', T, px=17, box=(1.14, 0.46), clockpx=30, datepx=11.5, y=-0.04),
    front=[dict(img('stop', 46), **{'in': 'px'}, angle=124, radius='ringout-6', rotate=124 - 45, opacity='smooth(0.2,0.35,time)*(1-0.0)')],
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=15, text='ink', fill='#2A2C30/14', on='#D8352A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#8FD0C0'], [1, '#5FA596']]}, stroke={'type': 'linear', 'stops': [[0, '#FFFFFF'], [0.5, '#8C979B'], [1, '#E6ECEE']]}, width=3, corner=18, text='#14302A'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#FBF6E6'], [1, '#EADFC2']]}, stroke='#8C979B', width=1.6, corner=8, text='ink'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#FBF6E6'], [1, '#E6DABB']]}, stroke='#2F6E62', width=2, corner=9, text='ink'),
    onlaunch=[dict(color='#D8352A', count=14, area='slot', life=[0.25, 0.5], size=[2, 3.5], speed=[90, 300], outward=True, dir=[-80, 80], drag=3, fadein=0, fadeout=0.6)])
