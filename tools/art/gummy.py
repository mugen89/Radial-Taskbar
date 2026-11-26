"""Gummy: jelly sweets on a lollipop that wobble when you poke them."""
from skinkit import *

K = Kit('gummy', 'Gummy', 'Glossy jelly sweets on a lollipop; they wobble when you point at them', ['candy', 'playful', 'bright'])
K.flag(sweets=dict(cols=6), halo='light', bits=dict(cols=6))
CANDY = Studio(lights=[((-0.42, -0.70, 0.60), 0.34, '#FFFFFF', 4.6), ((0.70, -0.36, 0.55), 0.22, '#FFF4FA', 2.2), ((0.10, 0.85, 0.45), 0.40, '#FFE3F2', 1.0)], sky='#FFF3FA', floor='#B06A90', ambient=0.62)
COLS = ('#FF3B5C', '#FF9A1F', '#FFD21F', '#4CD04A', '#2FB4FF', '#B45CFF')


def jelly(c, d, H, base, seed, deep=0.55, frost=0.0):
    """Light goes in, wanders and comes out on the far side; a hard gloss on top."""
    nx, ny, nz = normals(H, c.px)
    b = rgb(base)
    t = clamp(-d / 0.9)
    away = clamp(0.5 + 0.55 * (c.X * 0.45 + c.Y * 0.75))         # brighter where the light leaves
    thick = np.power(clamp(t * 1.6), 0.7)
    body = b * (0.30 + 0.55 * away + 0.15 * thick)[..., None] + (b ** 0.55) * (0.50 * away * (1 - 0.6 * thick))[..., None]
    rim = np.power(clamp(1 - nz), 1.6)
    body = body + (b ** 0.45) * (0.35 * rim)[..., None]
    spec = CANDY.reflect(nx, ny, nz, 0.10) * (0.05 + 0.95 * np.power(clamp(1 - nz), 4))[..., None]
    hl = np.power(clamp(nx * -0.40 + ny * -0.66 + nz * 0.64), 60) * 1.3
    col = body + spec * 0.8 + hl[..., None]
    if frost:
        col = col + (0.10 * frost * clamp(fbm(c.shape, 150, seed, 2)))[..., None]
    return col


def lolly():
    c = K.canvas(1080, 2)
    H = lathe(c, [(0, 0.10), (0.70, 0.095), (0.90, 0.07), (0.97, 0.04), (1.0, 0.0)], 0.02)
    turn = c.A / TAU * 7 + 2.6 * np.power(c.R, 0.8)
    k = 0.5 + 0.5 * np.sin(turn * TAU)
    s = smooth(0.40, 0.60, k)
    alb = mix(flat('#FFF6FB', c.shape), flat('#FF7FB2', c.shape), s[..., None])
    ridge = 0.010 * (0.5 - 0.5 * np.cos(turn * 2 * TAU))
    col = surface(c, H + ridge, alb, CANDY, rough=0.35, clear=1.0, reach=0.1)
    c.put(col, c.cover(c.R - 0.996), H)
    K.put(c, 'lolly', exposure=0.92)
    c = K.canvas(90, 2, 1.0, 6.0)            # its stick
    u = clamp(c.X / 0.8, -1, 1)
    c.put(flat('#FDFBF6', c.shape) * (0.45 + 0.55 * np.sqrt(1 - u * u) + 0.12 * gauss(u + 0.4, 0.3))[..., None] * 0.92, c.cover(c.box(0.80, 5.9, r=0.7)))
    K.put(c, 'stick', how='png')


