"""Zen Garden: raked sand in a cedar frame, stones, moss, and petals."""
from skinkit import *

K = Kit('zen', 'Zen Garden', 'Raked sand, smooth stones and a drifting petal', ['nature', 'calm', 'light'])
K.flag(stones=dict(cols=4), petals=dict(cols=4))
SUN = Studio(lights=[((-0.62, -0.60, 0.50), 0.40, '#FFF3DC', 4.4), ((0.75, -0.35, 0.50), 0.35, '#E6F0FF', 1.2), ((0.10, 0.85, 0.45), 0.5, '#FFE6C4', 0.7)], sky='#E8EEF6', floor='#6A5A48', ambient=0.52)
PITCH = 0.031


def grooves(d, pitch=PITCH):
    """Ridges left by a rake, along lines of equal distance."""
    t = (d / pitch) % 1
    return np.abs(t - 0.5) * 2 * 0.5 + 0.5 * (0.5 - 0.5 * np.cos(t * TAU))


def sand(c, seed):
    g = fbm(c.shape, 420, seed, 2)
    alb = mix(flat('#EBDDC0', c.shape), flat('#D8C4A0', c.shape), clamp(0.5 + 0.35 * fbm(c.shape, 5, seed + 1, 4))[..., None]) * (1 + 0.07 * g)[..., None]
    dark = (white(c.shape, seed + 2) > 2.3)
    return alb * (1 - 0.25 * blur(dark.astype(F), 0.6 * c.ss))[..., None], g


def garden():
    c = K.canvas(1100, 2)
    alb, g = sand(c, 3)
    H = 0.0155 * grooves(c.R + 0.0015 * fbm(c.shape, 8, 4, 3)) + 0.0010 * g
    H = np.where(c.R > 0.895, 0.004 + 0.0016 * g, H)
    # pebbles and moss along the frame
    d1, d2, v = worley(c.X, c.Y, 34, 5, True)
    band = smooth(0.888, 0.898, c.R) * smooth(0.952, 0.940, c.R)
    peb = smooth(0.40, 0.30, d1) * band
    H = H + peb * (0.018 * np.sqrt(clamp(1 - (d1 / 0.42) ** 2)))
    pc = mix(flat('#6E6C68', c.shape), flat('#B9B2A4', c.shape), v[..., None])
    alb = mix(alb, pc, peb[..., None])
    mossf = clamp(fbm(c.shape, 7, 12, 4) * 1.6 + 0.1) * smooth(0.90, 0.935, c.R) * smooth(0.96, 0.945, c.R)
    alb = mix(alb, mix(flat('#4F6A25', c.shape), flat('#7E9A3C', c.shape), clamp(0.5 + fbm(c.shape, 160, 13, 2))[..., None]), clamp(mossf * 1.2)[..., None])
    H = H + 0.016 * clamp(mossf) * (0.6 + 0.4 * fbm(c.shape, 190, 14, 2))
    frame = c.R > 0.948
    tex, wg = wood(c, 7, 1.8, '#8A5E3A', '#3F2717', rot=0.4)
    arcs = ramp(clamp(0.5 + 0.35 * circular_streaks(c, 8, 1000) + 0.12 * fbm(c.shape, 24, 9, 3)), '#3B2416', '#6E4628', '#A06E42')
    H = np.where(frame, lathe(c, [(0.940, 0.0), (0.950, 0.052), (0.958, 0.058), (0.990, 0.058), (1.0, 0.035)]), H)
    alb = np.where(frame[..., None], arcs, alb)
    k = ((c.A / TAU + 0.5) * 6) % 1
    H = H - 0.006 * smooth(0.4975, 0.4995, np.abs(k - 0.5)) * frame
    col = surface(c, H, alb, SUN, rough=0.8, reach=0.07, slope=0.75, ao_r=(0.006, 0.015, 0.05), clear=0.0)
    c.put(col, c.cover(c.R - 0.998), H)
    K.put(c, 'garden', exposure=0.98, quality=88)


