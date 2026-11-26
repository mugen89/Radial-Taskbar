"""Porcelain: white glaze, cobalt painting, cracks mended with gold."""
from skinkit import *

K = Kit('porcelain', 'Porcelain', 'White glaze, cobalt painting, and cracks mended with gold', ['porcelain', 'elegant', 'light'])
K.flag(crackglow='light', halo='light')
GLAZE = Studio(lights=[((-0.42, -0.70, 0.60), 0.34, '#FFFFFF', 4.2), ((0.78, -0.30, 0.50), 0.20, '#DCE9FF', 2.2), ((0.10, 0.86, 0.45), 0.40, '#FFE8D2', 0.8)], sky='#F2F6FF', floor='#8C93A6', ambient=0.62)
COBALT, WASH = '#15348A', '#4E7FD6'


def cobalt(alb, cov, seed, deep=COBALT, wash=WASH):
    """Cobalt under glaze: uneven, darker where the brush rested."""
    n = fbm(cov.shape, 22, seed, 4) * 0.5 + 0.5
    col = mix(flat(deep, cov.shape), flat(wash, cov.shape), clamp(0.15 + 0.85 * n)[..., None])
    return mix(alb, col, (cov * (0.80 + 0.20 * n))[..., None])


def leaf(ink, x, y, a, s, v=255):
    ink.brush(turned(bez((0, 0), (0.25, -0.35), (0.10, -0.75), (0, -1.0), 14), a, s, x, y), s * 0.42, v)


def blossom(ink, x, y, s, petals=6, rot=0.0):
    for k in range(petals):
        a = rot + k * TAU / petals
        ink.poly(turned([(0, 0)] + bez((-0.30, -0.35), (-0.46, -0.85), (-0.12, -1.02), (0, -0.88), 8) + bez((0, -0.88), (0.12, -1.02), (0.46, -0.85), (0.30, -0.35), 8), a, s, x, y), 190)
        ink.line(turned([(0, -0.25), (0, -0.72)], a, s, x, y), s * 0.05, 255)
    ink.dot(x, y, s * 0.22, 255)


def cracks(seed=11):
    """Mended cracks: polylines from the rim inward, with a few branches."""
    g = rng(seed)
    out = []
    for a0 in (0.62, 2.35, 3.60, 5.30):
        pts, a, r = [], a0, 1.0
        while r > 0.40:
            pts.append((math.sin(a) * r, -math.cos(a) * r))
            if 0.5 < r < 0.85 and g.random() < 0.35:
                b, q, rr = [pts[-1]], a, r
                s = 1 if g.random() < 0.5 else -1
                for _ in range(int(3 + g.random() * 4)):
                    q += s * (0.05 + 0.06 * g.random())
                    rr += (g.random() - 0.62) * 0.05
                    b.append((math.sin(q) * rr, -math.cos(q) * rr))
                out.append((b, 0.0048))
            r -= 0.022 + 0.03 * g.random()
            a += (g.random() - 0.5) * 0.11
        out.append((pts, 0.0075))
    return out


