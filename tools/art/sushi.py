"""Sushi Belt: little plates ride round the counter, chopsticks reach for your choice."""
from skinkit import *

K = Kit('sushi', 'Sushi Belt', 'Plates ride round the counter and chopsticks reach for your choice', ['food', 'playful', 'wood'])
K.flag(plates=dict(cols=4), bitsheet=dict(cols=4), steam='light')
BAR = Studio(lights=[((-0.45, -0.70, 0.58), 0.45, '#FFF3DE', 4.0), ((0.75, -0.32, 0.50), 0.30, '#E8EFFF', 1.5), ((0.10, 0.86, 0.45), 0.45, '#FFD9AE', 0.9)], sky='#F0E6D6', floor='#3A2A1E', ambient=0.52)


def counter():
    c = K.canvas(1080, 2)
    H = lathe(c, [(0, 0.030), (0.872, 0.030), (0.880, 0.050), (0.978, 0.052), (0.990, 0.046), (1.0, 0.015)], 0.003)
    tex, g = wood(c, 12, 1.4, '#E3B97C', '#B07C42', rot=0.15)
    arcs = ramp(clamp(0.5 + 0.30 * circular_streaks(c, 8, 700) + 0.12 * fbm(c.shape, 20, 9, 3)), '#B98246', '#D9AA6A', '#EBC78E')
    alb = np.where((c.R > 0.876)[..., None], arcs, tex)
    k = ((c.A / TAU + 0.5) * 10) % 1
    H = H - 0.004 * smooth(0.4970, 0.4995, np.abs(k - 0.5)) * (c.R > 0.882)
    col = surface(c, H + 0.0007 * g, alb, BAR, rough=0.5, clear=0.18, reach=0.12)
    c.put(col, c.cover(c.R - 0.998), H)
    # three rolls left on the counter
    for a, rr in ((2.45, 0.932), (2.58, 0.928), (5.05, 0.932)):
        x, y = c.polar(a, rr)
        r = np.hypot(c.X - x, c.Y - y)
        sh = 0.5 * gauss(np.maximum(0, np.hypot(c.X - x - 0.008, c.Y - y - 0.012) - 0.036), 0.016)
        c.shade_mul(1 - sh * (r > 0.038))
        h = 0.09 + 0.02 * smooth(0.040, 0.030, r)
        alb = flat('#1B2A20', c.shape)
        rice = flat('#FBF8F0', c.shape) * (0.93 + 0.07 * (worley(c.X, c.Y, 150, 3) > 0.35))[..., None]
        alb = mix(alb, rice, smooth(0.0355, 0.0335, r)[..., None])
        alb = mix(alb, flat('#F5835A', c.shape), smooth(0.016, 0.014, np.hypot(c.X - x + 0.004, c.Y - y))[..., None])
        alb = mix(alb, flat('#7FB24A', c.shape), smooth(0.008, 0.006, np.hypot(c.X - x - 0.013, c.Y - y - 0.004))[..., None])
        c.put(surface(c, np.where(r < 0.041, h, c.H), alb, BAR, rough=0.5, clear=0.2, shadows=False), c.cover(r - 0.040), h)
    K.put(c, 'counter', exposure=0.95)


def belt():
    """Crescent plates that overlap; looks the same after every step, so it can turn for ever."""
    c = K.canvas(1000, 2)
    n = 30
    a = c.A * n / TAU + 0.9 * np.sin((c.R - 0.62) * 5.2) * 1.2
    k = a % 1
    H = 0.020 + 0.012 * k
    alb = flat('#3C4046', c.shape) * (1 + 0.04 * circular_streaks(c, 5, 900))[..., None]
    col = surface(c, H, alb, COOL, rough=0.35, clear=0.35, metal=0.0, reach=0.04, strength=1.0)
    col = col * (1 - 0.55 * smooth(0.06, 0.0, k))[..., None] + (0.12 * smooth(0.90, 1.0, k))[..., None]
    edge = np.maximum(smooth(0.985, 0.998, c.R), 0)
    col = col * (1 - 0.6 * edge)[..., None]
    c.put(col, c.cover(c.R - 0.998))
    K.put(c, 'belt', exposure=1.0, quality=86)


