"""Clay: modelling clay with fingerprints, animated the way clay films are: a few frames a second, never quite the same."""
from skinkit import *

K = Kit('clay', 'Clay', 'Modelling clay with fingerprints, never quite the same from frame to frame', ['handmade', 'playful', 'bright'])
K.flag(blobs=dict(cols=6, rows=3), hub=dict(cols=3), crumbs=dict(cols=6))
COLS = ('#E4572E', '#F2B134', '#4FA36B', '#3F88C5', '#8E5BB5', '#E06C9F')
ROOM = Studio(lights=[((-0.52, -0.66, 0.54), 0.55, '#FFF6E6', 3.8), ((0.72, -0.36, 0.50), 0.40, '#E4EEFF', 1.4), ((0.10, 0.86, 0.45), 0.5, '#FFE2C4', 0.8)], sky='#EEF0F4', floor='#6A5E58', ambient=0.58)


def prints(c, seed, n, size=(0.10, 0.16), amp=0.0035):
    """Fingerprints: whorls of fine ridges in soft round dents."""
    g = rng(seed)
    out = np.zeros(c.shape, F)
    for _ in range(n):
        a, r = g.random() * TAU, math.sqrt(g.random()) * 0.92 * c.extent
        x, y, s, t = math.sin(a) * r, -math.cos(a) * r, size[0] + (size[1] - size[0]) * g.random(), g.random() * TAU
        px, py = c.X - x, c.Y - y
        u, v = px * math.cos(t) + py * math.sin(t), -px * math.sin(t) + py * math.cos(t)
        q = np.hypot(u / s, v / (s * 1.35))
        m = smooth(1.0, 0.55, q)
        if m.max() <= 0:
            continue
        w = np.hypot(u + 0.2 * s, v * 0.75) + 0.10 * s * np.sin(v / s * 4)
        out -= m * 2.2 * amp * (1 - 0.35 * q)
        out += m * amp * np.sin(w / s * 46) * 0.8
    return out


def clay(c, d, H, base, seed, dents=3, lumps=0.012, size=(0.14, 0.24), amp=0.005):
    H = H + lumps * fbm(c.shape, 5, seed, 3) * smooth(0.0, -0.12, d) + prints(c, seed + 9, dents, size, amp) * smooth(0.0, -0.05, d) + 0.0015 * fbm(c.shape, 90, seed + 2, 2)
    n = fbm(c.shape, 6, seed + 4, 4)
    alb = flat(base, c.shape) * (1 + 0.07 * n)[..., None]
    return surface(c, H, alb, ROOM, rough=0.55, clear=0.10, sheen=0.25, reach=0.16, ao_r=(0.01, 0.03, 0.08)), H


def slab():
    c = K.canvas(1080, 2)
    rr = 0.965 * (1 + 0.008 * np.sin(3 * c.A + 1) + 0.006 * np.sin(7 * c.A) + 0.004 * np.sin(13 * c.A + 2))
    d = c.R - rr
    H = bevel(d, 0.07, 0.07)
    col, H = clay(c, d, H, '#2E5E73', 3, dents=34, lumps=0.010, size=(0.05, 0.085), amp=0.0022)
    c.put(col, c.cover(d), H)
    # a rolled snake round the edge, pressed on
    tw = 0.011 * np.sin(c.A * 34 + 0.5 * np.sin(c.A * 3))
    d2 = np.abs(c.R - 0.895 - 0.006 * np.sin(5 * c.A)) - 0.046 - tw * 0.4
    h2 = 0.062 + 0.055 * np.sqrt(clamp(1 - (1 - clamp(-d2 / 0.046)) ** 2))
    stripe = smooth(-0.15, 0.15, np.sin(c.A * 34 + (c.R - 0.895) * 60))
    alb = mix(flat('#F2E6D0', c.shape), flat('#E4572E', c.shape), stripe[..., None])
    h2 = h2 + 0.003 * fbm(c.shape, 60, 5, 2)
    sh = 0.45 * gauss(np.maximum(0, np.abs(np.hypot(c.X - 0.008, c.Y - 0.012) - 0.895) - 0.046), 0.020)
    c.shade_mul(1 - sh * (d2 > 0))
    c.put(surface(c, np.where(d2 < 0, h2, H), alb, ROOM, rough=0.55, clear=0.10, sheen=0.2), c.cover(d2), h2)
    K.put(c, 'slab', exposure=0.95)


def blobs():
    ims = []
    for f in range(3):
        for k, base in enumerate(COLS):
            c = K.canvas(190, 3)
            g = rng(100 * f + k)
            ph = g.random(4) * TAU
            rr = 0.84 * (1 + 0.020 * np.sin(2 * c.A + ph[0]) + 0.016 * np.sin(3 * c.A + ph[1]) + 0.010 * np.sin(5 * c.A + ph[2]))
            d = c.R - rr
            t = clamp(-d / 0.30)
            H = 0.24 * np.sqrt(clamp(1 - (1 - t) ** 2)) - 0.07 * smooth(0.60, 0.36, c.R)      # a thumb pressed the middle in
            sh = 0.50 * gauss(np.maximum(0, np.hypot(c.X - 0.05, c.Y - 0.08) - rr * 0.97), 0.09)
            c.put(np.zeros(3, F), sh.astype(F))
            col, H = clay(c, d, H, base, 40 + k * 7 + f * 61, dents=5, lumps=0.03, size=(0.26, 0.40), amp=0.009)
            c.put(col, c.cover(d), H)
            ims.append(c.image(exposure=0.97))
    K.sheet(ims, 6, 'blobs', how='jpg')


