"""Space Colony: a cut through an asteroid where a small colony lives; rock layers, tunnels and gas pockets,
round rooms with lights on, an airlock in the middle, oxygen bubbles rising."""
from lineup import *

K = Kit('colony', 'Space Colony', 'A cut through an asteroid with a colony inside: rock layers, tunnels, lit round rooms and an airlock', ['space', 'cosy', 'warm'])
K.flag(halo='light')


def rock():
    c = K.canvas(1080, 2)
    edge = 0.97 + 0.02 * fbm(c.shape, 6, 3, 3)
    d = c.R - edge
    w = c.R + 0.06 * fbm(c.shape, 3, 5, 4)
    bands = [(0.0, '#3A3A44'), (0.25, '#5A4A3A'), (0.45, '#7A6448'), (0.62, '#4A4A52'), (0.80, '#8A7254'), (0.92, '#5E5650')]
    alb = flat(bands[0][1], c.shape)
    for r, col in bands[1:]:
        alb = mix(alb, flat(col, c.shape), smooth(r - 0.02, r + 0.02, w)[..., None])
    grain = fbm(c.shape, 14, 6, 3)
    alb = alb * (0.90 + 0.12 * grain)[..., None]
    H = 0.015 * fbm(c.shape, 8, 7, 4) + 0.004 * grain
    tun = np.ones(c.shape, F)
    for r0, a0, a1, wdt in ((0.50, -1.2, 0.6, 0.035), (0.72, 1.4, 3.2, 0.03), (0.34, 2.4, 4.0, 0.03), (0.88, -2.6, -1.4, 0.025)):
        aa = ((c.A - a0) % TAU)
        inside = aa < ((a1 - a0) % TAU)
        tun = np.minimum(tun, np.where(inside, np.abs(c.R - r0) - wdt, 1))
    hole = c.cover(tun)
    H = H - 0.03 * hole
    alb = mix(alb, flat('#1A1410', c.shape), hole[..., None])
    gas = np.zeros(c.shape + (3,), F)
    g = rng(9)
    for colr in ('#7FE08A', '#E07FC8', '#7FD3E8', '#7FE08A'):
        x, y = c.polar(g.random() * TAU, g.uniform(0.3, 0.85))
        gas = gas + rgb(colr) * (0.35 * gauss(np.hypot(c.X - x, c.Y - y), 0.10))[..., None]
    col = surface(c, H, alb, WARM, rough=0.8, reach=0.1) + gas
    col = col + rgb('#FFD27A') * (0.9 * gauss(tun, 0.008))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'rock')


def rooms():
    lights = ['#FFE2A8', '#BDF2D0', '#FFD0E8', '#CDE8FF']
    def one(c, k):
        d = c.R - 0.90
        frame = smooth(0.66, 0.68, c.R)
        H = 0.08 * np.sqrt(clamp(1 - ((c.R - 0.79) / 0.11) ** 2)) * frame
        H = rivets(c, H, 10, 0.79, 0.035, 0.06)
        col = metal(c, H, flat('#8A929C', c.shape), rough=0.35, grime=0.6, seed=20 + k, studio=WARM)
        inside = rgb(lights[k]) * (0.55 + 0.6 * smooth(0.7, 0.0, np.hypot(c.X, c.Y + 0.25)))[..., None] * np.ones(c.shape + (3,), F)
        inside = inside * (0.85 + 0.15 * smooth(-0.6, 0.6, c.Y))[..., None]
        col = mix(inside, col, frame[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'rooms', 4, one)


def airlock():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    stripe = (np.floor((c.A / TAU * 40 + c.R * 6)) % 2)
    ring_ = smooth(0.78, 0.80, c.R)
    H = 0.07 * np.sqrt(clamp(1 - ((c.R - 0.885) / 0.09) ** 2)) * ring_
    alb = mix(flat('#22262C', c.shape), np.where(stripe[..., None] > 0.5, rgb('#F2B233'), rgb('#1C1C1C')) * np.ones(c.shape + (3,), F), ring_[..., None])
    col = metal(c, H, alb, rough=0.4, grime=0.6, seed=8, studio=WARM, met=0.4)
    glass = mix(flat('#1A2A36', c.shape), flat('#0A1218', c.shape), smooth(0.0, 0.78, c.R)[..., None])
    col = mix(glass + V([0.5, 0.9, 1.0]) * (0.08 * gauss(c.R - 0.70, 0.02))[..., None], col, ring_[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'airlock')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE2A8')
    c = K.canvas(56, 4, 1.0, 1.3)  # a way sign
    ar = c.poly([(0, -1.2), (0.85, -0.1), (0.35, -0.1), (0.35, 1.1), (-0.35, 1.1), (-0.35, -0.1), (-0.85, -0.1)])
    c.put(surface(c, 0.15 * clamp(-ar / 0.25), flat('#F2B233', c.shape), SOFT, rough=0.5), c.cover(ar))
    K.put(c, 'sign', how='png')
    c = K.canvas(40, 4)  # a pebble for the launch
    e = c.circle(0.8) + 0.12 * fbm(c.shape, 3, 4, 2)
    c.put(surface(c, 0.3 * clamp(-e / 0.8), flat('#7A6448', c.shape), WARM, rough=0.8), c.cover(e))
    K.put(c, 'pebble', how='png')


K.run([rock, rooms, airlock])
P = dict(base='#2A2420', accent='#F2B233', accent2='#7FD3E8', text='#F6F0E4', sub='#CFC2A8', panel=('#3A332C', '#221E1A'), stroke='#F2B233', tile=('#F2E6CC', '#D9C8A6'), tilestroke='#8A7254',
         ink='#2A2420', dim=0.4, font='Bahnschrift, Segoe UI', badge='#F2B233', badgeink='#2A2420')
finish(K, P, sounds='flask',
       back=[soft(1.10, 0.03, 65), img('rock', 1.0, rotate='(1-open)*20', intro=intro(0.4, 'out', scale=0.9))],
       under=[img('halo', '1.6*hot', opacity='hot*0.7', when='hot>0.02'), img('rooms', '1.0*(1+0.05*hot-0.04*press)', frame='(i+ring)%4')],
       icon=dict(size=0.64, zoom=1.16, shadow=dict(x=0, y=1, blur=2, color='black/45')),
       hub=[img('airlock', 1.0, rotate='(1-open)*90', intro=intro(0.4, 'back', scale=0.6))],
       over=[img('sign', [0.075, 0.0975], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       style=dict(open='unfold', tilt=0.3),
       onlaunch=[dict(image='pebble', count=10, area='slot', life=[0.5, 0.9], size=[4, 8], speed=[100, 260], outward=True, dir=[-80, 80], gravity=600, spin=[-300, 300], fadein=0, fadeout=0.3),
                 dict(color='#BDF2D0', count=14, area='slot', life=[0.6, 1.2], size=[2, 4], speed=[20, 80], dir=[-30, 30], gravity=-60, fadein=0, fadeout=0.5)],
       screen=dict(effect='bubbles', color='#9FE8D8', color2='#E0FFF6', density=0.8, speed=0.8, size=1.0))
