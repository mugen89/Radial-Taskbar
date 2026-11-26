"""Alchemist: a stained bench, copper pipes, a cauldron, and flasks that fill with the colour of what you point at."""
from skinkit import *

K = Kit('alchemist', 'Alchemist', 'A bench of bubbling flasks that fill up with the colour of what you point at', ['fantasy', 'glass', 'laboratory'], 'Font Metamorphous: SIL Open Font License, see OFL.txt')
K.flag(liquid=dict(cols=4, rows=2), halo='light', puff=dict(cols=2), brew='light', bubble='light')
DEN = Studio(lights=[((-0.55, -0.66, 0.52), 0.45, '#FFD9A0', 3.6), ((0.78, -0.30, 0.48), 0.28, '#9AE0C0', 1.5), ((0.1, 0.88, 0.42), 0.36, '#FFB070', 0.8)], sky='#A08A6A', floor='#0E0906', ambient=0.42)


def bench():
    c = K.canvas(1080, 2)
    H = lathe(c, [(0, 0.02), (0.905, 0.02), (0.915, 0.044), (0.972, 0.052), (0.992, 0.044), (1.0, 0.0)], 0.004)
    plank = np.floor((c.X + 2) / 0.235)
    seam = np.abs(((c.X + 2) / 0.235) % 1 - 0.5)
    tex, g = wood(c, 17, 1.5, '#6B4526', '#24140A', rot=math.pi / 2)
    tone = (rng(5).random(64)).astype(F)[plank.astype(int) % 64]
    tex = tex * (0.78 + 0.44 * tone)[..., None]
    H = H - 0.010 * smooth(0.488, 0.499, seam) * (c.R < 0.905) + 0.0015 * g
    # burns and spills
    for x, y, r, col, k in ((0.45, -0.62, 0.09, '#0E0805', 0.8), (-0.66, 0.42, 0.07, '#2F6B3A', 0.55), (0.10, 0.74, 0.08, '#4A2A7A', 0.5), (-0.30, -0.72, 0.06, '#8A2A1A', 0.5), (0.74, 0.30, 0.06, '#1E5A6A', 0.5)):
        d = np.hypot(c.X - x, c.Y - y) - r * (1 + 0.35 * fbm(c.shape, 10, int(r * 999), 3))
        m = smooth(0.02, -0.03, d) * 0.6 + gauss(d, 0.010) * 0.6
        tex = mix(tex, flat(col, c.shape), clamp(m * k)[..., None])
    # a circle scratched into the wood, inlaid with copper
    ink = Ink(c)
    for r, w in ((0.875, 0.006), (0.845, 0.003), (0.445, 0.004)):
        ink.line(arcpts(r, 0, TAU, 400), w)
    for n, s in ((3, 0), (3, math.pi)):
        ink.line([(math.sin(s + k * TAU / 3) * 0.845, -math.cos(s + k * TAU / 3) * 0.845) for k in range(3)], 0.0042, closed=True)
    inlay = ink.arr(0.0004)
    col = surface(c, H, tex, DEN, rough=0.55, clear=0.22, reach=0.1)
    cop = metal(c, H + 0.002 * inlay, COPPER, rough=0.3, grime=0.5, studio=DEN, dirt='#20302A')
    col = mix(col, cop, (inlay * 0.85)[..., None])
    rim = smooth(0.908, 0.912, c.R)
    pat = clamp(fbm(c.shape, 8, 4, 5) * 1.4 - 0.1)
    brass = metal(c, H, mix(flat(OLD_BRASS, c.shape), flat('#3F7A66', c.shape), (0.55 * pat)[..., None]), rough=0.3, grime=0.6, studio=DEN)
    col = mix(col, brass, rim[..., None])
    for i in range(16):
        x, y = c.polar((i + 0.5) * TAU / 16, 0.942)
        r = np.hypot(c.X - x, c.Y - y)
        m = metal(c, np.where(r < 0.016, 0.05 + dome(r, 0.017, 0.016), H), BRASS, rough=0.2, grime=0.4, studio=DEN, reach=0.04)
        col = mix(col, m, smooth(0.0165, 0.0150, r)[..., None]) * (1 - 0.4 * gauss(r - 0.019, 0.004))[..., None]
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'bench', exposure=0.95)