def sweets():
    ims = []
    for k, base in enumerate(COLS):
        c = K.canvas(230, 3)
        g = rng(30 + k)
        ph = g.random(3) * TAU
        rr = 0.86 * (1 + 0.016 * np.sin(2 * c.A + ph[0]) + 0.012 * np.sin(3 * c.A + ph[1]))
        d = c.R - rr
        t = clamp(-d / 0.86)
        H = 0.46 * np.sqrt(clamp(1 - (1 - t) ** 2.4)) - 0.05 * smooth(0.50, 0.20, c.R)
        sh = 0.36 * gauss(np.maximum(0, np.hypot(c.X - 0.04, c.Y - 0.09) - rr * 0.95), 0.09)
        c.put(rgb(base) * 0.22, sh.astype(F))
        c.put(jelly(c, d, H, base, 5 + k), c.cover(d) * 0.97, H)
        ims.append(c.image(exposure=0.95))
    K.sheet(ims, 6, 'sweets')
    # the gloss that lies over the icon as well
    c = K.canvas(230, 3)
    ax, ay = c.X + 0.04, c.Y + 0.06
    rr = np.hypot(ax, ay)
    win = smooth(0.50, 0.58, rr) * (1 - smooth(0.72, 0.80, rr)) * smooth(0.45, 0.92, -(ax * 0.52 + ay * 0.86) / np.maximum(rr, 1e-4))
    low = smooth(0.50, 0.80, c.R) * smooth(0.45, 1.0, (c.X * 0.45 + c.Y * 0.88) / np.maximum(c.R, 1e-4)) * (1 - smooth(0.80, 0.88, c.R))
    c.col[:] = 1
    c.alpha = clamp(0.62 * win + 0.26 * low).astype(F)
    K.put(c, 'gloss', how='png', tone=False)


def hub():
    c = K.canvas(460, 2)
    rr = 0.95
    d = c.R - rr
    t = clamp(-d / 0.5)
    H = 0.30 * np.sqrt(clamp(1 - (1 - t) ** 2.2))
    col = jelly(c, d, H, '#6A4CFF', 8)
    dusk = smooth(0.80, 0.55, c.R)
    col = mix(col, flat('#4326B8', c.shape), (0.55 * dusk)[..., None])
    c.put(col, c.cover(d) * 0.98, H)
    g = rng(5)
    n = 260 if K.draft == 1 else 120
    for _ in range(n):              # sugar round the edge
        a, r = g.random() * TAU, 0.90 - abs(g.standard_normal()) * 0.06
        x, y, s = math.sin(a) * r, -math.cos(a) * r, 0.010 + 0.012 * g.random()
        q = c.box(s, s, x, y, rot=g.random() * 3, r=0.002)
        near = np.abs(q) < 0.05
        c.put(np.ones(3, F) * (0.75 + 0.35 * g.random()), (clamp(0.5 - q / c.px) * near * 0.85).astype(F))
    K.put(c, 'hub', exposure=0.95)
    ims = []
    for k, base in enumerate(COLS):
        c = K.canvas(56, 4)
        d = c.R - 0.86
        H = 0.6 * np.sqrt(clamp(1 - (c.R / 0.88) ** 2))
        c.put(jelly(c, d, H, base, 5), c.cover(d), H)
        ims.append(c.image())
    K.sheet(ims, 6, 'bits')
    c = K.canvas(40, 4)
    q = c.box(0.62, 0.62, rot=0.4, r=0.1)
    c.put(np.ones(3, F) * 0.95 * (0.8 + 0.2 * smooth(-0.5, 0.5, -c.Y - c.X))[..., None], c.cover(q) * 0.92)
    K.put(c, 'sugar', how='png')
    halo(K, 'halo', 220, 2.0, 0.2)


