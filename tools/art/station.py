"""Space Station: a hatch with a wide window; a planet turns slowly behind the apps, stars rush past outside."""
from lineup import *

K = Kit('station', 'Space Station', 'A hatch with a wide window: a planet turns slowly behind the apps while stars rush past', ['space', 'cool', 'clean'])
K.flag(halo='light')


def space():
    c = K.canvas(1080, 2)
    col = flat('#02040A', c.shape) + V([0.9, 0.95, 1.0]) * stars(c, 260, 5, 0.0, 0.99, 0.003, 0.8)[..., None]
    col = col + rgb('#3A4AA0') * (0.10 * clamp(fbm(c.shape, 3, 6, 4) + 0.2))[..., None]
    px, py, pr = 0.42, 0.40, 0.62
    X, Y = (c.X - px) / pr, (c.Y - py) / pr
    R = np.hypot(X, Y)
    z = np.sqrt(clamp(1 - R * R))
    land = fbm(c.shape, 6, 7, 5)
    sea = clamp(land * 2.2 + 0.1)
    alb = mix(flat('#123E7A', c.shape), mix(flat('#3E7A3A', c.shape), flat('#C8B47A', c.shape), clamp(land * 3 - 0.3)[..., None]), sea[..., None])
    clouds = clamp(fbm(c.shape, 10, 8, 4) * 2.0 - 0.1) * 0.8
    lit = clamp(z * 0.9 + 0.35 * (-X - Y))
    pl = alb * (0.2 + 0.9 * lit)[..., None] + V([1, 1, 1]) * (clouds * lit)[..., None] + rgb('#6AB0FF') * (0.6 * np.power(clamp(1 - z), 3))[..., None]
    col = mix(col, pl, c.cover((R - 1) * pr)[..., None])
    col = col + rgb('#6AB0FF') * (0.35 * gauss((R - 1) * pr, 0.02))[..., None]
    c.put(col, c.cover(c.R - 0.90))
    K.put(c, 'space')


def frame():
    c = K.canvas(1080, 2)
    ring_ = smooth(0.88, 0.89, c.R)
    d = c.R - 0.995
    seams = (np.abs(((c.A / TAU * 16) % 1) - 0.5) > 0.49) * ring_
    H = 0.06 * np.sqrt(clamp(1 - ((c.R - 0.94) / 0.055) ** 2)) * ring_ - 0.004 * seams
    H = rivets(c, H, 32, 0.965, 0.008, 0.06)
    alb = mix(flat('#E8ECF0', c.shape), flat('#B8C0C8', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 8, 3, 3))[..., None])
    col = metal(c, H, alb, rough=0.35, grime=0.4, seed=4, studio=COOL, met=0.3)
    lights = np.zeros(c.shape, F)
    for k in range(8):
        x, y = c.polar(k * TAU / 8 + TAU / 16, 0.915)
        lights = np.maximum(lights, gauss(np.hypot(c.X - x, c.Y - y), 0.008))
    col = col + rgb('#5FB8FF') * (1.5 * lights)[..., None]
    c.put(col, c.cover(d) * ring_, H)
    gl = smooth(0.2, 0.9, -(c.X * 0.55 + c.Y * 0.85)) * smooth(0.88, 0.5, c.R) * 0.10
    c.col = c.col + (gl * (1 - ring_))[..., None]
    c.alpha = np.maximum(c.alpha, gl * (1 - ring_))
    K.put(c, 'frame', how='png')


def modules():
    def one(c, k):
        d = c.box(0.78, 0.78, r=0.28)
        t = clamp(-d / 0.3)
        H = 0.08 * np.sqrt(t)
        alb = flat('#EEF2F6', c.shape) * (0.9 + 0.1 * fbm(c.shape, 10, 3 + k, 2))[..., None]
        col = metal(c, H, alb, rough=0.35, grime=0.3, seed=7 + k, studio=COOL, met=0.25)
        glow = gauss(c.box(0.62, 0.62, r=0.2), 0.012) * (1.4 if k else 0.6)
        col = col + rgb('#5FB8FF') * glow[..., None]
        col = mix(col, flat('#1A2838', c.shape), smooth(-0.14, -0.16, d)[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'modules', 2, one)


def hub():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.78, 0.80, c.R)
    H = 0.06 * np.sqrt(clamp(1 - ((c.R - 0.88) / 0.08) ** 2)) * rimz
    col = metal(c, H, flat('#E8ECF0', c.shape), rough=0.3, grime=0.3, seed=5, studio=COOL, met=0.3)
    face = mix(flat('#16243A', c.shape), flat('#080E18', c.shape), smooth(0.0, 0.8, c.R)[..., None]) + rgb('#5FB8FF') * (0.9 * gauss(c.R - 0.74, 0.008))[..., None]
    col = mix(face, col, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'hub')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#9FD4FF')
    c = K.canvas(48, 4, 1.0, 1.2)
    tri = c.poly([(0, -1.1), (0.8, 0.9), (0, 0.5), (-0.8, 0.9)])
    c.col[:] = rgb('#5FB8FF')
    c.alpha = c.cover(tri)
    K.put(c, 'marker', how='png', tone=False)


K.run([space, frame, modules, hub])
P = dict(base='#0A1020', accent='#5FB8FF', accent2='#FFFFFF', text='#EAF4FF', sub='#A8C4E0', panel=('#1A2438', '#0A1020'), stroke='#5FB8FF', tile=('#EEF2F6', '#D0D8E0'), tilestroke='#8A96A4',
         ink='#0A1020', dim=0.62, font='Bahnschrift, Segoe UI', badge='#5FB8FF', badgeink='#0A1020')
finish(K, P, sounds='cockpit',
       back=[soft(1.08, 0.03, 70), img('space', 1.0, rotate='time*1.5'), img('frame', 1.0, intro=intro(0.4, 'out', scale=0.92))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('modules', '0.98*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.66, zoom=1.16, shadow=dict(x=0, y=1, blur=3, color='black/50')),
       hub=[img('hub', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('marker', [0.07, 0.084], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       style=dict(open='zoom', tilt=0.35),
       onlaunch=[dict(color='#9FD4FF', count=28, area='slot', life=[0.4, 0.9], size=[1.5, 3], speed=[100, 360], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.5)],
       screen=dict(effect='stars', color='#9FC8FF', color2='#FFFFFF', density=1.0, speed=1.0, size=1.0))
