"""Vault: a bank vault door of brushed steel with heavy bolts; apps sit on the bolt heads, the combination dial
turns to your choice."""
from lineup import *

K = Kit('vault', 'Vault', 'A vault door of brushed steel with heavy bolts; the combination dial in the middle turns to your choice', ['metal', 'heavy', 'cool'])
K.flag(halo='light')


def door():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    rings = 0.003 * np.sin(c.R * 400) + 0.03 * smooth(0.90, 0.91, c.R) - 0.01 * gauss(c.R - 0.60, 0.004) - 0.01 * gauss(c.R - 0.88, 0.004)
    H = rings + 0.02 * smooth(0.35, 0.34, c.R)
    tx, ty = -np.sin(c.A), np.cos(c.A)
    col = metal(c, H, flat('#A8AEB6', c.shape), rough=0.22, aniso=(tx, ty, V(0.4)), grime=0.5, seed=4, studio=COOL, scratch=150)
    bolts = np.zeros(c.shape, F)
    Hb = np.zeros(c.shape, F)
    for k in range(16):
        x, y = c.polar(k * TAU / 16, 0.955)
        q = np.hypot(c.X - x, c.Y - y)
        bolts = np.maximum(bolts, smooth(0.032, 0.028, q))
        Hb = np.maximum(Hb, 0.03 * np.sqrt(clamp(1 - (q / 0.03) ** 2)))
    bcol = metal(c, Hb, flat('#C8CED6', c.shape), rough=0.18, grime=0.3, seed=6, studio=COOL)
    col = mix(col, bcol, bolts[..., None])
    c.put(col, c.cover(d), H + Hb)
    K.put(c, 'door')


def bolts():
    def one(c, k):
        d = c.R - 0.88
        t = clamp(-d / 0.88)
        H = lens(t, 0.12, 3.0) - 0.02 * gauss(c.R - 0.70, 0.01)
        tx, ty = -np.sin(c.A), np.cos(c.A)
        col = metal(c, H, flat('#B8BEC6' if k == 0 else '#D8B860', c.shape), rough=0.2, aniso=(tx, ty, V(0.4)), grime=0.4, seed=10 + k, studio=COOL if k == 0 else WARM)
        col = mix(col, flat('#1A1C20', c.shape), smooth(0.66, 0.64, c.R)[..., None] * 0.6)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'bolts', 2, one)


def dial():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    rimz = smooth(0.84, 0.86, c.R)
    grip = (np.abs(((c.A / TAU * 90) % 1) - 0.5) < 0.25) * rimz
    H = 0.05 * rimz + 0.006 * grip
    face = flat('#16181C', c.shape) * (0.9 + 0.1 * fbm(c.shape, 30, 3, 2))[..., None]
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    f = load_font('segoeuib.ttf', 0.07 / c.px)
    for k in range(0, 100, 10):
        x, y = c.polar(k / 100 * TAU, 0.72)
        dr.text(((x + 1) * c.w / 2, (y + 1) * c.h / 2), str(k), font=f, fill=255, anchor='mm')
    nums = np.asarray(im, F) / 255
    ticks = (np.abs(((c.A / TAU * 100) % 1) - 0.5) > 0.46) * smooth(0.79, 0.80, c.R) * smooth(0.84, 0.83, c.R)
    face = mix(face, flat('#E8ECF0', c.shape), clamp(nums + ticks)[..., None])
    col = metal(c, H, flat('#B8BEC6', c.shape), rough=0.25, grime=0.4, seed=5, studio=COOL)
    col = mix(face, col, rimz[..., None])
    col = col * (1 - 0.25 * smooth(0.55, 0.1, c.R))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'dial')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE6A0')
    c = K.canvas(40, 4, 1.0, 1.4)
    d = c.poly([(0, 1.3), (0.7, -1.0), (-0.7, -1.0)])
    c.col[:] = rgb('#F2C84A')
    c.alpha = c.cover(d)
    K.put(c, 'notch', how='png', tone=False)


K.run([door, bolts, dial])
P = dict(base='#1E2228', accent='#C9CED6', accent2='#F2C84A', text='#F2F4F6', sub='#B8BEC6', panel=('#2E3238', '#1A1E22'), stroke='#8A9098', tile=('#E8ECF0', '#C8CED6'), tilestroke='#6A7078',
         ink='#1E2228', dim=0.42, font='Bahnschrift, Segoe UI', badge='#F2C84A', badgeink='#1E2228')
finish(K, P, sounds='vault',
       back=[soft(1.10, 0.03, 70), img('door', 1.0, intro=intro(0.45, 'out', scale=0.92))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('bolts', '1.0*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0', rotate='a')],
       icon=dict(size=0.58, zoom=1.16, shadow=dict(x=0, y=1, blur=2, color='black/60')),
       hub=[img('dial', 1.0, rotate='sel*0.6+(1-open)*-200', intro=intro(0.5, 'back', scale=0.6))],
       over=[img('notch', [0.05, 0.07], **{'in': 'hub'}, y=-1.04, opacity='0.9')],
       style=dict(open='spin', speed=0.85, tilt=0.3),
       onlaunch=[dict(color='#F2C84A', count=20, area='slot', life=[0.3, 0.7], size=[1.5, 3], speed=[120, 360], outward=True, dir=[-70, 70], gravity=700, stretch=2, fadein=0, fadeout=0.4)])
