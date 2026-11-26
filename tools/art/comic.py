"""Comic: pop-art print. Four inks on cheap paper, each a little out of place, with halftone dots and wobbly outlines."""
import sys
from artkit import *
from pack import Pack

P = Pack('comic', sys.argv)
HERE = os.path.dirname(os.path.abspath(__file__))
BANGERS = os.path.join(HERE, 'fonts', 'bangers', 'Bangers-Regular.ttf')


def srgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], F) / 255


PAPER = srgb('#FFFAEC')
INKS = {'C': srgb('#1FA9E2'), 'M': srgb('#EF2C6B'), 'Y': srgb('#FFDF22'), 'K': srgb('#17120F')}


# ------------------------------------------------------------------ the press
class Print:
    """Coverage of four inks and of the paper, put together like a print: darker where inks lie on each other."""
    OFF = {'C': (-0.8, 0.5), 'M': (0.9, 0.3), 'Y': (0.2, -0.9), 'K': (0.0, 0.0)}     # out of register, in final pixels

    def __init__(self, size, ss=3, extent=1.0, aspect=1.0, seed=1):
        self.c = Canvas(size, ss, extent, aspect)
        self.seed = seed
        self.p = {k: np.zeros(self.c.shape, F) for k in 'CMYK'}
        self.alpha = np.zeros(self.c.shape, F)
        self.wob = fbm(self.c.shape, 7, seed + 1, 3)
        self.wob2 = fbm(self.c.shape, 13, seed + 2, 3)

    # ---- laying ink
    def put(self, cov, C=0.0, M=0.0, Y=0.0, K=0.0, paper=True):
        """A shape in these inks; whatever was below is knocked out."""
        for k, v in (('C', C), ('M', M), ('Y', Y), ('K', K)):
            self.p[k] = self.p[k] * (1 - cov) + v * cov
        if paper:
            self.alpha = np.maximum(self.alpha, cov)

    def over(self, cov, k='K', v=1.0):
        """One more ink on top of the others."""
        self.p[k] = np.maximum(self.p[k], cov * v)

    def stock(self, cov):
        self.alpha = np.maximum(self.alpha, cov)

    # ---- the hand
    def shake(self, d, amp=0.010):
        """A shape with the wobble of a hand."""
        return d + amp * self.wob

    def line(self, d, w, amp=0.0, vary=0.35):
        """Ink along the edge of a shape; the pen presses harder here and there."""
        e = d + amp * self.wob
        return self.c.cover(np.abs(e) - w * (1 + vary * self.wob2) * 0.5)

    def dots(self, tone, cell, angle=0.0, dx=0.0, dy=0.0):
        """Halftone. tone(x, y) gives 0..1 and is asked at the middle of each dot, so dots stay round."""
        c = self.c
        ca, sa = math.cos(angle), math.sin(angle)
        u, v = ((c.X - dx) * ca + (c.Y - dy) * sa) / cell, (-(c.X - dx) * sa + (c.Y - dy) * ca) / cell
        iu, iv = np.round(u), np.round(v)
        if callable(tone):
            t = tone((iu * ca - iv * sa) * cell + dx, (iu * sa + iv * ca) * cell + dy)
        else:
            t = np.full(c.shape, tone, F)
        t = clamp(t)
        r = np.sqrt(t / math.pi)
        e = np.hypot(u - iu, v - iv)
        # past half tone the dots meet; let the gaps become the dots
        gap = np.hypot(np.abs(u - iu) - 0.5, np.abs(v - iv) - 0.5)
        rg = np.sqrt((1 - t) / math.pi)
        d = np.where(t <= 0.5, (e - r), -(gap - rg)) * cell
        out = clamp(0.5 - d / c.px)
        return (out * (t > 0.012) * (t < 0.988) + (t >= 0.988)).astype(F)

    # ---- printing
    def image(self, grain=1.0, off=1.0, clip=True):
        c = self.c
        s = c.ss
        col = np.broadcast_to(PAPER, c.shape + (3,)).copy()
        n = fbm(c.shape, 40, self.seed + 11, 3)
        col *= (1 + 0.012 * grain * n)[..., None]
        for k in 'CMYK':
            p = self.p[k]
            ox, oy = self.OFF[k]
            p = shift(p, int(round(ox * s * off * P.draft)), int(round(oy * s * off * P.draft)))
            if grain:
                w = white(c.shape, self.seed + 20 + ord(k))
                tooth = blur(w, 0.75 * s) * s
                if k == 'K':
                    p = p * (1 - 0.75 * grain * smooth(1.55, 2.2, tooth))
                else:
                    p = p * (1 - 0.07 * grain * clamp(0.5 + tooth * 0.8 + 0.5 * n))
            col = col * (1 - p[..., None] * (1 - INKS[k]))
        a = self.alpha
        pm = col * a[..., None]
        h, w = c.h // s, c.w // s
        pm = pm.reshape(h, s, w, s, 3).mean(axis=(1, 3))
        al = a.reshape(h, s, w, s).mean(axis=(1, 3))
        out = pm / np.maximum(al, 1e-5)[..., None]
        rgba = np.concatenate([clamp(out), clamp(al)[..., None]], axis=2)
        return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')


