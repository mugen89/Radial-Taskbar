"""Hologram: figures of light above a small projector. Almost everything is drawn by the program; the pictures add light."""
from skinkit import *

K = Kit('hologram', 'Hologram', 'Thin figures of light above a small projector, with scan lines and glitches', ['sci-fi', 'light', 'blue'], 'Font Rajdhani: SIL Open Font License, see OFL.txt')
K.flag(cone='light', floor='light', halo='light', beam='light', lines='sharp', flash='light')
C, M = '#4FE3FF', '#FF4FD8'


def optics():
    def cone(q):
        g = rng(4)
        n = 220
        prof = blur1(np.abs(g.standard_normal((1, n))).astype(F), 1.2, 1)[0]
        u = (q.A / TAU + 0.5) * (n - 1)
        i = np.floor(u).astype(int)
        rays = prof[i] * (1 - (u - i)) + prof[(i + 1) % n] * (u - i)
        fall = smooth(0.20, 0.36, q.R) * np.power(clamp(1 - (q.R - 0.3) / 0.70), 1.3)
        return (0.10 + 0.26 * rays) * fall
    light(K, 'cone', 620, cone, C)

    def floor(q):
        s = 0.062
        # hexagons, thin lines
        x, y = q.X / s, q.Y / s
        qx, qy = np.abs((x % 1.732) - 0.866), np.abs((y % 3.0) - 1.5)
        d1 = np.abs(np.maximum(qx * 0.5 + qy * 0.866, qx) - 0.866)
        qx2, qy2 = np.abs(((x + 0.866) % 1.732) - 0.866), np.abs(((y + 1.5) % 3.0) - 1.5)
        d2 = np.abs(np.maximum(qx2 * 0.5 + qy2 * 0.866, qx2) - 0.866)
        e = smooth(0.10, 0.02, np.minimum(d1, d2))
        return 0.55 * e * smooth(1.0, 0.45, q.R) * smooth(0.22, 0.4, q.R)
    light(K, 'floor', 900, floor, C)
    halo(K, 'halo', 256, 2.2, 0.0, C)
    light(K, 'flash', 200, lambda q: 0.9 * gauss(q.Y, 0.030) * smooth(1.0, 0.2, np.abs(q.X)) + 0.35 * gauss(q.Y, 0.12) * smooth(1.0, 0.2, np.abs(q.X)), '#BFF6FF')

    def beam(q):                # a column of light under what is selected
        w = 0.16 + 0.62 * clamp((1 - q.Y) / 2)
        return 0.85 * smooth(1.0, 0.2, np.abs(q.X) / w) * smooth(1.0, 0.0, (1 - q.Y) / 2) * (0.6 + 0.4 * np.sin(q.Y * 90) ** 2)
    light(K, 'beam', 200, beam, C)
    im = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
    for y, a in enumerate((80, 30, 0, 30)):
        for x in range(4):
            im.putpixel((x, y), (0, 10, 18, a))
    im.save(os.path.join(K.dir, 'lines.png'))


def projector():
    c = K.canvas(460, 2)
    H = lathe(c, [(0, 0.0), (0.56, 0.0), (0.585, 0.06), (0.64, 0.085), (0.70, 0.07), (0.72, 0.045), (0.90, 0.04), (0.93, 0.075), (0.975, 0.075), (1.0, 0.02)], 0.004)
    n = 24
    k = np.abs(((c.A / TAU + 0.5) * n) % 1 - 0.5)
    vent = smooth(0.16, 0.22, 0.5 - k + 0.0) * 0
    slots = (np.abs(c.R - 0.81) < 0.062) & (k < 0.17)
    H = np.where(slots, H - 0.03, H)
    for i in range(6):
        x, y = c.polar((i + 0.5) * TAU / 6, 0.952)
        r = np.hypot(c.X - x, c.Y - y)
        H = np.where(r < 0.020, H + dome(r, 0.021, 0.016), H)
    col = metal(c, H + 0.0006 * circular_streaks(c, 4, 500), V([0.16, 0.18, 0.21]), rough=0.3, grime=0.4, studio=COOL, dirt='#05080C')
    col = np.where(slots[..., None], rgb('#0B2E3C') + rgb('#1FA9C9') * 0.22, col)
    lens = flat('#03131C', c.shape) + rgb('#0E5A78') * (0.55 * gauss(c.R - 0.50, 0.10))[..., None] + rgb('#39D6FF') * (0.16 * gauss(c.R, 0.40))[..., None]
    for r, w in ((0.20, 0.008), (0.34, 0.006), (0.46, 0.006)):
        lens = lens + rgb('#4FE3FF') * (0.10 * smooth(w, w * 0.3, np.abs(c.R - r)))[..., None]
    col = mix(lens, col, smooth(0.560, 0.568, c.R)[..., None])
    ring = gauss(c.R - 0.715, 0.010)
    col = col + rgb('#39D6FF') * (1.4 * ring)[..., None]
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'projector', exposure=1.0)


