"""Chalkboard: a slate board in a wooden frame; apps sit in chalk circles, with doodles and a little dust."""
from lineup import *

K = Kit('chalk', 'Chalkboard', 'A slate board in a wooden frame; apps sit in hand-drawn chalk circles', ['school', 'handmade', 'dark'])
K.flag(halo='light', dust='light')
CH = ['#F4F1E6', '#F7E27A', '#F6A6C1', '#9FD3F2']


def chalk(c, d, w, seed, strength=1.4):
    """Chalk along a distance field: grainy and a little broken."""
    grain = clamp(0.45 + 0.7 * fbm(c.shape, 90, seed, 2) + 0.25 * white(c.shape, seed))
    return clamp(gauss(d, w) * strength) * grain


def board():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    slate = mix(flat('#1C2822', c.shape), flat('#27362E', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 5, 2, 4))[..., None])
    smear = clamp(fbm(c.shape, 3, 4, 3) * 1.4 - 0.1) * 0.08 + 0.05 * clamp(np.sin((c.X * 1.3 + c.Y) * 9 + 3 * fbm(c.shape, 4, 5, 2)) * 0.5 + 0.5) * clamp(fbm(c.shape, 5, 6, 3) + 0.2)
    col = slate + V([0.82, 0.84, 0.78]) * smear[..., None]
    col = col * (1 - 0.35 * gauss(c.R - 0.90, 0.02))[..., None]  # the frame's shadow on the slate
    ink = Ink(c)  # a few doodles near the frame
    for k, (x, y) in enumerate([(-0.62, -0.58), (0.66, 0.52), (0.60, -0.60), (-0.66, 0.55)]):
        ink.line(wob([(x - 0.08, y), (x + 0.08, y)], 0.004, 70 + k), 0.008, 140)
    doodle = ink.arr(0.004) * clamp(0.5 + fbm(c.shape, 80, 9, 2))
    col = col + V([0.9, 0.9, 0.85]) * (0.25 * doodle)[..., None]
    wd, wh = wood(c, 8, scale=2.0, light='#A0703E', dark='#4A2C16', ring=12, rot=0.0)
    frame = smooth(0.896, 0.904, c.R)
    Hf = (0.05 * np.sqrt(clamp(1 - ((c.R - 0.948) / 0.05) ** 2)) + 0.004 * wh) * frame
    fcol = surface(c, Hf, wd, WARM, rough=0.5, reach=0.08)
    col = mix(col, fcol, frame[..., None])
    c.put(col, c.cover(d), Hf)
    K.put(c, 'board')


def circles():
    def one(c, k):
        g = rng(40 + k)
        cov = np.zeros(c.shape, F)
        for loop in range(2):
            ph = g.random() * TAU
            rr = 0.80 + 0.03 * np.sin(c.A * 2 + ph) + 0.02 * np.sin(c.A * 3 + ph * 2) + 0.025 * loop
            cov = np.maximum(cov, chalk(c, c.R - rr, 0.022, 50 + k * 3 + loop) * (0.7 + 0.3 * loop))
        c.col[:] = rgb(CH[k])
        c.alpha = clamp(cov * 0.95)
        return c
    plate(K, 'circles', 4, one)


def hub():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    slate = mix(flat('#1E2A24', c.shape), flat('#25342C', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 4, 3, 3))[..., None])
    rr = 0.90 + 0.015 * np.sin(c.A * 3 + 1)
    ring1 = chalk(c, c.R - rr, 0.012, 3) + 0.7 * chalk(c, c.R - rr + 0.04, 0.008, 4)
    col = slate + V([0.95, 0.94, 0.88]) * clamp(ring1)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'hub')
    c = K.canvas(80, 3, 1.0, 1.6)  # a chalk arrow pointing outward
    ink = Ink(c)
    ink.line([(0, 1.3), (0, -1.2)], 0.16)
    ink.line([(-0.55, -0.55), (0, -1.25), (0.55, -0.55)], 0.16)
    c.col[:] = rgb('#F4F1E6')
    c.alpha = clamp(ink.arr(0.03) * clamp(0.5 + 0.8 * fbm(c.shape, 30, 3, 2)))
    K.put(c, 'arrow', how='png', tone=False)
    halo(K, 'halo', 200, 2.2, 0.3, tint='#F4F1E6')
    halo(K, 'dust', 64, 1.6, 0.0, tint='#F4F1E6')
    c = K.canvas(300, 2, 1.0, 0.16)  # the ledge with chalk and a sponge
    wd, wh = wood(c, 4, scale=1.5, light='#A0703E', dark='#4A2C16', ring=6, rot=1.57)
    led = c.box(0.98, 0.10, y=0.03, r=0.02)
    H = 0.06 * smooth(0.10, 0.0, np.abs(c.Y - 0.03))
    col = surface(c, H, wd, WARM, rough=0.5)
    c.put(col, c.cover(led), H)
    for x, colr in ((-0.45, '#F4F1E6'), (-0.25, '#F7E27A')):
        st = c.capsule(x - 0.08, -0.03, x + 0.08, -0.03, 0.025)
        c.put(surface(c, 0.04 * clamp(-st / 0.025), flat(colr, c.shape), SOFT, rough=0.9), c.cover(st), 0.08)
    sp = c.box(0.14, 0.06, x=0.45, y=-0.04, r=0.02)
    c.put(surface(c, 0.05 * clamp(-sp / 0.05), flat('#5E6B74', c.shape), SOFT, rough=0.9), c.cover(sp), 0.1)
    K.put(c, 'ledge', how='png')


K.run([board, circles, hub])
P = dict(base='#1E2A24', accent='#F4F1E6', accent2='#F7E27A', text='#F4F1E6', sub='#C9D6C8', panel=('#26342D', '#1A241F'), stroke='#8A6238', tile=('#2E3E35', '#1E2A24'), tilestroke='#A0703E',
         ink='#F4F1E6', paneltext='text', dim=0.32, font='Segoe Print, Ink Free', badge='#F7E27A', badgeink='#1E2A24')
finish(K, P, sounds='pencil',
       back=[soft(1.08, 0.03, 65), img('board', 1.0, intro=intro(0.35, 'out', scale=0.92)), img('ledge', [0.62, 0.0992], y=1.02, intro=intro(0.35, 'out', y=0.2, delay=0.05))],
       under=[img('halo', '1.5*hot', opacity='hot*0.35', when='hot>0.02'), img('circles', '1.05*(1+0.06*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*360+20*hot')],
       icon=dict(size=0.80, zoom=1.14, shadow=dict(x=1, y=2, blur=2, color='black/50')),
       hub=[img('hub', 1.0, intro=intro(0.35, 'back', scale=0.6))],
       over=[img('arrow', [0.10, 0.16], **{'in': 'hub'}, angle='sel', radius=1.14, rotate='sel', opacity='on')],
       words_kw=dict(px=18, clockpx=32, shadow=dict(x=0, y=0, blur=2, color='black/40')),
       style=dict(open='fade', tilt=0.25),
       onlaunch=[dict(image='dust', count=30, area='slot', life=[0.5, 1.2], size=[6, 14], grow=1.8, speed=[30, 160], outward=True, dir=[-120, 120], gravity=60, drag=2.4, opacity=0.6, fadein=0, fadeout=0.6)],
       onhover=[dict(image='dust', count=4, area='slot', life=[0.4, 0.8], size=[3, 6], speed=[10, 40], dir=[150, 210], gravity=40, opacity=0.5, fadein=0, fadeout=0.6)])