def flat(im, name, colors=128):
    """Flat art packs best as a PNG with a palette."""
    p = os.path.join(P.dir, name)
    for ext in ('.png', '.jpg', '-mask.png'):
        if os.path.exists(p + ext):
            os.remove(p + ext)
    q = bleed(im)
    q = Image.merge('RGBA', q.split()[:3] + (im.getchannel('A'),))
    a = np.asarray(q).copy()
    a[a[..., 3] == 0] = 0
    q = Image.fromarray(a, 'RGBA').quantize(colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.save(p + '.png', optimize=True)
    print('%-14s %4dx%-4d %6.1f KB' % (name, im.size[0], im.size[1], os.path.getsize(p + '.png') / 1024), flush=True)


def sheet(cells, cols):
    w, h = cells[0].size
    rows = (len(cells) + cols - 1) // cols
    s = Image.new('RGBA', (w * cols, h * rows), (0, 0, 0, 0))
    for i, im in enumerate(cells):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    return s


def spikes(n, outer, inner, seed, vary=0.16, jitter=0.22, phase=0.0, x=0.0, y=0.0):
    """Points of an uneven star."""
    r = rng(seed)
    pts = []
    for i in range(n):
        a = phase + (i + r.uniform(-jitter, jitter)) / n * TAU
        q = outer * (1 - vary * r.random())
        pts.append((x + math.sin(a) * q, y - math.cos(a) * q))
        b = phase + (i + 0.5 + r.uniform(-jitter, jitter) * 0.6) / n * TAU
        q = inner * (1 + 0.5 * vary * r.uniform(-1, 1))
        pts.append((x + math.sin(b) * q, y - math.cos(b) * q))
    return pts


# ------------------------------------------------------------------ the wheel
def plate_(name, seed, blue=True, size=900):
    """Round panel: white border, thick ink ring, sunburst in dots, speed lines from the rim."""
    q = Print(P.px(size), P.ss(3), 1.0, seed=seed)
    c = q.c
    r = rng(seed)
    paper = q.shake(c.R - 0.984, 0.004)
    q.stock(c.cover(paper))
    field = q.shake(c.R - 0.925, 0.004)
    fc = c.cover(field)
    n = 30
    jit = np.interp((c.A / TAU + 0.5).ravel(), np.linspace(0, 1, 61), np.concatenate([r.uniform(-0.16, 0.16, 60), [0]])).reshape(c.shape).astype(F) * 0.6
    g = (c.A / TAU + 0.5) * n + jit
    e = (np.abs((g % 2.0) - 1.0) - 0.5) * (TAU / n) * c.R
    ray = c.cover(e)
    cell = 0.0245
    a15, a75 = math.radians(15), math.radians(75)
    if blue:
        lightC = q.dots(lambda x, y: 0.10 + 0.52 * smooth(0.40, 0.95, np.hypot(x, y)), cell, a15)
        darkC = q.dots(lambda x, y: 0.42 + 0.75 * smooth(0.38, 0.72, np.hypot(x, y)), cell, a15)
        rimM = q.dots(lambda x, y: 0.50 * smooth(0.62, 0.95, np.hypot(x, y)), cell, a75)
        q.put(fc, C=mix(lightC, darkC, ray), M=rimM * (0.45 + 0.55 * ray))
    else:
        # violet, for the outer rings: rosy rays between deep ones
        lightM = q.dots(lambda x, y: 0.16 + 0.34 * smooth(0.60, 0.95, np.hypot(x, y)), cell, a75)
        darkM = q.dots(lambda x, y: 0.50 + 0.20 * smooth(0.60, 0.95, np.hypot(x, y)), cell, a75)
        lightC = q.dots(lambda x, y: 0.30 * smooth(0.62, 0.95, np.hypot(x, y)), cell, a15)
        darkC = q.dots(lambda x, y: 0.55 + 0.50 * smooth(0.62, 0.90, np.hypot(x, y)), cell, a15)
        q.put(fc, C=mix(lightC, darkC, ray), M=mix(lightM, darkM, ray))
    # speed lines: wedges of ink that run in from the rim
    a = 0.0
    lines = np.full(c.shape, 9.0, F)
    while a < TAU:
        a += r.uniform(0.030, 0.105)
        ln = 0.06 + 0.22 * r.random() ** 2.2
        w = r.uniform(0.004, 0.0105)
        x0, y0 = c.polar(a, 0.935)
        x1, y1 = c.polar(a, 0.935 - ln)
        lines = np.minimum(lines, c.taper(x0, y0, w, x1, y1, -0.0008))
    q.over(c.cover(lines) * fc)
    # ink ring
    q.over(q.line(c.R - 0.936, 0.040, 0.005, 0.22))
    q.over(q.line(c.R - 0.984, 0.0085, 0.004, 0.5))
    flat(q.image(), name, 160)


def plate():
    plate_('plate', 11, True)


def plate2():
    plate_('plate2', 23, False)


def bubbles():
    """White bubbles for the entries, and the hard shadow under them."""
    cells = []
    for i in range(4):
        q = Print(P.px(190), 4, 1.10, seed=40 + i)
        c = q.c
        r = rng(40 + i)
        d = c.R - 0.960
        for k in (2, 3, 4, 6):
            d = d + 0.012 / k * 2 * r.uniform(0.4, 1) * np.cos(k * c.A + r.random() * TAU)
        cov = c.cover(d)
        tone = lambda x, y: 0.70 * smooth(0.22, 1.0, (x * 0.60 + y * 0.80)) * smooth(0.45, 0.95, np.hypot(x, y))
        q.put(cov, C=q.dots(tone, 0.095, math.radians(15)))
        q.over(q.line(d + 0.034, 0.068, 0.012, 0.50))
        # a second stroke, where the pen went round again
        a0 = -0.9 + i * 1.7
        arc = smooth(0.75, 0.35, np.abs((c.A - a0 + math.pi) % TAU - math.pi))
        q.over(c.cover(np.abs(d + 0.100 + 0.012 * q.wob) - 0.010 * arc) * (arc > 0.05))
        cells.append(q.image(grain=0.6))
    flat(sheet(cells, 4), 'bubble', 128)
    q = Print(P.px(150), 4, 1.10, seed=48)
    q.put(q.c.cover(q.shake(q.c.R - 0.955, 0.012)), K=1.0)
    flat(q.image(grain=0.4), 'shade', 32)


def stars():
    """The burst that pops out behind a chosen icon."""
    cells = []
    for i in range(3):
        q = Print(P.px(300), 4, 1.06, seed=60 + i)
        c = q.c
        a = c.poly(spikes(15, 0.985, 0.700, 60 + i, 0.17, 0.20, 0.1 * i))
        b = c.poly(spikes(14, 0.800, 0.560, 70 + i, 0.15, 0.20, 0.15 + 0.1 * i))
        q.put(c.cover(a), M=1.0, Y=1.0)
        shadeM = q.dots(lambda x, y: 0.75 * smooth(0.18, 0.74, np.hypot(x, y)), 0.062, math.radians(75))
        q.put(c.cover(b), Y=q.dots(lambda x, y: 0.25 + 0.9 * smooth(0.0, 0.40, np.hypot(x, y)), 0.062, 0.0), M=shadeM)
        q.over(q.line(a + 0.018, 0.040, 0.006, 0.4))
        q.over(q.line(b, 0.020, 0.006, 0.5))
        cells.append(q.image())
    flat(sheet(cells, 3), 'star', 128)


def burst():
    """The big jagged flash behind the wheel: red tips between yellow ones."""
    q = Print(P.px(1080), P.ss(3), 1.34, seed=30)
    c = q.c
    n = 26
    red = c.poly(flash(n, 1.300, 1.060, 31, 0.07, 0.10, 0.5 / n * TAU))
    yel = c.poly(flash(n, 1.235, 1.010, 37, 0.07, 0.10, 0.0))
    hole = 0.90 - c.R
    both = np.minimum(red, yel)
    q.stock(c.cover(np.maximum(both - 0.022, hole)))
    q.put(c.cover(np.maximum(red, hole)), M=1.0, Y=1.0, paper=False)
    q.put(c.cover(np.maximum(yel, hole)), Y=1.0, M=q.dots(lambda x, y: 0.72 * smooth(0.99, 1.21, np.hypot(x, y)), 0.030, math.radians(75)), paper=False)
    q.over(q.line(red + 0.006, 0.022, 0.004, 0.45) * c.cover(-yel))
    q.over(q.line(yel, 0.017, 0.004, 0.45))
    for k in 'CMYK':
        q.p[k] *= c.cover(hole)
    flat(q.image(), 'burst', 96)


def hub():
    """Speech bubble in the middle: a body, a tail that turns, and a patch that hides the line between them."""
    q = Print(P.px(440), P.ss(4), 1.06, seed=80)
    c = q.c
    d = c.R - 0.955
    r = rng(80)
    for k in (2, 3, 5):
        d = d + 0.010 / k * 2 * np.cos(k * c.A + r.random() * TAU)
    q.stock(c.cover(d - 0.030))
    light = lambda x, y: 1.0 - 0.72 * smooth(0.10, 0.95, -(x * 0.60 + y * 0.80)) * smooth(0.30, 0.85, np.hypot(x, y))
    dark = lambda x, y: 0.50 * smooth(0.25, 0.95, (x * 0.60 + y * 0.80)) * smooth(0.45, 0.90, np.hypot(x, y))
    q.put(c.cover(d), M=q.dots(light, 0.058, math.radians(75)), Y=1.0, C=q.dots(dark, 0.058, math.radians(15)))
    q.over(q.line(d + 0.022, 0.048, 0.006, 0.35))
    flat(q.image(), 'talk', 128)
    # the tail bends like a lick of flame and ends in a point
    L, R_ = [], []
    for k in range(15):
        t = k / 14
        y = -0.55 - 0.78 * t
        x = 0.085 * math.sin(t * math.pi * 0.9) * (1 if t < 2 else 0) - 0.10 * t * t
        w = 0.285 * (1 - t) ** 0.85
        L.append((x - w, y))
        R_.append((x + w, y))
    tail = L + R_[::-1][1:]
    q = Print(P.px(500), P.ss(4), 1.38, seed=81)
    c = q.c
    t = c.poly(tail)
    q.stock(c.cover(t - 0.030))
    q.put(c.cover(t), M=1.0, Y=1.0)
    q.over(q.line(t + 0.020, 0.048, 0.006, 0.35))
    cut = c.cover(c.Y + 0.60)
    for k in 'CMYK':
        q.p[k] *= cut
    q.alpha *= cut
    flat(q.image(), 'tail', 64)
    q = Print(P.px(500), P.ss(4), 1.38, seed=81)
    q.put(q.c.cover(np.maximum(q.c.poly(tail) + 0.046, 0.80 - q.c.R)) * smooth(1.07, 1.00, q.c.R), M=1.0, Y=1.0)
    flat(q.image(grain=0.5), 'patch', 64)


def box_(q, w, h, seed, tilt=0.0, wob=0.012):
    """A hand-ruled rectangle."""
    r = rng(seed)
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = sx * w + r.uniform(-1, 1) * wob, sy * h + r.uniform(-1, 1) * wob
        pts.append((x * math.cos(tilt) - y * math.sin(tilt), x * math.sin(tilt) + y * math.cos(tilt)))
    return q.c.poly(pts)


def captions():
    """Yellow caption box for the time, a small one for numbers, and the name tag."""
    q = Print(P.px(300), 4, 1.0, aspect=0.5, seed=90)
    c = q.c
    b = box_(q, 0.90, 0.385, 91, -0.012, 0.022)
    s = np.hypot(0, 0)
    sh = shift(c.cover(b), int(0.045 / c.px), int(0.050 / c.px))
    q.put(sh, K=1.0)
    q.put(c.cover(b), Y=1.0, M=q.dots(lambda x, y: 0.34 * smooth(-0.05, 0.45, y + 0.25 * x), 0.052, math.radians(75)))
    q.over(q.line(b + 0.010, 0.036, 0.008, 0.35))
    flat(q.image(), 'caption', 64)
    q = Print(P.px(72), 4, 1.0, seed=93)
    c = q.c
    b = box_(q, 0.70, 0.70, 94, -0.10, 0.06)
    q.put(shift(c.cover(b), int(0.14 / c.px), int(0.15 / c.px)), K=1.0)
    q.put(c.cover(b), Y=1.0)
    q.over(q.line(b + 0.03, 0.13, 0.02, 0.3))
    flat(q.image(), 'num', 32)
    # name tag, cut in nine: 2 picture points are one on screen
    n, h = 220, 120
    q = Print(P.px(n), 4, 1.0, aspect=h / n, seed=95)
    c = q.c
    u = 2.0 / n
    b = c.box(1 - 13 * u, h / n - 13 * u, x=-3 * u, y=-3 * u, r=1 * u)
    q.put(shift(c.cover(b), int(7 * u / c.px), int(7 * u / c.px)), K=1.0)
    q.put(c.cover(b), Y=1.0)
    q.over(q.line(b, 5.2 * u, 0.6 * u, 0.12))
    flat(q.image(grain=0.6), 'tag', 48)


def panel():
    """White panel with a thick frame and dots in two corners, cut in nine."""
    n = 440
    q = Print(P.px(n), 3, 1.0, seed=100)
    c = q.c
    u = 2.0 / n
    b = c.box(1 - 18 * u, 1 - 18 * u, x=-4 * u, y=-4 * u, r=2 * u)
    q.put(shift(c.cover(b), int(10 * u / c.px), int(10 * u / c.px)), K=1.0)
    e = 1 - 22 * u
    br = lambda x, y: 0.62 * smooth(150 * u, 10 * u, np.hypot(x - e, y - e))
    tl = lambda x, y: 0.75 * smooth(105 * u, 5 * u, np.hypot(x + e, y + e))
    q.put(c.cover(b), C=q.dots(br, 11 * u, math.radians(15)), Y=q.dots(tl, 11 * u, math.radians(0)) )
    q.over(q.line(b, 9.0 * u, 0.8 * u, 0.10))
    q.over(q.line(b + 11.5 * u, 2.0 * u, 0.8 * u, 0.15))
    flat(q.image(grain=0.6), 'panel', 64)


def tile():
    """Card: white, with a coloured head."""
    w, h = 220, 300
    q = Print(P.px(w), 3, 1.0, aspect=h / w, seed=104)
    c = q.c
    u = 2.0 / w
    H = h / w
    b = c.box(1 - 9 * u, H - 9 * u, x=-2 * u, y=-2 * u, r=14 * u)
    q.put(shift(c.cover(b), int(6 * u / c.px), int(6 * u / c.px)), K=1.0)
    sky = lambda x, y: 0.15 + 0.60 * smooth(H * 0.45, -H * 0.9, y)
    q.put(c.cover(b), C=q.dots(sky, 10 * u, math.radians(15)) * c.cover(c.Y - (H - 92 * u)))
    q.over(c.cover(np.abs(c.Y - (H - 92 * u) + 0.010 * q.wob) - 1.8 * u) * c.cover(b))
    q.over(q.line(b, 7.0 * u, 0.8 * u, 0.12))
    flat(q.image(grain=0.6), 'tile', 64)


def glyphs(q, text, height, x=0.0, y=0.0, arch=0.0, slant=0.0, bulge=0.0, grow=0.0, turn=5.0, seed=1, track=0.94, stroke=0.0):
    """Coverage of hand-set letters: each a little turned, on an arch. stroke widens them by that much."""
    c = q.c
    r = rng(seed)
    out = np.zeros(c.shape, F)
    f0 = load_font(BANGERS, height / c.px)
    ws = [f0.getlength(ch) * c.px * track for ch in text]
    n = len(text)
    sc = [(1 + bulge * (1 - abs(2 * i / max(1, n - 1) - 1)) + grow * (i / max(1, n - 1) - 0.5)) for i in range(n)]
    ws = [w * s for w, s in zip(ws, sc)]
    total = sum(ws)
    at = -total / 2
    for i, ch in enumerate(text):
        w = ws[i]
        mid = at + w / 2
        at += w
        px = height * sc[i] / c.px
        f = load_font(BANGERS, px)
        pad = int(px * 2.6) // 2 * 2
        im = Image.new('L', (pad, pad), 0)
        ImageDraw.Draw(im).text((pad / 2, pad / 2 - px * 0.04), ch, font=f, fill=255, anchor='mm', stroke_width=int(round(stroke / c.px)))
        t = mid / max(total / 2, 1e-6)
        ang = turn * r.uniform(-1, 1) + math.degrees(math.atan(2 * arch * t / max(total / 2, 1e-6))) * 1.0
        im = im.rotate(-ang, Image.BICUBIC)
        if slant:
            im = im.transform(im.size, Image.AFFINE, (1, slant, -slant * pad / 2, 0, 1, 0), Image.BICUBIC)
        X, Y = x + mid, y + arch * t * t + height * 0.05 * r.uniform(-1, 1)
        ix = int(round((X / c.extent + 1) * c.w / 2 - pad / 2))
        iy = int(round((Y / (c.extent * c.aspect) + 1) * c.h / 2 - pad / 2))
        a = np.asarray(im, F) / 255
        y0, x0, y1, x1 = max(0, iy), max(0, ix), min(c.h, iy + pad), min(c.w, ix + pad)
        if y1 > y0 and x1 > x0:
            out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], a[y0 - iy:y1 - iy, x0 - ix:x1 - ix])
    return out


