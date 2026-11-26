"""Origami: folded patterned paper that opens like a flower, and cranes that fly off."""
from skinkit import *

K = Kit('origami', 'Origami', 'Folded patterned paper that opens like a flower; cranes fly off when you launch', ['paper', 'elegant', 'folded'])
K.flag(crane=dict(cols=2))
RED, INDIGO, GOLD_, CREAM = '#C8202F', '#20356E', '#D8A73A', '#F7EFDF'


def waves(u, v):
    """Overlapping circles."""
    out = np.zeros(u.shape, F)
    for row in range(2):
        x = (u + 0.5 * row) % 1 - 0.5
        y = (v * 2 + row) % 2
        r = np.hypot(x, (y - 1.0) * 0.5)
        ring = np.abs(((r * 6) % 1) - 0.5) * 2
        out = np.where((r < 0.5) & (y < 1.35), smooth(0.35, 0.65, ring), out)
    return out


def hemp(u, v):
    """Six-pointed leaves, lines only."""
    x, y = u, v * 1.1547
    d = np.full(u.shape, 9.0, F)
    for k in range(3):
        a = k * math.pi / 3
        p = x * math.cos(a) + y * math.sin(a)
        d = np.minimum(d, np.abs((p + 0.5) % 1 - 0.5))
        q = x * math.cos(a + math.pi / 6) + y * math.sin(a + math.pi / 6)
        d = np.minimum(d, np.abs((q * 1.1547 + 0.5) % 1 - 0.5))
    return smooth(0.060, 0.025, d)


def blossoms(u, v):
    out = np.zeros(u.shape, F)
    for ox, oy in ((0, 0), (0.5, 0.5)):
        x, y = (u + ox) % 1 - 0.5, (v + oy) % 1 - 0.5
        a, r = np.arctan2(x, -y), np.hypot(x, y)
        pet = r - 0.27 * (0.72 + 0.28 * np.abs(np.cos(a * 2.5)))
        out = np.maximum(out, smooth(0.015, -0.015, pet) * (1 - 0.6 * smooth(0.07, 0.05, r)))
    return out


def washi(c, base, ink, pattern, scale, rot=0.0):
    u = (c.X * math.cos(rot) + c.Y * math.sin(rot)) * scale
    v = (-c.X * math.sin(rot) + c.Y * math.cos(rot)) * scale
    return mix(flat(base, c.shape), flat(ink, c.shape), pattern(u, v)[..., None]) * (1 + 0.03 * fbm(c.shape, 180, 4, 2))[..., None]


def folded(c, n, outer, inner, base, ink, pattern, scale, phase=0.0, depth=0.055, pt=0.0):
    """A disc folded into n rays: ridge and valley in turn, so every facet catches the light differently."""
    a = (c.A + phase) * n / TAU
    k = np.abs((a % 1) - 0.5) * 2                     # 1 on the ridge, 0 in the valley
    edge = outer - (outer - inner) * (1 - k) ** 1.0
    d = (c.R - edge) * 0.8
    H = depth * k * smooth(0.05, 0.9, c.R / outer)
    alb = washi(c, base, ink, pattern, scale)
    side = np.where((a % 1) < 0.5, 1.0, -1.0)
    col = surface(c, H, alb, SOFT, rough=0.85, reach=0.10, slope=0.6, ao_r=(0.006, 0.02, 0.05))
    col = col * (1 + 0.16 * side * np.cos(c.A + 0.9))[..., None]
    crease = np.maximum(gauss((k - 1.0) * TAU * c.R / n / 2, 0.0035), gauss(k * TAU * c.R / n / 2, 0.0035))
    col = col * (1 - 0.18 * gauss(k * TAU * c.R / n / 2, 0.006))[..., None] + (0.10 * gauss((1 - k) * TAU * c.R / n / 2, 0.004))[..., None]
    col = mix(col, flat(CREAM, c.shape), (0.9 * smooth(-0.012, -0.004, d))[..., None])     # the paper's white edge
    return col, d, H


def discs():
    for name, args in (('star1', (16, 1.0, 0.885, INDIGO, '#4C66AE', waves, 7.0, 0.0)), ('star2', (16, 0.955, 0.86, RED, '#E86A5E', hemp, 6.5, math.pi / 16)), ('star3', (24, 0.90, 0.84, CREAM, '#E6D3A8', hemp, 9.0, 0.0))):
        c = K.canvas(1000, 2)
        col, d, H = folded(c, *args)
        c.put(col, c.cover(d), H)
        K.put(c, name, exposure=0.98, quality=87)


