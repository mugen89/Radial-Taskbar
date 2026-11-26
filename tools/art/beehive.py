"""Beehive: wax comb full of honey; apps sit in honey-filled cells, a bee walks to your choice, honey drips on launch."""
from lineup import *

K = Kit('beehive', 'Beehive', 'Wax comb full of honey: apps sit in honey-filled cells and a bee walks to your choice', ['nature', 'warm', 'golden'])
K.flag(halo='light')


def hexcells(c, size):
    """Distance to the nearest hexagon edge on a flat-topped hex grid, and the cell's random value."""
    q = c.X / size
    r = c.Y / size
    s3 = math.sqrt(3)
    x, y = q, r
    gx = x * 2 / 3
    gy = (-x / 3 + s3 / 3 * y)
    # cube rounding
    cx, cz = gx, gy
    cy = -cx - cz
    rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
    dx, dy, dz = np.abs(rx - cx), np.abs(ry - cy), np.abs(rz - cz)
    fix_x = (dx > dy) & (dx > dz)
    fix_y = (~fix_x) & (dy > dz)
    rx = np.where(fix_x, -ry - rz, rx)
    ry = np.where(fix_y, -rx - rz, ry)
    rz = np.where(~fix_x & ~fix_y, -rx - ry, rz)
    px = rx * 1.5
    py = (rz + rx / 2) * s3
    lx, ly = np.abs(x - px), np.abs(y - py)
    edge = np.maximum(lx * 0.5 + ly * s3 / 2, lx) - 1.0
    seed = np.sin(rx * 12.9898 + rz * 78.233) * 43758.5453
    return edge * size, seed - np.floor(seed)


def comb():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    e, v = hexcells(c, 0.075)
    wall = smooth(-0.010, -0.004, e)
    inside = clamp(-e / 0.06)
    capped = v > 0.62
    H = 0.03 * wall + np.where(capped, 0.02 * np.sqrt(inside), -0.02 * inside)
    honey = mix(flat('#C8780A', c.shape), flat('#F2B83A', c.shape), clamp(0.3 + 0.6 * inside)[..., None])
    wax = flat('#F2D88A', c.shape)
    alb = np.where(capped[..., None], wax * (0.9 + 0.1 * fbm(c.shape, 40, 3, 2))[..., None], honey)
    alb = mix(alb, flat('#E8C060', c.shape), wall[..., None])
    col = surface(c, H, alb, WARM, rough=0.15, clear=0.9, reach=0.08)
    col = col * (1 - 0.3 * smooth(0.85, 1.0, c.R))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'comb')


def cells():
    def one(c, k):
        d = c.regular(6, 0.90, rot=TAU / 12)
        inside = clamp(-d / 0.5)
        wall = smooth(-0.14, -0.08, d)
        H = 0.08 * wall - 0.06 * inside * (1 - wall)
        honey = mix(flat('#B8680A', c.shape), flat('#FFC84A', c.shape), clamp(0.2 + 0.7 * inside + 0.2 * (-c.Y))[..., None])
        if k:
            honey = mix(honey, flat('#FFE08A', c.shape), 0.25)
        alb = mix(honey, flat('#F2D88A', c.shape), wall[..., None])
        col = surface(c, H, alb, WARM, rough=0.12, clear=1.0, reach=0.08)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'cells', 2, one)


def pool():
    c = K.canvas(460, 2)
    d = c.regular(6, 0.98, rot=TAU / 12)
    inside = clamp(-d / 0.4)
    wall = smooth(-0.12, -0.06, d)
    H = 0.06 * wall - 0.03 * inside * (1 - wall)
    honey = mix(flat('#D88A1A', c.shape), flat('#FFD86A', c.shape), clamp(0.4 + 0.5 * inside - 0.2 * c.Y)[..., None])
    alb = mix(honey, flat('#F2D88A', c.shape), wall[..., None])
    col = surface(c, H, alb, WARM, rough=0.1, clear=1.0, reach=0.08)
    c.put(col, c.cover(d), H)
    K.put(c, 'pool')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE08A')
    c = K.canvas(60, 4, 1.0, 1.0)  # a bee seen from above, head outward
    body = np.hypot(c.X / 0.32, (c.Y - 0.15) / 0.55) - 1
    head = c.circle(0.20, 0, -0.55)
    stripes = (np.floor((c.Y + 0.6) * 5) % 2) > 0
    alb = np.where(stripes[..., None], rgb('#1A1408'), rgb('#F2B81E')) * np.ones(c.shape + (3,), F)
    alb = np.where((head < 0)[..., None], rgb('#1A1408'), alb)
    wings = np.minimum(np.hypot((c.X - 0.42) / 0.36, (c.Y + 0.05) / 0.22) - 1, np.hypot((c.X + 0.42) / 0.36, (c.Y + 0.05) / 0.22) - 1)
    c.put(flat('#E8F4FF', c.shape), c.cover(wings * 0.3) * 0.55)
    bd = np.minimum(body * 0.3, head)
    c.put(surface(c, 0.15 * clamp(-bd / 0.2), alb.astype(F), WARM, rough=0.4), c.cover(bd))
    K.put(c, 'bee', how='png')
    c = K.canvas(40, 4, 1.0, 1.3)
    dr = np.minimum(c.circle(0.62, 0, 0.5), c.poly([(0, -1.25), (0.58, 0.30), (-0.58, 0.30)]))
    c.put(surface(c, 0.3 * np.sqrt(clamp(-dr / 0.6)), flat('#E89A1A', c.shape), WARM, rough=0.1, clear=1.0), c.cover(dr))
    K.put(c, 'drop', how='png')


K.run([comb, cells, pool])
P = dict(base='#3A2408', accent='#F2A81E', accent2='#FFE08A', text='#3A2408', sub='#6A4A18', panel=('#5A3A10', '#3A2408'), stroke='#F2A81E', tile=('#FFF2C8', '#F2D88A'), tilestroke='#B8801A',
         ink='#3A2408', paneltext='#FFF2C8', dim=0.32, font='Constantia, Georgia', badge='#3A2408', badgeink='#FFE08A')
finish(K, P, sounds='drip',
       back=[soft(1.08, 0.03, 60), img('comb', 1.0, intro=intro(0.4, 'out', scale=0.92))],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'), img('cells', '1.06*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.56, zoom=1.18, shadow=dict(x=0, y=1, blur=2, color='#3A2408/50')),
       hub=[soft(1.0, 0.05, 40), img('pool', 1.04, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('bee', [0.11, 0.11], **{'in': 'hub'}, angle='sel', radius='1.12+0.02*sin(time*9)', rotate='sel+6*sin(time*20)', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=3, color='#FFE08A')),
       tabs=dict(inset=13, text='#FFF2C8', fill='#00000022', on='#F2A81E/85'),
       style=dict(shape='hex', open='bloom', tilt=0.3),
       onlaunch=[dict(image='drop', count=10, area='slot', life=[0.6, 1.0], size=[5, 9], speed=[40, 140], outward=True, dir=[-50, 50], gravity=900, fadein=0, fadeout=0.3)],
       onhover=[dict(image='bee', count=1, area='slot', life=[0.8, 1.2], size=[10, 12], speed=[60, 120], outward=True, dir=[-60, 60], sway=40, swayhz=3, fadein=0.1, fadeout=0.4)],
       screen=dict(effect='fireflies', color='#F2C84A', color2='#FFF2B0', density=0.5, speed=0.6, size=0.7))