K.run([lolly, sweets, hub])
K.sounds('jelly')
T = 'title'
wob = '(1+0.035*sin(time*13+seed*6)*hot+0.10*hot-0.16*press+0.5*launch)'
wob2 = '(1-0.035*sin(time*13+seed*6)*hot+0.10*hot-0.10*press+0.5*launch)'
K.write(
    style=dict(shape='orb', material='solid', base='#FFF4FA', accent='#FF4F8B', accent2='#6A4CFF', text='#5A1E48', border='#FFB3D1', opacity=0.98, corner=20, font='Segoe UI', open='bloom', speed=1, hoverGrow=2,
               iconZoom=1.10, glow=0, tilt=0.6, pointer=False, burst=False, shadow=0.45, dim=0.22),
    wheel=dict(hub=90, thickness=92, gap=5, ringgap=14, rim=30, icon=42, crowd=1.45, area=[1.10, 1.10, 1.10, 1.45], hubkeep=0.78),
    colors=dict(plum='#5A1E48', white='#FFFFFF', pink='#FF4F8B'), fonts=dict(title='Segoe UI Black, Segoe UI'),
    back=[soft(0.2, 1.1, 40, 0.4, x=0.03), img('stick', [0.085, 0.51], y=1.13, intro=intro(0.3, 'out', y=-0.35, delay=0.08)), soft(1.09, 0.03, 50, 0.84), img('lolly', 1, rotate='time*-5+sel*0.12+(1-open)*-180', intro=intro(0.42, 'elastic', scale=0.5))],
    slot=dict(intro=intro(0.55, 'elastic', 0.06, scale=0.05, stagger=0.025, order='both'),
              under=[img('sweets', 1.0, frame='(i+ring*3)%6', scale=[wob, wob2], rotate='3*sin(time*9+seed*5)*hot', detail=1.1)],
              icon=dict(size=0.92, zoom=1.12, opacity=0.97, rotate='3*sin(time*9+seed*5)*hot'),
              over=[img('gloss', 1.0, scale=[wob, wob2], opacity=0.85), dict(shape='circle', y=0.80, size=0.16, fill='white', when='running', opacity='active ? 1 : 0.7'), dict(shape='circle', y=0.80, size=0.09, fill='pink', when='active')]
              + badge('white', 'plum', T, x=0.64, y=-0.64) + groupmark('white', -0.80, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.16, 0.05, 45, 0.80, **{'in': 'hub'}), dict(shape='circle', **{'in': 'hub'}, angle='sel', radius=1.10, size='0.20*on*(1+0.08*sin(time*12))', fill={'type': 'radial', 'from': [-0.3, -0.4], 'radius': 1.2, 'stops': [[0, '#FFE3F0'], [0.4, '#FF5C97'], [1, '#C21E62']]})],
    hub=[img('hub', 1.0, scale=['1+0.012*sin(time*5)+0.03*on*sin(time*11)', '1-0.012*sin(time*5)-0.03*on*sin(time*11)'], intro=intro(0.5, 'elastic', scale=0.2))] + words('white', '#FFD9EC', T, px=17, box=(1.26, 0.52), clockpx=31, datepx=12, shadow=dict(x=0, y=1, blur=2, color='#2A0E6B')),
    draw=dict(clock=False, shadow=False, text='white'), tabs=dict(inset=13, text='white', fill='#FFFFFF/16', on='#FF4F8B'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#FFF8FC'], [1, '#FFE0EE']]}, stroke='#FF8FBC', width=3, corner=24, text='plum'), tag=dict(fill={'type': 'linear', 'stops': [[0, '#FF7FB2'], [1, '#FF4F8B']]}, stroke='#FFC4DC', width=2, corner=15, text='white'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#FFFFFF'], [1, '#FFE0EE']]}, stroke='#FF8FBC', width=2.4, corner=16, text='plum'),
    onlaunch=[dict(image='bits', count=26, area='slot', life=[0.5, 1.0], size=[7, 15], speed=[120, 460], outward=True, dir=[-90, 90], gravity=620, drag=1.6, fadein=0, fadeout=0.3), dict(image='sugar', count=26, area='slot', life=[0.4, 0.9], size=[2, 4], speed=[100, 420], outward=True, dir=[-100, 100], gravity=500, drag=2, spin=[-300, 300], fadein=0, fadeout=0.4)],
    onhover=[dict(image='sugar', count=6, area='slot', life=[0.3, 0.6], size=[1.5, 3], speed=[30, 110], outward=True, dir=[-80, 80], gravity=260, spin=[-200, 200], fadein=0, fadeout=0.5)])
