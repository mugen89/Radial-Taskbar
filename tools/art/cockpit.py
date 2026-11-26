"""Cockpit: an artificial horizon that follows the pointer, four gauges that show the PC, lit switches."""
from skinkit import *

K = Kit('cockpit', 'Cockpit', 'An artificial horizon follows the pointer; the gauges show processor, memory, sound and time', ['aircraft', 'technical', 'instruments'])
K.flag(keys=dict(cols=2), halo='light', lamp='light')
DUSK = Studio(lights=[((-0.45, -0.72, 0.56), 0.36, '#EAF2FF', 3.8), ((0.80, -0.28, 0.48), 0.24, '#BFD6FF', 1.6), ((0.12, 0.88, 0.42), 0.34, '#FFCF9A', 0.8)], sky='#9AAAC2', floor='#0A0C10', ambient=0.42)
BLACK = V([0.030, 0.032, 0.036])


def screws(c, H, col, n, radius, size, seed=1, phase=0.0):
    for i in range(n):
        x, y = c.polar(i * TAU / n + phase, radius)
        r = np.hypot(c.X - x, c.Y - y)
        a = seed + i * 1.7
        hs = np.where(r < size, H + dome(r, size * 1.05, size * 0.5), H)
        sl = np.minimum(np.abs((c.X - x) * math.cos(a) + (c.Y - y) * math.sin(a)), np.abs(-(c.X - x) * math.sin(a) + (c.Y - y) * math.cos(a)))
        hs = np.where((sl < size * 0.13) & (r < size * 0.72), H, hs)
        col = mix(col, metal(c, hs, V([0.25, 0.26, 0.28]), rough=0.3, grime=0.4, studio=DUSK, reach=0.04, dirt='#050506'), smooth(size, size * 0.92, r)[..., None])
        col = col * (1 - 0.5 * gauss(r - size * 1.15, size * 0.25))[..., None]
    return col


def panel():
    c = K.canvas(1080, 2)
    H = lathe(c, [(0, 0.02), (0.965, 0.02), (0.975, 0.030), (0.992, 0.026), (1.0, 0.0)], 0.003)
    wr = fbm(c.shape, 190, 4, 3)
    alb = flat('#23272D', c.shape) * (1 + 0.05 * wr)[..., None]
    col = surface(c, H + 0.0022 * wr, alb, DUSK, rough=0.55, clear=0.08, reach=0.05)
    ink = Ink(c)
    for r, w in ((0.945, 0.003), (0.465, 0.003)):
        ink.line(arcpts(r, 0, TAU, 300), w, 170)
    for k in range(72):
        ink.line([c.polar(k * TAU / 72, 0.925 if k % 2 else 0.912), c.polar(k * TAU / 72, 0.940)], 0.0028 if k % 6 else 0.0055, 190)
    cov = ink.arr(0.0004)
    for k, t in enumerate(('N', '30', '60', 'E', '120', '150', 'S', '210', '240', 'W', '300', '330')):
        pass
    col = mix(col, flat('#DDE3EA', c.shape), (0.75 * cov)[..., None])
    col = screws(c, H, col, 8, 0.862, 0.020, 2, TAU / 16)
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'panel', exposure=1.02)