def flask():
    """Round flask seen from the front: back of the glass, liquid, front of the glass."""
    CY, R = 0.16, 0.70
    def shape(c):
        bulb = np.hypot(c.X, c.Y - CY) - R
        neck = c.box(0.20, 0.42, 0, -0.62, r=0.03)
        lip = c.box(0.27, 0.055, 0, -0.93, r=0.05)
        return smin(bulb, neck, 0.10), lip
    c = K.canvas(300, 3)
    d, lip = shape(c)
    u = np.hypot(c.X, c.Y - CY) / R
    inside = flat('#0E1614', c.shape) * 0.8
    c.put(inside, c.cover(d) * 0.62)
    sh = 0.55 * gauss(np.maximum(0, np.hypot((c.X - 0.05) * 1.0, (c.Y - 0.90) * 3.2) - 0.50), 0.16)
    c.put(np.zeros(3, F), (sh * (1 - c.alpha)).astype(F))
    K.put(c, 'flaskback')
    c = K.canvas(300, 3)
    d, lip = shape(c)
    edge = smooth(0.055, 0.0, -d) * (d < 0.004)
    hl = 0.85 * gauss(np.abs(np.hypot(c.X + 0.02, c.Y - CY) - R * 0.80), 0.035) * smooth(0.35, 0.95, -(c.X * 0.75 + (c.Y - CY) * 0.66) / np.maximum(np.hypot(c.X, c.Y - CY), 1e-3))
    hl2 = 0.40 * gauss(np.abs(np.hypot(c.X, c.Y - CY) - R * 0.86), 0.030) * smooth(0.5, 1.0, (c.X * 0.7 + (c.Y - CY) * 0.7) / np.maximum(np.hypot(c.X, c.Y - CY), 1e-3))
    nk = 0.65 * gauss(c.X + 0.12, 0.022) * smooth(-0.96, -0.85, c.Y) * smooth(-0.40, -0.55, c.Y)
    li = clamp(hl + hl2 + nk + 0.30 * edge) * c.cover(d)
    dk = 0.35 * edge * c.cover(d)
    a = clamp(li + dk * (1 - li))
    c.col = from_srgb(np.ones(c.shape + (3,), F) * (li / np.maximum(li + dk * (1 - li), 1e-4))[..., None] * np.array([0.94, 1.0, 0.97], F))
    c.alpha = a.astype(F)
    lc = c.cover(lip)
    c.put(flat('#CFE3DA', c.shape) * (0.35 + 0.9 * gauss(c.X + 0.12, 0.08))[..., None], lc * 0.8)
    cork = c.box(0.155, 0.10, 0, -0.985, r=0.03)
    K.put(c, 'flaskfront', how='png', tone=False)
    ims = []
    for f in range(8):              # eight fill levels
        c = K.canvas(200, 2)
        d, lip = shape(c)
        lev = CY + R * (0.62 - 1.28 * f / 7)
        wavy = lev + 0.020 * np.sin(c.X * 7 + f * 1.3)
        dd = np.maximum(d + 0.055, wavy - c.Y)
        body = c.cover(dd)
        depth = clamp((c.Y - wavy) / 1.2)
        lum = 0.62 + 0.38 * depth * 0 + 0.30 * gauss(np.hypot(c.X + 0.2, c.Y - CY - 0.1), 0.5)
        surf = gauss(np.hypot(0, (c.Y - wavy)), 0.030) * (d < -0.055)
        c.col[:] = 1
        c.alpha = clamp(body * (0.66 + 0.18 * depth) + 0.45 * surf * (np.abs(c.X) < 0.75)).astype(F) * c.cover(d + 0.05)
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'liquid')


