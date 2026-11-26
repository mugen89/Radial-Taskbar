"""Nixie: glowing glass tubes on walnut and copper."""
from skinkit import *

K = Kit('nixie', 'Nixie', 'Glowing glass tubes on walnut and copper', ['retro', 'tubes', 'glow'])
K.flag(glow='light', spill='light', pulse='light', halo='light')
LAB = Studio(lights=[((-0.45, -0.72, 0.56), 0.34, '#FFE9CF', 3.4), ((0.80, -0.25, 0.48), 0.22, '#CFE0FF', 1.5), ((0.15, 0.86, 0.42), 0.34, '#FF9A4A', 1.0)], sky='#8A8076', floor='#0C0806', ambient=0.40)


def base():
    c = K.canvas(1050, 2)
    H = lathe(c, [(0, 0.03), (0.90, 0.03), (0.915, 0.055), (0.965, 0.070), (0.99, 0.060), (1.0, 0.02)], 0.004)
    tex, g = wood(c, 9, 1.5, '#54301A', '#1A0C07', rot=-0.25)
    col = surface(c, H + 0.0012 * g, tex, LAB, rough=0.42, clear=0.45, reach=0.14)
    cop = metal(c, H + 0.0006 * circular_streaks(c, 3, 900), COPPER, rough=0.26, grime=0.55, studio=LAB, aniso=(np.cos(c.A), np.sin(c.A), 0.5), dirt='#2A140C')
    ring = np.maximum(smooth(0.908, 0.912, c.R), 0)
    col = mix(col, cop, ring[..., None])
    for k in range(12):              # screws
        x, y = c.polar((k + 0.5) * TAU / 12, 0.952)
        r = np.hypot(c.X - x, c.Y - y)
        hs = np.where(r < 0.017, 0.075 + dome(r, 0.018, 0.010), H)
        a = k * 1.3
        hs = np.where((np.abs((c.X - x) * math.cos(a) + (c.Y - y) * math.sin(a)) < 0.0026) & (r < 0.014), 0.072, hs)
        m = metal(c, hs, BRASS, rough=0.2, grime=0.3, studio=LAB, reach=0.04)
        col = mix(col, m, smooth(0.0180, 0.0165, r)[..., None])
        col = col * (1 - 0.45 * gauss(r - 0.020, 0.004))[..., None]
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'base', exposure=0.92)
    light(K, 'spill', 420, lambda q: 0.9 * gauss(q.R - 0.66, 0.16) + 0.25 * gauss(q.R - 0.66, 0.34), '#FF5A14')


def tube():
    """A tube seen from the front: foot, glass, mesh. The light comes later."""
    c = K.canvas(340, 3)
    body = c.box(0.50, 0.70, 0, -0.06, r=0.48)
    dome_ = np.minimum(body, c.taper(0, -0.72, 0.16, 0, -0.86, 0.05))
    u = clamp(c.X / 0.52, -1, 1)
    nx = u
    nz = np.sqrt(clamp(1 - nx * nx))
    inside = flat('#0D0907', c.shape) * (0.6 + 0.9 * nz)[..., None]
    # the anode: a fine honeycomb in front, stamped metal at the sides
    s = 0.062
    hx = c.X / s
    hy = c.Y / (s * 0.866)
    row = np.floor(hy)
    cx = hx + 0.5 * (row % 2)
    q = np.hypot((cx % 1) - 0.5, ((hy % 1) - 0.5) * 0.9)
    mesh = smooth(0.36, 0.47, q) * (np.abs(c.X) < 0.40) * (c.Y > -0.55) * (c.Y < 0.52)
    inside = inside + rgb('#8A7A66') * (0.085 * mesh)[..., None]
    plate = (np.abs(np.abs(c.X) - 0.405) < 0.020) & (c.Y > -0.56) & (c.Y < 0.54)
    inside = np.where(plate[..., None], rgb('#5A5046') * (0.35 + 0.65 * nz)[..., None], inside)
    for y in (-0.56, 0.535):
        inside = np.where(((np.abs(c.Y - y) < 0.030) & (np.abs(c.X) < 0.43))[..., None], rgb('#C9BFAE') * (0.20 + 0.45 * nz)[..., None], inside)
    for x in (-0.2, 0.0, 0.2):
        inside = inside + rgb('#B9A88C') * (0.10 * gauss(c.X - x, 0.010) * (c.Y > 0.50))[..., None]
    # reflections on the glass
    refl = 0.34 * gauss(u + 0.66, 0.085) * smooth(-0.72, -0.45, c.Y) * smooth(0.66, 0.40, c.Y) + 0.22 * gauss(u - 0.76, 0.06) * smooth(-0.6, -0.3, c.Y) * smooth(0.62, 0.4, c.Y)
    refl += 0.40 * gauss(np.hypot(c.X + 0.16, (c.Y + 0.60) * 1.4), 0.10)
    edge = np.power(clamp(1 - nz), 1.8) * 0.16
    inside = inside + (refl + edge)[..., None] * rgb('#E8F0FF')
    c.put(inside, clamp(c.cover(dome_)))
    # foot of black bakelite with a copper ring
    foot = c.box(0.50, 0.13, 0, 0.735, r=0.07)
    nzf = np.sqrt(clamp(1 - (c.X / 0.54) ** 2))
    fcol = flat('#17120F', c.shape) * (0.5 + 1.3 * gauss(c.X / 0.52 + 0.5, 0.35))[..., None] + (0.16 * gauss(c.X / 0.52 + 0.55, 0.12))[..., None] * rgb('#FFE9CF')
    c.put(fcol, c.cover(foot))
    ring = c.box(0.47, 0.045, 0, 0.615, r=0.04)
    k = 0.22 + 0.40 * nzf + 0.6 * gauss(c.X / 0.52 + 0.45, 0.12) + 0.25 * gauss(c.X / 0.52 - 0.6, 0.10)
    c.put(flat(COPPER, c.shape) * k[..., None], c.cover(ring))
    sh = 0.6 * gauss(np.maximum(0, c.box(0.46, 0.10, 0.04, 0.80, r=0.08)), 0.09)
    c.put(np.zeros(3, F), (sh * (1 - c.alpha) * (c.Y > 0.3)).astype(F))
    K.put(c, 'tube', exposure=1.05)
    light(K, 'glow', 260, lambda q: 1.0 * gauss(np.hypot(q.X * 1.25, q.Y * 0.95 + 0.05), 0.42) * 0.8 + 0.22 * gauss(np.hypot(q.X, q.Y), 0.62), '#FF6A1E')