def bezel():
    c = K.canvas(520, 2)
    H = np.where(c.R > 0.72, lathe(c, [(0.72, 0.0), (0.745, 0.04), (0.78, 0.10), (0.93, 0.12), (0.975, 0.10), (1.0, 0.0)], 0.0), 0)
    col = surface(c, H + 0.0025 * fbm(c.shape, 120, 3, 2), flat('#1B1E23', c.shape), DUSK, rough=0.45, clear=0.25)
    col = screws(c, H, col, 4, 0.865, 0.045, 5, TAU / 8)
    ring = np.maximum(smooth(0.010, 0.004, np.abs(c.R - 0.755)), 0)
    col = col * (1 - 0.5 * ring)[..., None]
    c.put(col, c.cover(c.R - 0.985) * smooth(0.720, 0.726, c.R), H)
    K.put(c, 'bezel')
    # the ball's picture: sky over earth, with a ladder; larger than what is seen
    c = K.canvas(640, 2)
    sky = ramp(clamp((c.Y + 1)), '#1C5FB8', '#3F8FE0', '#7FBCF2')
    earth = ramp(clamp(c.Y), '#8A5A2C', '#5F3A1A', '#3A220E')
    col = np.where((c.Y < 0)[..., None], sky, earth)
    ink = Ink(c)
    ink.line([(-1, 0), (1, 0)], 0.008)
    for k in range(1, 9):
        for s in (-1, 1):
            y, w = s * k * 0.075, 0.16 if k % 2 == 0 else 0.08
            ink.line([(-w, y), (w, y)], 0.0055)
    for k in range(-4, 5):
        if k:
            ink.line([(0, 0), (k * 0.5, 1.0)], 0.004, 110)
    col = mix(col, flat('#FFFFFF', c.shape), (0.9 * ink.arr(0.0012))[..., None])
    c.col, c.alpha = col.astype(F), np.ones(c.shape, F)
    K.put(c, 'horizon', tone=False, quality=86)
    # glass, with a shadow under the bezel
    c = K.canvas(400, 2)
    ax, ay = c.X + 0.05, c.Y + 0.10
    rr = np.hypot(ax, ay)
    win = smooth(0.62, 0.70, rr) * (1 - smooth(0.84, 0.92, rr)) * smooth(0.45, 0.95, -(ax * 0.5 + ay * 0.86) / np.maximum(rr, 1e-4))
    li = 0.28 * win
    dk = 0.75 * smooth(0.70, 1.0, np.hypot(c.X + 0.04, c.Y + 0.06)) ** 1.5
    a = clamp(li + dk * (1 - li)) * c.cover(c.R - 0.99)
    c.col = from_srgb(np.ones(c.shape + (3,), F) * (li / np.maximum(li + dk * (1 - li), 1e-4))[..., None])
    c.alpha = a.astype(F)
    K.put(c, 'glass', how='png', tone=False)


