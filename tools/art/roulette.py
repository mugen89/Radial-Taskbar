"""Roulette: a walnut bowl, red and black pockets, and a ball that rolls to the choice."""
from skinkit import *

K = Kit('roulette', 'Roulette', 'Walnut, brass and felt; the ball rolls to your choice', ['casino', 'game', 'wood'])
K.flag(halo='light', ballglow='light')


def bowl():
    c = K.canvas(1100, 2)
    H = lathe(c, [(0, 0.0), (0.70, 0.0), (0.745, 0.012), (0.80, 0.030), (0.865, 0.066), (0.875, 0.084), (0.905, 0.092), (0.975, 0.098), (0.992, 0.090), (1.0, 0.060)], 0.004)
    tex, g = wood(c, 4, 1.6, '#8A4B22', '#2A1208', rot=0.2)
    # segments of the outer ring: the grain turns with the bowl
    n = 12
    k = np.floor((c.A / TAU + 0.5) * n)
    seam = np.abs(((c.A / TAU + 0.5) * n) % 1 - 0.5)
    rot = fbm(c.shape, 3, 8, 2)
    streak = circular_streaks(c, 6, 900) * 0.5 + 0.5 * fbm(c.shape, 30, 5, 3)
    ringcol = ramp(clamp(0.5 + 0.30 * streak + 0.10 * np.sin(k * 2.4) + 0.1 * rot), '#1F0C05', '#5A2810', '#A45C28')
    alb = np.where((c.R > 0.872)[..., None], ringcol, tex * 1.05)
    H = H - 0.0035 * smooth(0.496, 0.4995, seam) * (c.R > 0.905) * (c.R < 0.98)
    # brass inlays
    inlay = np.maximum(smooth(0.0035, 0.0015, np.abs(c.R - 0.905)), np.maximum(smooth(0.0030, 0.0012, np.abs(c.R - 0.975)), smooth(0.006, 0.003, np.abs(c.R - 0.755))))
    H = H + 0.003 * inlay
    col = surface(c, H, alb, WARM, rough=0.38, clear=0.75, reach=0.16, ao_r=(0.006, 0.02, 0.06))
    br = metal(c, H, BRASS, rough=0.2, grime=0.35)
    col = mix(col, br, inlay[..., None])
    c.put(col, c.cover(c.R - 0.998), H)
    # brass deflectors, upright and across in turn
    for i in range(8):
        a = (i + 0.5) * TAU / 8
        x, y = c.polar(a, 0.822)
        d = c.poly(turned([(0, -0.044), (0.015, 0), (0, 0.044), (-0.015, 0)], a + (math.pi / 2 if i % 2 else 0), 1, x, y))
        h = bevel(d, 0.014, 0.022, 'chamfer')
        hh = np.where(d < 0, c.H + h + 0.004, c.H)
        m = metal(c, hh, GOLD, rough=0.15, grime=0.2, reach=0.06)
        sh = gauss(np.maximum(0, c.poly(turned([(0, -0.044), (0.015, 0), (0, 0.044), (-0.015, 0)], a + (math.pi / 2 if i % 2 else 0), 1, x + 0.008, y + 0.012))), 0.012)
        c.shade_mul(1 - 0.5 * sh * (d > 0))
        c.put(m, c.cover(d), hh)
    K.put(c, 'bowl', exposure=0.95)


def rotor():
    """The turning disc below the pockets."""
    c = K.canvas(900, 2)
    H = lathe(c, [(0, 0.03), (0.50, 0.03), (0.56, 0.012), (0.95, 0.012), (0.965, 0.035), (0.99, 0.035), (1.0, 0.015)], 0.004)
    alb = flat('#17120F', c.shape) * (1 + 0.10 * circular_streaks(c, 3, 800))[..., None]
    col = surface(c, H, alb, WARM, rough=0.4, clear=0.3)
    rim = smooth(0.945, 0.952, c.R)
    col = mix(col, metal(c, H, BRASS, rough=0.22, grime=0.3, aniso=None), rim[..., None])
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'rotor', exposure=0.95)
    # a fret between two pockets
    c = K.canvas(40, 4, 1.0, 5.0)
    d = c.box(0.42, 4.8, r=0.42)
    H = bevel(d, 0.42, 0.40)
    c.put(metal(c, H, GOLD, rough=0.15, grime=0.15, reach=0.4), c.cover(d), H)
    K.put(c, 'fret', how='png')


