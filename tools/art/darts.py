"""Dartboard: sisal, wire and numbers; apps sit in wire rings, the bull in the middle, a dart points at your choice."""
from lineup import *

K = Kit('darts', 'Dartboard', 'Sisal, wire and numbers: apps sit in wire rings round the bull while a dart points at your choice', ['game', 'pub', 'bold'])
K.flag(halo='light', thud='light')
CREAM, BLACK, RED, GREEN = '#E8DCB8', '#1A1A18', '#C8282A', '#1E7A3A'


def board():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    seg = (np.floor((c.A / TAU + 0.5) * 20 + 0.5) % 2).astype(int)
    base = np.where(seg[..., None] == 0, rgb(BLACK), rgb(CREAM)) * np.ones(c.shape + (3,), F)
    ring2 = np.where(seg[..., None] == 0, rgb(RED), rgb(GREEN)) * np.ones(c.shape + (3,), F)
    col = base.copy()
    for r0, r1 in ((0.55, 0.60), (0.82, 0.87)):
        m = ((c.R > r0) & (c.R < r1))[..., None]
        col = np.where(m, ring2, col)
    sisal = 0.85 + 0.15 * fbm(c.shape, 120, 3, 2) + 0.06 * np.sin(c.A * 400)
    col = col * sisal[..., None]
    wires = np.zeros(c.shape, F)
    for r in (0.55, 0.60, 0.82, 0.87):
        wires = np.maximum(wires, gauss(c.R - r, 0.0025))
    a = ((c.A / TAU + 0.5) * 20 + 0.5) % 1
    wires = np.maximum(wires, gauss(np.abs(a - 0.5) * c.R * TAU / 20 - c.R * TAU / 40 + 0 * c.R, 0.0025) * smooth(0.12, 0.14, c.R) * smooth(0.88, 0.87, c.R))
    outer = smooth(0.87, 0.875, c.R)
    col = mix(col, flat('#141412', c.shape), outer[..., None])
    im = Image.new('L', (c.w, c.h), 0)
    dr = ImageDraw.Draw(im)
    f = load_font('segoeuib.ttf', 0.07 / c.px)
    for k, n in enumerate([20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]):
        x, y = c.polar(k * TAU / 20, 0.935)
        dr.text(((x + 1) * c.w / 2, (y + 1) * c.h / 2), str(n), font=f, fill=255, anchor='mm')
    nums = np.asarray(im, F) / 255
    col = mix(col, flat('#F2F2EE', c.shape), nums[..., None])
    col = col + V([0.8, 0.8, 0.85]) * (0.8 * wires)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'board')


def rings():
    def one(c, k):
        d = c.R - 0.86
        col = flat('#141412', c.shape) * (0.8 + 0.2 * fbm(c.shape, 40, 3 + k, 2))[..., None]
        wire = gauss(c.R - 0.84, 0.012) + gauss(c.R - 0.70, 0.008) * 0.6
        col = col + V([0.85, 0.85, 0.9]) * wire[..., None]
        c.put(col, c.cover(d) * 0.88)
        return c
    plate(K, 'rings', 2, one)


def bull():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = np.where((c.R < 0.45)[..., None], rgb(RED), rgb(GREEN)) * np.ones(c.shape + (3,), F)
    col = col * (0.75 + 0.15 * fbm(c.shape, 60, 3, 2))[..., None] * (1 - 0.35 * smooth(0.6, 0.0, c.R))[..., None]
    col = col + V([0.85, 0.85, 0.9]) * (gauss(c.R - 0.45, 0.006) + gauss(c.R - 0.93, 0.008))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'bull')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFFFFF')
    light(K, 'thud', 200, lambda c: gauss(c.R - 0.75, 0.08), tint='#FFFFFF')
    c = K.canvas(40, 4, 1.0, 3.4)  # a dart, its point toward the middle
    barrel = c.capsule(0, 0.2, 0, 1.5, 0.22)
    point = c.taper(0, 1.5, 0.1, 0, 3.2, 0.02)
    shaft = c.capsule(0, -1.2, 0, 0.2, 0.08)
    flight = c.poly([(0, -1.0), (0.8, -3.2), (0, -2.6), (-0.8, -3.2)])
    H = 0.2 * np.sqrt(clamp(1 - (c.X / 0.25) ** 2))
    col = np.where((point < 0)[..., None], rgb('#D8DCE2'), np.where((barrel < 0)[..., None], rgb('#A8AEB8'), np.where((flight < 0)[..., None], rgb('#C8282A'), rgb('#1A1A1A')))) * np.ones(c.shape + (3,), F)
    d = np.minimum(np.minimum(barrel, point), np.minimum(shaft, flight))
    c.put(surface(c, H, col.astype(F), COOL, rough=0.3, metal=0.5), c.cover(d), H)
    K.put(c, 'dart', how='png')


K.run([board, rings, bull])
P = dict(base='#141412', accent=RED, accent2=GREEN, text='#FFFFFF', sub='#E8DCB8', panel=('#2A2A26', '#141412'), stroke='#A8AEB8', tile=('#E8DCB8', '#C8BC98'), tilestroke='#6A6458',
         ink='#141412', dim=0.38, font='Bahnschrift, Segoe UI', badge='#E8DCB8', badgeink='#141412')
finish(K, P, sounds='wood',
       back=[soft(1.08, 0.03, 70), img('board', 1.0, rotate='(1-open)*-90', intro=intro(0.4, 'out', scale=0.92))],
       under=[img('thud', '1.5*(1+0.8*launch)', opacity='0.4*hot+launch'), img('rings', '0.96*(1+0.04*hot-0.04*press)', frame='hot>0.5 ? 1 : 0')],
       icon=dict(size=0.62, zoom=1.16, shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('bull', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('dart', [0.05, 0.17], **{'in': 'hub'}, angle='sel', radius=1.18, rotate='sel+180', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=1, blur=4, color='black/90')),
       style=dict(open='spin', tilt=0.3),
       onlaunch=[dict(color='#E8DCB8', count=16, area='slot', life=[0.3, 0.6], size=[1, 2.4], speed=[60, 200], outward=True, dir=[-90, 90], gravity=400, fadein=0, fadeout=0.5)])
