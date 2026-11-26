"""Art Deco: black lacquer with brass sunbursts and stepped arcs; apps sit in brass octagons, tall elegant letters."""
from lineup import *

K = Kit('deco', 'Art Deco', 'Black lacquer with brass sunbursts and stepped arcs; apps sit in brass octagons', ['elegant', 'gold', 'dark'])
K.flag(halo='light')
BRASS = '#C9A050'


def lacquer():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    black = flat('#0C0C0E', c.shape) * (0.9 + 0.1 * smooth(1.0, 0.0, c.R))[..., None]
    rays = smooth(0.42, 0.48, np.abs(((c.A / TAU * 48) % 1) - 0.5)) * smooth(0.48, 0.50, c.R) * smooth(0.90, 0.88, c.R)
    steps = np.zeros(c.shape, F)
    for r in (0.50, 0.53, 0.56):
        steps = np.maximum(steps, gauss(c.R - r, 0.0025))
    for r in (0.88, 0.91):
        steps = np.maximum(steps, gauss(c.R - r, 0.003))
    rimz = smooth(0.93, 0.935, c.R)
    stepdots = (np.abs(((c.A / TAU * 96) % 1) - 0.5) < 0.2) * gauss(c.R - 0.965, 0.008)
    brass = clamp(0.35 * rays + steps + rimz + stepdots)
    H = 0.01 * brass + 0.03 * rimz * np.sqrt(clamp(1 - ((c.R - 0.965) / 0.03) ** 2))
    col = surface(c, H, black, SOFT, rough=0.08, clear=1.0, reach=0.05)
    col = mix(col, metal(c, H, flat(BRASS, c.shape), rough=0.22, grime=0.2, seed=4, studio=WARM), clamp(brass)[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'lacquer')


def octagons():
    def one(c, k):
        d = c.regular(8, 0.92, rot=TAU / 16)
        inner = c.regular(8, 0.72, rot=TAU / 16)
        frame = clamp(c.cover(d) - c.cover(inner))
        H = 0.05 * frame + 0.01 * gauss(c.regular(8, 0.62, rot=TAU / 16), 0.01)
        col = mix(flat('#141416', c.shape) if k == 0 else flat('#1E1A12', c.shape), flat(BRASS, c.shape), clamp(frame + 0.8 * gauss(inner + 0.1, 0.006))[..., None])
        col = surface(c, H, col, WARM, rough=0.2, metal=0.6, clear=0.6, reach=0.05)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'octagons', 2, one)


def sunburst():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    rays = smooth(0.40, 0.48, np.abs(((c.A / TAU * 36) % 1) - 0.5)) * smooth(0.70, 0.72, c.R)
    ring_ = smooth(0.70, 0.72, c.R)
    brass = clamp(rays + gauss(c.R - 0.71, 0.006) + gauss(c.R - 0.95, 0.008))
    H = 0.02 * brass + 0.02 * ring_
    col = surface(c, H, flat('#0E0E10', c.shape), SOFT, rough=0.08, clear=1.0)
    col = mix(col, metal(c, H, flat(BRASS, c.shape), rough=0.2, grime=0.2, seed=6, studio=WARM), brass[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'sunburst')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE0A0')
    c = K.canvas(40, 4, 1.0, 1.5)
    dd = c.poly([(0, -1.4), (0.7, 0.2), (0.25, 0.2), (0.25, 1.4), (-0.25, 1.4), (-0.25, 0.2), (-0.7, 0.2)])
    c.put(metal(c, 0.1 * clamp(-dd / 0.2), flat(BRASS, c.shape), rough=0.2, grime=0.1, seed=2, studio=WARM), c.cover(dd))
    K.put(c, 'spire', how='png')


K.run([lacquer, octagons, sunburst])
P = dict(base='#0C0C0E', accent=BRASS, accent2='#E8D8A8', text='#E8D8A8', sub='#B8A070', panel=('#1A1A1C', '#0C0C0E'), stroke=BRASS, tile=('#E8DCC0', '#C8B88A'), tilestroke='#8A6A2A',
         ink='#0C0C0E', dim=0.45, font='Bahnschrift Condensed, Bahnschrift', badge=BRASS, badgeink='#0C0C0E')
finish(K, P, sounds='jukebox',
       back=[soft(1.08, 0.03, 70), img('lacquer', 1.0, intro=intro(0.45, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('octagons', '1.0*(1+0.04*hot-0.03*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.56, zoom=1.14, shadow=dict(x=0, y=1, blur=3, color='black/60')),
       hub=[img('sunburst', 1.0, rotate='(1-open)*-45', intro=intro(0.5, 'back', scale=0.7))],
       over=[img('spire', [0.05, 0.075], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=19, clockpx=36, datepx=13),
       style=dict(open='unfold', speed=0.9, tilt=0.3),
       onlaunch=[dict(color='#E8D8A8', count=18, area='slot', life=[0.4, 0.8], size=[1.2, 2.6], speed=[60, 220], outward=True, dir=[-60, 60], drag=2, stretch=2, fadein=0, fadeout=0.5)])
