"""Vampire: crimson velvet under black wrought iron, garnets set in silver, a locket in the middle, bats over the night."""
from lineup import *

K = Kit('vampire', 'Vampire', 'Crimson velvet under black wrought iron; apps rest on garnets set in silver while bats cross the dark', ['gothic', 'dark', 'red'])
K.flag(halo='light')
K.font('cinzel', 'Cinzel[wght].ttf')
SILVER = '#C9CCD2'


def velvet():
    c = K.canvas(1080, 2)
    folds = fbm(c.shape, 3, 21, 3)
    nap = 0.5 + 0.5 * np.sin(c.A * 7 + folds * 4)
    col = mix(flat('#33050E', c.shape), flat('#7E0F20', c.shape), clamp(0.30 + 0.5 * nap * smooth(0.95, 0.25, c.R))[..., None])
    col = col * (0.85 + 0.25 * clamp(fbm(c.shape, 6, 22, 3) * 0.8 + 0.3))[..., None]
    # wrought iron round the edge, with points
    n = 28
    a = (c.A % (TAU / n)) - TAU / n / 2
    tip = 0.955 + 0.045 * clamp(1 - np.abs(a) / (TAU / n * 0.32))
    iron = np.minimum(np.abs(c.R - 0.925) - 0.022, np.maximum(c.R - tip, 0.94 - c.R))
    Hi = 0.05 * clamp(-iron / 0.02)
    icol = metal(c, Hi, flat('#1A1A20', c.shape), rough=0.45, grime=0.3, seed=4, studio=WARM)
    col = col * (1 - 0.5 * gauss(c.R - 0.90, 0.02))[..., None]
    c.put(col, c.cover(c.R - 0.94))
    c.put(icol, c.cover(iron), Hi)
    K.put(c, 'velvet')


def gems():
    tones = ['#7A0A1A', '#A8142C', '#4A0A3A', '#2A0C12']
    def one(c, k):
        prong = np.zeros(c.shape, F)
        for i in range(8):
            prong = np.maximum(prong, gauss(np.hypot(c.X - math.sin(i * TAU / 8) * 0.74, c.Y + math.cos(i * TAU / 8) * 0.74), 0.05))
        bez = smooth(0.70, 0.72, c.R) * smooth(0.88, 0.86, c.R)
        Hb = 0.06 * np.sqrt(clamp(1 - ((c.R - 0.79) / 0.09) ** 2)) * bez + 0.04 * prong
        silver = metal(c, Hb, flat(SILVER, c.shape), rough=0.25, grime=0.55, seed=10 + k, studio=COOL)
        c.put(silver, c.cover(c.R - 0.88), Hb)
        t = clamp(1 - c.R / 0.72)
        Hg = lens(t, 0.22, 2.0)
        nx, ny, nz = normals(Hg, c.px)
        b = rgb(tones[k])
        inner = clamp(0.5 + 0.6 * (c.Y * 0.8 + c.X * 0.3))
        body = b * (0.35 + 0.9 * inner)[..., None] + (b ** 0.6) * (0.5 * gauss(np.hypot(c.X - 0.12, c.Y - 0.25), 0.30))[..., None]
        spec = np.power(clamp(nx * -0.40 + ny * -0.66 + nz * 0.64), 80) * 1.4 + COOL.reflect(nx, ny, nz, 0.06).mean(axis=2) * 0.15 * np.power(clamp(1 - nz), 3)
        c.put(body + spec[..., None], c.cover(c.R - 0.72), Hg)
        return c
    plate(K, 'gems', 4, one)


def locket():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    rimz = smooth(0.80, 0.82, c.R)
    fil = 0.5 + 0.5 * np.sin(c.A * 24) * np.sin((c.R - 0.88) * 60)
    H = (0.07 * np.sqrt(clamp(1 - ((c.R - 0.895) / 0.08) ** 2)) + 0.012 * fil) * rimz
    silver = metal(c, H, flat(SILVER, c.shape), rough=0.28, grime=0.7, seed=6, studio=COOL)
    c.put(silver, c.cover(d), H)
    t = clamp(1 - c.R / 0.80)
    Hg = lens(t, 0.10, 2.0)
    nx, ny, nz = normals(Hg, c.px)
    body = rgb('#3A0610') * (0.6 + 0.7 * clamp(0.5 + 0.6 * c.Y))[..., None]
    spec = np.power(clamp(nx * -0.40 + ny * -0.66 + nz * 0.64), 60) * 0.9
    c.put(body + spec[..., None], c.cover(c.R - 0.80), Hg)
    K.put(c, 'locket')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FF4A5A')
    c = K.canvas(60, 4, 1.0, 1.5)  # a drop of red that points at the choice
    dd = np.minimum(c.circle(0.62, 0, 0.55), c.poly([(0, -1.45), (0.58, 0.30), (-0.58, 0.30)]))
    t = clamp(-dd / 0.6)
    Hd = 0.3 * np.sqrt(t)
    nx, ny, nz = normals(Hd, c.px)
    col = rgb('#8E0A1C') * (0.5 + 0.6 * clamp(0.5 + 0.5 * c.Y))[..., None] + np.power(clamp(nx * -0.4 + ny * -0.66 + nz * 0.64), 40)[..., None] * 1.2
    c.put(col, c.cover(dd), Hd)
    K.put(c, 'drop', how='png')


K.run([velvet, gems, locket])
P = dict(base='#1A0508', accent='#B3122A', accent2='#E6C9CC', text='#EFE0E2', sub='#C9A5AA', panel=('#2A0A10', '#140306'), stroke='#8C8F96', tile=('#3A0A14', '#22060C'), tilestroke='#8C8F96',
         ink='#EFE0E2', dim=0.55, font=dict(file='Cinzel[wght].ttf', family='Cinzel'), badge='#C9CCD2', badgeink='#1A0508')
finish(K, P, sounds='spooky',
       back=[soft(1.10, 0.03, 70), img('velvet', 1.0, intro=intro(0.42, 'out', scale=0.92))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('gems', '1.0*(1+0.05*hot-0.04*press)', frame='(i+ring)%4')],
       icon=dict(size=0.62, zoom=1.16, shadow=dict(x=0, y=2, blur=3, color='black/60')),
       hub=[img('locket', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('drop', [0.08, 0.12], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=16, clockpx=30, shadow=dict(x=0, y=1, blur=3, color='black/80')),
       style=dict(open='fade', speed=0.9, tilt=0.3),
       onlaunch=[dict(image='drop', count=12, area='slot', life=[0.6, 1.1], size=[5, 9], speed=[60, 200], outward=True, dir=[-60, 60], gravity=900, fadein=0, fadeout=0.3)],
       onhover=[dict(color='#B3122A', count=5, area='slot', life=[0.3, 0.7], size=[1.2, 2.6], speed=[20, 70], outward=True, dir=[-60, 60], gravity=120, fadein=0, fadeout=0.6)],
       screen=dict(effect='bats', color='#2A0A14', color2='#4A1020', density=1.2, speed=0.9, size=1.0))
