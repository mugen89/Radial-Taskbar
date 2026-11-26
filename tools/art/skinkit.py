"""One script, one skin: pictures, skin.json, sounds.

    from skinkit import *
    K = Kit('porcelain', name='Porcelain', about='...', tags=[...])
    def plate(): ...  K.put(c, 'plate')
    K.run([plate, ...])
    K.write(style=..., wheel=..., ring=[...], slot={...}, ...)
"""
import json
import shutil
import sys

from metals import *
from pack import Pack, ROOT

FONTS = os.path.join(ROOT, 'tools', 'art', 'fonts')


class Kit(Pack):
    def __init__(self, id, name, about, tags, license=None):
        super().__init__(id, sys.argv)
        self.meta = {'format': 1, 'id': id, 'name': name, 'author': 'Radial Taskbar', 'version': '1.0'}
        if license:
            self.meta['license'] = license
        self.meta.update(about=about, tags=tags, preview='preview.jpg')
        self.flags = {}

    # ---------------------------------------------------------------- pictures
    def canvas(self, size, ss=2, extent=1.0, aspect=1.0):
        return Canvas(self.px(size), self.ss(ss), extent, aspect)

    def put(self, c, name, quality=89, how='auto', exposure=1.0, tone=True, **flags):
        im = c.image(exposure=exposure, tone=tone) if isinstance(c, Canvas) else c
        self.save(im, name, quality, how)

    def flag(self, **kw):
        """flag(halo='light', bubbles=dict(cols=4)): what skin.json has to say about a picture."""
        for k, v in kw.items():
            self.flags[k] = v if isinstance(v, dict) else {x: True for x in v.split()}

    def sheet(self, ims, cols, name, how='png', **flags):
        w, h = ims[0].size
        rows = (len(ims) + cols - 1) // cols
        s = Image.new('RGBA', (w * cols, h * rows), (0, 0, 0, 0))
        for i, im in enumerate(ims):
            s.paste(im, ((i % cols) * w, (i // cols) * h))
        self.save(s, name, how=how)

    def font(self, folder, *files):
        for f in files:
            shutil.copy(os.path.join(FONTS, folder, f), os.path.join(self.dir, f))
        for lic in ('OFL.txt', 'LICENSE.txt'):
            p = os.path.join(FONTS, folder, lic)
            if os.path.exists(p):
                shutil.copy(p, os.path.join(self.dir, 'OFL.txt' if not os.path.exists(os.path.join(self.dir, 'OFL.txt')) or len(files) else lic))

    # ---------------------------------------------------------------- skin.json
    def write(self, **parts):
        names = sorted(f for f in os.listdir(self.dir) if f.endswith(('.png', '.jpg')) and not f.endswith('-mask.png') and not f.startswith('preview'))
        images = {}
        for f in names:
            n = f.rsplit('.', 1)[0]
            d = {'file': f}
            if os.path.exists(os.path.join(self.dir, n + '-mask.png')):
                d['mask'] = n + '-mask.png'
            d.update(self.flags.get(n, {}))
            images[n] = f if list(d) == ['file'] else d
        j = dict(self.meta)
        order = ['style', 'wheel', 'colors', 'fonts', 'images', 'back', 'ring', 'slot', 'kid', 'over', 'hub', 'front', 'fan', 'pinbutton', 'settingsbutton', 'draw', 'tabs', 'panel', 'tag', 'tile',
                 'particles', 'onopen', 'onhover', 'onlaunch', 'sounds', 'cursor']
        parts['images'] = images
        parts.setdefault('sounds', {k: k + '.wav' for k in ('open', 'move', 'launch', 'close') if os.path.exists(os.path.join(self.dir, k + '.wav'))})
        for k in parts:
            assert k in order, k
        for k in order:
            if k in parts:
                j[k] = parts[k]
        with open(os.path.join(self.dir, 'skin.json'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(dump(j))
        self.finish()


def line(v):
    return json.dumps(v, ensure_ascii=False, separators=(', ', ': '))


def dump(j):
    """Readable JSON: one layer per line."""
    out = []
    for k, v in j.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out.append('  %s: [\n%s\n  ]' % (line(k), ',\n'.join('    ' + line(x) for x in v)))
        elif k in ('images', 'slot', 'kid') and isinstance(v, dict):
            rows = []
            for a, b in v.items():
                if isinstance(b, list) and b and isinstance(b[0], dict):
                    rows.append('    %s: [\n%s\n    ]' % (line(a), ',\n'.join('      ' + line(x) for x in b)))
                else:
                    rows.append('    %s: %s' % (line(a), line(b)))
            out.append('  %s: {\n%s\n  }' % (line(k), ',\n'.join(rows)))
        else:
            out.append('  %s: %s' % (line(k), line(v)))
    return '{\n' + ',\n'.join(out) + '\n}\n'


# -------------------------------------------------------------------- layers that every skin needs
def soft(size=1.10, y=0.02, a=65, inner=0.86, x=0.0, **kw):
    """A round shadow."""
    d = {'shape': 'circle', 'x': x, 'y': y, 'size': size, 'fill': {'type': 'radial', 'stops': [[0, 'black/%d' % a], [inner, 'black/%d' % int(a * 0.86)], [1, 'black/0']]}, 'opacity': 'sat(open)*0.95'}
    d.update(kw)
    return d


class _Any:
    """Enough of the formula language to find out how far a size moves."""
    fn = dict(sin=math.sin, cos=math.cos, abs=abs, floor=math.floor, fract=lambda x: x - math.floor(x), sqrt=lambda x: math.sqrt(max(0, x)), pow=pow, exp=math.exp, min=min, max=max,
              clamp=lambda x, a, b: min(b, max(a, x)), sat=lambda x: min(1, max(0, x)), mix=lambda a, b, t: a + (b - a) * t, step=lambda e, x: 1.0 if x >= e else 0.0,
              smooth=lambda a, b, x: (lambda t: t * t * (3 - 2 * t))(min(1, max(0, (x - a) / (b - a)))), noise=lambda x: 0.5, rnd=lambda x: 0.5, wave=lambda x: 0.5 - 0.5 * math.cos(x * TAU), tri=lambda x: abs((x % 1) * 2 - 1),
              outcubic=lambda t: 1 - (1 - t) ** 3, outback=lambda t: 1 + 2.7 * (t - 1) ** 3 + 1.7 * (t - 1) ** 2, outelastic=lambda t: t, outbounce=lambda t: t, inout=lambda t: t)

    @classmethod
    def spread(cls, f):
        out = []
        for hot in (0, 1):
            for time in [k * 0.31 for k in range(33)]:
                env = dict(cls.fn, hot=hot, on=hot, launch=0, press=0, time=time, i=1, j=2, n=10, a=0, seed=0.3, open=1, sound=hot, beat=hot, near=hot, active=0, ring=0, px=0, py=0, sel=0, idle=1 - hot, motion=1, radius=240, hub=90, ringin=100, ringout=190)
                try:
                    out.append(float(eval(f, {'__builtins__': {}}, env)))
                except Exception:
                    return None
        return min(out), max(out)


def img(name, size=1.0, **kw):
    d = {'image': name, 'size': size}
    if isinstance(size, str) and kw.get('in') != 'px':
        sp = _Any.spread(size)
        if sp and sp[1] > 0 and sp[0] < sp[1] * 0.88:
            top = float('%.3g' % sp[1])
            k = '(%s)/%g' % (size, top)
            sc = kw.pop('scale', None)
            d['size'] = top
            if isinstance(sc, (list, tuple)):
                kw['scale'] = ['(%s)*%s' % (q, k) for q in sc]
            else:
                kw['scale'] = k if sc is None else '(%s)*%s' % (sc, k)
    d.update(kw)
    return d


def intro(time=0.34, ease='back', delay=0.0, **kw):
    d = {'time': time, 'ease': ease}
    if delay:
        d['delay'] = delay
    d.update(kw)
    return d


def words(color, sub, font, px=17, y=-0.05, box=(1.22, 0.52), subpx=11.5, suby=0.28, clockpx=30, clocky=-0.08, datey=0.21, datepx=12, weight=700, clock='{hh}:{mm}', date='{date}', **kw):
    """Name and state of what is selected, or the time."""
    t = [{'text': '{title}', 'y': y, 'box': list(box), 'px': px, 'color': color, 'font': font, 'weight': weight, 'wrap': True},
         {'text': '{sub}', 'y': suby, 'box': [box[0] * 0.95, 0.2], 'px': subpx, 'color': sub, 'font': font, 'weight': weight},
         {'text': clock, 'y': clocky, 'box': [box[0], 0.55], 'px': clockpx, 'color': color, 'font': font, 'weight': weight, 'opacity': 'idle'},
         {'text': date, 'y': datey, 'box': [box[0] * 0.95, 0.2], 'px': datepx, 'color': sub, 'font': font, 'weight': weight, 'opacity': 'idle'}]
    for l in t:
        l.update({k: v for k, v in kw.items() if k not in l})
    return t


def badge(fill, ink, font, x=0.70, y=-0.70, size=0.25, stroke=None, em=0.30):
    w = 'numbers && number<10 && !kid'
    c = {'shape': 'circle', 'x': x, 'y': y, 'size': size, 'fill': fill, 'when': w}
    if stroke:
        c.update(stroke=stroke, width=1.2)
    return [c, {'text': '{number}', 'x': x, 'y': y - 0.01, 'em': em, 'color': ink, 'font': font, 'weight': 700, 'when': w}]


def running(color, hot, y=0.92, size=0.15, light=None):
    """A dot while a program runs, brighter while it is the active one."""
    t = [{'shape': 'circle', 'y': y, 'size': size, 'fill': color, 'when': 'running', 'opacity': 'active ? 1 : 0.75', 'glow': 4, 'glowcolor': hot},
         {'shape': 'circle', 'y': y, 'size': size * 0.55, 'fill': hot, 'when': 'running', 'opacity': 'active ? 1 : 0.35+0.35*wave(time*0.5+seed)'}]
    return t


def groupmark(color, y=-0.92, w=0.14):
    return [{'shape': 'poly', 'points': [[-w, y + w * 0.85], [0, y], [w, y + w * 0.85]], 'stroke': color, 'width': 2.2, 'caps': True, 'when': 'group'}]


# -------------------------------------------------------------------- drawing by hand on a canvas
class Ink:
    """Flat shapes on a canvas, as coverage. Coordinates are the canvas's."""

    def __init__(self, c, scale=1):
        self.c = c
        self.im = Image.new('L', (c.w, c.h), 0)
        self.d = ImageDraw.Draw(self.im)

    def p(self, x, y):
        c = self.c
        return ((x / c.extent + 1) * c.w / 2, (y / (c.extent * c.aspect) + 1) * c.h / 2)

    def line(self, pts, width, v=255, closed=False):
        q = [self.p(*a) for a in pts]
        if closed:
            q.append(q[0])
        w = max(1, int(round(width / self.c.px)))
        self.d.line(q, fill=v, width=w, joint='curve')
        if w > 2:
            for x, y in (q[0], q[-1]):
                self.d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=v)
        return self

    def poly(self, pts, v=255):
        self.d.polygon([self.p(*a) for a in pts], fill=v)
        return self

    def dot(self, x, y, r, v=255, ry=None):
        a, b = self.p(x - r, y - (ry or r))
        e, f = self.p(x + r, y + (ry or r))
        self.d.ellipse([a, b, e, f], fill=v)
        return self

    def brush(self, pts, w, v=255, shape='leaf', seed=None, rough=0.0):
        """A stroke that swells and tapers. w: greatest width."""
        n = len(pts)
        g = rng(seed) if seed is not None else None
        left, right = [], []
        for i in range(n):
            t = i / max(1, n - 1)
            k = {'leaf': math.sin(math.pi * t) ** 0.7, 'tail': (1 - t) ** 0.8 * min(1, t * 12 + 0.25), 'even': min(1, t * 14 + 0.5, (1 - t) * 14 + 0.5), 'head': t ** 0.8 * min(1, (1 - t) * 12 + 0.25)}[shape]
            if g is not None and rough:
                k *= 1 + rough * float(g.standard_normal())
            a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            l = math.hypot(dx, dy) or 1
            ox, oy = -dy / l * w * k / 2, dx / l * w * k / 2
            left.append((pts[i][0] + ox, pts[i][1] + oy))
            right.append((pts[i][0] - ox, pts[i][1] - oy))
        self.poly(left + right[::-1], v)
        return self

    def arr(self, soft=0.0):
        a = np.asarray(self.im, F) / 255
        return blur(a, soft / self.c.px) if soft else a


def bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def arcpts(r, a0, a1, n=48, x=0.0, y=0.0):
    """Angles in radians, clockwise from up."""
    return [(x + math.sin(a0 + (a1 - a0) * i / n) * r, y - math.cos(a0 + (a1 - a0) * i / n) * r) for i in range(n + 1)]


def wob(pts, amp, seed, every=6):
    """A hand that is not quite steady."""
    g = rng(seed)
    n = len(pts)
    k = max(2, n // every + 2)
    ox, oy = g.standard_normal(k) * amp, g.standard_normal(k) * amp
    u = np.linspace(0, k - 1, n)
    a, b = np.interp(u, range(k), ox), np.interp(u, range(k), oy)
    return [(p[0] + a[i], p[1] + b[i]) for i, p in enumerate(pts)]


def lerpts(p, q, n=10):
    return [(p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n) for i in range(n + 1)]


def turned(pts, a, s=1.0, x=0.0, y=0.0):
    """Points rotated clockwise by a, scaled, moved."""
    c, n = math.cos(a), math.sin(a)
    return [(x + (p[0] * c - p[1] * n) * s, y + (p[0] * n + p[1] * c) * s) for p in pts]


def lathe(c, pts, soft_=0.0):
    """Height of something turned on a lathe: [(radius, height), ...]."""
    r = np.array([p[0] for p in pts], F)
    h = np.array([p[1] for p in pts], F)
    H = np.interp(c.R, r, h).astype(F)
    return blur(H, soft_ / c.px) if soft_ else H


def flat(col, shape):
    return np.broadcast_to(rgb(col) if isinstance(col, str) else V(col), shape + (3,))


def ramp(t, *cols):
    """Colour along t 0..1 through the given colours."""
    cs = [rgb(x) if isinstance(x, str) else V(x) for x in cols]
    n = len(cs) - 1
    u = clamp(t) * n
    out = np.zeros(t.shape + (3,), F)
    for i in range(n):
        k = clamp(u - i)
        out = cs[0] * np.ones(t.shape + (3,), F) if i == 0 else out
        out = out * (1 - k[..., None]) + cs[i + 1] * k[..., None]
    return out.astype(F)


def paint(alb, cov, col):
    """Colour laid on an albedo picture."""
    return mix(alb, flat(col, cov.shape), cov[..., None])


def surface(c, H, alb, studio=SOFT, metal=0.0, rough=0.4, clear=0.0, reach=0.14, slope=0.7, ao_r=(0.008, 0.025, 0.06), ao_s=1.1, strength=1.0, aniso=None, sheen=0.0, shadows=True):
    nx, ny, nz = normals(H, c.px, strength)
    ao = occlusion(H, c.px, ao_r, ao_s)
    sh = cast(H, c.px, reach=reach, slope=slope) if shadows else None
    return shade(studio, nx, ny, nz, alb, metal=metal, rough=rough, ao=ao, sh=sh, clear=clear, aniso=aniso, sheen=sheen)


def light(K, name, size, fn, tint=None, quality=86):
    """A picture that adds light: fn(c) gives brightness 0..; saved on black."""
    c = Canvas(K.px(size), 1, 1.0)
    v = np.maximum(fn(c), 0)
    col = np.ones(c.shape + (3,), F) if tint is None else flat(tint, c.shape)
    c.col = (col * v[..., None]).astype(F) if v.ndim == 2 else v.astype(F)
    c.alpha[:] = 1
    edge = smooth(1.0, 0.94, np.maximum(np.abs(c.X), np.abs(c.Y) / c.aspect))
    c.col = c.col * edge[..., None]
    K.save(c.image(tone=False, dither=False), name, quality, 'jpg')


def halo(K, name='halo', size=256, power=2.2, inner=0.0, tint=None):
    light(K, name, size, lambda c: (1 - smooth(inner, 0.98, c.R)) ** power, tint)


def ringglow(K, name='ringglow', size=320, r=0.70, w=0.07, wide=0.22, tint=None):
    light(K, name, size, lambda c: gauss(c.R - r, w) + 0.45 * gauss(c.R - r, wide), tint)


def flames(K, name, frames=12, size=96, aspect=1.7, hot='#FFF3C8', mid='#FF9A2A', out='#C4320A', seed=5):
    """A candle or torch flame that loops, as a sheet of 4 columns that adds light."""
    ims = []
    base = None
    for f in range(frames):
        c = Canvas(K.px(size), 2, 1.0, aspect)
        ph = f / frames * TAU
        y = (aspect - c.Y) / (2 * aspect)           # 0 at the bottom, 1 at the top
        if base is None:
            base = [fbm((c.h * 2, c.w), 5, seed + k, 3) for k in range(2)]
        def field(k, speed):
            off = int(f / frames * c.h) % c.h
            return np.roll(base[k], -off * speed, axis=0)[:c.h]
        sway = 0.10 * math.sin(ph) + 0.06 * math.sin(2 * ph + 1)
        wob = field(0, 2) * 0.16 * y + sway * y * y
        w = 0.40 * np.sqrt(clamp(y * 7)) * np.power(clamp(1 - y), 0.75) * 1.45
        d = np.abs(c.X - wob) / np.maximum(w, 1e-3)
        k = clamp(1.15 - d) * smooth(0.0, 0.06, y) * smooth(1.0, 0.80, y + 0.10 * field(1, 2))
        core = clamp(1.25 * (1 - d * 1.5)) * smooth(0.02, 0.15, y) * smooth(0.75, 0.25, y)
        col = rgb(out) * (np.power(k, 1.2) * 0.9)[..., None] + rgb(mid) * (np.power(k, 2.2) * 1.2)[..., None] + rgb(hot) * (core * 1.1)[..., None]
        c.col = clamp(col).astype(F)
        c.alpha[:] = 1
        ims.append(c.image(tone=False, dither=False))
    K.sheet(ims, 4, name, how='jpg')


def stars(c, n, seed, rmin=0.0, rmax=1.0, size=0.004, bright=1.0):
    out = np.zeros(c.shape, F)
    g = rng(seed)
    for _ in range(n):
        a, r = g.random() * TAU, math.sqrt(rmin ** 2 + (rmax ** 2 - rmin ** 2) * g.random())
        x, y, s = math.sin(a) * r, -math.cos(a) * r, size * (0.4 + g.random() ** 3 * 1.8)
        px, py = (x / c.extent + 1) * c.w / 2, (y / (c.extent * c.aspect) + 1) * c.h / 2
        k = int(s / c.px * 5) + 2
        x0, x1, y0, y1 = int(px) - k, int(px) + k + 1, int(py) - k, int(py) + k + 1
        if x0 < 0 or y0 < 0 or x1 > c.w or y1 > c.h:
            continue
        d = np.hypot(c.X[y0:y1, x0:x1] - x, c.Y[y0:y1, x0:x1] - y)
        out[y0:y1, x0:x1] += (gauss(d, s) + 0.18 * gauss(d, s * 3)) * bright * (0.35 + 0.65 * g.random())
    return out


def boxshadow(K, name='shadow', hx=0.97, hy=0.97, r=0.04, ext=1.2, sigma=0.07, a=0.6, size=160, aspect=1.0):
    """The soft shadow of something that is not round."""
    c = Canvas(size, 1, ext, aspect)
    c.col[:] = 0
    c.alpha = (a * blur(c.cover(c.box(hx, hy, r=r)), sigma / c.px)).astype(F)
    K.save(c.image(tone=False, dither=False), name, how='png')


def nine(c, d, H, col):
    """Finishes a panel picture whose edge is the distance field d."""
    c.put(col, c.cover(d), H)
    return c