def gauge():
    """One dial for all four; its writing is drawn by the program."""
    c = K.canvas(300, 3)
    H = lathe(c, [(0, 0.0), (0.76, 0.0), (0.785, 0.09), (0.83, 0.14), (0.92, 0.15), (0.97, 0.11), (1.0, 0.0)], 0.008)
    col = surface(c, H, flat('#17191D', c.shape), DUSK, rough=0.35, clear=0.45, reach=0.3)
    face = flat('#0C0D10', c.shape) * (1 + 0.3 * smooth(0.8, 0.0, c.R))[..., None]
    ink, red, grn, yel = Ink(c), Ink(c), Ink(c), Ink(c)
    for k in range(25):
        a = math.radians(-120 + k * 10)
        ink.line([c.polar(a, 0.61 if k % 4 else 0.55), c.polar(a, 0.69)], 0.016 if k % 4 else 0.030)
    grn.line(arcpts(0.715, math.radians(-120), math.radians(50), 60), 0.030)
    yel.line(arcpts(0.715, math.radians(50), math.radians(90), 30), 0.030)
    red.line(arcpts(0.715, math.radians(90), math.radians(120), 20), 0.030)
    for i, k in ((ink, '#E9EEF4'), (grn, '#37C871'), (yel, '#F2C230'), (red, '#E5342C')):
        face = mix(face, flat(k, c.shape), (0.92 * i.arr(0.003))[..., None])
    face = face * (0.45 + 0.55 * smooth(0.0, 0.25, 0.76 - c.R + 0.12 * (c.X + c.Y)))[..., None]
    col = mix(face, col, smooth(0.755, 0.765, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'gauge', exposure=1.0)
    c = K.canvas(60, 4, 1.0, 5.0)            # needle: pivot in the middle
    d = np.minimum(c.poly([(-0.34, 0.2), (-0.14, -4.6), (0.14, -4.6), (0.34, 0.2)]), c.poly([(-0.34, 0.2), (-0.50, 1.7), (0.50, 1.7), (0.34, 0.2)]))
    c.put(np.where((c.Y < 0.0)[..., None], rgb('#F4F7FA'), rgb('#2A2C30')) * (0.9 + 0.1 * smooth(-0.1, 0.1, c.X))[..., None], c.cover(d))
    r = np.hypot(c.X, c.Y)
    c.put(rgb('#2A2D32') * (0.8 + 0.8 * gauss(np.hypot(c.X + 0.2, c.Y + 0.25), 0.35))[..., None], c.cover(r - 0.80))
    K.put(c, 'needle', how='png', tone=False)


def keys():
    ims = []
    for lit in (0, 1):
        c = K.canvas(240, 3)
        d = c.box(0.84, 0.84, r=0.16)
        well = bevel(d, 0.06, 0.06)
        d2 = c.box(0.72, 0.72, r=0.12)
        H = np.where(d2 < 0, 0.10 + bevel(d2, 0.07, 0.06), np.where(d < -0.02, 0.0, well))
        alb = flat('#2B3037', c.shape) * (1 + 0.03 * fbm(c.shape, 90, 3, 2))[..., None]
        col = surface(c, H, alb, DUSK, rough=0.45, clear=0.25, reach=0.2)
        if lit:
            gl = smooth(0.0, -0.30, d2)
            col = col * 0.8 + rgb('#FFB020') * (0.95 * smooth(0.012, -0.012, d2) * (0.45 + 0.75 * gauss(c.R, 0.65)))[..., None]
            edge = smooth(0.03, 0.0, np.abs(d2))
            col = col + rgb('#FFD27A') * (0.7 * edge)[..., None]
        col = col * (1 - 0.75 * smooth(0.03, 0.008, np.abs(d2 - 0.035)) * (d < -0.01))[..., None]
        c.put(col, c.cover(d), H)
        ims.append(c.image(exposure=1.05))
    K.sheet(ims, 2, 'keys', how='jpg')
    halo(K, 'halo', 220, 2.0, 0.15, '#FFB84A')
    halo(K, 'lamp', 80, 2.0, 0.0)
    boxshadow(K, 'keyshadow', 0.84, 0.84, 0.16, 1.15, 0.08, 0.6, 96)


K.run([panel, bezel, gauge, keys])
K.sounds('cockpit')
T = 'title'
def dial(x, y, label, value, extra=()):
    return [soft(0.36, y + 0.03, 60, 0.80, x=x + 0.015), img('gauge', 0.33, x=x, y=y, intro=intro(0.3, 'back', 0.08, scale=0.5)), dict(text=label, x=x, y=y + 0.085, px=8.5, color='#DDE3EA', font='small', weight=600, opacity='smooth(0.2,0.4,time)')] + list(extra) + \
           [img('needle', [0.028, 0.14], x=x, y=y, rotate=value, pivot=[0.5, 0.5], opacity='smooth(0.1,0.3,time)')]
sweep = '-120+240*outcubic(sat(time*1.6))*%s'
hand = [img('needle', [0.020, 0.115], x=-0.80, y=-0.80, rotate='minute*6', pivot=[0.5, 0.5]), ]
K.write(
    style=dict(shape='orb', material='solid', base='#171A1F', accent='#FFB020', accent2='#37C871', text='#EAF0F6', border='#5A626C', opacity=0.98, corner=9, font='Bahnschrift', open='zoom', speed=1.1, hoverGrow=2,
               iconZoom=1.08, glow=0.3, tilt=0.4, pointer=False, burst=False, shadow=0.7, dim=0.36),
    wheel=dict(hub=94, thickness=92, gap=5, ringgap=10, rim=30, icon=40, crowd=1.5, area=1.24, hubkeep=0.60, shadow=0.5),
    colors=dict(white='#F4F7FA', amber='#FFB020', green='#37C871'), fonts=dict(title='Bahnschrift, Segoe UI Semibold', small='Bahnschrift, Segoe UI'),
    back=[soft(1.09, 0.025, 66)] + dial(-0.80, 0.80, 'CPU', sweep % 'cpu') + dial(0.80, 0.80, 'RAM', sweep % 'ram') + dial(0.80, -0.80, 'SOUND', sweep % 'sound') + dial(-0.80, -0.80, '{hh}:{mm}', 'hour*30', hand) + [img('panel', 1, intro=intro(0.26, 'out', scale=0.9))],
    ring=[dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringout+4', to=360, stroke='white/25', width=1)],
    slot=dict(intro=intro(0.24, 'back', 0.06, scale=0.6, stagger=0.022, order='ring'),
              under=[img('halo', 1.8, opacity='0.50*hot+launch*1.5'), img('keyshadow', 1.18, x=0.03, y=0.06), img('keys', '1.12*(1-0.04*press)', frame=0, detail=1.04), img('keys', '1.12*(1-0.04*press)', frame=1, opacity='sat(hot)*0.92+launch', detail=1.04)],
              icon=dict(size=0.92, zoom=1.08, shadow=dict(y=1, blur=2, color='black/60')),
              over=[dict(shape='rect', y=0.80, size=[0.36, 0.055], corner=1.5, fill='#0C2A18', when='running'), dict(shape='rect', y=0.80, size=[0.36, 0.055], corner=1.5, fill='green', when='running', opacity='active ? 1 : 0.6', glow=5, glowcolor='green'),
                    dict(text='{number}', x=-0.66, y=-0.66, em=0.25, color='white', font='small', weight=600, when='numbers && number<10 && !kid'), dict(shape='poly', points=[[0.52, -0.72], [0.72, -0.72], [0.72, -0.52]], closed=True, fill='amber', when='group')], marks=False, chevron=False, badge=False),
    over=[soft(1.16, 0.05, 66, 0.82, **{'in': 'hub'})],
    hub=[dict(shape='circle', size=0.78, fill={'image': 'horizon', 'zoom': 1.45, 'u': '0', 'v': 'clamp(py*0.22,-0.22,0.22)', 'turn': 'clamp(px*26,-32,32)'}),
         dict(shape='line', points=[[-0.46, 0.0], [-0.20, 0.0], [-0.13, 0.09]], stroke='#FFB020', width=3, caps=True, opacity='idle*0.0+0.9', y=0.52), dict(shape='line', points=[[0.46, 0.0], [0.20, 0.0], [0.13, 0.09]], stroke='#FFB020', width=3, caps=True, opacity=0.9, y=0.52), dict(shape='circle', y=0.52, size=0.05, fill='#FFB020'),
         img('glass', 0.78), img('bezel', 1.04, intro=intro(0.3, 'back', scale=0.6)), dict(shape='poly', angle='sel', radius=0.80, turns=True, points=[[-0.075, 0.06], [0, -0.075], [0.075, 0.06]], closed=True, fill='amber', opacity='on', glow=5, glowcolor='amber'),
         dict(shape='rect', y=-0.03, size=[0.64, 0.29], corner=6, fill='#07090C/72', stroke='white/25', width=1)] + words('white', 'amber', T, px=16, y=-0.10, box=(1.16, 0.40), subpx=10.5, suby=0.17, clockpx=29, clocky=-0.09, datey=0.17, datepx=10.5, weight=600),
    front=[dict(shape='circle', x=-0.13, y='-0.955', size=0.030, fill='#37C871', glow=5, glowcolor='green', opacity='smooth(0.2,0.3,time)'), dict(shape='circle', x=0.0, y=-0.965, size=0.030, fill='#FFB020', glow=5, glowcolor='amber', opacity='0.25+0.75*on'), dict(shape='circle', x=0.13, y=-0.955, size=0.030, fill='#E5342C', glow=5, glowcolor='#E5342C', opacity='0.20+0.8*smooth(0.80,0.95,cpu)*step(0.5,fract(time*2))+launch')],
    draw=dict(clock=False, shadow=False, text='white'), tabs=dict(inset=27, text='white', fill='#000000/55', on='#FFB020/85'),
    pinbutton={'in': 'hub', 'x': -0.19, 'y': 0.36, 'size': 10}, settingsbutton={'in': 'hub', 'x': 0.19, 'y': 0.36, 'size': 10},
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#2B3037'], [1, '#171A1F']]}, stroke='#5A626C', width=2.4, corner=10, text='white'), tag=dict(fill='#0C0D10', stroke='#FFB020', width=1.4, corner=4, text='amber'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#333941'], [1, '#1B1E23']]}, stroke='#6A737E', width=2, corner=8, text='white'),
    onlaunch=[dict(color='#FFB020', light=True, count=34, area='slot', life=[0.2, 0.5], size=[2, 4], speed=[200, 640], outward=True, dir=[-35, 35], drag=2, stretch=1, fadein=0, fadeout=0.6)])
