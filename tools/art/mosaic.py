"""Mosaic: an antique floor of small stone tiles; the apps' tiles turn over to show glass and gold beneath."""
from lineup import *

K = Kit('mosaic', 'Mosaic', "An antique floor of small stone tiles; an app's tile turns over to show glass and gold beneath", ['ancient', 'warm', 'stone'])
K.flag(halo='light')
K.font('cinzel', 'Cinzel[wght].ttf')
STONES = ['#C8642A', '#E0B060', '#EDE0C8', '#5A6A72', '#8A3A22']


def tiles(c, size, seed, palette, rings=True):
    """Small square tiles laid in rings, as colour and a height field."""
    if rings:
        u = c.A / TAU * np.maximum(6, np.floor(c.R / size) * 6.28)
        v = c.R / size
    else:
        u, v = c.X / size, c.Y / size
    iu, iv = np.floor(u), np.floor(v)
    fu, fv = u - iu, v - iv
    gap = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    H = 0.01 * smooth(0.02, 0.12, gap)
    h = np.sin(iu * 12.9898 + iv * 78.233 + seed) * 43758.5453
    h = h - np.floor(h)
    idx = np.minimum((h * len(palette)).astype(int), len(palette) - 1)
    pal = np.array([rgb(p) for p in palette], F)
    col = pal[idx] * (0.85 + 0.2 * fbm(c.shape, 50, seed, 2))[..., None]
    col = mix(flat('#8A7E6A', c.shape), col, smooth(0.02, 0.08, gap)[..., None])
    return col, H


def floor():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col, H = tiles(c, 0.035, 3, STONES)
    band = smooth(0.88, 0.885, c.R)
    wave = smooth(0.0, 0.02, np.sin(c.A * 24 + (c.R - 0.93) * 60) * 0.03 - (c.R - 0.935) * 0.6)
    border = np.where((wave > 0.5)[..., None], rgb('#2A3A42'), rgb('#EDE0C8')) * np.ones(c.shape + (3,), F)
    col = mix(col, border * (0.9 + 0.1 * fbm(c.shape, 40, 5, 2))[..., None], band[..., None])
    out = surface(c, H, col, WARM, rough=0.7, reach=0.06)
    c.put(out, c.cover(d), H)
    K.put(c, 'floor')


def flips():
    def one(c, k):
        d = c.box(0.84, 0.84, r=0.05)
        if k == 0:
            col, H = tiles(c, 0.30, 11, ['#E0B060', '#C8642A', '#EDE0C8'], rings=False)
            out = surface(c, H + 0.03 * clamp(-d / 0.05), col, WARM, rough=0.7)
        else:
            col, H = tiles(c, 0.24, 13, ['#2A8AA8', '#1E6A8A', '#4AB0C8', '#D4AF5A'], rings=False)
            out = surface(c, H + 0.03 * clamp(-d / 0.05), col, COOL, rough=0.15, clear=1.0)
        c.put(out, c.cover(d), H)
        return c
    plate(K, 'flips', 2, one)


def rosette():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    col, H = tiles(c, 0.05, 21, ['#C8642A', '#E0B060', '#5A6A72', '#8A3A22'])
    centre = smooth(0.74, 0.72, c.R)
    cream = flat('#F2E8D4', c.shape) * (0.92 + 0.08 * fbm(c.shape, 30, 3, 2))[..., None]
    col = mix(col, cream, centre[..., None])
    col = col * (1 - 0.3 * gauss(c.R - 0.73, 0.01))[..., None]
    out = surface(c, H * (1 - centre), col, WARM, rough=0.7)
    c.put(out, c.cover(d), H)
    K.put(c, 'rosette')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE8C0')
    c = K.canvas(40, 4)
    dd = c.box(0.7, 0.7, r=0.05, rot=0.785)
    c.put(surface(c, 0.1 * clamp(-dd / 0.3), flat('#2A8AA8', c.shape), COOL, rough=0.15, clear=1.0), c.cover(dd))
    K.put(c, 'tessera', how='png')


K.run([floor, flips, rosette])
P = dict(base='#3A2A1E', accent='#C8642A', accent2='#2A8AA8', text='#2A1E14', sub='#5A4A3A', panel=('#F2E8D4', '#E0D2B8'), stroke='#8A3A22', tile=('#F2E8D4', '#E0D2B8'), tilestroke='#8A6A4A',
         ink='#2A1E14', paneltext='#2A1E14', dim=0.3, font=dict(file='Cinzel[wght].ttf', family='Cinzel'), badge='#8A3A22', badgeink='#F2E8D4')
flip = 'abs(cos(sat(hot)*3.14159))'
finish(K, P, sounds='stone',
       back=[soft(1.08, 0.03, 60), img('floor', 1.0, intro=intro(0.45, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), soft(0.92, 0.06, 40),
              img('flips', '0.96*(1+0.05*hot-0.03*press)', frame='hot>0.5 ? 1 : 0', rotate='a', scale=['max(0.04,' + flip + ')', '1'])],
       icon=dict(size=0.56, zoom=1.14, shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('rosette', 1.0, intro=intro(0.45, 'back', scale=0.7))],
       over=[img('tessera', [0.06, 0.06], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=16, clockpx=29, shadow=dict(x=0, y=0, blur=2, color='#F2E8D4')),
       tabs=dict(inset=13, text='#F2E8D4', fill='#00000033', on='#C8642A/85'),
       style=dict(open='bloom', speed=0.9, tilt=0.3),
       onlaunch=[dict(image='tessera', count=16, area='slot', life=[0.5, 0.9], size=[4, 8], speed=[100, 280], outward=True, dir=[-80, 80], gravity=700, spin=[-400, 400], fadein=0, fadeout=0.3)])
