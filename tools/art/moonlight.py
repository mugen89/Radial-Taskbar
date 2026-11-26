"""Moonlight: a night sky with drifting clouds above a ring of trees; the apps sit on the moon's phases,
an owl blinks in the dark, fireflies hum."""
from lineup import *

K = Kit('moonlight', 'Moonlight', "A night sky over a ring of trees; apps sit on the moon's phases while an owl blinks in the dark", ['night', 'calm', 'blue'])
K.flag(halo='light', eyes='light')


def night():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    sky = mix(flat('#22346E', c.shape), flat('#0A1430', c.shape), smooth(0.0, 0.95, c.R)[..., None])
    sky = sky + V([0.9, 0.92, 1.0]) * stars(c, 140, 7, 0.0, 0.85, 0.003, 0.7)[..., None]
    cloud = clamp(fbm(c.shape, 3, 8, 5) * 1.6 - 0.15) * smooth(0.9, 0.4, c.R)
    sky = mix(sky, flat('#7A86B0', c.shape), (0.35 * cloud)[..., None])
    treeline = 0.80 + 0.06 * np.abs(np.sin(c.A * 22)) + 0.03 * np.abs(np.sin(c.A * 57 + 1)) + 0.02 * fbm(c.shape, 30, 9, 2)
    trees = smooth(treeline - 0.004, treeline + 0.004, c.R)
    col = mix(sky, flat('#050810', c.shape), trees[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'night')
    light(K, 'eyes', 120, lambda c: gauss(np.hypot(c.X + 0.3, c.Y), 0.12) + gauss(np.hypot(c.X - 0.3, c.Y), 0.12), tint='#FFD84A')


def phases():
    def one(c, k):
        d = c.R - 0.84
        z = np.sqrt(clamp(1 - (c.R / 0.84) ** 2))
        ph = k / 8 * TAU
        lit = clamp((c.X / 0.84 * math.sin(ph) + z * math.cos(ph) * -1) * -1 * 3 + 0.5) if k else np.zeros(c.shape, F) + 0.04
        craters = np.zeros(c.shape, F)
        g = rng(30)
        for _ in range(10):
            x, y, r = g.uniform(-0.6, 0.6), g.uniform(-0.6, 0.6), g.uniform(0.05, 0.14)
            craters = craters + 0.4 * smooth(r, r * 0.6, np.hypot(c.X - x, c.Y - y))
        alb = mix(flat('#F2ECD4', c.shape), flat('#C8C0A0', c.shape), clamp(0.4 * fbm(c.shape, 5, 4, 3) + 0.4 * craters)[..., None])
        dark = flat('#1A2040', c.shape)
        col = mix(dark, alb * (0.6 + 0.4 * z)[..., None], clamp(lit)[..., None])
        col = col + rgb('#3A4A80') * (0.25 * gauss(d, 0.03))[..., None]
        c.put(col, c.cover(d))
        return c
    plate(K, 'phases', 8, one)


def hub():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = mix(flat('#1A2A5A', c.shape), flat('#0A1230', c.shape), smooth(0.0, 0.95, c.R)[..., None])
    crescent = c.cover(c.R - 0.93) * (1 - c.cover(np.hypot(c.X - 0.06, c.Y + 0.03) - 0.92))
    col = col + V([0.95, 0.92, 0.8]) * (0.8 * crescent)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'hub')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#E8E2C8')
    c = K.canvas(40, 4)
    c.col[:] = rgb('#F2ECD4')
    c.alpha = c.cover(c.star(4, 0.95, 0.22))
    K.put(c, 'twinkle', how='png', tone=False)


K.run([night, phases, hub])
P = dict(base='#0A1430', accent='#E8E2C8', accent2='#9FB8E8', text='#F2EEDC', sub='#B8C4E0', panel=('#1A2A5A', '#0A1430'), stroke='#9FB8E8', tile=('#F2EEDC', '#D8D2BC'), tilestroke='#6A7AA8',
         ink='#0A1430', dim=0.5, font='Constantia, Georgia', badge='#E8E2C8', badgeink='#0A1430')
finish(K, P, sounds='drip',
       back=[soft(1.08, 0.03, 65), img('night', 1.0, intro=intro(0.5, 'out', scale=0.92)),
             img('eyes', 0.10, x=-0.62, y=0.64, opacity='0.9*step(0.05,fract(time*0.23))*sat(open)'), img('eyes', 0.08, x=0.70, y=0.52, opacity='0.8*step(0.04,fract(time*0.17+0.5))*sat(open)')],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('phases', '0.98*(1+0.05*hot-0.04*press)', frame='(i+ring)%8')],
       icon=dict(size=0.54, zoom=1.18, shadow=dict(x=0, y=1, blur=4, color='#0A1430/80')),
       hub=[img('hub', 1.0, intro=intro(0.5, 'back', scale=0.6))],
       over=[img('twinkle', '0.09*(1+0.2*sin(time*5))', **{'in': 'hub'}, angle='sel', radius=1.10, rotate='time*30', opacity='on')],
       style=dict(open='fade', speed=0.85, tilt=0.3),
       onlaunch=[dict(image='twinkle', count=16, area='slot', life=[0.5, 1.0], size=[5, 10], speed=[50, 200], outward=True, dir=[-100, 100], drag=1.5, spin=[-200, 200], fadein=0, fadeout=0.5)],
       screen=dict(effect='fireflies', color='#C8E070', color2='#FFF6B0', density=0.6, speed=0.5, size=0.8))
