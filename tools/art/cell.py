"""Living Cell: a view down a microscope; vesicles that breathe carry the apps, a nucleus in the middle,
pulses run outward."""
from lineup import *

K = Kit('cell', 'Living Cell', 'A view down a microscope: breathing vesicles carry the apps, a nucleus in the middle sends pulses outward', ['science', 'organic', 'calm'])
K.flag(halo='light', pulse='light')


def field():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = mix(flat('#CFEDE4', c.shape), flat('#8FCBBE', c.shape), smooth(0.3, 0.99, c.R)[..., None])
    col = col * (0.92 + 0.08 * fbm(c.shape, 5, 3, 4))[..., None]
    g = rng(5)
    org = np.zeros(c.shape, F)
    for _ in range(40):
        a, r = g.random() * TAU, g.uniform(0.15, 0.92)
        x, y = c.polar(a, r)
        rot = g.random() * 3
        cs, sn = math.cos(rot), math.sin(rot)
        u, v = (c.X - x) * cs + (c.Y - y) * sn, -(c.X - x) * sn + (c.Y - y) * cs
        e = np.hypot(u / g.uniform(0.03, 0.06), v / g.uniform(0.015, 0.03)) - 1
        org = np.maximum(org, gauss(e, 0.25) * 0.6 + smooth(0.0, -0.4, e) * 0.25)
    col = col - V([0.25, 0.10, 0.12]) * org[..., None]
    mem = gauss(c.R - 0.93 - 0.01 * np.sin(c.A * 7), 0.006)
    col = col - V([0.3, 0.15, 0.2]) * mem[..., None]
    vign = smooth(0.80, 0.99, c.R)
    col = col * (1 - 0.6 * vign)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'field')


def vesicles():
    tints = ['#7FD8C0', '#E09AC8', '#9AC0F0', '#E8D08A']
    def one(c, k):
        d = c.R - 0.84 - 0.03 * np.sin(c.A * 3 + k)
        mem = gauss(d, 0.03)
        inner = clamp(-d / 0.84)
        col = rgb(tints[k]) * (0.55 + 0.4 * inner)[..., None] * np.ones(c.shape + (3,), F) + V([1, 1, 1]) * (0.6 * mem)[..., None]
        a = clamp(0.35 + 0.4 * mem + 0.25 * smooth(0.0, 0.5, inner))
        c.col, c.alpha = col.astype(F), (a * c.cover(d - 0.03)).astype(F)
        return c
    plate(K, 'vesicles', 4, one)


def nucleus():
    c = K.canvas(460, 2)
    d = c.R - 0.95 - 0.02 * np.sin(c.A * 5)
    chrom = clamp(fbm(c.shape, 14, 4, 4) * 1.6 + 0.2)
    col = mix(flat('#8A4A9A', c.shape), flat('#4A1E5A', c.shape), chrom[..., None]) * (0.7 + 0.3 * smooth(0.95, 0.3, c.R))[..., None]
    col = col + V([1, 0.9, 1]) * (0.5 * gauss(d, 0.02))[..., None]
    col = col * (1 - 0.35 * smooth(0.6, 0.0, c.R))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'nucleus')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#E0FFF6')
    light(K, 'pulse', 320, lambda c: gauss(c.R - 0.85, 0.04), tint='#9AF0D8')
    c = K.canvas(40, 4)
    c.col[:] = rgb('#E09AC8')
    c.alpha = c.cover(c.R - 0.8) * 0.9
    K.put(c, 'dot', how='png', tone=False)


K.run([field, vesicles, nucleus])
P = dict(base='#0E2A2A', accent='#5FD0B0', accent2='#E07FB8', text='#FFFFFF', sub='#E8F4F0', panel=('#E8F6F2', '#C8E6DE'), stroke='#5FA090', tile=('#F4FBF8', '#D8EEE8'), tilestroke='#5FA090',
         ink='#0E2A2A', paneltext='#0E2A2A', dim=0.4, font='Segoe UI', badge='#E07FB8', badgeink='#FFFFFF')
breath = '(1+0.035*sin(time*2+seed*6))'
finish(K, P, sounds='drip',
       back=[soft(1.06, 0.02, 55), img('field', 1.0, intro=intro(0.5, 'out', scale=0.9)),
             img('pulse', '0.5+0.6*fract(time*0.35)', opacity='0.7*(1-fract(time*0.35))'), img('pulse', '0.5+0.6*fract(time*0.35+0.5)', opacity='0.7*(1-fract(time*0.35+0.5))')],
       under=[img('halo', '1.6*hot', opacity='hot*0.5', when='hot>0.02'), img('vesicles', '1.02*' + breath + '*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='time*6+seed*90')],
       icon=dict(size=0.62, zoom=1.16, shadow=dict(x=0, y=1, blur=3, color='#0E2A2A/40')),
       hub=[img('nucleus', '1.0*(1+0.02*sin(time*1.6))', intro=intro(0.5, 'back', scale=0.6))],
       over=[img('dot', '0.07*(1+0.2*sin(time*4))', **{'in': 'hub'}, angle='sel', radius=1.10, opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=1, blur=4, color='#2A0A30')),
       tabs=dict(inset=13, text='#0E2A2A', fill='#FFFFFF/40', on='#5FD0B0/85'),
       style=dict(open='bloom', speed=0.9, tilt=0.25),
       onlaunch=[dict(image='dot', count=20, area='slot', life=[0.6, 1.2], size=[3, 6], speed=[40, 180], outward=True, dir=[-100, 100], drag=1.6, swirl=60, fadein=0, fadeout=0.5)],
       screen=dict(effect='bubbles', color='#BFF0E4', color2='#FFFFFF', density=0.7, speed=0.6, size=1.0))
