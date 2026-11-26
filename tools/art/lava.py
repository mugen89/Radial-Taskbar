"""Lava: cracked black crust over glowing rock; apps rest on basalt stones veined with fire, embers rise outside."""
from lineup import *

K = Kit('lava', 'Lava', 'Cracked black crust over glowing rock; apps rest on basalt veined with fire while embers rise', ['fire', 'dark', 'hot'])
K.flag(halo='light', heat='light')


def heat(x):
    return np.stack([clamp(x * 2.2), clamp(x * 1.2 - 0.25), clamp(x * 0.9 - 0.6)], axis=-1).astype(F)


def crust():
    c = K.canvas(1080, 2)
    d = c.R - (0.98 + 0.012 * fbm(c.shape, 8, 2, 3))
    f1, f2, v = worley(c.X + 0.03 * fbm(c.shape, 6, 3, 3), c.Y, 7, 4, True)
    gap = f2 - f1
    crack = smooth(0.06, 0.0, gap)
    H = 0.05 * smooth(0.0, 0.15, gap) + 0.01 * fbm(c.shape, 40, 5, 3)
    rock = mix(flat('#14100E', c.shape), flat('#2E2420', c.shape), clamp(0.5 + 0.6 * fbm(c.shape, 30, 6, 3))[..., None])
    col = surface(c, H, rock, WARM, rough=0.8, reach=0.1)
    glow = crack * (0.7 + 0.3 * fbm(c.shape, 10, 7, 3))
    col = col * (1 - crack)[..., None] + heat(glow * 1.2) * 1.4
    col = col + heat(blur(glow, 6 * c.ss) * 0.6) * 0.5
    c.put(col, c.cover(d), H)
    K.put(c, 'crust')


def stones():
    def one(c, k):
        d = c.R - (0.82 + 0.05 * fbm(c.shape, 3, 10 + k, 3))
        t = clamp(-d / 0.5)
        H = 0.14 * np.sqrt(t) + 0.02 * fbm(c.shape, 20, 12 + k, 3)
        f1, f2, _ = worley(c.X, c.Y, 4, 20 + k, True)
        vein = smooth(0.05, 0.0, f2 - f1) * smooth(0.0, -0.15, d)
        col = surface(c, H, flat('#1E1814', c.shape), WARM, rough=0.6, reach=0.1)
        col = col * (1 - vein)[..., None] + heat(vein * (1.0 if k % 2 else 0.8)) * 1.5
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'stones', 4, one)


def core():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.78, 0.80, c.R)
    flow = clamp(0.5 + 0.5 * np.sin(c.A * 9 + c.R * 14 + 3 * fbm(c.shape, 5, 3, 3)))
    molten = heat(0.6 + 0.4 * flow) * 1.3
    col = mix(flat('#0E0A08', c.shape) * (0.8 + 0.4 * fbm(c.shape, 20, 4, 2))[..., None], molten, rimz[..., None])
    col = col + heat(gauss(c.R - 0.78, 0.03)) * 0.8
    c.put(col, c.cover(d))
    K.put(c, 'core')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FF8A3A')
    light(K, 'heat', 300, lambda c: (1 - smooth(0.0, 1.0, c.R)) ** 1.8, tint='#FF5A1A')
    c = K.canvas(40, 4, 1.0, 1.4)
    dd = c.poly([(0, -1.3), (0.8, 1.1), (-0.8, 1.1)])
    c.col[:] = rgb('#FFB04A')
    c.alpha = c.cover(dd)
    K.put(c, 'arrow', how='png', tone=False)


K.run([crust, stones, core])
P = dict(base='#140806', accent='#FF5A1A', accent2='#FFC24A', text='#FFE6C8', sub='#E8A878', panel=('#2A140C', '#140806'), stroke='#FF5A1A', tile=('#2E2420', '#1A1410'), tilestroke='#FF8A3A',
         ink='#FFE6C8', dim=0.55, font='Bahnschrift, Segoe UI', badge='#FFC24A', badgeink='#140806')
finish(K, P, sounds='stone',
       back=[soft(1.10, 0.03, 70), img('heat', 1.6, opacity='0.25+0.1*sin(time*1.3)'), img('crust', 1.0, intro=intro(0.45, 'out', scale=0.92))],
       under=[img('heat', '1.5*(1+0.1*sin(time*3+seed*6))', opacity='0.3+0.5*hot'), img('stones', '1.0*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*360')],
       icon=dict(size=0.56, zoom=1.16, shadow=dict(x=0, y=1, blur=4, color='#FF5A1A/50')),
       hub=[img('core', 1.0, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('arrow', [0.06, 0.084], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=1, blur=4, color='black/90')),
       style=dict(open='bloom', tilt=0.35),
       onlaunch=[dict(color='#FFB04A', count=30, area='slot', life=[0.5, 1.0], size=[1.5, 3.5], speed=[80, 300], outward=True, dir=[-80, 80], gravity=-150, drag=1.4, fadein=0, fadeout=0.5)],
       screen=dict(effect='embers', color='#FF5A1A', color2='#FFC24A', density=1.2, speed=1.0, size=1.0))