def ripple():
    """Rings raked round a stone: covers the garden's own rings, fading out at the edge."""
    for name, seed in (('ripple', 5),):
        c = K.canvas(380, 2)
        alb, g = sand(c, 21)
        H = 0.052 * grooves(c.R, 0.135) + 0.003 * g
        col = surface(c, H, alb, SUN, rough=0.85, reach=0.16, slope=0.75, ao_r=(0.015, 0.04, 0.1))
        t = (c.R / 0.098) % 1
        edge = smooth(0.985, 0.93, c.R)
        c.put(col * (1 - 0.45 * gauss(c.R - 0.95, 0.03))[..., None], edge)
        K.put(c, name, exposure=0.98)


def stones():
    ims = []
    for k, (a, b) in enumerate((('#8C8F92', '#5D6165'), ('#A79E90', '#6F675B'), ('#6F7C82', '#434D53'), ('#9A8E86', '#5C524B'))):
        c = K.canvas(240, 3)
        g = rng(60 + k)
        ph, am = g.random(3) * TAU, 0.02 + 0.04 * g.random(3)
        rr = 0.80 * (1 + sum(am[j] * [1.0, 0.6, 0.3][j] * np.sin((j + 2) * c.A + ph[j]) for j in range(3)))
        d = c.R - rr
        t = clamp(-d / 0.80)
        H = 0.34 * np.sqrt(clamp(1 - (1 - t) ** 2.0))
        n = fbm(c.shape, 10, 70 + k, 5)
        vein = gauss(c.X * math.cos(k) + c.Y * math.sin(k) + 0.12 * fbm(c.shape, 4, 80 + k, 3) - 0.2, 0.022)
        alb = mix(flat(a, c.shape), flat(b, c.shape), clamp(0.5 + 0.5 * n)[..., None])
        alb = mix(alb, flat('#DAD5CB', c.shape), (0.55 * vein)[..., None]) * (1 + 0.08 * fbm(c.shape, 120, 90 + k, 2))[..., None]
        col = surface(c, H + 0.006 * n, alb, SUN, rough=0.6, clear=0.10, shadows=False)
        sh = 0.60 * gauss(np.maximum(0, np.hypot(c.X - 0.07, c.Y - 0.10) - rr * 0.97), 0.10) * smooth(1.0, 0.96, np.maximum(np.abs(c.X), np.abs(c.Y)))
        c.put(flat('#2A1E10', c.shape), sh.astype(F))
        c.put(col, c.cover(d), H)
        ims.append(c.image())
    K.sheet(ims, 4, 'stones')


def middle():
    c = K.canvas(480, 2)
    rr = 0.93 * (1 + 0.018 * np.sin(3 * c.A + 1) + 0.012 * np.sin(5 * c.A))
    d = c.R - rr
    t = clamp(-d / 0.35)
    n = fbm(c.shape, 7, 5, 6)
    H = 0.16 * np.sqrt(clamp(1 - (1 - t) ** 2)) + 0.008 * n + 0.004 * fbm(c.shape, 60, 6, 3)
    alb = mix(flat('#5A6064', c.shape), flat('#343A3E', c.shape), clamp(0.5 + 0.55 * n)[..., None])
    alb = mix(alb, flat('#8E9092', c.shape), (0.5 * gauss(c.X * 0.8 - c.Y * 0.6 + 0.10 * fbm(c.shape, 3, 8, 3) + 0.35, 0.012))[..., None])
    moss = clamp(fbm(c.shape, 6, 14, 5) * 1.5 - 0.15 + 0.9 * smooth(0.70, 0.98, c.R) * smooth(-0.6, 0.8, (c.X * 0.7 + c.Y * 0.7))) * smooth(0.60, 0.82, c.R)
    H = H + 0.03 * clamp(moss) * (0.6 + 0.4 * fbm(c.shape, 130, 15, 2))
    alb = mix(alb, mix(flat('#41591E', c.shape), flat('#86A23F', c.shape), clamp(0.5 + fbm(c.shape, 120, 16, 2))[..., None]), clamp(moss * 1.3)[..., None])
    col = surface(c, H, alb, SUN, rough=0.65, clear=0.06, reach=0.12)
    c.put(col, c.cover(d), H)
    K.put(c, 'boulder', exposure=0.95)