def word(text, seed, back, front, arch=0.10, slant=0.0, size=0.62, n=15, spread=(0.97, 0.66), turn=5.0, bulge=0.15, grow=0.0, cloud=False):
    """One big sound: a burst with letters that stand out of it."""
    q = Print(P.px(400), 3, 1.0, aspect=0.76, seed=seed)
    c = q.c
    pts = [(px * 0.985, py * 0.735) for px, py in spikes(n, spread[0], spread[1], seed, 0.16, 0.22, 0.1)]
    if cloud:
        d = np.full(c.shape, 9.0, F)
        r = rng(seed)
        for i in range(n):
            a = (i + r.uniform(-0.2, 0.2)) / n * TAU
            d = np.minimum(d, c.circle(r.uniform(0.20, 0.27), math.sin(a) * 0.66, -math.cos(a) * 0.46))
        d = np.minimum(d, np.hypot(c.X, c.Y / 0.72) - 0.70)
    else:
        d = c.poly(pts)
    q.stock(c.cover(d - 0.022))
    ring = lambda x, y: smooth(0.15, 0.85, np.hypot(x, y / 0.75))
    tone = {}
    for k, (lo, hi) in back.items():
        tone[k] = q.dots(lambda x, y, lo=lo, hi=hi: lo + (hi - lo) * ring(x, y), 0.048, math.radians({'C': 15, 'M': 75, 'Y': 0}[k])) if lo != hi else lo
    q.put(c.cover(d), **tone)
    q.over(q.line(d + 0.006, 0.030, 0.005, 0.4))
    args = dict(arch=arch, slant=slant, turn=turn, bulge=bulge, grow=grow, seed=seed + 5)
    fill = glyphs(q, text, size, **args)
    wide = glyphs(q, text, size, stroke=0.030, **args)
    deep = np.zeros(c.shape, F)
    for i in range(1, 9):
        k = 0.0105 * i
        deep = np.maximum(deep, shift(wide, int(k / c.px), int(k * 1.15 / c.px)))
    white_ = glyphs(q, text, size, stroke=0.062, **args)
    q.put(np.maximum(white_, shift(white_, int(0.07 / c.px), int(0.08 / c.px))))
    q.put(np.maximum(deep, wide), K=1.0)
    tone = {}
    for k, (lo, hi) in front.items():
        tone[k] = q.dots(lambda x, y, lo=lo, hi=hi: lo + (hi - lo) * smooth(-0.28, 0.30, y), 0.040, math.radians({'C': 15, 'M': 75, 'Y': 0}[k])) if lo != hi else lo
    q.put(fill, **tone)
    # a glint along the upper left of the letters
    inn = glyphs(q, text, size, stroke=0.0, **args)
    k1, k2 = int(0.020 / c.px), int(0.042 / c.px)
    gl = np.minimum(shift(inn, k1, k1), 1 - shift(inn, k2, k2)) * inn * (c.Y < 0.06 + 0.2 * c.X)
    q.put(gl * 0.95)
    return q.image(grain=0.7)


