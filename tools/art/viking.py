"""Viking Shield: a painted round shield of planks with an iron boss and a rawhide rim; small shields for the apps,
splinters fly on launch."""
from lineup import *

K = Kit('viking', 'Viking Shield', 'A painted round shield of planks with an iron boss and rawhide rim; apps sit on small shields', ['nordic', 'wood', 'warm'])
K.flag(halo='light')
K.font('medievalsharp', 'MedievalSharp.ttf')
PAINT = ['#B8322A', '#E8D8B4', '#2A4E7A', '#D8A23A']


def shield():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    wd, wh = wood(c, 3, scale=1.4, light='#B08050', dark='#5A3A20', ring=6, rot=1.57)
    planks = (np.abs(((c.X + 1) * 4.5) % 1 - 0.5) > 0.485)
    H = 0.004 * wh - 0.006 * planks
    seg = (np.floor((c.A / TAU + 0.5) * 8) % 2).astype(int)
    paint = np.where(seg[..., None] == 0, rgb(PAINT[0]), rgb(PAINT[1]))
    wear = clamp(fbm(c.shape, 10, 4, 4) * 1.6 + 0.35)
    alb = mix(wd, paint * np.ones(c.shape + (3,), F), (wear * smooth(0.90, 0.88, c.R))[..., None])
    rim = smooth(0.90, 0.91, c.R)
    stitch = (np.abs(((c.A / TAU) * 120) % 1 - 0.5) < 0.12) * gauss(c.R - 0.945, 0.006)
    Hr = 0.04 * np.sqrt(clamp(1 - ((c.R - 0.95) / 0.045) ** 2)) * rim - 0.006 * stitch
    alb = mix(alb, flat('#6A4A2A', c.shape) * (0.9 + 0.1 * fbm(c.shape, 30, 6, 2))[..., None], rim[..., None])
    col = surface(c, H + Hr, alb, WARM, rough=0.7, reach=0.1)
    nails = np.zeros(c.shape, F)
    for k in range(16):
        x, y = c.polar(k * TAU / 16, 0.86)
        nails = np.maximum(nails, smooth(0.022, 0.016, np.hypot(c.X - x, c.Y - y)))
    col = mix(col, metal(c, 0.02 * nails, flat('#4A4A50', c.shape), rough=0.4, grime=0.5, seed=3, studio=WARM), nails[..., None])
    c.put(col, c.cover(d), H + Hr)
    K.put(c, 'shield')


def bucklers():
    def one(c, k):
        d = c.R - 0.90
        wd, wh = wood(c, 7 + k, scale=1.0, light='#B08050', dark='#5A3A20', ring=4, rot=1.57)
        paint = rgb(PAINT[k]) * np.ones(c.shape + (3,), F)
        alb = mix(wd, paint, (clamp(fbm(c.shape, 8, 9 + k, 3) * 1.5 + 0.4) * smooth(0.80, 0.76, c.R))[..., None])
        rim = smooth(0.78, 0.80, c.R)
        H = 0.04 * np.sqrt(clamp(1 - ((c.R - 0.85) / 0.05) ** 2)) * rim + 0.003 * wh
        col = surface(c, H, mix(alb, flat('#3A3A40', c.shape), rim[..., None]), WARM, rough=0.6, reach=0.08)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'bucklers', 4, one)


def boss():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    t = clamp(-d / 0.96)
    H = lens(t, 0.22, 2.2)
    H = rivets(c, H, 8, 0.86, 0.04, 0.03)
    col = metal(c, H, flat('#3A3C42', c.shape), rough=0.35, grime=0.7, seed=5, studio=WARM, scratch=120)
    col = col * (1 - 0.35 * smooth(0.7, 0.1, c.R))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'boss')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFD8A0')
    c = K.canvas(40, 4, 1.0, 2.6)  # an arrowhead that points at the choice
    hd = np.minimum(c.poly([(0, -2.5), (0.6, -1.1), (0, -1.4), (-0.6, -1.1)]), c.box(0.12, 1.8, y=0.6))
    c.put(metal(c, 0.1 * clamp(-hd / 0.2), flat('#8A8C92', c.shape), rough=0.3, grime=0.4, seed=2, studio=WARM), c.cover(hd))
    K.put(c, 'arrowhead', how='png')
    c = K.canvas(32, 4, 1.0, 3.0)  # a splinter
    sp = c.taper(0, -2.6, 0.05, 0, 2.6, 0.35)
    c.put(flat('#B08050', c.shape), c.cover(sp))
    K.put(c, 'splinter', how='png')


K.run([shield, bucklers, boss])
P = dict(base='#2A1E16', accent='#B8322A', accent2='#E8D2A0', text='#F2E6CC', sub='#D2BC94', panel=('#4A3020', '#2A1E16'), stroke='#8A6A44', tile=('#E8D8B4', '#C8B48A'), tilestroke='#6A4A2A',
         ink='#2A1E16', dim=0.36, font=dict(file='MedievalSharp.ttf', family='MedievalSharp'), badge='#D8A23A', badgeink='#2A1E16')
finish(K, P, sounds='wood',
       back=[soft(1.10, 0.04, 65), img('shield', 1.0, rotate='(1-open)*-25', intro=intro(0.4, 'back', scale=0.85))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('bucklers', '0.98*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*360')],
       icon=dict(size=0.58, zoom=1.16, shadow=dict(x=1, y=2, blur=3, color='black/60')),
       hub=[img('boss', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('arrowhead', [0.06, 0.156], **{'in': 'hub'}, angle='sel', radius=1.14, rotate='sel', opacity='on')],
       words_kw=dict(px=18, clockpx=32, shadow=dict(x=0, y=1, blur=3, color='black/90')),
       style=dict(open='spin', tilt=0.35),
       onlaunch=[dict(image='splinter', count=16, area='slot', life=[0.5, 0.9], size=[6, 10], speed=[120, 340], outward=True, dir=[-80, 80], gravity=800, spin=[-500, 500], fadein=0, fadeout=0.3)])