def cauldron():
    c = K.canvas(480, 2)
    H = lathe(c, [(0, -0.10), (0.76, -0.06), (0.79, 0.02), (0.82, 0.10), (0.90, 0.125), (0.965, 0.10), (1.0, 0.0)], 0.006)
    ham = worley(c.X, c.Y, 13, 4)
    pat = clamp(fbm(c.shape, 5, 8, 5) * 1.5 - 0.1)
    alb = mix(flat(COPPER, c.shape), flat('#3F8A72', c.shape), (0.45 * pat)[..., None])
    col = metal(c, H + 0.012 * ham * (c.R > 0.8), alb, rough=0.26, grime=0.5, studio=DEN, dirt='#14100C')
    for k in range(10):
        x, y = c.polar(k * TAU / 10, 0.89)
        r = np.hypot(c.X - x, c.Y - y)
        col = mix(col, metal(c, np.where(r < 0.036, 0.125 + dome(r, 0.038, 0.030), H), BRASS, rough=0.2, grime=0.4, studio=DEN, reach=0.05), smooth(0.037, 0.033, r)[..., None]) * (1 - 0.35 * gauss(r - 0.042, 0.008))[..., None]
    liq = ramp(clamp(0.5 + 0.5 * fbm(c.shape, 4, 3, 5)), '#04221A', '#0A5A40', '#0E7A52') * (1 - 0.55 * smooth(0.45, 0.80, c.R))[..., None]
    col = mix(liq, col, smooth(0.775, 0.790, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'cauldron')

    def brew(q):                    # swirls of light in the liquid
        a = q.A + 3.2 * np.exp(-q.R * 1.6) + 1.4 * q.R
        n = fbm(q.shape, 5, 9, 4)
        s = np.sin(a * 3 + 2.2 * n) * 0.5 + 0.5
        return 0.75 * np.power(s, 3) * smooth(0.98, 0.6, q.R) * (0.35 + 0.65 * smooth(0.0, 0.4, q.R))
    light(K, 'brew', 320, brew, '#4CFFB0')
    light(K, 'bubble', 64, lambda q: 0.75 * gauss(q.R - 0.70, 0.13) + 0.9 * gauss(np.hypot(q.X + 0.30, q.Y + 0.32), 0.16) + 0.10 * (q.R < 0.7))
    halo(K, 'halo', 220, 2.0, 0.1)
    ims = []
    for k in range(2):
        c = K.canvas(96, 2)
        n = fbm(c.shape, 3, 20 + k, 5)
        c.col[:] = 1
        c.alpha = clamp(smooth(0.95, 0.1, c.R + 0.35 * n) * 0.75).astype(F)
        ims.append(c.image(tone=False))
    K.sheet(ims, 2, 'puff')


K.run([bench, flask, cauldron])
K.font('metamorphous', 'Metamorphous-Regular.ttf')
K.sounds('flask')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#1C120A', accent='#4CFFB0', accent2='#E8A24A', text='#F4E6C8', border='#B9803F', opacity=0.97, corner=9, font='Metamorphous', open='bloom', speed=1, hoverGrow=3,
               iconZoom=1.12, glow=0.5, tilt=0.4, pointer=False, burst=False, shadow=0.7, dim=0.42),
    wheel=dict(hub=94, thickness=102, gap=5, ringgap=12, rim=36, icon=40, crowd=1.52, area=1.12, hubkeep=0.70),
    colors=dict(pale='#F4E6C8', brew='#8CFFD0', amber='#E8A24A'), fonts=dict(title=dict(file='Metamorphous-Regular.ttf', family='Metamorphous')),
    back=[soft(1.09, 0.025, 66), img('bench', 1, intro=intro(0.28, 'out', scale=0.88))],
    ring=[dict(shape='line', **{'in': 'px'}, points=[['sin(rad(a+j*span))*(ringin-14)', '-cos(rad(a+j*span))*(ringin-14)'], ['sin(rad(a+j*span))*(ringin+14)', '-cos(rad(a+j*span))*(ringin+14)']], copies='n', stroke={'type': 'linear', 'stops': [[0, '#F0B48C'], [1, '#7A3E22']]}, width=6),
          dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringin-13', to=360, stroke={'type': 'linear', 'stops': [[0, '#F0B48C'], [0.5, '#7A3E22'], [1, '#D98F62']]}, width=6),
          dict(shape='circle', **{'in': 'px'}, copies='n', angle='a+j*span', radius='ringin-12+26*fract(time*0.7+rnd(j)*5)', size=3.4, fill='brew', opacity='0.8*motion', glow=4, glowcolor='accent')],
    slot=dict(intro=intro(0.34, 'back', 0.06, scale=0.3, y=0.5, stagger=0.022, order='both'),
              under=[img('halo', 1.9, opacity='0.45*hot+launch*1.5', tint='item'), img('flaskback', '1.18*(1+0.04*hot)', rotate='3*sin(time*6+seed*6)*hot'), img('liquid', '1.18*(1+0.04*hot)', frame='floor(2.2+5.3*sat(hot)+0.4*sin(time*2+seed*6))', tint='item', opacity=0.90, rotate='3*sin(time*6+seed*6)*hot'),
                     img('halo', 1.1, y=0.2, opacity='0.35*sat(hot)', tint='item')],
              icon=dict(size=0.80, y=0.16, zoom=1.16, rotate='3*sin(time*6+seed*6)*hot', shadow=dict(y=1, blur=3, color='black/60')),
              over=[img('bubble', '0.10+0.07*rnd(j+i*7)', copies=5, x='-0.34+0.68*rnd(j*3+i)+0.04*sin(time*4+j)', y='0.70-1.0*fract(time*(0.35+0.25*rnd(j+i))+rnd(j*5+i))', opacity='(0.25+0.75*sat(hot))*sin(3.14159*fract(time*(0.35+0.25*rnd(j+i))+rnd(j*5+i)))'),
                    img('flaskfront', '1.18*(1+0.04*hot)', rotate='3*sin(time*6+seed*6)*hot')] + running('#E8A24A', '#FFF0C8', 0.98, 0.15) + badge('#1C120A', 'pale', T, x=0.66, y=-0.40, stroke='#B9803F') + groupmark('amber', -1.06, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.20, 0.05, 70, 0.80, **{'in': 'hub'}), img('halo', 0.42, **{'in': 'hub'}, angle='sel', radius=0.94, opacity='on*(0.8+0.2*noise(time*8))', tint='#4CFFB0'), dict(shape='poly', **{'in': 'hub'}, angle='sel', radius=1.09, turns=True, points=[[-0.075, 0.05], [0, -0.075], [0.075, 0.05]], closed=True, fill='#8CFFD0', opacity='on', glow=5, glowcolor='accent')],
    hub=[img('cauldron', 1.02, intro=intro(0.34, 'back', scale=0.4)), img('brew', 0.78, rotate='time*26', opacity='0.20+0.10*on+launch'), img('brew', 0.74, rotate='-time*17+70', opacity='0.13'), dict(shape='circle', size=0.78, fill={'type': 'radial', 'stops': [[0, '#03140E/78'], [0.7, '#03140E/45'], [1, '#03140E/0']]}), img('bubble', '0.06+0.08*rnd(j+3)', copies=8, angle='rnd(j)*360', radius='0.62*sqrt(rnd(j+20))', opacity='0.8*sin(3.14159*fract(time*0.5+rnd(j+40)))', scale='0.3+0.7*fract(time*0.5+rnd(j+40))')]
    + words('#F4FFF8', 'brew', T, px=17, box=(1.24, 0.56), clockpx=30, datepx=11.5, subpx=10.5, weight=400, shadow=dict(x=0, y=1, blur=4, color='#02140E')),
    draw=dict(clock=False, shadow=False, text='#E6FFF2'), tabs=dict(inset=18, text='#E6FFF2', fill='#4CFFB0/14', on='#1F9A6A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#3A2514'], [1, '#1A0F07']]}, stroke={'type': 'linear', 'stops': [[0, '#F0B48C'], [0.5, '#7A3E22'], [1, '#D98F62']]}, width=3, corner=10, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#2A1A0E'], [1, '#140B05']]}, stroke='#C47A4C', width=1.6, corner=8, text='pale'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#4A3018'], [1, '#22140A']]}, stroke='#B9803F', width=2, corner=8, text='pale'),
    particles=[dict(image='puff', color='#4CFFB0', rate=1.4, max=10, area='hub', life=[1.4, 2.4], size=[14, 26], grow=2.2, speed=[10, 26], dir=[-25, 25], gravity=-26, spin=[-20, 20], opacity=0.16, fadein=0.3, fadeout=0.6)],
    onlaunch=[dict(image='puff', count=16, area='slot', life=[0.5, 1.0], size=[16, 34], grow=2.2, speed=[60, 220], outward=True, dir=[-120, 120], drag=2.6, gravity=-60, spin=[-60, 60], opacity=0.6, fadein=0.02, fadeout=0.7),
              dict(color='#8CFFD0', light=True, count=34, area='slot', life=[0.3, 0.8], size=[1.5, 3.5], speed=[90, 420], outward=True, dir=[-120, 120], gravity=200, drag=2, fadein=0, fadeout=0.6)])
