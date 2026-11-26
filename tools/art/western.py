"""Wild West: the wheel is a revolver's cylinder of blued steel, every app sits in a brass cartridge,
sheriff stars on the outer ring, a lasso round it all."""
from lineup import *

K = Kit('western', 'Wild West', 'A revolver cylinder of blued steel; apps sit in brass cartridges, sheriff stars ride the outer ring', ['western', 'metal', 'warm'])
K.flag(halo='light', puff='light')
BRASS = '#C8963E'


def cylinder():
    c = K.canvas(1080, 2)
    d = c.R - 0.95
    t = clamp(-d / 0.95)
    H = lens(t, 0.14, 3.0)
    n = 12
    a = (c.A % (TAU / n)) - TAU / n / 2
    w = c.R * np.abs(a)
    flute = smooth(0.075, 0.035, w) * smooth(0.50, 0.58, c.R) * smooth(0.93, 0.86, c.R)
    H = H - 0.05 * flute * np.sqrt(clamp(1 - (w / 0.075) ** 2))
    H = H + 0.02 * smooth(0.30, 0.26, c.R)
    g = fbm(c.shape, 5, 11, 4)
    blue = mix(flat('#3A4760', c.shape), flat('#66779A', c.shape), clamp(0.5 + 0.6 * g)[..., None])
    case = clamp(fbm(c.shape, 9, 12, 4) * 1.4)
    tint = mix(flat('#5A3E5E', c.shape), flat('#7A5A38', c.shape), clamp(0.5 + fbm(c.shape, 14, 13, 3))[..., None])
    blue = mix(blue, tint, (0.35 * case * smooth(0.75, 0.95, c.R))[..., None])
    col = metal(c, H, blue, rough=0.22, grime=0.45, seed=5, studio=WARM, scratch=220)
    c.put(col, c.cover(d), H)
    K.put(c, 'cylinder', exposure=1.3)


def rope():
    c = K.canvas(1180, 2)
    r0, half = 0.965, 0.03
    u = (c.R - r0) / half
    d = np.abs(c.R - r0) - half
    tw = np.sin(c.A * 110 + u * 2.4)
    H = 0.03 * np.sqrt(clamp(1 - u * u)) * (0.75 + 0.25 * tw)
    fib = fbm(c.shape, 160, 21, 2)
    alb = mix(flat('#7A5A30', c.shape), flat('#C9A66B', c.shape), clamp(0.5 + 0.4 * tw + 0.3 * fib)[..., None])
    col = surface(c, H, alb, WARM, rough=0.8, reach=0.05)
    c.put(col, c.cover(d), H)
    K.put(c, 'rope')


def slots():
    def one(c, k):
        if k == 0:  # a chamber with a brass cartridge in it
            d = c.R - 0.92
            rim = smooth(0.60, 0.64, c.R) * smooth(0.82, 0.78, c.R)
            H = 0.03 * smooth(0.92, 0.86, c.R) + 0.05 * rim - 0.02 * smooth(0.86, 0.82, c.R) * (1 - rim)
            alb = mix(flat('#12161C', c.shape), flat(BRASS, c.shape), rim[..., None])
            alb = mix(alb, flat('#2A2318', c.shape), smooth(0.62, 0.58, c.R)[..., None])
            alb = mix(alb, flat('#5A4020', c.shape), (0.35 * clamp(fbm(c.shape, 20, 3, 3)) * rim)[..., None])
            col = metal(c, H, alb, rough=0.28, grime=0.5, seed=7, studio=WARM, met=0.9)
        else:  # a sheriff's star
            d = c.star(6, 0.80, 0.46)
            for i in range(6):
                d = np.minimum(d, c.circle(0.11, *c.polar(i * TAU / 6, 0.82)))
            t = clamp(-d / 0.22)
            H = 0.09 * np.sqrt(t) - 0.008 * gauss(c.R - 0.42, 0.012)
            col = metal(c, H, flat('#D8AE52', c.shape), rough=0.24, grime=0.45, seed=9, studio=WARM)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'slots', 2, one)