def plate():
    c = K.canvas(1000, 2)
    H = lathe(c, [(0, 0.016), (0.42, 0.016), (0.46, 0.030), (0.50, 0.016), (0.84, 0.016), (0.905, 0.060), (0.965, 0.085), (0.988, 0.082), (1.0, 0.055)], 0.008)
    alb = flat('#F3F6FA', c.shape) * (1 + 0.012 * fbm(c.shape, 5, 3, 3))[..., None]
    ink = Ink(c)
    # lattice round the rim
    u = (c.A / TAU + 0.5) * 48
    f, v = np.abs((u % 1) - 0.5) * 2, (c.R - 0.900) / 0.078
    inband = (v > 0) & (v < 1)
    d = f + np.abs(v - 0.5) * 2
    lat = np.maximum(smooth(0.16, 0.08, np.abs(d - 0.86)), np.maximum(smooth(0.20, 0.12, d) * 1.0, smooth(0.10, 0.04, np.abs(d - 0.46)) * 0.75)) * inband
    for r, w in ((0.893, 0.0050), (0.984, 0.0045), (0.878, 0.0022)):
        lat = np.maximum(lat, smooth(w + 0.002, w, np.abs(c.R - r)))
    # scrolling vines, outside and inside the ring of dishes
    for r0, amp, n, s in ((0.835, 0.022, 24, 0.052), (0.515, 0.018, 16, 0.042)):
        pts = [(math.sin(a) * (r0 + amp * math.sin(a * n / 2)), -math.cos(a) * (r0 + amp * math.sin(a * n / 2))) for a in np.linspace(0, TAU, 900)]
        ink.line(pts, 0.0048, 235)
        for k in range(n):
            a = (k + 0.5) * TAU / n
            rr = r0 + amp * math.sin(a * n / 2)
            x, y = math.sin(a) * rr, -math.cos(a) * rr
            side = 1 if k % 2 else -1
            leaf(ink, x, y, a + side * 0.9 + (0 if side > 0 else math.pi), s, 215)
            leaf(ink, x, y, a - side * 0.5 + (math.pi if side > 0 else 0), s * 0.72, 175)
            if k % 4 == 0:
                blossom(ink, math.sin(a) * (r0 + 0.004), -math.cos(a) * (r0 + 0.004), s * 0.52, 6, a)
    alb = cobalt(alb, np.maximum(lat, ink.arr(0.0012)), 21)
    # gold: the rim and the mended cracks
    cr = Ink(c)
    for pts, w in cracks():
        cr.line(pts, w)
    crack = cr.arr(0.0011)
    gold = np.maximum(smooth(0.988, 0.991, c.R), crack)
    H = H + 0.006 * blur(crack, 0.002 / c.px)
    col = surface(c, H, alb, GLAZE, rough=0.35, clear=0.85)
    g = metal(c, H + 0.004 * blur(crack, 0.004 / c.px), GOLD, rough=0.22, grime=0.15, studio=WARM, strength=1.4)
    c.put(mix(col, g, gold[..., None]), c.cover(c.R - 0.998), H)
    K.put(c, 'plate', exposure=0.90)
    light(K, 'crackglow', 560, lambda q: _crackglow(q), '#FFCC66')


def _crackglow(q):
    ink = Ink(q)
    for pts, w in cracks():
        ink.line(pts, w * 1.4)
    a = ink.arr()
    return clamp(1.2 * blur(a, 0.004 / q.px) + 0.5 * blur(a, 0.014 / q.px)) * (q.R < 0.99)


def dish():
    c = K.canvas(300, 3)
    H = lathe(c, [(0, 0.02), (0.66, 0.02), (0.82, 0.10), (0.94, 0.16), (0.975, 0.16), (1.0, 0.10)], 0.02)
    alb = flat('#F6F8FB', c.shape)
    u = (c.A / TAU + 0.5) * 22
    f = np.abs((u % 1) - 0.5) * 2
    v = (c.R - 0.80) / 0.13
    pet = smooth(0.12, 0.0, np.hypot(f * 0.9, (v - 0.35) * 1.1) - 0.62) * (v > 0) * (v < 1)
    vein = smooth(0.16, 0.06, f) * (v > 0.1) * (v < 0.75)
    lines = np.maximum(smooth(0.012, 0.005, np.abs(c.R - 0.785)), smooth(0.009, 0.003, np.abs(c.R - 0.735)))
    alb = cobalt(alb, clamp(np.maximum(pet * 0.62, np.maximum(vein * 0.9, lines))), 5)
    col = surface(c, H, alb, GLAZE, rough=0.35, clear=0.9, reach=0.3)
    g = metal(c, H, GOLD, rough=0.2, grime=0.1, studio=WARM)
    c.put(mix(col, g, smooth(0.955, 0.965, c.R)[..., None]), c.cover(c.R - 0.985), H)
    K.put(c, 'dish', exposure=0.92)