def hub():
    ims = []
    for f in range(3):
        c = K.canvas(430, 2)
        g = rng(700 + f)
        ph = g.random(4) * TAU
        rr = 0.935 * (1 + 0.010 * np.sin(2 * c.A + ph[0]) + 0.008 * np.sin(3 * c.A + ph[1]) + 0.005 * np.sin(6 * c.A + ph[2]))
        d = c.R - rr
        H = bevel(d, 0.14, 0.14)
        n = 20
        k = ((c.A / TAU + 0.5) * n) % 1
        H = H - 0.035 * smooth(0.070, 0.045, np.hypot((k - 0.5) * TAU * 0.86 / n, c.R - 0.82))          # pressed with a stick
        col, H = clay(c, d, H, '#F4E9D6', 80 + f * 13, dents=9, lumps=0.014, size=(0.13, 0.20), amp=0.0035)
        c.put(col, c.cover(d), H)
        ims.append(c.image(exposure=0.93))
    K.sheet(ims, 3, 'hub', how='jpg')
    ims = []
    for k, base in enumerate(COLS):
        c = K.canvas(48, 4)
        g = rng(k)
        ph = g.random(2) * TAU
        rr = 0.80 * (1 + 0.10 * np.sin(2 * c.A + ph[0]) + 0.08 * np.sin(3 * c.A + ph[1]))
        d = c.R - rr
        H = 0.55 * np.sqrt(clamp(1 - (c.R / np.maximum(rr, 0.1)) ** 2))
        c.put(surface(c, H, flat(base, c.shape), ROOM, rough=0.6, shadows=False), c.cover(d), H)
        ims.append(c.image())
    K.sheet(ims, 6, 'crumbs')
    c = K.canvas(110, 3, 1.0, 1.1)           # a pointer rolled between two fingers
    d = c.taper(0, 0.75, 0.46, 0, -0.85, 0.12)
    H = 0.5 * np.sqrt(clamp(1 - (1 - clamp(-d / 0.40)) ** 2))
    col, H = clay(c, d, H, '#E4572E', 33, dents=3, lumps=0.05, size=(0.3, 0.45), amp=0.012)
    c.put(col, c.cover(d), H)
    K.put(c, 'cone', how='png')


K.run([slab, blobs, hub])
K.sounds('clay')
T = 'title'
step = 'floor(time*6+i*1.7)'
K.write(
    style=dict(shape='orb', material='solid', base='#2E5E73', accent='#E4572E', accent2='#F2B134', text='#FFF6E6', border='#F2E6D0', opacity=0.98, corner=16, font='Segoe Print', open='bloom', speed=1, hoverGrow=2,
               iconZoom=1.12, glow=0, tilt=0.3, pointer=False, burst=False, shadow=0.55, dim=0.26),
    wheel=dict(hub=92, thickness=92, gap=4, ringgap=12, rim=40, icon=42, crowd=1.45, area=1.10, hubkeep=0.74),
    colors=dict(ink='#4A2A1E', red='#C23F1C', cream='#FFF6E6'), fonts=dict(title='Segoe Print, Ink Free, Segoe UI'),
    back=[soft(1.06, 0.03, 60, 0.85), img('slab', 1, rotate='(1-open)*-25', intro=intro(0.34, 'back', scale=0.8))],
    slot=dict(intro=intro(0.42, 'bounce', 0.06, scale=0.1, stagger=0.03, order='random'),
              under=[img('blobs', 1.06, frame='(%s%%3)*6+(i+ring*2)%%6' % step, rotate='4*(rnd(%s)-0.5)' % step, scale=['1+0.10*hot+0.10*press+0.6*launch', '1+0.10*hot-0.16*press-0.3*launch'], detail=1.1)],
              icon=dict(size=0.98, zoom=1.14, rotate='3*(rnd(%s+9)-0.5)' % step, x='0.012*(rnd(%s+3)-0.5)' % step, shadow=dict(x=1, y=2, blur=2, color='black/45')),
              over=[dict(shape='circle', y=0.80, x='0.02*(rnd(%s)-0.5)' % step, size=0.18, fill='#F2E6D0', stroke='#4A2A1E/50', width=1, when='running'), dict(shape='circle', y=0.80, size=0.10, fill='#E4572E', when='active')]
              + badge('#FFF6E6', 'ink', T, x=0.64, y=-0.64) + groupmark('cream', -0.78, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.14, 0.05, 55, 0.80, **{'in': 'hub'}), img('cone', [0.20, 0.22], **{'in': 'hub'}, angle='sel', radius=1.10, turns=True, opacity='on', scale='0.4+0.6*on')],
    hub=[img('hub', 1.0, frame='floor(time*5)%3', intro=intro(0.4, 'bounce', scale=0.3))] + words('ink', 'red', T, px=20, y=-0.04, box=(1.22, 0.56), clockpx=31, datepx=13, subpx=12.5, weight=700),
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=22, text='ink', fill='#D9C6A6/70', on='#E4572E'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#376F87'], [1, '#26505F']]}, stroke={'type': 'linear', 'stops': [[0, '#FFF6E6'], [1, '#CDB994']]}, width=5, corner=18, text='cream'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#F9EFDD'], [1, '#E4D4B8']]}, stroke='#C9B48E', width=2, corner=12, text='ink'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#F9EFDD'], [1, '#E4D4B8']]}, stroke='#E4572E', width=3, corner=14, text='ink'),
    onlaunch=[dict(image='crumbs', count=30, area='slot', life=[0.5, 1.0], size=[5, 12], speed=[120, 420], outward=True, dir=[-90, 90], gravity=900, drag=1.4, spin=[-300, 300], fadein=0, fadeout=0.2)],
    onhover=[dict(image='crumbs', count=3, area='slot', life=[0.3, 0.6], size=[3, 5], speed=[40, 120], outward=True, dir=[-70, 70], gravity=500, fadein=0, fadeout=0.4)])
