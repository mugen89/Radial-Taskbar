"""Sticker Album: a scrapbook page with washi tape; apps are die-cut stickers with a corner curling up."""
from lineup import *

K = Kit('stickers', 'Sticker Album', 'A scrapbook page with washi tape; every app is a die-cut sticker with a corner curling up', ['playful', 'paper', 'bright'])
K.flag(halo='light', stars=dict(cols=4))
COLS = ['#FF6A4A', '#4AA8E8', '#FFC83A', '#7AD07A']


def page():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = flat('#F2E6D0', c.shape) * (0.94 + 0.06 * fbm(c.shape, 30, 3, 3))[..., None]
    lines = gauss(((c.Y + 1) * 14) % 1 - 0.5, 0.02) * 0.10
    col = col - V([0.2, 0.15, 0.05]) * lines[..., None]
    for k, (x, y, a, tone) in enumerate(((-0.55, -0.70, 0.4, '#F6A6C1'), (0.62, 0.62, -0.5, '#9FD3F2'), (0.70, -0.55, 0.9, '#F7E27A'))):
        tape = c.box(0.22, 0.06, x=x, y=y, rot=a)
        stripes = 0.5 + 0.5 * np.sin((c.X * math.cos(a) + c.Y * math.sin(a)) * 80)
        tcol = mix(flat(tone, c.shape), flat('#FFFFFF', c.shape), (0.3 * stripes)[..., None])
        col = mix(col, tcol, (c.cover(tape) * 0.85)[..., None])
    col = col * (1 - 0.15 * smooth(0.85, 1.0, c.R))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'page')


def stickers():
    shapes = ['circle', 'star', 'heart', 'cloud']
    def one(c, k):
        kind = shapes[k]
        if kind == 'circle':
            body = c.circle(0.70)
        elif kind == 'star':
            body = c.star(5, 0.86, 0.48) - 0.04
        elif kind == 'heart':
            pts = bez((0, 0.80), (0.95, 0.10), (0.55, -0.80), (0, -0.40), 16) + bez((0, -0.40), (-0.55, -0.80), (-0.95, 0.10), (0, 0.80), 16)
            body = c.poly(pts)
        else:
            body = np.minimum(np.minimum(c.circle(0.38, -0.30, 0.10), c.circle(0.45, 0.10, -0.05)), np.minimum(c.circle(0.34, 0.42, 0.15), c.box(0.62, 0.22, y=0.24, r=0.2)))
        outline = body - 0.10
        curl = (c.X + c.Y) > 0.95
        fold = c.poly([(0.95 - 0.6, 0.6), (0.6, 0.95 - 0.6), (0.95, 0.95)])
        shadow = c.cover(outline - 0.02) * 0.25
        c.put(flat('#000000', c.shape), blur(shadow, 4 * c.ss) * (1 - curl))
        c.put(flat('#FFFFFF', c.shape), c.cover(outline) * (1 - curl))
        c.put(flat(COLS[k], c.shape) * (0.95 + 0.05 * fbm(c.shape, 20, 3, 2))[..., None], c.cover(body) * (1 - curl))
        flap = c.cover(fold)  # the corner, peeled back: its white underside
        c.put(mix(flat('#E8E4DC', c.shape), flat('#FFFFFF', c.shape), clamp(0.5 - (c.X + c.Y - 1.3) * 2)[..., None]), flap * 0.95)
        return c
    plate(K, 'stickers', 4, one)


def badge_():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    scal = 0.94 + 0.03 * np.cos(c.A * 18)
    edge = c.R - scal
    c.put(flat('#FFFFFF', c.shape), c.cover(edge))
    c.put(flat('#FF6A4A', c.shape) * (0.95 + 0.05 * fbm(c.shape, 20, 3, 2))[..., None], c.cover(c.R - 0.84))
    c.put(flat('#FFF4E0', c.shape), c.cover(c.R - 0.76))
    K.put(c, 'badge')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFF2D8')
    ims = []
    for k, colr in enumerate(['#FF6A4A', '#4AA8E8', '#FFC83A', '#7AD07A']):
        cc = K.canvas(40, 4)
        s = cc.star(5, 0.9, 0.45)
        cc.put(flat('#FFFFFF', cc.shape), cc.cover(s - 0.12))
        cc.put(flat(colr, cc.shape), cc.cover(s))
        ims.append(cc.image(tone=False))
    K.sheet(ims, 4, 'stars', how='png')


K.run([page, stickers, badge_])
P = dict(base='#F2E6D0', accent='#FF6A4A', accent2='#4AA8E8', text='#2A2A3A', sub='#5A5A6A', panel=('#FFFFFF', '#F2EEE6'), stroke='#FF6A4A', tile=('#FFFFFF', '#F2EEE6'), tilestroke='#C8C0B0',
         ink='#2A2A3A', paneltext='#2A2A3A', dim=0.22, font='Segoe UI Black, Segoe UI', badge='#4AA8E8', badgeink='#FFFFFF')
finish(K, P, sounds='paper',
       back=[soft(1.06, 0.03, 45), img('page', 1.0, intro=intro(0.4, 'out', scale=0.95))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('stickers', '1.08*(1+0.06*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*30-15')],
       icon=dict(size=0.48, zoom=1.18, tone='sticker', shadow=dict(x=0, y=1, blur=2, color='black/25')),
       hub=[soft(1.0, 0.05, 30), img('badge', 1.0, rotate='-4', intro=intro(0.4, 'back', scale=0.6))],
       over=[img('stars', [0.07, 0.07], **{'in': 'hub'}, frame='floor(time*1.5)%4', angle='sel', radius=1.10, rotate='sel', opacity='on')],
       tabs=dict(inset=13, text='#2A2A3A', fill='#FFFFFF/55', on='#FF6A4A/85'),
       style=dict(open='bloom', speed=1.05, tilt=0.3),
       onlaunch=[dict(image='stars', count=16, area='slot', life=[0.6, 1.1], size=[7, 12], speed=[120, 320], outward=True, dir=[-100, 100], gravity=500, spin=[-400, 400], fadein=0, fadeout=0.3)])