def bits():
    ims = []
    for k in range(4):
        c = K.canvas(64, 4)
        a = k * 1.1
        pts = turned(bez((0, 0.9), (0.85, 0.3), (0.55, -0.85), (0.08, -0.78), 14) + [(0, -0.6)] + bez((-0.08, -0.78), (-0.55, -0.85), (-0.80, 0.3), (0, 0.9), 14), a, 0.92)
        cov = Ink(c).poly(pts).arr(0.02)
        t = clamp(0.5 + 0.5 * (c.X * math.sin(a) - c.Y * math.cos(a)))
        c.col = ramp(t, '#F3A9BE', '#FBD6E0', '#FFF3F6')
        c.alpha = cov
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'petals')
    c = K.canvas(150, 4)                     # a whole blossom
    c2 = np.zeros(c.shape, F)
    col = flat('#FBD6E0', c.shape)
    for k in range(5):
        a = k * TAU / 5 + 0.2
        pts = turned(bez((0, 0), (0.42, -0.25), (0.46, -0.90), (0.07, -0.92), 12) + [(0, -0.78)] + bez((-0.07, -0.92), (-0.46, -0.90), (-0.42, -0.25), (0, 0), 12), a, 0.98)
        cov = Ink(c).poly(pts).arr(0.01)
        t = clamp((c.X * math.sin(a) - c.Y * math.cos(a)) / 0.95)
        col = mix(col, ramp(t, '#E0708F', '#FBC6D5', '#FFF0F4') * (0.92 + 0.08 * smooth(0.0, 0.1, np.abs(c.X * math.cos(a) + c.Y * math.sin(a))))[..., None], cov[..., None])
        c2 = np.maximum(c2, cov)
    ink = Ink(c)
    for k in range(14):
        a = k * TAU / 14
        ink.line([(0, 0), turned([(0, -0.36)], a)[0]], 0.022)
        ink.dot(*turned([(0, -0.38)], a)[0], 0.035)
    col = mix(col, flat('#C9304F', c.shape), (ink.arr(0.006) * 0.85)[..., None])
    c.col, c.alpha = col.astype(F), c2
    K.put(c, 'blossom', how='png', tone=False)
    c = K.canvas(90, 3, 1.0, 2.4)           # a bamboo leaf as pointer
    cov = Ink(c).poly(bez((0, -2.3), (0.75, -1.2), (0.55, 1.2), (0.05, 2.2), 20) + bez((-0.05, 2.2), (-0.55, 1.2), (-0.75, -1.2), (0, -2.3), 20)).arr(0.02)
    c.col = mix(flat('#4E7A2C', c.shape), flat('#8FB84E', c.shape), smooth(-0.1, 0.1, c.X)[..., None]) * (0.9 + 0.1 * np.sin((c.X * 2 + c.Y) * 24))[..., None]
    c.alpha = cov
    K.put(c, 'leaf', how='png', tone=False)