def hub():
    c = K.canvas(460, 2)
    H = lathe(c, [(0, 0.03), (0.70, 0.03), (0.80, 0.055), (0.93, 0.12), (0.97, 0.125), (1.0, 0.07)], 0.014)
    alb = flat('#F7F9FC', c.shape)
    ink = Ink(c)
    n = 18
    for k in range(n):              # a border of pointed petals
        a = k * TAU / n
        ink.poly(turned([(0, -0.94)] + bez((0, -0.94), (0.115, -0.90), (0.105, -0.80), (0, -0.735), 10) + bez((0, -0.735), (-0.105, -0.80), (-0.115, -0.90), (0, -0.94), 10), a), 150)
        ink.line(turned(bez((0, -0.94), (0.115, -0.90), (0.105, -0.80), (0, -0.735), 12), a), 0.012, 255)
        ink.line(turned(bez((0, -0.94), (-0.115, -0.90), (-0.105, -0.80), (0, -0.735), 12), a), 0.012, 255)
        ink.dot(*turned([(0, -0.83)], a)[0], 0.016, 255)
    lines = np.maximum(smooth(0.010, 0.004, np.abs(c.R - 0.705)), smooth(0.007, 0.002, np.abs(c.R - 0.680)))
    alb = cobalt(alb, np.maximum(ink.arr(0.003), lines), 9)
    col = surface(c, H, alb, GLAZE, rough=0.35, clear=0.9, reach=0.25)
    g = metal(c, H, GOLD, rough=0.2, grime=0.1, studio=WARM)
    c.put(mix(col, g, smooth(0.962, 0.97, c.R)[..., None]), c.cover(c.R - 0.99), H)
    K.put(c, 'hub', exposure=0.92)


def bits():
    # cobalt spreading in water, under what is selected
    c = K.canvas(300, 2)
    n = fbm(c.shape, 5, 8, 5)
    d = c.R - 0.72 - 0.14 * n
    a = smooth(0.06, -0.10, d) * (0.45 + 0.55 * gauss(d + 0.03, 0.06)) * (0.8 + 0.2 * fbm(c.shape, 14, 4, 3))
    c.col = mix(flat(WASH, c.shape), flat(COBALT, c.shape), clamp(gauss(d + 0.02, 0.07))[..., None])
    c.alpha = clamp(a * 0.95).astype(F)
    K.put(c, 'wash', tone=False)
    # petals for the air
    ims = []
    for k in range(4):
        c = K.canvas(64, 4)
        a = k * 0.7 + 0.3
        pts = turned(bez((0, 0.9), (0.75, 0.4), (0.60, -0.6), (0, -0.9), 14) + bez((0, -0.9), (-0.5, -0.5), (-0.55, 0.4), (0, 0.9), 14), a, 0.92)
        cov = Ink(c).poly(pts).arr(0.02)
        t = clamp(0.5 + 0.5 * (c.X * math.sin(a) - c.Y * math.cos(a)))
        c.col = ramp(t, COBALT, WASH, '#DCE8FF')
        c.alpha = cov
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'petals')
    c = K.canvas(48, 4)
    H = dome(c.R, 0.9, 0.6)
    c.put(metal(c, H, GOLD, rough=0.15, grime=0), c.cover(c.R - 0.88), H)
    K.put(c, 'drop')
    halo(K, 'halo', 200, 2.4, 0.2, '#FFD27A')