def square(name, base, ink, pattern, scale, fold):
    """A square of paper seen from above with its corners folded in."""
    c = K.canvas(260, 3)
    x, y = np.abs(c.X), np.abs(c.Y)
    d = np.maximum(x, y) - 0.70
    m = x + y
    if fold == 'in':                # corners meet in the middle
        H = 0.05 * np.abs(x - y) / 0.7 + 0.02
        lit = np.where(np.abs(c.X) > np.abs(c.Y), np.where(c.X > 0, -0.16, 0.10), np.where(c.Y > 0, -0.20, 0.18))
    else:                           # eight facets
        a = (c.A / TAU + 0.5) * 8
        H = 0.05 * np.abs((a % 1) - 0.5) * c.R
        lit = 0.16 * np.where((a % 1) < 0.5, 1, -1) * np.cos(c.A + 0.9)
    alb = washi(c, base, ink, pattern, scale, 0.2)
    col = surface(c, H, alb, SOFT, rough=0.85, reach=0.15) * (1 + lit)[..., None]
    crease = gauss(x - y, 0.010)
    col = col * (1 - 0.22 * crease)[..., None]
    col = mix(col, flat(CREAM, c.shape), (0.9 * smooth(-0.034, -0.018, d))[..., None])
    sh = 0.42 * gauss(np.maximum(0, np.maximum(np.abs(c.X - 0.03), np.abs(c.Y - 0.05)) - 0.69), 0.08)
    c.put(np.zeros(3, F), (sh * smooth(1.0, 0.93, np.maximum(x, y))).astype(F))
    c.put(col, c.cover(d), H)
    K.put(c, name)


def slots():
    square('sq1', '#F7EFDF', '#E6D3A8', hemp, 3.2, 'in')
    square('sq2', RED, '#E86A5E', blossoms, 2.4, 'eight')
    square('sq3', INDIGO, '#4C66AE', waves, 2.6, 'eight')
    square('sq4', GOLD_, '#F0CC74', hemp, 3.0, 'eight')