def words():
    cells = [
        word('ZAP!', 201, {'Y': (1, 1), 'M': (0.0, 0.45)}, {'M': (1, 1), 'Y': (1, 1)}, arch=0.07, size=0.66),
        word('POW!', 203, {'M': (1, 1), 'Y': (1, 1)}, {'Y': (1, 1), 'M': (0.0, 0.40)}, arch=0.10, size=0.62),
        word('ZOOM!', 205, {'C': (0.35, 1.0)}, {'Y': (1, 1), 'M': (0.05, 0.75)}, arch=-0.04, size=0.56, slant=0.22, grow=0.35, bulge=0.0, n=17),
        word('WHAM!', 207, {'M': (0.25, 1.0)}, {'Y': (1, 1), 'C': (0, 0)}, arch=0.09, size=0.52, n=17),
        word('TA-DA!', 209, {'C': (0.55, 0.95), 'Y': (1, 1)}, {'M': (1, 1), 'Y': (1, 1)}, arch=0.12, size=0.47, n=19, turn=7),
        word('BOING!', 211, {'C': (1, 1), 'M': (0.15, 0.60)}, {'Y': (1, 1), 'M': (0.25, 0.85)}, arch=-0.08, size=0.50, n=11, cloud=True, turn=9, bulge=0.0),
    ]
    flat(sheet(cells, 3), 'words', 160)


