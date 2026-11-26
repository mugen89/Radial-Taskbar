"""Blueprint: a drawing that draws itself. Only the paper and the stamp are pictures, all lines are drawn by the program."""
from skinkit import *

K = Kit('blueprint', 'Blueprint', 'White lines on blue paper; circles and dimensions draw themselves', ['technical', 'minimal', 'blue'])


def sheet():
    c = K.canvas(1000, 2)
    n = fbm(c.shape, 4, 3, 5)
    fine = fbm(c.shape, 200, 9, 2)
    col = mix(flat('#1B4C99', c.shape), flat('#123a78', c.shape), clamp(0.5 + 0.4 * n + 0.35 * c.R ** 2)[..., None]) * (1 + 0.016 * fine)[..., None]
    # printed grid
    g = np.zeros(c.shape, F)
    for step, w, a in ((0.05, 0.0009, 0.10), (0.25, 0.0014, 0.20)):
        for v in (c.X, c.Y):
            g = np.maximum(g, a * smooth(w * 1.6, w * 0.4, np.abs((v / step + 0.5) % 1 - 0.5) * step))
    ink = Ink(c)
    for k, w in ((0.955, 0.0048), (0.925, 0.0018)):
        ink.line([(-k, -k), (k, -k), (k, k), (-k, k)], w, 235, closed=True)
    for i in range(1, 6):           # margin marks
        x = -0.94 + i * 1.88 / 6
        for p, q in (((x, -0.955), (x, -0.925)), ((x, 0.925), (x, 0.955)), ((-0.955, x), (-0.925, x)), ((0.925, x), (0.955, x))):
            ink.line([p, q], 0.0018, 220)
    for i in range(6):
        x = -0.94 + (i + 0.5) * 1.88 / 6
        for t, px, py in ((chr(65 + i), x, -0.94), (chr(65 + i), x, 0.94), (str(i + 1), -0.94, x), (str(i + 1), 0.94, x)):
            g = np.maximum(g, 0.7 * c.text(t, 0.022, px, py, 'segoeui.ttf'))
    # title block
    x0, y0, x1, y1 = 0.48, 0.80, 0.925, 0.925
    ink.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0032, 235, closed=True)
    ink.line([(x0, 0.862), (x1, 0.862)], 0.0016, 220)
    ink.line([(0.70, 0.862), (0.70, y1)], 0.0016, 220)
    g = np.maximum(g, ink.arr())
    col = mix(col, flat('#E9F2FF', c.shape), (0.86 * g)[..., None])
    # folds, a little worn
    H = np.zeros(c.shape, F)
    for v in (c.X + 0.02 * n * 0.1, c.Y):
        for at in (-0.5, 0.5):
            H += 0.010 * np.exp(-np.abs(v - at) / 0.010)
            col = mix(col, flat('#C9DCF6', c.shape), (0.16 * gauss(v - at, 0.0016) * clamp(0.4 + fbm(c.shape, 40, 7, 3)))[..., None])
    H += 0.00022 * fine + 0.010 * n
    lit = surface(c, H, col, SOFT, rough=0.8, reach=0.05, strength=0.8)
    rag = 0.0022 * fbm(c.shape, 90, 12, 3)
    c.put(lit, c.cover(c.box(0.990, 0.990, r=0.008) + rag), H)
    K.put(c, 'sheet', quality=90, exposure=1.12)
    c = Canvas(160, 1, 1.2)
    c.col[:] = 0
    c.alpha = (0.55 * blur(c.cover(c.box(0.97, 0.97, r=0.02)), 0.07 / c.px)).astype(F)
    K.put(c, 'shadow', how='png', tone=False)