K.run([plate, dish, hub, bits])
K.flag(petals=dict(cols=4))
K.sounds('glass')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#F4F7FB', accent='#2A57B8', accent2='#C9A24A', text='#17357F', border='#C9A24A', opacity=0.98, corner=12, font='Constantia', open='bloom', speed=1, hoverGrow=4,
               iconZoom=1.12, glow=0.2, tilt=0.4, pointer=False, burst=False, shadow=0.5, dim=0.26),
    wheel=dict(hub=94, thickness=90, gap=5, ringgap=30, rim=30, icon=44, crowd=1.45, area=1.14, hubkeep=0.68),
    colors=dict(ink='#17357F', cobalt='#2A57B8', gold='#C9A24A', white='#FFFFFF'),
    fonts=dict(title='Constantia, Cambria, Georgia'),
    ring=[soft(1.10, 0.025, 60), img('plate', 1, rotate='(1-open)*-30', intro=intro(0.36, 'out', scale=0.86)), img('crackglow', 1, opacity='0.08*wave(time*0.15)+0.30*on*(0.7+0.3*wave(time*0.9))+launch')],
    slot=dict(intro=intro(0.36, 'back', 0.05, scale=0.2, radius=-0.2, stagger=0.02, order='both'),
              under=[img('wash', '1.2+0.34*outcubic(sat(hot))', opacity='0.85*sat(hot)', rotate='i*47+time*4'), soft(1.14, 0.07, 46, 0.82), img('dish', '1.06*(1+0.05*hot-0.04*press+0.2*launch)', detail=1.06),
                     img('halo', 1.7, opacity='launch*2')],
              icon=dict(size=1.06, zoom=1.14, tone='duo', hot='original', ink='#14318A', paper='#FFFFFF'),
              over=[{'shape': 'arc', 'r': 0.985, 'from': 0, 'to': '360*sat(hot)', 'stroke': {'type': 'linear', 'stops': [[0, '#FFF0C0'], [0.5, '#C9942E'], [1, '#FFE3A0']]}, 'width': 2.6, 'when': 'hot>0.01', 'caps': True, 'glow': 4, 'glowcolor': '#FFCC66'}]
              + running('#C9A24A', '#FFF3CF', 0.90, 0.16) + badge('#17357F', 'white', T) + groupmark('#2A57B8', -0.86), marks=False, chevron=False, badge=False),
    over=[soft(1.20, 0.04, 55, 0.80, **{'in': 'hub'}), img('drop', 0.11, **{'in': 'hub'}, angle='sel', radius=1.06, opacity='on', scale='0.4+0.6*on')],
    hub=[img('hub', 1.0, intro=intro(0.34, 'back', scale=0.4, rotate=-40), rotate='sel*0.15')] + words('ink', 'cobalt', T, px=17, box=(1.16, 0.46), clockpx=29),
    draw=dict(clock=False, shadow=False, text='ink'), tabs=dict(inset=12, text='ink', fill='#C7D6F2/85', on='#2A57B8'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#FFFFFF'], [1, '#E9EFF8']]}, stroke={'type': 'linear', 'stops': [[0, '#F3D992'], [0.5, '#A87B22'], [1, '#E9C877']]}, width=2.4, corner=14, text='ink'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#FFFFFF'], [1, '#E9EFF8']]}, stroke='#B98A2E', width=1.6, corner=9, text='ink'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#FFFFFF'], [1, '#E3EBF7']]}, stroke='#2A57B8', width=2, corner=9, text='ink'),
    particles=[dict(image='petals', rate=0.8, max=7, area='stage', life=[3, 5], size=[6, 11], speed=[4, 12], dir=[130, 230], gravity=8, spin=[-60, 60], sway=18, swayhz=0.4, opacity=0.85, fadein=0.2, fadeout=0.4)],
    onlaunch=[dict(image='petals', count=30, area='slot', life=[0.5, 1.0], size=[7, 15], speed=[90, 380], outward=True, dir=[-90, 90], gravity=240, drag=2.2, spin=[-300, 300], fadein=0, fadeout=0.5),
              dict(color='#FFD27A', light=True, count=24, area='slot', life=[0.3, 0.7], size=[2, 4], speed=[120, 460], outward=True, dir=[-80, 80], gravity=300, drag=2.5, fadeout=0.6)],
    onhover=[dict(color='#E9C877', count=4, area='slot', life=[0.3, 0.5], size=[2, 3], speed=[30, 100], outward=True, dir=[-60, 60], drag=2, fadein=0, fadeout=0.6)])