def turret():
    c = K.canvas(620, 2)
    H = np.zeros(c.shape, F)
    d = np.full(c.shape, 9.0, F)
    for k in range(4):
        a = k * TAU / 4
        x, y = c.polar(a, 0.90)
        arm = c.taper(*c.polar(a, 0.45), 0.075, *c.polar(a, 0.86), 0.034)
        H = np.maximum(H, bevel(arm, 0.05, 0.055))
        r = np.hypot(c.X - x, c.Y - y)
        H = np.where(r < 0.085, np.maximum(H, dome(r, 0.088, 0.10)), H)
        c2 = c.ring(0.050, 0.013, *c.polar(a, 0.79))
        H = np.maximum(H, bevel(c2, 0.012, 0.07))
        d = np.minimum(d, np.minimum(arm, np.minimum(r - 0.085, c2)))
    body = lathe(c, [(0, 0.10), (0.55, 0.10), (0.60, 0.125), (0.66, 0.125), (0.69, 0.07), (0.74, 0.05), (0.76, 0.02), (0.78, 0)], 0.004)
    H = np.where(c.R < 0.77, np.maximum(H, body), H)
    d = np.minimum(d, c.R - 0.765)
    t = np.stack([-np.cos(c.A), np.sin(c.A)], 0)
    col = metal(c, H, GOLD, rough=0.18, grime=0.35, reach=0.2, aniso=(t[0], t[1], 0.35))
    c.put(col, c.cover(d), H)
    K.put(c, 'turret', exposure=0.95)
    # the felt cap in the middle
    c = K.canvas(400, 2)
    H = lathe(c, [(0, 0.05), (0.84, 0.05), (0.87, 0.07), (0.95, 0.075), (1.0, 0.03)], 0.006)
    felt = flat('#0D4B2E', c.shape) * (1 + 0.16 * fbm(c.shape, 160, 4, 2) + 0.10 * blur(white(c.shape, 7), 1.0))[..., None]
    col = surface(c, H + 0.0035 * fbm(c.shape, 220, 5, 2), felt, SOFT, rough=0.9, sheen=0.35)
    ink = Ink(c)
    for k in range(24):
        ink.line([turned([(0, -0.80)], k * TAU / 24)[0], turned([(0, -0.83 if k % 2 else -0.76)], k * TAU / 24)[0]], 0.008)
    ln = np.maximum(ink.arr(0.002), smooth(0.006, 0.002, np.abs(c.R - 0.715)))
    col = mix(col, flat('#D9B45C', c.shape), (0.75 * ln)[..., None])
    col = mix(col, metal(c, H, GOLD, rough=0.16, grime=0.2), smooth(0.855, 0.862, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'cap', exposure=0.95)


def bits():
    c = K.canvas(96, 4)
    H = dome(c.R, 0.92, 0.9)
    col = surface(c, H, flat('#F6F1E6', c.shape), SOFT, rough=0.2, clear=1.0, shadows=False)
    c.put(col, c.cover(c.R - 0.90), H)
    K.put(c, 'ball', how='png')
    ims = []
    for k in range(8):              # a spinning chip
        c = K.canvas(72, 3)
        w = abs(math.cos(k * math.pi / 8)) * 0.92 + 0.06
        x = c.X / w
        r = np.hypot(x, c.Y)
        sect = (np.floor((np.arctan2(x, -c.Y) / TAU + 0.5) * 12) % 2)
        alb = np.where(((r > 0.66) & (sect > 0))[..., None], rgb('#F4EEE0'), rgb('#B01820'))
        alb = np.where((r < 0.60)[..., None], rgb('#8E1018'), alb)
        alb = np.where(((r > 0.56) & (r < 0.61))[..., None], rgb('#E9C97A'), alb)
        k2 = 0.55 + 0.45 * clamp(0.6 - 0.4 * c.Y - 0.3 * c.X)
        c.put(alb * (k2 * (0.7 + 0.3 * abs(math.cos(k * math.pi / 8))))[..., None], c.cover((r - 0.92) * w))
        ims.append(c.image(tone=False))
    K.sheet(ims, 8, 'chip')
    halo(K, 'halo', 220, 2.0, 0.15, '#FFD27A')


K.run([bowl, rotor, turret, bits])
K.flag(chip=dict(cols=8))
K.sounds('casino')
T = 'title'
def pocket(c0, c1, when):
    return [{'shape': 'slot', 'inset': 1.2, 'fill': {'type': 'linear', 'from': [-0.5, -1], 'to': [0.5, 1], 'stops': [[0, c1], [1, c0]]}, 'when': when}]
K.write(
    style=dict(shape='wedge', material='solid', base='#1B0E08', accent='#FFCE6A', accent2='#B3141C', text='#FBEFD3', border='#C99A45', opacity=0.97, corner=5, font='Georgia', open='spin', speed=1.05, hoverGrow=3,
               iconZoom=1.12, glow=0.4, tilt=0.4, pointer=False, burst=False, shadow=0.7, dim=0.34),
    wheel=dict(hub=96, thickness=92, gap=5, ringgap=10, rim=62, icon=46, crowd=1.45, area=1.10, hubkeep=0.62, shadow=0.6),
    colors=dict(ivory='#FBF3E0', gold='#E9C97A', red='#B3141C'),
    fonts=dict(title='Georgia, Cambria'),
    back=[soft(1.08, 0.025, 72), img('bowl', 1, intro=intro(0.30, 'out', scale=0.85))],
    ring=[dict(img('rotor', 1), **{'in': 'px', 'size': '2*(ringout+9)'}, rotate='(1-open)*-200+time*1.2')],
    slot=dict(intro=intro(0.40, 'out', 0.03, angle=-120, scale=0.8, stagger=0.0, order='ring'),
              under=pocket('#5A060C', '#C2161F', '(n%2==0 && i%2==0) || (n%2==1 && i>0 && i%2==1)') + pocket('#050506', '#2C2C33', '(n%2==0 && i%2==1) || (n%2==1 && i>0 && i%2==0)') + pocket('#06331A', '#12803F', 'n%2==1 && i==0')
              + [{'shape': 'slot', 'inset': 1.2, 'fill': {'type': 'radial', 'from': [0, 0], 'radius': 1.1, 'stops': [[0, '#FFE7A6/55'], [1, '#FFE7A6/0']]}, 'opacity': 'hot+launch*2'},
                 {'shape': 'slot', 'inset': 1.2, 'stroke': {'type': 'linear', 'stops': [[0, '#FFE9B0'], [1, '#A8772A']]}, 'width': '1+1.6*hot', 'opacity': '0.5+0.5*hot'},
                 dict(text='{number}', radius=0.84, angle='a', turns=True, em=0.30, color='ivory', font=T, weight=700, opacity=0.85, when='!kid'), img('halo', 1.5, opacity='0.5*hot+launch')],
              icon=dict(size=0.96, zoom=1.14, shadow=dict(y=2, blur=3, color='black/65')),
              over=[dict(shape='circle', y=0.80, size=0.14, fill='#E9C97A', stroke='#6B4612', width=1, when='running'), dict(shape='circle', y=0.80, size=0.08, fill='#FFFFFF', when='active', glow=5, glowcolor='#FFD27A')] + groupmark('#E9C97A', -0.62, 0.12), marks=False, chevron=False, badge=False),
    over=[dict(img('fret', 1), **{'in': 'px', 'size': [10, 92]}, when='0'),
          soft(1.26, 0.04, 70, 0.78, **{'in': 'hub'}), dict(img('turret', 1.22), **{'in': 'hub'}, rotate='sel*0.6+time*8+(1-open)*-260', intro=intro(0.4, 'out', scale=0.6)),
          dict(shape='circle', **{'in': 'px'}, angle='sel', radius='radius-40', x=3, y=5, size=24, fill={'type': 'radial', 'stops': [[0, 'black/70'], [0.6, 'black/45'], [1, 'black/0']]}, opacity='on'),
          dict(img('ball', 21), **{'in': 'px'}, angle='sel', radius='radius-40-22*outbounce(sat(launch*2))+3*noise(time*14)*on', rotate='sel*6', opacity='on', scale='0.6+0.4*on')],
    hub=[img('cap', 0.80, intro=intro(0.34, 'back', scale=0.4))] + words('ivory', 'gold', T, px=16, y=-0.04, box=(0.98, 0.42), subpx=10, suby=0.24, clockpx=26, clocky=-0.07, datey=0.19, datepx=10.5),
    draw=dict(clock=False, shadow=False, text='ivory'), tabs=dict(inset=24, text='ivory', fill='#0D4B2E/90', on='#B3141C'),
    pinbutton={'in': 'hub', 'x': -0.17, 'y': 0.47, 'size': 10.5}, settingsbutton={'in': 'hub', 'x': 0.17, 'y': 0.47, 'size': 10.5},
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#12593A'], [1, '#0A3A24']]}, stroke={'type': 'linear', 'stops': [[0, '#F0C97A'], [0.5, '#8A6427'], [1, '#D9A95A']]}, width=3, corner=12, text='ivory'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#2E170C'], [1, '#180B05']]}, stroke='#C99A45', width=1.6, corner=9, text='ivory'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#FFFDF6'], [1, '#EFE7D4']]}, stroke='#B3141C', width=2, corner=9, text='#2A1208'),
    onlaunch=[dict(image='chip', count=16, area='slot', life=[0.5, 0.9], size=[12, 20], speed=[160, 460], outward=True, dir=[-70, 70], gravity=700, drag=1.6, spin=[-400, 400], fadein=0, fadeout=0.3),
              dict(color='#FFE7A6', light=True, count=22, area='slot', life=[0.25, 0.55], size=[2, 4], speed=[120, 420], outward=True, dir=[-80, 80], drag=2.5, fadeout=0.6)])