def stamp():
    c = K.canvas(300, 3, 1.0, 0.5)
    t = np.maximum(c.text('APPROVED', 0.315, 0, 0.0, 'impact.ttf'), 0)
    d = c.box(0.95, 0.42, r=0.05)
    frame = np.maximum(smooth(0.006, -0.006, np.abs(d + 0.03) - 0.024), smooth(0.006, -0.006, np.abs(d + 0.10) - 0.008))
    worn = clamp(1.25 - 1.1 * clamp(fbm(c.shape, 40, 5, 4) * 0.9 + 0.25) - 0.5 * clamp(fbm(c.shape, 9, 2, 3) - 0.3))
    c.col[:] = rgb('#E02B35')
    c.alpha = clamp(np.maximum(t, frame) * worn * 1.05).astype(F)
    K.put(c, 'stamp', how='png', tone=False)
    c = K.canvas(220, 3, 1.0, 0.14)          # a pencil, pointing left
    H = np.where(np.abs(c.Y) < 0.085, 0.10 - 0.25 * np.abs(c.Y) + 0.02 * np.cos(c.Y / 0.085 * 4.5), 0)
    cone = (c.X + 1.0) * 0.28
    alb = flat('#E2A021', c.shape)
    alb = np.where((c.X < -0.70)[..., None], rgb('#E9C79A'), alb)
    alb = np.where((c.X < -0.91)[..., None], rgb('#2A2E38'), alb)
    alb = np.where((c.X > 0.80)[..., None], rgb('#C9CDD3'), alb)
    alb = np.where((c.X > 0.90)[..., None], rgb('#D8706B'), alb)
    cov = c.cover(np.maximum(np.abs(c.Y) - np.minimum(0.095, cone), np.abs(c.X) - 0.995))
    c.put(surface(c, H, alb, SOFT, rough=0.4, clear=0.3), cov, H)
    K.put(c, 'pencil', how='png')


K.run([sheet, stamp])
K.sounds('pencil')
W, T = '#EAF3FF', 'title'
draw = 'outcubic(sat(time*2.4))'
def circ(r, w=1.4, a=90, delay=0.0, **kw):
    return dict({'shape': 'arc', 'in': 'px', 'r': r, 'from': 0, 'to': '360*outcubic(sat((time-%g)*2.2))' % delay, 'stroke': W + '/%d' % a, 'width': w}, **kw)