def hub():
    c = K.canvas(480, 2)
    H = lathe(c, [(0, 0.0), (0.80, 0.0), (0.815, 0.05), (0.86, 0.10), (0.93, 0.11), (0.97, 0.09), (1.0, 0.02)], 0.006)
    cop = metal(c, H + 0.001 * circular_streaks(c, 5, 500), COPPER, rough=0.22, grime=0.45, studio=LAB, dirt='#2A140C')
    s = 0.034
    hy = c.Y / (s * 0.866)
    cx = c.X / s + 0.5 * (np.floor(hy) % 2)
    q = np.hypot((cx % 1) - 0.5, ((hy % 1) - 0.5) * 0.9)
    mesh = smooth(0.36, 0.48, q)
    well = flat('#0B0705', c.shape) + rgb('#7A5A40') * (0.10 * mesh * smooth(0.8, 0.5, c.R))[..., None] + rgb('#FF5A14') * (0.035 * gauss(c.R, 0.5))[..., None]
    well = well * (1 - 0.6 * smooth(0.6, 0.81, c.R))[..., None]
    col = mix(well, cop, smooth(0.805, 0.812, c.R)[..., None])
    c.put(col, c.cover(c.R - 0.985), H)
    K.put(c, 'hub')
    # the glass over it
    c = K.canvas(400, 2)
    ax, ay = c.X + 0.07, c.Y + 0.11
    rr = np.hypot(ax, ay)
    win = smooth(0.56, 0.66, rr) * (1 - smooth(0.80, 0.90, rr)) * smooth(0.40, 0.95, -(ax * 0.55 + ay * 0.84) / np.maximum(rr, 1e-4))
    low = smooth(0.70, 0.95, c.R) * smooth(0.3, 1.0, (c.X * 0.5 + c.Y * 0.86) / np.maximum(c.R, 1e-4)) * (1 - smooth(0.95, 1.0, c.R))
    li = 0.40 * win + 0.22 * low
    dk = 0.5 * smooth(0.80, 1.0, c.R) ** 2
    a = clamp(li + dk * (1 - li)) * c.cover(c.R - 0.99)
    c.col = from_srgb(np.ones(c.shape + (3,), F) * (li / np.maximum(li + dk * (1 - li), 1e-4))[..., None])
    c.alpha = a.astype(F)
    K.put(c, 'glass', how='png', tone=False)
    halo(K, 'pulse', 64, 2.0, 0.0, '#FFB070')
    halo(K, 'halo', 220, 2.2, 0.1, '#FF8A3A')