def hub():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    H = lens(clamp(-d / 0.96), 0.10, 3) - 0.012 * gauss(c.R - 0.82, 0.01)
    alb = mix(flat('#1F2630', c.shape), flat('#3A4556', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 6, 3, 3))[..., None])
    H = H - 0.004 * gauss(c.star(5, 0.66, 0.27), 0.008)
    col = metal(c, H, alb, rough=0.3, grime=0.5, seed=4, studio=WARM, scratch=60)
    col = col * (1 - 0.3 * smooth(0.75, 0.2, c.R))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'hub')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFD38A')
    halo(K, 'puff', 160, 1.4, 0.0, tint='#B9B1A6')
    # a cartridge that points at the choice
    c = K.canvas(60, 4, 1.0, 2.4)
    case_ = c.box(0.62, 1.25, y=0.95, r=0.08)
    rim = c.box(0.72, 0.12, y=2.18, r=0.04)
    tip = c.taper(0, -0.35, 0.60, 0, -2.0, 0.16)
    H = 0.25 * np.sqrt(clamp(1 - (c.X / 0.7) ** 2))
    alb = np.where((tip < 0)[..., None], rgb('#8A8E94'), rgb(BRASS))
    col = metal(c, H, alb, rough=0.25, grime=0.3, seed=2, studio=WARM, met=0.9)
    c.put(col, c.cover(np.minimum(np.minimum(case_, rim), tip)), H)
    K.put(c, 'bullet', how='png')
    c = K.canvas(40, 4, 1.0, 2.0)  # an empty shell for the launch
    col = metal(c, 0.2 * np.sqrt(clamp(1 - (c.X / 0.7) ** 2)), flat(BRASS, c.shape), rough=0.3, grime=0.2, seed=3, studio=WARM, met=0.9)
    c.put(col, c.cover(c.box(0.6, 1.7, r=0.12)))
    K.put(c, 'shell', how='png')


K.run([cylinder, rope, slots, hub])
P = dict(base='#232933', accent=BRASS, accent2='#F0C878', text='#F4E6C6', sub='#D2BC8E', panel=('#3A3026', '#221B14'), stroke='#B8873A', tile=('#E9D3A8', '#CDAF78'), tilestroke='#6E4A22',
         ink='#2A1E12', dim=0.36, font='Rockwell, Georgia', badge=BRASS, badgeink='#221A10')
finish(K, P, sounds='western',
       back=[soft(1.14, 0.03, 65), img('rope', 1.09, rotate='(1-open)*40', intro=intro(0.4, 'out', scale=0.9)), img('cylinder', 1.0, rotate='(1-open)*-300', intro=intro(0.55, 'out', scale=0.86))],
       under=[img('halo', '1.6*hot', opacity='hot*0.7', when='hot>0.02'), img('slots', '1.0*(1+0.05*hot-0.05*press)', frame='ring>0 ? 1 : 0', rotate='ring>0 ? 8*sin(time*2+seed*6)*hot : 0')],
       icon=dict(size=0.62, zoom=1.16, shadow=dict(x=1, y=2, blur=3, color='black/60')),
       hub=[img('hub', 1.0, rotate='(1-open)*120', intro=intro(0.45, 'back', scale=0.6))],
       over=[img('bullet', [0.07, 0.168], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       style=dict(open='spin', speed=1.0, tilt=0.35),
       onlaunch=[dict(image='shell', count=3, area='slot', life=[0.7, 1.1], size=[6, 9], speed=[160, 300], outward=True, dir=[-40, 40], gravity=900, spin=[-720, 720], fadein=0, fadeout=0.3),
                 dict(image='puff', count=10, area='slot', life=[0.6, 1.2], size=[14, 26], grow=2.2, speed=[20, 80], outward=True, dir=[-60, 60], drag=2, opacity=0.5, fadein=0.1, fadeout=0.6)],
       onhover=[dict(color='#D8C29A', count=5, area='slot', life=[0.3, 0.7], size=[1, 2.5], speed=[20, 60], outward=True, dir=[-70, 70], gravity=80, fadein=0, fadeout=0.6)])
