"""Digital Rain: green signs pour down the whole screen behind a dark glass terminal wheel."""
from lineup import *

K = Kit('rain', 'Digital Rain', 'Green signs pour down the screen behind a dark glass terminal wheel', ['code', 'terminal', 'dark'])
K.flag(halo='light', pulse='light')
G, PALE, CHARS = '#3DFF7A', '#D8FFE4', '0123456789ABCDEFHJKLMNPRSTUVXYZ+-*=<>:;|~^%$#@&?'


def signs(c, cols, rows, seed, r0=0.0, r1=1.0):
    """Faint columns of signs, bright at the foot of each trail, as coverage."""
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    cell = c.w / cols
    f = load_font('consolab.ttf', cell * 0.9)
    g = rng(seed)
    for i in range(cols):
        head, length = g.random() * rows * 1.3, 4 + g.random() * 14
        for j in range(rows):
            k = head - j
            if 0 <= k < length:
                v = (1 - k / length) ** 1.6
                x, y = (i + 0.5) * cell, (j + 0.5) * cell * c.h / c.w * cols / rows
                dr.text((x, y), CHARS[int(g.random() * len(CHARS))], font=f, fill=int(255 * v), anchor='mm')
    a = np.asarray(im, F) / 255
    return a * smooth(r1, r1 - 0.04, c.R) * smooth(r0, r0 + 0.04, c.R)


def disc():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    glass = mix(flat('#071A0E', c.shape), flat('#010603', c.shape), smooth(0.1, 0.95, c.R)[..., None])
    rain = signs(c, 44, 44, 7, 0.0, 0.94)
    col = glass + rgb(G) * (0.55 * rain)[..., None]
    rim = gauss(c.R - 0.972, 0.006) + 0.35 * gauss(c.R - 0.972, 0.025)
    inner = gauss(c.R - 0.62, 0.003) * 0.5
    col = col + rgb(G) * (1.6 * rim + inner)[..., None]
    gloss = smooth(0.2, 0.9, -(c.X * 0.55 + c.Y * 0.85)) * smooth(0.98, 0.70, c.R) * 0.05
    col = col + gloss[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'disc', exposure=1.0)


def tiles():
    def one(c, k):
        d = c.box(0.80, 0.80, r=0.16)
        lines = 0.5 + 0.5 * np.sin(c.Y * 90)
        body = mix(flat('#031008', c.shape), flat('#06200F', c.shape), (0.4 * lines)[..., None])
        edge = gauss(d + 0.012, 0.012) * (1.2 if k else 0.8)
        col = body + rgb(G) * edge[..., None] + rgb(G) * (0.10 * smooth(0.0, -0.5, d))[..., None]
        c.put(col, c.cover(d) * 0.94)
        return c
    plate(K, 'tiles', 2, one)


def hub():
    c = K.canvas(460, 2)
    d = c.R - 0.95
    col = mix(flat('#03140A', c.shape), flat('#000000', c.shape), smooth(0.0, 0.95, c.R)[..., None])
    a = c.A % (TAU / 60)
    ticks = (np.abs(a - TAU / 120) < 0.012) * smooth(0.86, 0.87, c.R) * smooth(0.92, 0.91, c.R)
    ring = gauss(c.R - 0.93, 0.008) + gauss(c.R - 0.84, 0.004) * 0.6
    col = col + rgb(G) * (1.2 * ring + 0.8 * ticks)[..., None] + rgb(G) * (0.25 * signs(c, 14, 14, 3, 0.0, 0.80))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'hub')
    halo(K, 'halo', 220, 2.0, 0.25, tint=G)
    light(K, 'pulse', 320, lambda c: gauss(c.R - 0.8, 0.05), tint=G)
    c = K.canvas(80, 3)  # the caret that points at the choice
    cov = c.cover(c.poly([(-0.6, -0.8), (0.75, 0.0), (-0.6, 0.8), (-0.25, 0.0)]))
    c.col[:] = rgb(G)
    c.alpha = cov
    K.put(c, 'caret', how='png', tone=False)


K.run([disc, tiles, hub])
P = dict(base='#020A05', accent=G, accent2=PALE, text=PALE, sub='#7DFFA6', panel=('#06180C', '#020803'), stroke=G, tile=('#0A2413', '#04120A'), tilestroke=G, ink=PALE, dim=0.86,
         font='Consolas', badge=G, badgeink='#021006')
finish(K, P, sounds='term',
       back=[soft(1.08, 0.02, 70), img('disc', 1, rotate='(1-open)*-25', intro=intro(0.30, 'out', scale=0.9)), img('pulse', '1.05+0.3*fract(time*0.4)', opacity='0.5*(1-fract(time*0.4))')],
       under=[img('halo', '1.7*hot', opacity='hot*0.9', when='hot>0.02'), img('tiles', '0.98*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.86, zoom=1.12, tone='original', shadow=dict(x=0, y=0, blur=6, color='#3DFF7A/45')),
       hub=[img('hub', 1.0, intro=intro(0.35, 'back', scale=0.6))],
       over=[img('caret', 0.16, **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel-90', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=6, color='#3DFF7A/70')),
       style=dict(shape='hex', open='zoom', speed=1.1, tilt=0.2),
       onlaunch=[dict(color=G, count=40, area='slot', life=[0.3, 0.8], size=[1.5, 3.5], speed=[80, 380], outward=True, dir=[-100, 100], drag=2.2, fadein=0, fadeout=0.6)],
       onhover=[dict(color=G, count=6, area='slot', life=[0.2, 0.5], size=[1, 2], speed=[20, 90], outward=True, dir=[-70, 70], drag=3, fadein=0, fadeout=0.7)],
       screen=dict(effect='rain', color=G, color2=PALE, density=1.0, speed=1.0, size=1.0))