def marks():
    """Running, active, stacked and other small signs."""
    q = Print(P.px(64), 5, 1.0, seed=120)
    c = q.c
    d = q.shake(c.R - 0.84, 0.03)
    q.stock(c.cover(d - 0.11))
    q.put(c.cover(d), M=1.0, Y=1.0)
    q.over(q.line(d + 0.02, 0.17, 0.02, 0.25))
    q.put(c.cover(np.hypot((c.X + 0.30) / 1.3, c.Y + 0.34) - 0.15))
    flat(q.image(grain=0.4), 'dot', 48)
    q = Print(P.px(104), 5, 1.0, seed=122)
    c = q.c
    d = c.poly(spikes(10, 0.90, 0.58, 123, 0.10, 0.14))
    q.stock(c.cover(d - 0.06))
    q.put(c.cover(d), Y=1.0, M=q.dots(lambda x, y: 0.5 * smooth(0.2, 0.8, np.hypot(x, y)), 0.13, 0.4))
    q.over(q.line(d + 0.02, 0.10, 0.01, 0.3))
    e = np.minimum(c.taper(0.02, -0.40, 0.115, 0, 0.08, 0.060), c.circle(0.095, 0.0, 0.31))
    q.put(c.cover(e), K=1.0)
    flat(q.image(grain=0.4), 'bang', 48)
    # vibration: arcs beside a bubble that is alive
    q = Print(P.px(260), 4, 1.42, seed=124)
    c = q.c
    cov = np.zeros(c.shape, F)
    for mid, off in ((-0.80, 0.0), (2.34, 0.0)):
        for r0, half, w in ((1.14, 0.30, 0.050), (1.28, 0.21, 0.042)):
            e = np.abs((c.A - mid + math.pi) % TAU - math.pi)
            taper_ = clamp(1 - (e / half) ** 2)
            cov = np.maximum(cov, c.cover(np.abs(c.R - r0 + 0.010 * q.wob) - w * 0.5 * np.sqrt(taper_) ) * (e < half))
    halo = clamp(blur(cov, 0.016 / c.px) * 3.2)
    q.stock(halo)
    q.over(cov)
    flat(q.image(grain=0.4), 'buzz', 32)
    q = Print(P.px(110), 4, 1.0, seed=126)
    c = q.c
    d = np.full(c.shape, 9.0, F)
    for x, y, r0 in ((-0.40, 0.10, 0.42), (0.10, -0.28, 0.46), (0.46, 0.14, 0.38), (0.02, 0.32, 0.46)):
        d = np.minimum(d, c.circle(r0, x, y))
    q.put(c.cover(d), C=q.dots(lambda x, y: 0.5 * smooth(0.0, 0.7, x * 0.4 + y), 0.16, 0.3))
    q.over(q.line(d + 0.02, 0.085, 0.02, 0.4))
    flat(q.image(grain=0.4), 'puff', 32)
    cells = []
    for i, ink in enumerate(({'Y': 1.0}, {'M': 1.0, 'Y': 1.0}, {'C': 0.9}, {})):
        q = Print(P.px(72), 5, 1.0, seed=130 + i)
        c = q.c
        d = c.star(5, 0.86, 0.40, 0.15 * i) if i != 3 else c.poly([(0, -0.9), (0.16, -0.16), (0.9, 0), (0.16, 0.16), (0, 0.9), (-0.16, 0.16), (-0.9, 0), (-0.16, -0.16)])
        d = d - 0.03
        q.put(c.cover(d), **ink)
        q.over(q.line(d + 0.02, 0.13, 0.015, 0.3))
        cells.append(q.image(grain=0.4))
    flat(sheet(cells, 4), 'bit', 64)
    q = Print(P.px(40), 5, 1.0, aspect=3.0, seed=136)
    c = q.c
    d = c.taper(0, 2.3, 0.10, 0, -2.2, 0.62)
    q.stock(c.cover(d - 0.22))
    q.put(c.cover(d), K=1.0)
    flat(q.image(grain=0.3), 'dash', 24)