K.run([base, tube, hub])
K.sounds('nixie')
T = 'title'
G = dict(x=0, y=0, blur=7, color='#FF4A0C')
K.write(
    style=dict(shape='orb', material='solid', base='#160D08', accent='#FF8A3A', accent2='#FFD0A0', text='#FFE3C9', border='#B9744A', opacity=0.97, corner=10, font='Bahnschrift', open='fade', speed=1.05, hoverGrow=2,
               iconZoom=1.10, glow=0.7, tilt=0.4, pointer=False, burst=False, shadow=0.7, dim=0.42),
    wheel=dict(hub=94, thickness=106, gap=4, ringgap=18, rim=34, icon=40, crowd=1.52, area=1.10, hubkeep=0.72),
    colors=dict(lit='#FFB77A', hot='#FF5A14', pale='#FFE3C9'), fonts=dict(title='Bahnschrift Light, Bahnschrift, Segoe UI Light', thin='Segoe UI Light, Segoe UI'),
    back=[soft(1.09, 0.025, 66), img('base', 1, intro=intro(0.26, 'out', scale=0.9))],
    ring=[dict(shape='line', **{'in': 'px'}, points=[['sin(rad(a+j*span))*(ringin-14)', '-cos(rad(a+j*span))*(ringin-14)'], ['sin(rad(a+j*span))*(ringout+6)', '-cos(rad(a+j*span))*(ringout+6)']], copies='n', stroke={'type': 'linear', 'stops': [[0, '#E79A6C'], [1, '#7A3E22']]}, width=3.4),
          dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringin-14', to=360, stroke='#A8623E', width=3), dict(shape='arc', **{'in': 'px', 'from': 0}, r='ringout+6', to=360, stroke='#A8623E', width=2.4),
          dict(img('pulse', 15), **{'in': 'px'}, copies='n', angle='a+j*span', radius='ringin-14+(ringout-ringin+20)*fract(time*0.55+rnd(j)*3)', opacity='0.8*motion'),
          dict(img('spill', 1), **{'in': 'px', 'size': '2*(ringout+10)/0.80'}, opacity='0.07+0.015*noise(time*9)')],
    slot=dict(intro=intro(0.22, 'out', 0.06, scale=0.8, y=0.15, stagger=0.03, order='random'),
              under=[img('glow', 2.2, opacity='0.30*hot+launch*1.5'), img('tube', '1.42*(1+0.05*hot)', detail=1.06), img('glow', 1.60, y=-0.06, opacity='(0.10+0.42*sat(hot)+0.04*noise(time*11+i*5))*smooth(0.12,0.2,time-i*0.02)')],
              icon=dict(size=1.0, y=-0.08, zoom=1.10, tone='neon', hot='original', ink='#FF9A4E', paper='#FFE3C9'),
              over=[img('glow', 1.25, y=-0.06, opacity='0.10+0.20*sat(hot)+0.03*noise(time*13+i*7)'), dict(shape='circle', y=0.94, x=-0.36, size=0.12, fill='#3A0D04', when='running'),
                    dict(shape='circle', y=0.94, x=-0.36, size=0.10, fill='#FF7A2E', when='running', opacity='active ? 1 : 0.65', glow=6, glowcolor='#FF5A14'), dict(text='{number}', y=0.945, x='group ? 0.30 : 0', em=0.26, color='#E9B48C', font='thin', when='numbers && number<10 && !kid'),
                    dict(shape='poly', points=[[-0.09, -0.02], [0, -0.10], [0.09, -0.02]], x=0.30, y=0.99, closed=True, fill='#E9B48C', when='group && !numbers')], marks=False, chevron=False, badge=False),

    over=[soft(1.20, 0.05, 66, 0.78, **{'in': 'hub'}), img('halo', 0.34, **{'in': 'hub'}, angle='sel', radius=1.0, opacity='on*(0.85+0.15*noise(time*9))')],
    hub=[img('hub', 1.0, intro=intro(0.32, 'back', scale=0.5)), img('glow', 0.95, opacity='0.22+0.03*noise(time*10)'), dict(text='88:88', y=-0.10, px=38, font='thin', color='#FFB77A/6', opacity='idle')]
    + words('#FFC793', '#FF8A3A', T, px=18, box=(1.22, 0.5), clockpx=38, clocky=-0.10, datey=0.28, datepx=12.5, weight=300, shadow=G) + [img('glass', 0.82)],
    draw=dict(clock=False, shadow=False, text='#FFC793'), tabs=dict(inset=18, text='#FFC793', fill='#FF8A3A/14', on='#C4521A'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#2C1A10'], [1, '#140B06']]}, stroke={'type': 'linear', 'stops': [[0, '#F0B48C'], [0.5, '#7A3E22'], [1, '#D98F62']]}, width=2.6, corner=10, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#1C110A'], [1, '#0D0704']]}, stroke='#C47A4C', width=1.6, corner=9, text='#FFC793'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#2C1A10'], [1, '#140B06']]}, stroke='#B9744A', width=1.8, corner=8, text='pale'),
    onlaunch=[dict(color='#FFB070', light=True, count=34, area='slot', life=[0.2, 0.5], size=[1.5, 3], speed=[140, 520], outward=True, dir=[-80, 80], gravity=500, drag=2, stretch=0.8, fadein=0, fadeout=0.6)],
    onhover=[dict(color='#FF9A4E', light=True, count=4, area='slot', life=[0.15, 0.35], size=[1, 2], speed=[40, 130], outward=True, dir=[-70, 70], drag=2, fadein=0, fadeout=0.7)])
