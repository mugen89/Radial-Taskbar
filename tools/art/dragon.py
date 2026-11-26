"""Dragon Scale: overlapping metal scales that shimmer from green to bronze, a great scale for every app,
a dragon's eye in the middle, embers drifting up past it all."""
from lineup import *

K = Kit('dragon', 'Dragon Scale', 'Overlapping scales shimmer from green to bronze; a dragon eye watches from the middle while embers rise', ['fantasy', 'metal', 'dark'])
K.flag(halo='light')
K.font('cinzeldecorative', 'CinzelDecorative-Bold.ttf')


def hide():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    rows = 11
    v = c.R * rows
    row = np.floor(v)
    per = np.maximum(6, np.floor(row * 3.3 + 6))
    u = (c.A / TAU + 0.5) * per + 0.5 * (row % 2)
    fu, fv = u % 1 - 0.5, v % 1
    sd = np.hypot(fu * 1.05, (fv - 0.05) * 1.1) - 0.62
    t = clamp(-sd / 0.5)
    H = 0.03 * np.sqrt(t) + 0.004 * fbm(c.shape, 30, 3, 2)
    nx, ny, nz = normals(H, c.px)
    hue = clamp(0.5 + 0.5 * nx * 1.5 + 0.3 * fbm(c.shape, 4, 5, 3))
    alb = mix(flat('#1E5A3A', c.shape), flat('#8A6A2A', c.shape), hue[..., None])
    edge = gauss(sd, 0.03)
    alb = mix(alb, flat('#C9A040', c.shape), (0.5 * edge)[..., None])
    col = metal(c, H, alb, rough=0.3, grime=0.7, seed=6, studio=WARM, met=0.85)
    col = col * (1 - 0.5 * smooth(0.2, -0.3, sd))[..., None]
    col = col * (1 - 0.4 * smooth(0.85, 1.0, c.R))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'hide')


def scales():
    tones = ['#2E7A4E', '#9A7A34', '#8A2A1E', '#2A2A34']
    def one(c, k):
        d = np.maximum(c.circle(0.86, 0, -0.12), c.Y - 0.86 + 0.0 * c.X)
        d = np.minimum(d, c.poly([(-0.72, 0.30), (0.72, 0.30), (0, 0.95)]))
        t = clamp(-d / 0.5)
        ridge = gauss(c.X, 0.06) * smooth(-0.9, 0.6, c.Y)
        H = 0.10 * np.sqrt(t) + 0.03 * ridge
        alb = mix(flat(tones[k], c.shape), flat('#E0C060', c.shape), (0.35 * gauss(d, 0.05))[..., None])
        col = metal(c, H, alb, rough=0.25, grime=0.5, seed=12 + k, studio=WARM, met=0.85)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'scales', 4, one)


def eye():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.80, 0.82, c.R)
    H = 0.07 * np.sqrt(clamp(1 - ((c.R - 0.89) / 0.08) ** 2)) * rimz
    bronze = metal(c, H, flat('#8A6A2A', c.shape), rough=0.3, grime=0.6, seed=4, studio=WARM)
    streak = 0.5 + 0.5 * np.sin(c.A * 60 + 6 * fbm(c.shape, 6, 3, 2))
    iris = mix(flat('#3A1A04', c.shape), flat('#C8781A', c.shape), clamp(0.2 + 0.5 * smooth(0.1, 0.8, c.R) * streak)[..., None])
    slit = np.hypot(c.X / 0.10, c.Y / 0.74) - 1
    iris = mix(iris, flat('#0A0402', c.shape), c.cover(slit * 0.1)[..., None])
    iris = iris * (0.55 + 0.45 * smooth(0.82, 0.3, c.R))[..., None]
    col = mix(iris, bronze, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'eye')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFB050')
    c = K.canvas(48, 4, 1.0, 1.6)  # a claw that points at the choice
    cl = c.taper(0, 1.4, 0.45, 0.15, -1.45, 0.03)
    c.put(surface(c, 0.2 * clamp(-cl / 0.4), flat('#E8DCC0', c.shape), WARM, rough=0.35, clear=0.4), c.cover(cl))
    K.put(c, 'claw', how='png')


K.run([hide, scales, eye])
P = dict(base='#0E1A14', accent='#C9A040', accent2='#5FD08A', text='#F2E6C4', sub='#C9B88A', panel=('#1E2A22', '#0E1A14'), stroke='#C9A040', tile=('#E8DCC0', '#C9B88A'), tilestroke='#8A6A2A',
         ink='#0E1A14', dim=0.5, font=dict(file='CinzelDecorative-Bold.ttf', family='Cinzel Decorative'), badge='#C9A040', badgeink='#0E1A14')
finish(K, P, sounds='stone',
       back=[soft(1.10, 0.03, 70), img('hide', 1.0, rotate='(1-open)*-30', intro=intro(0.45, 'out', scale=0.9))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('scales', '1.02*(1+0.06*hot-0.04*press)', frame='(i+ring)%4', rotate='a')],
       icon=dict(size=0.60, zoom=1.18, shadow=dict(x=0, y=2, blur=3, color='black/65')),
       hub=[img('eye', 1.0, intro=intro(0.5, 'back', scale=0.6))],
       over=[img('claw', [0.07, 0.112], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=15, clockpx=28, shadow=dict(x=0, y=1, blur=4, color='black/90')),
       style=dict(open='bloom', tilt=0.4),
       onlaunch=[dict(color='#FF9A3A', count=30, area='slot', life=[0.5, 1.0], size=[1.5, 3.5], speed=[80, 300], outward=True, dir=[-80, 80], gravity=-120, drag=1.5, fadein=0, fadeout=0.5)],
       screen=dict(effect='embers', color='#FF6A1A', color2='#FFC24A', density=0.9, speed=0.9, size=1.0))
