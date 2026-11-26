"""Coffee: a glazed saucer, little cups of espresso, latte and cappuccino, steam over the big cup in the middle."""
from lineup import *

K = Kit('coffee', 'Coffee', 'A cosy cup in the middle, small cups of espresso, latte and cappuccino round it, and steam', ['cosy', 'warm', 'cafe'])
K.flag(halo='light')
CUP = '#F7F3EC'
DRINKS = [('#3A1F10', '#A0622E', None), ('#A8774A', '#E8D2B0', 'heart'), ('#E9DCC6', '#C9A27A', 'dust'), ('#4A2814', '#7A4422', 'swirl')]


def saucer():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    H = lathe(c, [(0, 0.0), (0.55, 0.0), (0.70, 0.02), (0.88, 0.06), (0.95, 0.07), (0.99, 0.04), (1.0, 0.0)], 0.01)
    glaze = mix(flat('#F3EBDD', c.shape), flat('#E6D8C2', c.shape), clamp(0.5 + 0.4 * fbm(c.shape, 4, 3, 3))[..., None])
    glaze = mix(glaze, flat('#7A4A28', c.shape), (0.85 * gauss(c.R - 0.915, 0.005) + 0.5 * gauss(c.R - 0.93, 0.002))[..., None])
    col = surface(c, H, glaze, WARM, rough=0.16, clear=1.0, reach=0.1)
    c.put(col, c.cover(d), H)
    K.put(c, 'saucer')


def cups():
    def one(c, k):
        base, crema, art = DRINKS[k]
        cup = c.circle(0.80)
        handle = c.capsule(0.62, 0.50, 0.86, 0.70, 0.07) - 0.0
        d = np.minimum(cup, handle)
        inner = 0.62
        lip = smooth(inner, inner + 0.02, c.R) * smooth(0.80, 0.78, c.R)
        H = 0.12 * np.sqrt(clamp(1 - ((c.R - 0.71) / 0.09) ** 2)) * lip + 0.08 * clamp(-handle / 0.07) * (cup > 0)
        alb = flat(CUP, c.shape)
        drink = mix(flat(base, c.shape), flat(crema, c.shape), smooth(0.30, inner, c.R)[..., None])
        drink = drink * (0.92 + 0.08 * fbm(c.shape, 40, 5 + k, 2))[..., None]
        if art == 'heart':
            pts = turned(bez((0, 0.30), (0.55, -0.05), (0.32, -0.55), (0, -0.25), 14) + bez((0, -0.25), (-0.32, -0.55), (-0.55, -0.05), (0, 0.30), 14), 0, 0.9)
            drink = mix(drink, flat('#F6EBDA', c.shape), Ink(c).poly(pts).arr(0.02)[..., None])
        elif art == 'dust':
            drink = mix(drink, flat('#6A3E1E', c.shape), (clamp(white(c.shape, 7 + k) - 1.6) * smooth(0.5, 0.1, c.R) * 0.8)[..., None])
        elif art == 'swirl':
            sp = [(math.sin(a) * 0.05 * a, -math.cos(a) * 0.05 * a) for a in np.linspace(0.5, 11, 80)]
            drink = mix(drink, flat('#C9A27A', c.shape), (Ink(c).line(sp, 0.035).arr(0.01) * 0.8)[..., None])
        alb = np.where((c.R < inner)[..., None], drink, alb)
        col = surface(c, H, alb, WARM, rough=0.2, clear=0.8, reach=0.1)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'cups', 4, one)


def bigcup():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    lip = smooth(0.80, 0.82, c.R)
    H = 0.10 * np.sqrt(clamp(1 - ((c.R - 0.895) / 0.075) ** 2)) * lip
    coffee = mix(flat('#2A170C', c.shape), flat('#5A3216', c.shape), smooth(0.2, 0.80, c.R)[..., None])
    foam = smooth(0.62, 0.78, c.R) * clamp(0.6 + 0.6 * fbm(c.shape, 30, 3, 3))
    coffee = mix(coffee, flat('#D9B98E', c.shape), (0.85 * foam)[..., None])
    pts = turned(bez((0, 0.30), (0.55, -0.05), (0.32, -0.55), (0, -0.25), 14) + bez((0, -0.25), (-0.32, -0.55), (-0.55, -0.05), (0, 0.30), 14), 0, 0.22)
    heart = Ink(c).poly([(x, y + 0.62) for x, y in pts]).arr(0.01)
    coffee = mix(coffee, flat('#F3E3CA', c.shape), heart[..., None])
    alb = np.where((c.R < 0.80)[..., None], coffee, flat(CUP, c.shape))
    col = surface(c, H, alb, WARM, rough=0.2, clear=0.8, reach=0.1)
    c.put(col, c.cover(d), H)
    K.put(c, 'bigcup')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE0B0')
    c = K.canvas(96, 2, 1.0, 1.6)  # a wisp of steam
    v = (1 - smooth(0.0, 1.0, np.hypot(c.X * 1.3 + 0.2 * np.sin(c.Y * 3), c.Y / 1.6))) ** 1.6
    c.col[:] = 1
    c.alpha = (v * 0.55).astype(F)
    K.put(c, 'steam', how='png', tone=False)
    c = K.canvas(48, 4, 1.0, 1.35)  # a coffee bean
    e = np.hypot(c.X / 0.8, c.Y / 1.05) - 1
    H = 0.25 * np.sqrt(clamp(-e)) - 0.06 * gauss(c.X - 0.12 * np.sin(c.Y * 2), 0.04)
    col = surface(c, H, flat('#4A2712', c.shape), WARM, rough=0.35, clear=0.6)
    c.put(col, c.cover(e * 0.8))
    K.put(c, 'bean', how='png')


K.run([saucer, cups, bigcup])
P = dict(base='#3B2416', accent='#C88A4A', accent2='#F2D6A8', text='#FFF4E2', sub='#EBD3AE', panel=('#5A3A24', '#3B2416'), stroke='#C88A4A', tile=('#F7EFE2', '#E8D9C2'), tilestroke='#B07A48',
         ink='#3B2416', dim=0.28, font='Constantia, Georgia', badge='#C88A4A', badgeink='#FFF4E2')
finish(K, P, sounds='cafe',
       back=[soft(1.10, 0.04, 55), img('saucer', 1.0, intro=intro(0.38, 'out', scale=0.9))],
       under=[img('halo', '1.5*hot', opacity='hot*0.6', when='hot>0.02'), soft(1.02, 0.08, 45), img('cups', '1.02*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*40-20')],
       icon=dict(size=0.56, zoom=1.18, shadow=dict(x=0, y=1, blur=2, color='black/45')),
       hub=[soft(1.02, 0.06, 50), img('bigcup', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('bean', [0.10, 0.135], **{'in': 'hub'}, angle='sel', radius=1.12, rotate='sel', opacity='on')],
       words_kw=dict(y=-0.10, suby=0.20, clocky=-0.12, datey=0.14),
       style=dict(open='bloom', tilt=0.3),
       particles=[dict(image='steam', rate=1.6, max=6, area='hub', life=[1.6, 2.6], size=[26, 44], grow=1.8, speed=[14, 28], dir=[-12, 12], sway=10, swayhz=0.5, opacity=0.35, fadein=0.3, fadeout=0.5)],
       onlaunch=[dict(image='bean', count=14, area='slot', life=[0.6, 1.0], size=[7, 11], speed=[120, 320], outward=True, dir=[-90, 90], gravity=700, spin=[-400, 400], fadein=0, fadeout=0.3)])
