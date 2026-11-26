"""Frost: ice crystals grow in from the rim of a frozen disc; apps rest on clear ice, breath mist on launch, snow outside."""
from lineup import *

K = Kit('frost', 'Frost', 'Ice crystals grow in from the rim of a frozen disc; apps rest on clear ice while snow falls outside', ['winter', 'cool', 'calm'])
K.flag(halo='light', mist='light')


def ferns(c, seed, n, r0, r1, width):
    """Frost feathers that grow from radius r0 toward r1."""
    ink = Ink(c)
    g = rng(seed)
    for _ in range(n):
        a = g.random() * TAU
        dirn = 1 if r1 > r0 else -1
        L = abs(r1 - r0) * g.uniform(0.5, 1.0)
        pts = [c.polar(a + 0.06 * math.sin(t * 6 + a), r0 + dirn * L * t) for t in np.linspace(0, 1, 18)]
        ink.line(pts, width, 255)
        for t in np.linspace(0.1, 0.9, 7):
            x, y = c.polar(a, r0 + dirn * L * t)
            for side in (-1, 1):
                b = a + side * 0.9 * (1 - t * 0.4)
                l2 = L * 0.18 * (1 - t * 0.7)
                bx, by = math.sin(b) * l2 * -dirn * -1, -math.cos(b) * l2 * -dirn * -1
                ink.line([(x, y), (x + bx * 0.6 + math.sin(a) * l2 * dirn * 0.6, y + by * 0.6 - math.cos(a) * l2 * dirn * 0.6)], width * 0.6, 200)
    return ink.arr(width * 0.4)


def ice():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    deep = mix(flat('#1C4A6E', c.shape), flat('#0A2236', c.shape), smooth(0.0, 0.95, c.R)[..., None])
    w1, w2, _ = worley(c.X, c.Y, 6, 3, True)
    cracks = clamp(gauss(w2 - w1, 0.02) * 0.6)
    fern = ferns(c, 5, 60, 0.98, 0.45, 0.006)
    col = deep + V([0.85, 0.95, 1.0]) * (0.45 * fern + 0.25 * cracks)[..., None]
    col = col + V([0.6, 0.8, 1.0]) * (0.25 * smooth(0.85, 1.0, c.R))[..., None]
    gloss = smooth(0.1, 0.9, -(c.X * 0.55 + c.Y * 0.85)) * smooth(0.98, 0.6, c.R) * 0.06
    c.put(col + gloss[..., None], c.cover(d))
    K.put(c, 'ice')


def tiles():
    def one(c, k):
        d = c.regular(6, 0.88, rot=TAU / 12 * k)
        t = clamp(-d / 0.5)
        H = lens(t, 0.12, 2.5)
        nx, ny, nz = normals(H, c.px)
        body = mix(flat('#BFE6FF', c.shape), flat('#5FA8D8', c.shape), clamp(0.3 + 0.5 * c.Y)[..., None]) * 0.55
        frosty = smooth(0.4, 0.0, t) * clamp(0.6 + 0.5 * fbm(c.shape, 40, 3 + k, 2))
        spec = np.power(clamp(nx * -0.40 + ny * -0.66 + nz * 0.64), 50) * 1.2
        col = body + V([1, 1, 1]) * (0.5 * frosty + spec)[..., None]
        c.put(col, c.cover(d) * (0.78 + 0.2 * frosty))
        return c
    plate(K, 'tiles', 2, one)


def lake():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = mix(flat('#2A6A94', c.shape), flat('#0E3352', c.shape), smooth(0.0, 0.95, c.R)[..., None])
    flake = np.zeros(c.shape, F)
    for k in range(6):
        a = k * TAU / 6
        x, y = c.polar(a, 0.55)
        flake = np.maximum(flake, gauss(c.capsule(0, 0, x, y, 0), 0.006))
        for t in (0.25, 0.4):
            px, py = c.polar(a, 0.55 * t * 2)
            for s in (-0.6, 0.6):
                qx, qy = c.polar(a + s, 0.12)
                flake = np.maximum(flake, gauss(c.capsule(px, py, px + qx, py + qy, 0), 0.005))
    ring_ = gauss(c.R - 0.92, 0.006)
    col = col + V([0.9, 0.97, 1.0]) * (0.22 * flake + 0.8 * ring_)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'lake')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#CFF0FF')
    halo(K, 'mist', 120, 1.4, 0.0, tint='#EAF6FF')
    c = K.canvas(64, 4)  # a crystal that points at the choice
    d = c.poly([(0, -0.95), (0.35, -0.2), (0.22, 0.9), (-0.22, 0.9), (-0.35, -0.2)])
    c.put(mix(flat('#E8F8FF', c.shape), flat('#7FC4F0', c.shape), smooth(-0.1, 0.1, c.X)[..., None]), c.cover(d))
    K.put(c, 'crystal', how='png', tone=False)


K.run([ice, tiles, lake])
P = dict(base='#0E2236', accent='#9FD8FF', accent2='#FFFFFF', text='#F2FAFF', sub='#B8D8F0', panel=('#1C3A56', '#0E2236'), stroke='#9FD8FF', tile=('#EAF6FF', '#C8E4F6'), tilestroke='#7FB8E0',
         ink='#0E2236', dim=0.45, font='Candara, Segoe UI', badge='#9FD8FF', badgeink='#0E2236')
finish(K, P, sounds='glass',
       back=[soft(1.08, 0.03, 60), img('ice', 1.0, intro=intro(0.45, 'out', scale=0.9))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('tiles', '1.0*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0', rotate='a')],
       icon=dict(size=0.66, zoom=1.16, shadow=dict(x=0, y=1, blur=4, color='#0A2236/60')),
       hub=[img('lake', 1.0, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('crystal', [0.09, 0.09], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       style=dict(open='zoom', speed=0.9, tilt=0.3),
       onlaunch=[dict(image='mist', count=14, area='slot', life=[0.6, 1.3], size=[18, 34], grow=2, speed=[20, 90], outward=True, dir=[-60, 60], drag=1.5, opacity=0.45, fadein=0.1, fadeout=0.6),
                 dict(color='#FFFFFF', count=20, area='slot', life=[0.4, 0.9], size=[1.2, 2.6], speed=[60, 220], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.5)],
       screen=dict(effect='snow', color='#FFFFFF', color2='#CFE8FF', density=1.0, speed=0.8, size=1.0))