def rush():
    """Lines that shoot outward when the wheel opens."""
    q = Print(P.px(900), 2, 1.0, seed=140)
    c = q.c
    r = rng(141)
    a = 0.0
    d = np.full(c.shape, 9.0, F)
    while a < TAU:
        a += r.uniform(0.028, 0.085)
        i0, o0 = r.uniform(0.44, 0.66), r.uniform(0.84, 0.985)
        w = r.uniform(0.003, 0.011)
        x0, y0 = c.polar(a, i0)
        x1, y1 = c.polar(a, o0)
        m = 0.35
        xm, ym = x0 + (x1 - x0) * m, y0 + (y1 - y0) * m
        d = np.minimum(d, np.minimum(c.taper(x0, y0, -0.001, xm, ym, w), c.taper(xm, ym, w, x1, y1, -0.001)))
    q.stock(c.cover(d - 0.0055))
    q.over(c.cover(d))
    flat(q.image(grain=0.2), 'rush', 24)


def tone():
    """Seamless halftone for the strip behind an open group."""
    n = P.px(96)
    q = Print(n, 4, 1.0, seed=150)
    c = q.c
    cell = 2.0 / 8
    e = np.minimum(np.hypot((c.X / cell) % 1 - 0.5, (c.Y / cell) % 1 - 0.5), np.hypot((c.X / cell + 0.5) % 1 - 0.5, (c.Y / cell + 0.5) % 1 - 0.5)) * cell
    q.put(np.ones(c.shape, F), Y=1.0, M=c.cover(e - 0.22 * cell))
    flat(q.image(grain=0.0, off=0.0), 'tone', 16)


