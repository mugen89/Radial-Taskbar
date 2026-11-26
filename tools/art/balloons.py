"""Balloons: shiny foil balloons against a soft sky; they bob and tug at their strings, confetti on launch."""
from lineup import *

K = Kit('balloons', 'Balloons', 'Shiny foil balloons against a soft sky; they bob and tug at their strings, confetti on launch', ['party', 'playful', 'bright'])
K.flag(halo='light', confetti=dict(cols=6))
FOILS = ['#FF5A8A', '#FFC83A', '#5AB8FF', '#B87AFF', '#5AD08A', '#C8CCD2']


def sky():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = mix(flat('#DDF0FC', c.shape), flat('#9CD0F2', c.shape), smooth(-0.9, 0.9, c.Y)[..., None])
    cloud = clamp(fbm(c.shape, 3, 4, 5) * 1.6 + 0.1) * smooth(-0.2, 0.9, c.Y)
    col = mix(col, flat('#FFFFFF', c.shape), (0.6 * cloud)[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'sky')


def foils():
    def one(c, k):
        cx, cy, rx, ry = 0.0, -0.16, 0.64, 0.72
        e = np.hypot((c.X - cx) / rx, (c.Y - cy) / ry)
        d = (e - 1) * rx
        z = np.sqrt(clamp(1 - e * e))
        nx, ny = (c.X - cx) / rx * (1 - 0.15 * z), (c.Y - cy) / ry * (1 - 0.15 * z)
        nz = np.sqrt(clamp(1 - nx * nx - ny * ny))
        base = rgb(FOILS[k])
        band = 0.5 + 0.5 * np.cos((ny * 2.2 + nx * 0.6) * 3.2)
        env = clamp(0.25 + 0.75 * band) * (0.55 + 0.45 * nz)
        spec = np.power(clamp(nx * -0.45 + ny * -0.62 + nz * 0.64), 40) * 1.6 + np.power(clamp(nx * 0.5 + ny * -0.2 + nz * 0.84), 60) * 0.5
        seam = gauss(d, 0.012) * 0.5
        col = base * (0.30 + 0.95 * env)[..., None] + V([1, 1, 1]) * (spec + seam)[..., None]
        knot = c.cover(c.poly([(-0.07, cy + ry + 0.08), (0.07, cy + ry + 0.08), (0, cy + ry - 0.04)]))
        sx = 0.05 * np.sin((c.Y - cy - ry) * 9)
        string = smooth(0.016, 0.008, np.abs(c.X - sx)) * smooth(cy + ry + 0.06, cy + ry + 0.10, c.Y) * smooth(1.0, 0.94, c.Y)
        c.put(flat('#F4F4F4', c.shape), clamp(string))
        c.put(base * 0.75, knot)
        c.put(col, c.cover(d))
        return c
    plate(K, 'foils', 6, one)


def puff():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    edge = 0.90 + 0.05 * np.abs(np.sin(c.A * 4)) + 0.02 * np.abs(np.sin(c.A * 9))
    shape = np.minimum(c.R - edge, d)
    t = clamp(-shape / 0.6)
    H = 0.12 * np.sqrt(t)
    col = surface(c, H, flat('#FFFFFF', c.shape), SOFT, rough=0.9, reach=0.05)
    c.put(col, c.cover(shape), H)
    K.put(c, 'puff')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFFFFF')
    ims = []
    for k in range(6):
        cc = K.canvas(24, 4, 1.0, 1.0)
        cc.col[:] = rgb(FOILS[k])
        cc.alpha = cc.cover(cc.box(0.5, 0.8, rot=k * 0.5))
        ims.append(cc.image(tone=False))
    K.sheet(ims, 6, 'confetti', how='png')


K.run([sky, foils, puff])
P = dict(base='#BFE2F6', accent='#FF5A8A', accent2='#FFD23A', text='#2A4A6A', sub='#5A7A9A', panel=('#FFFFFF', '#E6F2FA'), stroke='#5AB8FF', tile=('#FFFFFF', '#E6F2FA'), tilestroke='#5AB8FF',
         ink='#2A4A6A', paneltext='#2A4A6A', dim=0.2, font='Segoe UI Black, Segoe UI', badge='#FF5A8A', badgeink='#FFFFFF')
bob = '0.04*sin(time*1.6+seed*6)'
finish(K, P, sounds='jelly',
       back=[soft(1.06, 0.03, 40), img('sky', 1.0, intro=intro(0.45, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'),
              img('foils', '1.14*(1+0.05*hot-0.04*press)', frame='(i+ring)%6', y='0.12+' + bob, rotate='4*sin(time*1.3+seed*9)')],
       icon=dict(size=0.52, zoom=1.18, shadow=dict(x=0, y=1, blur=3, color='black/30')),
       hub=[soft(1.0, 0.06, 30), img('puff', 1.0, scale='1+0.02*sin(time*1.2)', intro=intro(0.45, 'back', scale=0.6))],
       over=[img('confetti', [0.04, 0.04], **{'in': 'hub'}, frame='floor(time*3)%6', angle='sel', radius=1.10, rotate='time*120', opacity='on')],
       tabs=dict(inset=13, text='#2A4A6A', fill='#FFFFFF/55', on='#FF5A8A/85'),
       style=dict(open='bloom', speed=1.0, tilt=0.35),
       onlaunch=[dict(image='confetti', count=40, area='slot', life=[0.7, 1.3], size=[4, 8], speed=[150, 400], outward=True, dir=[-110, 110], gravity=500, drag=1.5, spin=[-600, 600], sway=20, swayhz=3, fadein=0, fadeout=0.3)])