K.run([garden, ripple, stones, middle, bits])
K.sounds('sand')
T = 'title'
K.write(
    style=dict(shape='orb', material='solid', base='#4A4238', accent='#E58BA5', accent2='#8FB84E', text='#FBF4E6', border='#A08A68', opacity=0.97, corner=10, font='Candara', open='bloom', speed=0.95, hoverGrow=3,
               iconZoom=1.12, glow=0, tilt=0.3, pointer=False, burst=False, shadow=0.55, dim=0.26),
    wheel=dict(hub=92, thickness=94, gap=5, ringgap=8, rim=36, icon=42, crowd=1.5, area=1.10, hubkeep=0.74),
    colors=dict(pale='#FBF4E6', moss='#C6DB8E', pink='#FFD3DF'), fonts=dict(title='Candara, Segoe UI'),
    back=[soft(1.10, 0.025, 60), img('garden', 1, rotate='(1-open)*10', intro=intro(0.34, 'out', scale=0.88))],
    slot=dict(intro=intro(0.40, 'out', 0.08, scale=0.4, stagger=0.02, order='both'),
              under=[img('ripple', '(1.30+0.30*hot)*(1+0.5*launch)', rotate='i*40', opacity='0.96'), img('ripple', '1.30*(1+0.9*fract(time*0.45))', opacity='hot*0.45*(1-fract(time*0.45))', when='hot>0.02'),
                     img('stones', '1.0*(1+0.06*hot-0.04*press)', frame='(i+ring)%4', rotate='0', detail=1.06)],
              icon=dict(size=0.98, zoom=1.16, shadow=dict(x=1, y=2, blur=3, color='black/55')),
              over=[img('blossom', '0.50*outback(sat(hot))', x=0.56, y=0.52, rotate='seed*70+20*hot', opacity='sat(hot*2)'), img('blossom', 0.30, x=-0.56, y=0.58, rotate='seed*70', when='running'), img('blossom', '0.40+0.02*sin(time*2)', x=-0.56, y=0.58, rotate='time*10', when='active')]
              + badge('#4A4238', '#FBF4E6', T, x=0.62, y=-0.62) + groupmark('#FBF4E6', -0.80, 0.12), marks=False, chevron=False, badge=False),
    over=[soft(1.16, 0.06, 55, 0.78, **{'in': 'hub'}), img('leaf', [0.085, 0.204], **{'in': 'hub'}, angle='sel', radius=1.08, rotate='sel+8*sin(time*2)', opacity='on', scale='0.5+0.5*on')],
    hub=[img('boulder', 1.02, intro=intro(0.38, 'back', scale=0.5))] + words('pale', 'moss', T, px=18, box=(1.22, 0.5), clockpx=31, datepx=12.5, shadow=dict(x=0, y=1, blur=3, color='black/70')),
    draw=dict(clock=False, shadow=False, text='pale'), tabs=dict(inset=13, text='pale', fill='#FFFFFF/14', on='#E58BA5/85'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#57503F'], [1, '#3B342A']]}, stroke={'type': 'linear', 'stops': [[0, '#B58A5A'], [0.5, '#5F3F25'], [1, '#93693F']]}, width=4, corner=11, text='pale'),
    tag=dict(fill={'type': 'linear', 'stops': [[0, '#5A6064'], [1, '#3A4044']]}, stroke='#2A2E31', width=1.4, corner=11, text='pale'),
    tile=dict(fill={'type': 'linear', 'stops': [[0, '#EBDDC0'], [1, '#D3BF98']]}, stroke='#6E4628', width=2.4, corner=8, text='#3B342A'),
    particles=[dict(image='petals', rate=0.9, max=9, area='stage', life=[3, 5.5], size=[6, 11], speed=[6, 16], dir=[110, 200], gravity=6, spin=[-70, 70], sway=24, swayhz=0.35, opacity=0.95, fadein=0.15, fadeout=0.3)],
    onlaunch=[dict(image='petals', count=34, area='slot', life=[0.6, 1.2], size=[7, 14], speed=[80, 320], outward=True, dir=[-120, 120], gravity=120, drag=2.2, sway=20, swayhz=0.8, spin=[-260, 260], fadein=0, fadeout=0.5)],
    onhover=[dict(color='#EBDDC0', count=6, area='slot', life=[0.25, 0.5], size=[1, 2.2], speed=[20, 70], outward=True, dir=[-60, 60], drag=3, fadein=0, fadeout=0.7)])