def plates():
    ims = []
    for k, (rim, dot) in enumerate((('#2F5FB0', '#FFFFFF'), ('#C8372D', '#F7D9A0'), ('#3E8A57', '#FFFFFF'), ('#D9A32B', '#7A3E12'))):
        c = K.canvas(250, 3)
        H = lathe(c, [(0, 0.04), (0.60, 0.04), (0.76, 0.10), (0.90, 0.17), (0.96, 0.17), (1.0, 0.10)], 0.02)
        alb = flat('#FAF7F0', c.shape)
        band = smooth(0.70, 0.72, c.R) * smooth(0.935, 0.915, c.R)
        alb = paint(alb, band, rim)
        a = (c.A / TAU + 0.5) * 18
        if k == 0:                  # waves
            q = np.hypot(((a % 1) - 0.5) * 0.30, (c.R - 0.84) * 1.0)
            alb = paint(alb, smooth(0.012, 0.004, np.abs(q - 0.07)) * band, dot)
            alb = paint(alb, smooth(0.012, 0.004, np.abs(q - 0.035)) * band, dot)
        elif k == 1:                # dots
            alb = paint(alb, smooth(0.034, 0.024, np.hypot(((a % 1) - 0.5) * 0.30, c.R - 0.82)), dot)
        elif k == 2:                # slanted strokes
            s = np.abs(((a + (c.R - 0.8) * 6) % 1) - 0.5)
            alb = paint(alb, smooth(0.13, 0.09, s) * band * 0.9, dot)
        else:                       # check
            s = ((np.floor(a * 2) + np.floor((c.R - 0.70) / 0.075)) % 2)
            alb = paint(alb, s * band * 0.75, dot)
        col = surface(c, H, alb, BAR, rough=0.3, clear=0.85, reach=0.3)
        sh = 0.5 * gauss(np.maximum(0, np.hypot(c.X - 0.05, c.Y - 0.09) - 0.86), 0.09)
        c2 = np.clip(1 - np.maximum(0, np.maximum(np.abs(c.X), np.abs(c.Y)) - 0.9) / 0.1, 0, 1)
        c.put(np.zeros(3, F), (sh * c2).astype(F))
        c.put(col, c.cover(c.R - 0.92), H)
        ims.append(c.image(exposure=0.93))
    K.sheet(ims, 4, 'plates', how='jpg')


