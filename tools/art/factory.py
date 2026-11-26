"""Factory: a diamond-plate floor with hazard stripes, a conveyor belt that runs round, crates on it, a gear in the middle."""
from lineup import *

K = Kit('factory', 'Factory', 'A conveyor belt runs round a steel floor with hazard stripes; apps ride on crates, a big gear turns in the middle', ['industrial', 'metal', 'orange'])
K.flag(halo='light')
ORANGE = '#F28C28'


def floor():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    def bumps(ang):
        u = c.X * math.cos(ang) + c.Y * math.sin(ang)
        v = -c.X * math.sin(ang) + c.Y * math.cos(ang)
        cu, cv = (u * 14) % 1 - 0.5, (v * 14 + 0.5 * np.floor(u * 14)) % 1 - 0.5
        return clamp(1 - np.hypot(cu / 0.42, cv / 0.12))
    H = 0.012 * np.maximum(bumps(0.785), bumps(-0.785)) + 0.002 * fbm(c.shape, 30, 3, 2)
    stripe = ((c.X + c.Y) * 9) % 1 < 0.5
    rim = smooth(0.89, 0.90, c.R)
    alb = mix(flat('#8C939B', c.shape), np.where(stripe[..., None], rgb('#F2C21E'), rgb('#1A1A1A')) * np.ones(c.shape + (3,), F), rim[..., None])
    H = H * (1 - rim) + 0.02 * rim
    col = metal(c, H, alb, rough=0.35, grime=0.7, seed=3, studio=WARM, scratch=200, met=0.75)
    c.put(col, c.cover(d), H)
    K.put(c, 'floor')


def belt():
    c = K.canvas(1080, 2)
    r0, half = 0.71, 0.15
    d = np.abs(c.R - r0) - half
    seg = np.abs(((c.A / TAU * 120) % 1) - 0.5)
    H = 0.02 * smooth(0.40, 0.48, seg) + 0.01 * clamp(1 - np.abs(c.R - r0) / half)
    alb = flat('#2A2C30', c.shape) * (0.9 + 0.1 * fbm(c.shape, 60, 4, 2))[..., None]
    col = surface(c, H, alb, WARM, rough=0.7, reach=0.06)
    edge = gauss(np.abs(c.R - r0) - half, 0.004)
    col = col + V([0.5, 0.5, 0.55]) * (0.5 * edge)[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'belt')


def crates():
    paints = [ORANGE, '#3A6EA8', '#4E8A3A', '#C8A040']
    def one(c, k):
        d = c.box(0.80, 0.80, r=0.06)
        frame = smooth(-0.11, -0.09, d)
        H = 0.05 * clamp(-d / 0.05) + 0.03 * frame + 0.004 * (np.abs(((c.X + 1) * 8) % 1 - 0.5) < 0.04) * (1 - frame)
        corners = np.zeros(c.shape, F)
        for x in (-0.66, 0.66):
            for y in (-0.66, 0.66):
                corners = np.maximum(corners, smooth(0.10, 0.08, np.maximum(np.abs(c.X - x), np.abs(c.Y - y))))
        H = H + 0.02 * corners
        alb = mix(flat(paints[k], c.shape), flat('#6A6E74', c.shape), corners[..., None])
        col = metal(c, H, alb, rough=0.45, grime=0.6, seed=30 + k, studio=WARM, scratch=60, met=0.3)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'crates', 4, one)


def gear():
    c = K.canvas(460, 2)
    d = c.gear(18, 0.97, 0.10)
    H = 0.08 * clamp(-d / 0.08) - 0.03 * smooth(0.82, 0.80, c.R) * smooth(0.40, 0.42, c.R)
    alb = mix(flat(ORANGE, c.shape), flat('#2A2C30', c.shape), smooth(0.81, 0.79, c.R)[..., None])
    col = metal(c, H, alb, rough=0.4, grime=0.7, seed=5, studio=WARM, met=0.4)
    c.put(col, c.cover(d), H)
    K.put(c, 'gear')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFB860')
    c = K.canvas(56, 4, 1.0, 1.2)
    ch = c.poly([(0, -1.1), (0.9, 0.0), (0.9, 0.6), (0, -0.4), (-0.9, 0.6), (-0.9, 0.0)])
    c.put(surface(c, 0.12 * clamp(-ch / 0.25), flat('#F2C21E', c.shape), SOFT, rough=0.5), c.cover(ch))
    K.put(c, 'chevron', how='png')


K.run([floor, belt, crates, gear])
P = dict(base='#22262B', accent=ORANGE, accent2='#FFD23A', text='#F4F4F0', sub='#C8CDD2', panel=('#33383E', '#1E2226'), stroke=ORANGE, tile=('#E8EAEC', '#C8CDD2'), tilestroke='#6A6E74',
         ink='#22262B', dim=0.38, font='Bahnschrift, Segoe UI', badge='#FFD23A', badgeink='#22262B')
finish(K, P, sounds='vault',
       back=[soft(1.10, 0.03, 65), img('floor', 1.0, intro=intro(0.35, 'out', scale=0.92)), img('belt', 1.0, rotate='time*-4+(1-open)*-60')],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('crates', '0.92*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*12-6')],
       icon=dict(size=0.70, zoom=1.14, shadow=dict(x=1, y=2, blur=2, color='black/55')),
       hub=[img('gear', 1.0, rotate='time*8+(1-open)*-120', intro=intro(0.4, 'back', scale=0.6)), dict(shape='circle', size=0.78, fill='#22262B')],
       over=[img('chevron', [0.075, 0.09], **{'in': 'hub'}, angle='sel', radius=1.12, rotate='sel', opacity='on')],
       style=dict(open='spin', tilt=0.3),
       onlaunch=[dict(color='#FFC45A', count=34, area='slot', life=[0.3, 0.7], size=[1.5, 3], speed=[180, 520], outward=True, dir=[-60, 60], gravity=900, stretch=2.5, fadein=0, fadeout=0.4)],
       onhover=[dict(color='#FFC45A', count=6, area='slot', life=[0.2, 0.4], size=[1, 2], speed=[60, 160], outward=True, dir=[-40, 40], gravity=600, stretch=2, fadein=0, fadeout=0.5)])