K.write(
    style=dict(shape='orb', material='solid', base='#15417F', accent='#FFFFFF', accent2='#8FC0FF', text='#EAF3FF', border='#BFD8FF', opacity=0.98, corner=2, font='Segoe Print', open='fade', speed=1.1, hoverGrow=0,
               iconZoom=1.10, glow=0, tilt=0.15, pointer=False, burst=False, shadow=0, dim=0.28),
    wheel=dict(hub=92, thickness=88, gap=6, ringgap=12, rim=26, icon=44, crowd=1.5, area=1.32, hubkeep=0.82),
    colors=dict(chalk=W, blue='#15417F', red='#E02B35'),
    fonts=dict(title='Segoe Print, Ink Free, Segoe UI', digits='Bahnschrift, Segoe UI'),
    back=[img('shadow', 1.40, x=0.02, y=0.035, opacity='sat(open)', rotate=-1.2), img('sheet', 1.16, rotate=-1.2, intro=intro(0.26, 'out', scale=0.94, rotate=-5)),
          dict(shape='line', points=[['-1.02*' + draw, 0], ['1.02*' + draw, 0]], stroke=W + '/35', width=1, dash=[14, 6]),
          dict(shape='line', points=[[0, '-1.02*' + draw], [0, '1.02*' + draw]], stroke=W + '/35', width=1, dash=[14, 6]),
          dict(text='{profile}', x=0.82, y=0.965, box=[0.46, 0.06], px=12, color=W, font=T, opacity='smooth(0.25,0.5,time)'),
          dict(text='{date}', x=0.685, y=1.035, box=[0.24, 0.06], px=9.5, color=W + '/85', font=T, opacity='smooth(0.3,0.55,time)'),
          dict(text='{hh}:{mm}', x=0.945, y=1.03, box=[0.2, 0.06], px=10.5, color=W + '/85', font=T, opacity='smooth(0.3,0.55,time)')],
    ring=[circ('ringout+3', 2.0, 92, 0.02), circ('ringout+9', 0.9, 60, 0.06), circ('(ringin+ringout)/2', 0.9, 45, 0.10, dash=[12, 4, ]), circ('ringin-3', 1.2, 70, 0.04),
          {'shape': 'ticks', 'in': 'px', 'inner': 'ringout+11', 'outer': 'ringout+17', 'count': 72, 'major': 6, 'stroke': W + '/55', 'width': 1, 'opacity': 'smooth(0.2,0.45,time)'},
          {'shape': 'line', 'in': 'px', 'points': [['sin(rad(a+j*span))*(ringin-2)', '-cos(rad(a+j*span))*(ringin-2)'], ['sin(rad(a+j*span))*(ringout+12)', '-cos(rad(a+j*span))*(ringout+12)']], 'copies': 'n', 'stroke': W + '/30', 'width': 1, 'dash': [9, 4], 'opacity': draw}],
    slot=dict(intro=intro(0.24, 'out', 0.10, scale=0.75, stagger=0.02, order='ring'),
              under=[dict(shape='circle', size='0.94+0.06*hot', fill='#F4F8FF', opacity='sat(hot)*0.96'), dict(shape='circle', size=0.94, fill='#15417F/55', opacity='1-sat(hot)'),
                     dict(shape='arc', r='0.94+0.04*hot', **{'from': 0}, to='360*in', stroke=W, width='1.6+0.9*hot'), dict(shape='arc', r=1.06, **{'from': '-30+time*40'}, to='30+time*40', stroke=W, width=1.6, opacity='sat(hot)', copies=4, angle='j*90', turns=True)]
              + [dict(shape='line', points=[[x * 1.02, y * 1.02], [x * 1.20, y * 1.20]], stroke=W + '/70', width=1.2) for x, y in ((1, 0), (-1, 0), (0, 1), (0, -1))],
              icon=dict(size=1.10, zoom=1.10, tone='duo', hot='original', ink='#123A78', paper='#F2F8FF'),
              over=[dict(image='stamp', size=[1.9, 0.95], rotate='-14+seed*8', opacity='step(0.02,launch)', scale='mix(1.7,1,outcubic(sat(launch*4)))'),
                    dict(shape='circle', y=0.94, size=0.13, fill='#15417F', stroke=W, width=1.4, when='running'), dict(shape='circle', y=0.94, size=0.07, fill=W, when='active')]
              + badge('#15417F', W, 'digits', stroke=W) + [dict(shape='poly', points=[[0.52, -0.78], [0.80, -0.78], [0.80, -0.50]], stroke=W, width=1.8, when='group && !numbers'), dict(text='+', x=0, y=-0.95, em=0.40, color=W, font='digits', when='group')],
              marks=False, chevron=False, badge=False),
    over=[dict(shape='line', **{'in': 'px'}, points=[['sin(rad(sel))*(hub+3)', '-cos(rad(sel))*(hub+3)'], ['sin(rad(sel))*(hub+15)', '-cos(rad(sel))*(hub+15)']], stroke=W, width=1.6, opacity='on*0.9'),
          dict(shape='poly', **{'in': 'px'}, angle='sel', radius='radius-4', turns=True, points=[[-4, 9], [0, -2], [4, 9]], closed=True, fill=W, opacity='on'),
          img('pencil', [0.24, 0.0336], angle='sel', radius=0.93, rotate='sel-90+5*sin(time*9)*on', pivot=[0, 0.5], opacity='on', intro=intro(0.2))],
    hub=[dict(shape='circle', size=0.97, fill='#15417F/70'), {'shape': 'arc', 'r': 0.97, 'from': 0, 'to': '360*' + draw, 'stroke': W, 'width': 2}, {'shape': 'arc', 'r': 0.91, 'from': 0, 'to': '360*' + draw, 'stroke': W + '/60', 'width': 1},
         {'shape': 'arc', 'r': 0.83, 'from': 0, 'to': 'sel', 'stroke': W + '/80', 'width': 1.2, 'opacity': 'on', 'when': 'sel>1'},
         {'shape': 'ticks', 'inner': 0.91, 'outer': 0.97, 'count': 60, 'major': 5, 'stroke': W + '/70', 'width': 1, 'opacity': draw}] + words(W, '#A9CCFF', T, px=19, box=(1.36, 0.56), clockpx=31, datepx=12.5, weight=600, subpx=12),
    fan=[{'shape': 'ring', 'inner': 'ringin-2', 'outer': 'ringout+3', 'from': 'a-span/2-2', 'to': 'a+span/2+2', 'fill': '#15417F/92', 'stroke': W, 'width': 1.6, 'in': 'px'}],
    draw=dict(clock=False, shadow=False, text=W, fan=False), tabs=dict(inset=10, text=W, fill='#FFFFFF/10', on='#FFFFFF/35'),
    panel=dict(fill='#15417F', stroke=W, width=1.8, corner=2, text=W), tag=dict(fill='#15417F', stroke=W, width=1.6, corner=2, text=W), tile=dict(fill='#15417F', stroke=W, width=1.6, corner=2, text=W),
    onlaunch=[dict(color='#E02B35', count=14, area='slot', life=[0.25, 0.5], size=[1.5, 3], speed=[80, 260], outward=True, dir=[-80, 80], drag=3, fadein=0, fadeout=0.6)],
    onhover=[dict(color='#EAF3FF', count=3, area='slot', life=[0.3, 0.6], size=[1, 2], speed=[10, 40], dir=[90, 270], gravity=60, fadein=0, fadeout=0.6)])