def pointer_():
    """An arrow drawn with a fat pen."""
    q = Print(P.px(96), 5, 1.0, seed=160)
    c = q.c
    k = 0.86
    pts = [(x * k - 0.06, y * k - 0.04) for x, y in ((-0.80, -0.92), (-0.74, 0.58), (-0.40, 0.32), (-0.10, 0.90), (0.26, 0.73), (-0.04, 0.18), (0.46, 0.14))]
    d = c.poly(pts)
    q.put(shift(c.cover(d - 0.05), int(0.10 / c.px), int(0.10 / c.px)), K=1.0)
    q.put(c.cover(d - 0.05), K=1.0)
    q.put(c.cover(d + 0.045), C=q.dots(lambda x, y: 0.55 * smooth(0.1, 0.8, y - x * 0.4), 0.14, 0.3))
    flat(q.image(grain=0.3), 'arrow', 32)


def flash(n, tip, valley, seed, vary, jitter, phase):
    """Spikes that keep their places but not their length."""
    r = rng(seed)
    pts = []
    for i in range(n):
        a = phase + (i + r.uniform(-jitter, jitter)) / n * TAU
        long_ = 1.0 if i % 2 == 0 else 0.955
        q = tip * long_ * (1 - vary * r.random())
        pts.append((math.sin(a) * q, -math.cos(a) * q))
        b = phase + (i + 0.5 + r.uniform(-jitter, jitter) * 0.5) / n * TAU
        q = valley * (1 + 0.012 * r.uniform(-1, 1))
        pts.append((math.sin(b) * q, -math.cos(b) * q))
    return pts


# ------------------------------------------------------------------ build
P.run([plate, plate2, burst, bubbles, stars, hub, captions, panel, tile, words, marks, rush, tone, pointer_])
if P.want('sounds'):
    P.sounds('comic')
P.finish()