def middle():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    H = bevel(d, 0.05, 0.05)
    tex, g = wood(c, 31, 1.2, '#9A6A3C', '#5A3820', rot=0.05)
    col = surface(c, H + 0.003 * g, tex, BAR, rough=0.5, clear=0.25)
    # a branded ring and a paper disc
    ln = np.maximum(smooth(0.008, 0.003, np.abs(c.R - 0.86)), smooth(0.005, 0.002, np.abs(c.R - 0.835)))
    col = col * (1 - 0.65 * ln)[..., None]
    p = c.R - 0.77
    H2 = np.where(p < 0, 0.062 + 0.001 * fbm(c.shape, 150, 3, 3), H)
    paper = surface(c, H2, flat('#F7F0DE', c.shape), BAR, rough=0.9, shadows=False)
    sh = 0.4 * gauss(np.maximum(0, np.hypot(c.X - 0.012, c.Y - 0.018) - 0.77), 0.02)
    col = col * (1 - sh)[..., None]
    col = mix(col, paper, c.cover(p)[..., None])
    col = mix(col, flat('#C8372D', c.shape), (0.9 * smooth(0.006, 0.002, np.abs(c.R - 0.725)))[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'board', exposure=0.95)
    # chopsticks, points to the left
    c = K.canvas(360, 3, 1.0, 0.20)
    for y0, y1, base in ((-0.10, -0.035), (0.10, 0.035),) and (((-0.115, -0.03), 0, 0), ((0.115, 0.03), 0, 0)):
        ya, yb = y0
        d = c.taper(0.97, ya, 0.048, -0.97, yb, 0.018)
        t = clamp((c.X + 1) / 2)
        yc = yb + (ya - yb) * t
        w = 0.018 + 0.030 * t
        u = clamp((c.Y - yc) / w, -1, 1)
        lac = mix(flat('#B5211B', c.shape), flat('#4A0D0A', c.shape), smooth(0.62, 0.64, t)[..., None])
        lac = mix(lac, flat('#E3B453', c.shape), (smooth(0.015, 0.008, np.abs(t - 0.63)) + smooth(0.010, 0.005, np.abs(t - 0.66)))[..., None] * 0.95)
        col = lac * (0.35 + 0.65 * np.sqrt(1 - u * u))[..., None] + (0.55 * gauss(u + 0.40, 0.16))[..., None] * 0.6
        c.put(np.zeros(3, F), (0.35 * gauss(np.maximum(0, c.taper(0.97, ya + 0.035, 0.048, -0.97, yb + 0.02, 0.018)), 0.03)).astype(F) * (c.alpha < 0.5))
        c.put(col, c.cover(d))
    K.put(c, 'sticks', how='png')
    ims = []
    for k, col in enumerate(('#FDFBF4', '#F5835A', '#2A4A30', '#7FB24A')):
        c = K.canvas(48, 4)
        d = c.box(0.70, 0.34, rot=0.5 + k, r=0.30) if k != 2 else c.box(0.66, 0.50, rot=0.3, r=0.06)
        H = 0.4 * np.sqrt(clamp(1 - (1 - clamp(-d / 0.34)) ** 2))
        c.put(surface(c, H, flat(col, c.shape), BAR, rough=0.4, clear=0.4, shadows=False), c.cover(d), H)
        ims.append(c.image())
    K.sheet(ims, 4, 'bitsheet')
    light(K, 'steam', 128, lambda q: 0.5 * np.power(1 - smooth(0.1, 0.98, q.R), 1.6) * clamp(0.6 + 0.5 * fbm(q.shape, 4, 3, 4)))


K.run([counter, belt, plates, middle])
K.sounds('wood')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#5A3820', accent='#C8372D', accent2='#3E8A57', text='#FBF3E2', border='#E3B97C', opacity=0.98, corner=8, font='Yu Gothic UI', open='spin', speed=1, hoverGrow=2,
               iconZoom=1.14, glow=0, tilt=0.4, pointer=False, burst=False, shadow=0.55, dim=0.26),
    wheel=dict(hub=92, thickness=96, gap=3, ringgap=14, rim=36, icon=42, crowd=1.48, area=1.40, hubkeep=0.60),
    colors=dict(ink='#33201A', red='#C8372D', cream='#FBF3E2'), fonts=dict(title='Yu Gothic UI Semibold, Segoe UI Semibold, Segoe UI'),
    back=[soft(1.08, 0.03, 60), img('counter', 1, intro=intro(0.28, 'out', scale=0.9))],
    ring=[dict(img('belt', 1), **{'in': 'px', 'size': '2*(ringout+5)'}, rotate='time*4-(1-open)*60'), dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringout+5', to=360, stroke='#8A8F96', width=2.4), dict(shape='circle', **{'in': 'px'}, size='2*(ringin-6)', fill='#C9975A', when='ring==0'),
          dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringin-5', to=360, stroke='#8A8F96', width=2.4)],
    slot=dict(intro=intro(0.50, 'out', 0.02, angle=-70, scale=1, opacity=0, stagger=0.014, order='ring'),
              under=[img('plates', '1.12*(1+0.05*hot-0.03*press)', frame='(i+ring)%4', rotate='time*4+i*20', detail=1.06)],
              icon=dict(size=1.0, zoom=1.16, y='-0.04*hot', shadow=dict(x=1, y=3, blur=4, color='black/50')),
              over=[img('steam', 1.2, y='-0.5-0.35*fract(time*0.5)', opacity='0.40*hot*(1-fract(time*0.5))'), img('steam', 0.9, x=0.15, y='-0.4-0.4*fract(time*0.5+0.5)', opacity='0.40*hot*(1-fract(time*0.5+0.5))')]
              + running('#C8372D', '#FFE0B0', 0.86, 0.16) + badge('#FBF3E2', 'ink', T, stroke='#C8372D') + groupmark('#33201A', -0.84, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.16, 0.05, 55, 0.80, **{'in': 'hub'})],
    hub=[img('board', 1.0, intro=intro(0.34, 'back', scale=0.4))] + words('ink', 'red', T, px=16.5, y=-0.04, box=(1.12, 0.46), subpx=11, suby=0.26, clockpx=29, clocky=-0.07, datey=0.21, datepx=11.5),
    front=[img('sticks', [0.34, 0.068], angle='sel', radius='0.80+0.03*sin(time*5)-0.05*launch', rotate='sel-90+2*sin(time*5)', pivot=[0, 0.5], opacity='on', intro=intro(0.2))],
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=24, text='ink', fill='#E3C79A/80', on='#C8372D'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#6B4527'], [1, '#452A16']]}, stroke={'type': 'linear', 'stops': [[0, '#EBC78E'], [1, '#B07C42']]}, width=5, corner=8, text='cream'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#FBF6E9'], [1, '#EADFC6']]}, stroke='#C8372D', width=1.8, corner=5, text='ink'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#FBF6E9'], [1, '#EADFC6']]}, stroke='#5A3820', width=2.4, corner=7, text='ink'),
    onlaunch=[dict(image='bitsheet', count=26, area='slot', life=[0.5, 0.9], size=[5, 10], speed=[120, 420], outward=True, dir=[-90, 90], gravity=700, drag=1.6, spin=[-300, 300], fadein=0, fadeout=0.3)])