K.run([optics, projector])
K.font('rajdhani', 'Rajdhani-SemiBold.ttf')
K.sounds('holo')
T = 'title'
def glitch(s):
    return '(step(0.965,noise(time*9+%g))*(noise(time*60+%g)-0.5)*motion)' % (s, s)
fl = '(0.86+0.14*noise(time*17+i*9))'
K.write(
    style=dict(shape='orb', material='solid', base='#04141E', accent=C, accent2=M, text='#D6F8FF', border='#2FA9C9', opacity=0.92, corner=6, font='Rajdhani', open='zoom', speed=1.1, hoverGrow=3,
               iconZoom=1.12, glow=0.8, tilt=0.8, pointer=False, burst=False, shadow=0.3, dim=0.46),
    wheel=dict(hub=86, thickness=92, gap=6, ringgap=10, rim=26, icon=44, crowd=1.5, area=1.16, hubkeep=0.86),
    colors=dict(c=C, m=M, pale='#D6F8FF'), fonts=dict(title=dict(file='Rajdhani-SemiBold.ttf', family='Rajdhani')),
    back=[dict(shape='circle', size=1.12, fill={'type': 'radial', 'stops': [[0, '#021019/92'], [0.62, '#021019/78'], [0.90, '#021019/45'], [1, '#021019/0']]}, opacity='sat(open)'),
          img('projector', 0.40, intro=intro(0.22, 'out', scale=0.6)), img('floor', 1.05, rotate='time*1.5', opacity='0.26*sat(open)', depth=-0.5), img('cone', 1.04, rotate='time*5', opacity='(0.36+0.08*noise(time*12))*sat(open)', scale='0.4+0.6*outcubic(sat(time*3))'),
          img('cone', 1.04, rotate='-time*8+40', opacity='0.18*sat(open)', scale='0.4+0.6*outcubic(sat(time*2.6))')],
    ring=[dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringout+5', to='360*outcubic(sat(time*2.4))', stroke='c/75', width=1.4, glow=5, glowcolor='c', depth=0.5),
          dict(shape='arc', **{'in': 'px', 'from': 'j*120+time*14'}, r='ringout+12', to='j*120+46+time*14', copies=3, stroke='c', width=2.6, opacity=0.8, depth=0.8, glow=5, glowcolor='c'),
          dict(shape='arc', **{'in': 'px', 'from': 'j*90-time*22'}, r='ringin-6', to='j*90+24-time*22', copies=4, stroke='m/85', width=2, opacity=0.8, depth=0.3),
          {'shape': 'ticks', 'in': 'px', 'inner': 'ringout+7', 'outer': 'ringout+10', 'count': 120, 'major': 10, 'stroke': 'c/45', 'width': 1, 'depth': 0.5}],
    slot=dict(intro=intro(0.22, 'out', 0.06, scale=0.3, y=0.5, stagger=0.02, order='ring'),
              under=[img('beam', [1.05, 1.5], y=0.35, opacity='sat(hot)*0.75*' + fl), img('halo', 1.7, opacity='0.10+0.40*hot+launch*2'),
                     dict(shape='circle', size=0.96, fill='#05202E/55'), dict(shape='arc', r=0.96, **{'from': 0}, to=360, stroke='c', width=1.4, opacity='(0.45+0.55*sat(hot))*' + fl, glow=4, glowcolor='c'),
                     dict(shape='arc', r=1.06, **{'from': 'j*120+time*(20+60*hot)'}, to='j*120+34+time*(20+60*hot)', copies=3, stroke='c', width=2, opacity='0.35+0.65*sat(hot)')],
              icon=dict(size=1.10, zoom=1.14, tone='duo', hot='original', ink='#04384C', paper='#8DF1FF', x='0.10*' + glitch(0), opacity='0.92*' + fl),
              over=[dict(shape='circle', size=0.94, fill={'image': 'lines', 'tile': True, 'zoom': 0.018, 'v': 'time*0.35'}, opacity=0.75), img('flash', [1.1, 0.5], y='-1.0+2.0*fract(time*0.5+i*0.13)', opacity='0.22+0.4*hot'),
                    dict(shape='rect', x='0.5*(rnd(floor(time*24)+j)-0.5)', y='-0.8+1.6*rnd(floor(time*30)+j*3)', size=['0.5+0.5*rnd(floor(time*28)+j*7)', 0.035], copies=7, fill='c', opacity='launch*0.9')]
              + [dict(shape='circle', y=0.96, size=0.10, fill='c', when='running', opacity='active ? 1 : 0.6', glow=6, glowcolor='c'), dict(shape='arc', r=0.18, y=0.96, **{'from': 0}, to=360, stroke='c', width=1.2, when='active', scale='1+0.4*fract(time)', opacity='1-fract(time)')]
              + badge('#04141E', 'c', T, stroke=C, em=0.34) + groupmark('c', -0.98, 0.12), marks=False, chevron=False, badge=False),
    fan=[{'shape': 'ring', 'in': 'px', 'inner': 'ringin-2', 'outer': 'ringout+3', 'from': 'a-span/2-2', 'to': 'a+span/2+2', 'fill': '#04141E/85', 'stroke': 'c', 'width': 1.4, 'glow': 4, 'glowcolor': 'c'}],
    over=[dict(shape='line', **{'in': 'px'}, points=[['sin(rad(sel))*(hub+2)', '-cos(rad(sel))*(hub+2)'], ['sin(rad(sel))*(hub+16)', '-cos(rad(sel))*(hub+16)']], stroke='c', width=2.4, opacity='on', glow=6, glowcolor='c', caps=True)],
    hub=[dict(shape='circle', size=0.97, fill='#031019/60'), dict(shape='arc', r=0.97, **{'from': 0}, to=360, stroke='c/70', width=1.4, glow=5, glowcolor='c'), dict(shape='arc', r=0.90, **{'from': 'sel-24'}, to='sel+24', stroke='c', width=3, opacity='on', glow=6, glowcolor='c'),
         dict(shape='arc', r=0.90, **{'from': 'time*30'}, to='time*30+70', stroke='m/80', width=1.6), dict(shape='arc', r=0.84, **{'from': 'j*30'}, to='j*30+9', copies=12, stroke='c/35', width=1.4)]
    + words('pale', 'c', T, px=19, box=(1.40, 0.66), clockpx=36, datepx=13, subpx=13, weight=600, shadow=dict(x=0, y=0, blur=6, color=C), x='0.05*' + glitch(50))
    + [dict(shape='circle', size=0.96, fill={'image': 'lines', 'tile': True, 'zoom': 0.014, 'v': 'time*0.3'}, opacity=0.5)],
    draw=dict(clock=False, shadow=False, text='pale', fan=False), tabs=dict(inset=13, text='pale', fill='#4FE3FF/12', on='#4FE3FF/45'),
    panel=dict(fill='#04141E/90', stroke='c', width=1.4, corner=10, cutcorner=True, text='pale'), tag=dict(fill='#04141E/92', stroke='c', width=1.3, corner=7, cutcorner=True, text='pale'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#0A3244/92'], [1, '#04141E/92']]}, stroke='c', width=1.3, corner=8, cutcorner=True, text='pale'),
    particles=[dict(color=C, light=True, rate=9, max=40, area='wheel', life=[0.8, 1.8], size=[1, 2.2], speed=[14, 40], dir=[-8, 8], gravity=-30, fadein=0.2, fadeout=0.5, opacity=0.8)],
    onlaunch=[dict(color=C, light=True, count=40, area='slot', life=[0.25, 0.6], size=[1.5, 3], speed=[120, 520], outward=True, dir=[-90, 90], drag=3, stretch=1, fadein=0, fadeout=0.6), dict(color=M, light=True, count=14, area='slot', life=[0.25, 0.5], size=[1.5, 3], speed=[80, 360], outward=True, dir=[-90, 90], drag=3, stretch=1, fadein=0, fadeout=0.6)])