def hub():
    c = K.canvas(520, 2)
    col, d, H = folded(c, 12, 0.985, 0.90, GOLD_, '#F0CC74', hemp, 4.0, 0.0, depth=0.10)
    c.put(col, c.cover(d), H)
    K.put(c, 'rosette')
    c = K.canvas(420, 2)
    d = c.R - 0.97
    H = bevel(d, 0.02, 0.012) + 0.0012 * fbm(c.shape, 120, 3, 3)
    col = surface(c, H, flat('#FBF6EA', c.shape) * (1 + 0.02 * fbm(c.shape, 200, 5, 2))[..., None], SOFT, rough=0.9)
    ln = np.maximum(smooth(0.006, 0.002, np.abs(c.R - 0.90)), smooth(0.003, 0.001, np.abs(c.R - 0.865)))
    col = mix(col, flat(RED, c.shape), (0.9 * ln)[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'face')
    # a crane, wings up and wings down
    ims = []
    for f in range(2):
        c = K.canvas(150, 4)
        w = 0.0 if f == 0 else 0.52
        parts = [([(-0.95, -0.62 + w * 1.2), (-0.05, 0.00), (0.10, 0.34)], '#FFFFFF', 1.0), ([(0.80, -0.78 + w * 1.5), (-0.05, 0.00), (0.22, 0.34)], '#E9E2D2', 0.96), ([(-0.12, 0.02), (0.24, 0.02), (0.12, 0.42), (-0.02, 0.42)], '#D8CFBC', 0.9),
                 ([(0.10, 0.30), (0.20, 0.10), (0.92, -0.30), (0.86, -0.22)], '#F6F1E6', 1.0), ([(0.92, -0.30), (0.80, -0.26), (0.96, -0.08)], '#E04A4F', 1.0), ([(-0.02, 0.30), (-0.10, 0.10), (-0.98, 0.30), (-0.90, 0.38)], '#EDE6D6', 0.95)]
        for pts, col, k in parts:
            cov = Ink(c).poly(pts).arr(0.004)
            d = c.poly(pts)
            c.put(rgb(col) * (k - 0.25 * smooth(-0.06, 0.0, d))[..., None], cov)
        ims.append(c.image(tone=False))
    K.sheet(ims, 2, 'crane')
    c = K.canvas(110, 3, 1.0, 1.0)           # pointer: one folded triangle
    d = c.poly([(0, -0.95), (0.75, 0.80), (-0.75, 0.80)])
    col = np.where((c.X < 0)[..., None], rgb('#E04A4F'), rgb('#A8141F'))
    c.put(col * (1 - 0.1 * smooth(-0.1, 0, d))[..., None], c.cover(d))
    K.put(c, 'arrow', how='png', tone=False)


K.run([discs, slots, hub])
K.sounds('paper')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#FBF6EA', accent=RED, accent2=GOLD_, text='#20264A', border='#D8C49A', opacity=0.98, corner=4, font='Yu Gothic UI', open='unfold', speed=1, hoverGrow=3,
               iconZoom=1.12, glow=0, tilt=0.6, pointer=False, burst=False, shadow=0.5, dim=0.26),
    wheel=dict(hub=92, thickness=92, gap=5, ringgap=14, rim=36, icon=42, crowd=1.5, area=1.14, hubkeep=0.62),
    colors=dict(ink='#20264A', red=RED, cream=CREAM), fonts=dict(title='Yu Gothic UI Semibold, Segoe UI Semibold, Segoe UI'),
    back=[soft(1.10, 0.03, 55, 0.85), img('star1', 1.04, rotate='time*1.2', depth=-0.5, intro=intro(0.42, 'back', scale=0.15, rotate=110)), img('star2', 1.0, rotate='time*-1.6', depth=-0.25, intro=intro(0.42, 'back', 0.05, scale=0.15, rotate=-130)),
          img('star3', 1.0, rotate='0', intro=intro(0.40, 'back', 0.10, scale=0.15, rotate=80))],
    slot=dict(intro=intro(0.36, 'back', 0.12, scale=0.05, rotate=180, stagger=0.02, order='both'),
              under=[img('sq2', '1.30*(0.55+0.45*outback(sat(hot*1.2)))', rotate='45-45*sat(hot)+20*hot', opacity='sat(hot*4)', when='hot>0.01'), img('sq4', '1.30*(0.55+0.45*outback(sat(hot*1.2)))', rotate='45*sat(hot)+20*hot', opacity='sat(hot*4)', when='hot>0.01'),
                     img('sq3', 1.10, rotate='45', when='i%2==1', opacity='1-0.0*hot'), img('sq2', 1.10, rotate='45', when='i%2==0'), img('sq1', '1.06*(1+0.06*hot-0.05*press+launch*0.3)', rotate='8*hot', detail=1.08)],
              icon=dict(size=1.0, zoom=1.14, shadow=dict(x=1, y=3, blur=3, color='#20264A/45')),
              over=[dict(shape='poly', points=[[0, -0.12], [0.12, 0.10], [-0.12, 0.10]], closed=True, y=0.82, fill='red', when='running', opacity='active ? 1 : 0.75'), dict(shape='poly', points=[[0, -0.12], [0.0, 0.10], [-0.12, 0.10]], closed=True, y=0.82, fill='#FFD9A0', when='active')]
              + badge(INDIGO, 'cream', T, x=0.66, y=-0.66) + groupmark('ink', -0.80, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.24, 0.05, 50, 0.80, **{'in': 'hub'}), img('arrow', 0.17, **{'in': 'hub'}, angle='sel', radius=1.12, turns=True, opacity='on', scale='0.3+0.7*on')],
    hub=[img('rosette', 1.12, rotate='sel*0.4+time*2', intro=intro(0.42, 'back', 0.06, scale=0.1, rotate=-200)), soft(0.92, 0.03, 35, 0.86), img('face', 0.80, intro=intro(0.36, 'back', 0.12, scale=0.1))] + words('ink', 'red', T, px=16, y=-0.04, box=(1.10, 0.44), subpx=10.5, suby=0.25, clockpx=28, clocky=-0.07, datey=0.20, datepx=11),
    front=[img('crane', 0.10, angle='time*-16', radius='1.02+0.03*sin(time*1.7)', frame='floor(time*5)%2', scale=['-1', '1'], rotate='6*sin(time*2)', opacity='smooth(0.4,0.8,time)'), img('crane', 0.075, angle='time*-16+150', radius='1.06+0.02*sin(time*2.1)', frame='floor(time*6+1)%2', scale=['-1', '1'], rotate='6*sin(time*2+1)', opacity='smooth(0.5,0.9,time)')],
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=24, text='ink', fill='#E6D3A8/80', on=RED),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#FFFCF4'], [1, '#F0E5CC']]}, stroke=RED, width=2, corner=3, text='ink'), tag=dict(fill={'type': 'linear', 'stops': [[0, '#FFFCF4'], [1, '#F0E5CC']]}, stroke=RED, width=1.5, corner=2, text='ink'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#FFFCF4'], [1, '#F0E5CC']]}, stroke=INDIGO, width=2, corner=3, text='ink'),
    onlaunch=[dict(image='crane', count=9, area='slot', life=[0.9, 1.5], size=[16, 30], speed=[120, 300], dir=[-70, 70], gravity=-60, drag=0.6, sway=24, swayhz=1.2, fadein=0.05, fadeout=0.4)],
    onhover=[dict(color=GOLD_, count=3, area='slot', life=[0.3, 0.6], size=[1.5, 3], speed=[30, 90], outward=True, dir=[-70, 70], gravity=160, fadein=0, fadeout=0.6)])
