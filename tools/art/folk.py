"""Folk Pattern: red, black and white Balkan cross-stitch in bands and rosettes, inside a carved wooden frame."""
from lineup import *

K = Kit('folk', 'Folk Pattern', 'Red, black and white Balkan cross-stitch in bands and rosettes, inside a carved wooden frame', ['folk', 'red', 'craft'])
K.flag(halo='light')
RED, BLACK, WHITE = '#B8202A', '#1A1A1A', '#F4EEE2'


def stitchgrid(c, cell):
    """Cell coordinates and the cross that fills each cell."""
    gx, gy = c.X / cell, c.Y / cell
    ix, iy = np.floor(gx), np.floor(gy)
    fx, fy = gx - ix - 0.5, gy - iy - 0.5
    x = np.minimum(np.abs(fx - fy), np.abs(fx + fy)) / math.sqrt(2)
    return ix, iy, clamp(smooth(0.22, 0.10, x) * smooth(0.5, 0.4, np.maximum(np.abs(fx), np.abs(fy))))


def rosette(ix, iy, n):
    """An eight-pointed star of cross stitch, n cells from the middle: 0 none, 1 red, 2 black."""
    ax, ay = np.abs(ix), np.abs(iy)
    star = ((ax + ay) <= n) | ((ax <= n * 0.35) & (ay <= n)) | ((ay <= n * 0.35) & (ax <= n))
    inner = (ax + ay) <= n * 0.45
    return np.where(inner, 2, np.where(star, 1, 0))


def linen(c):
    wx = 0.5 + 0.5 * np.sin(c.X * 380)
    wy = 0.5 + 0.5 * np.sin(c.Y * 380)
    return flat(WHITE, c.shape) * (0.92 + 0.05 * wx * wy + 0.03 * fbm(c.shape, 40, 2, 2))[..., None]


def cloth():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = linen(c)
    cell = 0.016
    ix, iy, cross = stitchgrid(c, cell)
    rr = np.hypot(ix, iy) * cell
    ang = np.arctan2(ix, -iy)
    band1 = (np.abs(rr - 0.47) < cell * 2.5) & ((np.floor(ang / TAU * 48) + np.floor(rr / cell)) % 3 != 0)
    zig = (np.abs(rr - 0.47 - cell * 2.2 * np.abs(((ang / TAU * 24) % 1) * 2 - 1)) < cell * 0.8)
    band2 = (np.abs(rr - 0.86) < cell * 3) & ((np.floor(ang / TAU * 72) % 2 == 0) ^ (np.abs(rr - 0.86) < cell * 1.2))
    m = np.zeros(c.shape, np.int32)
    m = np.where(band1, 1, m)
    m = np.where(zig, 2, m)
    m = np.where(band2, 1, m)
    for k in range(8):  # rosettes between the bands
        x, y = c.polar(k * TAU / 8 + TAU / 16, 0.67)
        r = rosette(ix - round(x / cell), iy - round(y / cell), 6)
        m = np.where(r > 0, r, m)
    col = mix(col, flat(RED, c.shape), ((m == 1) * cross)[..., None])
    col = mix(col, flat(BLACK, c.shape), ((m == 2) * cross)[..., None])
    frame = smooth(0.92, 0.925, c.R)
    wd, wh = wood(c, 5, scale=1.3, light='#9A6A3A', dark='#4A2C16', ring=6)
    notch = gauss(np.abs(((c.A / TAU * 64) % 1) - 0.5), 0.08) * gauss(c.R - 0.96, 0.02)
    H = (0.04 * np.sqrt(clamp(1 - ((c.R - 0.958) / 0.035) ** 2)) - 0.012 * notch) * frame
    col = mix(col * (1 - 0.25 * gauss(c.R - 0.92, 0.012))[..., None], surface(c, H, wd, WARM, rough=0.55, reach=0.06), frame[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'cloth')


def rosettes():
    def one(c, k):
        d = c.R - 0.90
        col = linen(c)
        cell = 0.085
        ix, iy, cross = stitchgrid(c, cell)
        r = rosette(ix, iy, 8)
        ring_ = (np.abs(np.hypot(ix, iy) * cell - 0.80) < cell * 0.6)
        r = np.where(ring_, 2 if k == 0 else 1, r)
        r = np.where(np.hypot(ix, iy) * cell < 0.45, 0, r)
        col = mix(col, flat(RED, c.shape), ((r == 1) * cross)[..., None])
        col = mix(col, flat(BLACK, c.shape), ((r == 2) * cross)[..., None])
        c.put(col, c.cover(d))
        return c
    plate(K, 'rosettes', 2, one)


def centre():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = linen(c)
    cell = 0.04
    ix, iy, cross = stitchgrid(c, cell)
    rr = np.hypot(ix, iy) * cell
    ang = np.arctan2(ix, -iy)
    m = np.where((np.abs(rr - 0.86) < cell * 1.5) & (np.floor(ang / TAU * 40) % 2 == 0), 1, 0)
    m = np.where(np.abs(rr - 0.74) < cell * 0.6, 2, m)
    col = mix(col, flat(RED, c.shape), ((m == 1) * cross)[..., None])
    col = mix(col, flat(BLACK, c.shape), ((m == 2) * cross)[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'centre')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFF2E0')
    c = K.canvas(40, 4)
    cell = 0.25
    ix, iy, cross = stitchgrid(c, cell)
    r = rosette(ix, iy, 3)
    c.col = np.where((r == 2)[..., None], rgb(BLACK), rgb(RED)) * np.ones(c.shape + (3,), F)
    c.alpha = ((r > 0) * cross).astype(F)
    K.put(c, 'motif', how='png', tone=False)


K.run([cloth, rosettes, centre])
P = dict(base='#F4EEE2', accent=RED, accent2=BLACK, text='#1A1A1A', sub='#5A2A22', panel=('#F8F4EC', '#E8DECC'), stroke=RED, tile=('#F8F4EC', '#E8DECC'), tilestroke='#9A6A3A',
         ink='#1A1A1A', paneltext='#1A1A1A', dim=0.25, font='Constantia, Georgia', badge=RED, badgeink='#F8F4EC')
finish(K, P, sounds='wood',
       back=[soft(1.08, 0.03, 50), img('cloth', 1.0, intro=intro(0.45, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), soft(0.96, 0.05, 35), img('rosettes', '1.0*(1+0.04*hot-0.03*press)', frame='(i+ring)%2', rotate='hot*45')],
       icon=dict(size=0.48, zoom=1.16, shadow=dict(x=0, y=1, blur=2, color='#1A1A1A/35')),
       hub=[img('centre', 1.0, intro=intro(0.45, 'back', scale=0.7))],
       over=[img('motif', '0.08*(1+0.1*sin(time*4))', **{'in': 'hub'}, angle='sel', radius=1.10, opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=2, color='#F8F4EC')),
       tabs=dict(inset=13, text='#1A1A1A', fill='#00000010', on='#B8202A/85'),
       style=dict(open='unfold', speed=0.9, tilt=0.25),
       onlaunch=[dict(image='motif', count=14, area='slot', life=[0.5, 1.0], size=[5, 9], speed=[60, 220], outward=True, dir=[-90, 90], drag=1.8, spin=[-200, 200], fadein=0, fadeout=0.5)])
