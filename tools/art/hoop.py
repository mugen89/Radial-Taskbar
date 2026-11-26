"""Embroidery Hoop: linen stretched in a wooden hoop; apps sit in cross-stitched rings, a needle with thread
points at your choice."""
from lineup import *

K = Kit('hoop', 'Embroidery Hoop', 'Linen stretched in a wooden hoop; apps sit in cross-stitched rings while a threaded needle points', ['craft', 'light', 'cosy'])
K.flag(halo='light')
THREADS = ['#C8303A', '#2A5A8A', '#3A8A4A', '#D8A23A']


def linen(c, seed=2):
    wx = 0.5 + 0.5 * np.sin(c.X * 420)
    wy = 0.5 + 0.5 * np.sin(c.Y * 420)
    return flat('#EDE4D0', c.shape) * (0.90 + 0.06 * wx * wy + 0.04 * fbm(c.shape, 40, seed, 2))[..., None]


def crosses(c, r, n, size=0.035, upto=None, line=None):
    """Cross stitches along a circle, the first `upto` of them clockwise from the top; with `line`, thin printed lines
    of that width instead of thread."""
    cov = np.zeros(c.shape, F)
    for k in range(n if upto is None else upto):
        x, y = c.polar(k * TAU / n, r)
        for s in (1, -1):
            dd = c.capsule(x - size, y - size * s, x + size, y + size * s, 0)
            cov = np.maximum(cov, smooth(size * 0.34, size * 0.20, dd) if line is None else smooth(line, line * 0.5, dd))
    return clamp(cov)


def cloth():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = linen(c)
    sat = np.zeros(c.shape, F)
    for k in range(6):  # small flowers of satin stitch between the rings
        x, y = c.polar(k * TAU / 6 + 0.3, 0.42)
        for j in range(5):
            px, py = c.polar(j * TAU / 5, 0.035)
            sat = np.maximum(sat, c.cover(np.hypot(c.X - x - px, c.Y - y - py) - 0.025))
    col = mix(col, flat('#E8909A', c.shape), (0.8 * sat)[..., None])
    hoop = smooth(0.905, 0.91, c.R)
    wd, wh = wood(c, 4, scale=1.2, light='#D8B07A', dark='#9A7044', ring=5)
    H = (0.04 * np.sqrt(clamp(1 - ((c.R - 0.95) / 0.045) ** 2)) - 0.004 * gauss(c.R - 0.95, 0.004)) * hoop
    col = mix(col * (1 - 0.3 * gauss(c.R - 0.905, 0.015))[..., None], surface(c, H, wd, WARM, rough=0.5, reach=0.06), hoop[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'cloth')


STEPS = 6  # frames per thread colour: 6, 8, ... 16 of the 16 stitches done


def rings():
    """Work in progress: the transfer pattern is printed in blue and some of it is stitched; pointing at an app
    stitches the rest (frame = colour * STEPS + step)."""
    def one(c, k):
        colour, step = divmod(k, STEPS)
        d = c.R - 0.92
        col = linen(c, 10 + colour)
        pattern = crosses(c, 0.78, 16, 0.055, line=0.009)
        done = crosses(c, 0.78, 16, 0.055, upto=6 + 2 * step)
        col = mix(col, flat('#4A6ED8', c.shape), (0.8 * pattern)[..., None])
        col = mix(col, flat(THREADS[colour], c.shape) * (0.85 + 0.15 * fbm(c.shape, 60, 3, 2))[..., None], done[..., None])
        c.put(col, c.cover(d) * 0.97)
        return c
    plate(K, 'rings', 4 * STEPS, one, cols=STEPS)


def centre():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = linen(c, 30)
    back = np.abs(((c.A / TAU * 70) % 1) - 0.5) < 0.38
    stitch = gauss(c.R - 0.88, 0.012) * back
    col = mix(col, flat('#2A5A8A', c.shape), clamp(stitch * 1.2)[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'centre')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFF2D8')
    c = K.canvas(40, 4, 1.0, 2.0)
    nd = c.taper(0, 1.9, 0.10, 0, -1.9, 0.015)
    eye = c.capsule(0, 1.45, 0, 1.70, 0.035)
    thread = gauss(c.X - 0.25 * np.sin(c.Y * 2.5) - 0.05, 0.03) * smooth(1.4, 1.0, c.Y)
    c.put(flat('#C8303A', c.shape), clamp(thread))
    c.put(metal(c, 0.1 * clamp(-nd / 0.1), flat('#C8CCD2', c.shape), rough=0.2, grime=0.1, seed=2, studio=COOL), c.cover(np.maximum(nd, -eye)))
    K.put(c, 'needle', how='png')


K.run([cloth, rings, centre])
P = dict(base='#EDE4D0', accent='#C8303A', accent2='#2A5A8A', text='#3A2A1E', sub='#6A5A4A', panel=('#F4EEE0', '#E4D8C0'), stroke='#9A7044', tile=('#F4EEE0', '#E4D8C0'), tilestroke='#9A7044',
         ink='#3A2A1E', paneltext='#3A2A1E', dim=0.25, font='Gabriola, Constantia', badge='#C8303A', badgeink='#F4EEE0')
finish(K, P, sounds='paper',
       back=[soft(1.08, 0.03, 50), img('cloth', 1.0, intro=intro(0.45, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('rings', '1.0*(1+0.04*hot-0.03*press)', frame=f'((i+ring)%4)*{STEPS}+min({STEPS - 1},floor(hot*{STEPS}))', rotate='seed*360')],
       icon=dict(size=0.60, zoom=1.14, shadow=dict(x=0, y=1, blur=2, color='#3A2A1E/40')),
       hub=[img('centre', 1.0, intro=intro(0.45, 'back', scale=0.7))],
       over=[img('needle', [0.04, 0.08], **{'in': 'hub'}, angle='sel', radius=1.12, rotate='sel+10*sin(time*2)', opacity='on')],
       words_kw=dict(px=21, clockpx=36, datepx=15, shadow=dict(x=0, y=0, blur=2, color='#F4EEE0')),
       tabs=dict(inset=13, text='#3A2A1E', fill='#00000012', on='#C8303A/80'),
       style=dict(open='unfold', speed=0.9, tilt=0.25),
       onlaunch=[dict(color='#C8303A', count=12, area='slot', life=[0.4, 0.8], size=[1.2, 2.4], speed=[40, 160], outward=True, dir=[-90, 90], drag=2, stretch=3, fadein=0, fadeout=0.5)])
