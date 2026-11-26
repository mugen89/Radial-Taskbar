"""A small software renderer for theme artwork.

Everything is a height field seen straight from above: shapes are signed distance fields, bevels turn distance into
height, height gives normals, and normals are lit by an analytic studio (soft boxes, sky, floor). Contact shadows and
cast shadows come from marching over the height field. Coordinates run from -extent to +extent with y pointing down,
angles are clockwise from straight up, like in the program itself.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

F = np.float32
TAU = 2 * math.pi


# ------------------------------------------------------------------ small maths
def clamp(x, a=0.0, b=1.0):
    return np.clip(x, a, b)


def mix(a, b, t):
    return a + (b - a) * t


def smooth(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def gauss(x, w):
    return np.exp(-(x / w) ** 2)


def smin(a, b, k):
    h = clamp(0.5 + 0.5 * (b - a) / k)
    return mix(b, a, h) - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def rgb(h):
    """'#RRGGBB' to linear light."""
    h = h.lstrip('#')
    v = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], F) / 255
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4).astype(F)


def to_srgb(x):
    x = clamp(x)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def from_srgb(v):
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4).astype(F)


def film(x):
    """Filmic curve (a fitted ACES shape)."""
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14))


def V(a):
    """Colour or scalar broadcast over an image."""
    return np.asarray(a, F)


# ------------------------------------------------------------------ blur
def box1(a, r, axis):
    if r < 1:
        return a
    n = a.shape[axis]
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float64)
    hi = np.take(c, np.arange(2 * r + 1, n + 2 * r + 1), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(F)


def blur(a, sigma):
    """Three box passes are within a few percent of a Gaussian."""
    if sigma < 0.3:
        return a
    r = max(1, int(round((math.sqrt(4 * sigma * sigma + 1) - 1) / 2)))
    for _ in range(3):
        a = box1(box1(a, r, 0), r, 1)
    return a


def blur1(a, sigma, axis):
    r = max(1, int(round((math.sqrt(4 * sigma * sigma + 1) - 1) / 2)))
    for _ in range(3):
        a = box1(a, r, axis)
    return a


# ------------------------------------------------------------------ noise
def rng(seed):
    return np.random.default_rng(seed)


def lattice(shape, cells, seed, tile=False):
    """Smooth random field with `cells` features across the larger side."""
    h, w = shape
    cy = max(2, int(round(cells * h / max(h, w))))
    cx = max(2, int(round(cells * w / max(h, w))))
    g = rng(seed).standard_normal((cy + 4, cx + 4)).astype(F)
    if tile:
        g[-4:] = g[:4]
        g[:, -4:] = g[:, :4]
    im = Image.fromarray(g, 'F')
    # two guard cells on every side keep the cubic filter off the border
    out = im.resize((w, h), Image.BICUBIC, box=(2, 2, 2 + cx, 2 + cy))
    return np.asarray(out, F)


def fbm(shape, cells, seed, octaves=5, gain=0.5, lac=2.0, ridged=False):
    out = np.zeros(shape, F)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = lattice(shape, cells * lac ** o, seed + o * 17)
        if ridged:
            n = 1 - np.abs(n)
        out += amp * n
        tot += amp
        amp *= gain
        if cells * lac ** o > max(shape):
            break
    return out / tot


def white(shape, seed):
    return rng(seed).standard_normal(shape).astype(F)


def worley(X, Y, scale, seed, second=False):
    """Distance to the nearest (and second nearest) of scattered points; also a random value per cell."""
    r = rng(seed)
    N = 256
    jx = r.random((N, N)).astype(F)
    jy = r.random((N, N)).astype(F)
    jv = r.random((N, N)).astype(F)
    x, y = X * scale + 100.0, Y * scale + 100.0
    ix, iy = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    d1 = np.full(X.shape, 9.0, F)
    d2 = np.full(X.shape, 9.0, F)
    val = np.zeros(X.shape, F)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cx, cy = ix + ox, iy + oy
            kx, ky = cx % N, cy % N
            d = np.hypot(cx + jx[ky, kx] - x, cy + jy[ky, kx] - y).astype(F)
            near = d < d1
            d2 = np.where(near, d1, np.minimum(d2, d))
            val = np.where(near, jv[ky, kx], val)
            d1 = np.where(near, d, d1)
    return (d1, d2, val) if second else d1


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, size, ss=2, extent=1.0, aspect=1.0):
        """size: final width in pixels; aspect: height / width."""
        self.size, self.ss, self.extent, self.aspect = size, ss, extent, aspect
        w, h = size * ss, int(round(size * aspect)) * ss
        self.w, self.h = w, h
        self.shape = (h, w)
        self.px = 2 * extent / w                 # one sample, in canvas units
        xs = ((np.arange(w) + 0.5) / w * 2 - 1) * extent
        ys = ((np.arange(h) + 0.5) / h * 2 - 1) * extent * aspect
        self.X, self.Y = np.meshgrid(xs.astype(F), ys.astype(F))
        self.R = np.hypot(self.X, self.Y)
        self.A = np.arctan2(self.X, -self.Y)     # clockwise from up, -pi..pi
        self.col = np.zeros((h, w, 3), F)        # linear, not premultiplied
        self.alpha = np.zeros((h, w), F)
        self.H = np.zeros((h, w), F)             # height, in canvas units
        self.emit = np.zeros((h, w, 3), F)

    def cover(self, d, soft=1.0):
        """Antialiased coverage of a signed distance field."""
        return clamp(0.5 - d / (self.px * soft)).astype(F)

    # -------------------------------------------------------------- distances
    def polar(self, a, r):
        return math.sin(a) * r, -math.cos(a) * r

    def circle(self, r, x=0.0, y=0.0):
        return (self.R if x == 0 and y == 0 else np.hypot(self.X - x, self.Y - y)) - r

    def ring(self, r, half, x=0.0, y=0.0):
        return np.abs(self.circle(r, x, y)) - half

    def box(self, hx, hy, x=0.0, y=0.0, rot=0.0, r=0.0):
        px, py = self.X - x, self.Y - y
        if rot:
            c, s = math.cos(rot), math.sin(rot)
            px, py = px * c + py * s, -px * s + py * c
        qx, qy = np.abs(px) - hx + r, np.abs(py) - hy + r
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

    def capsule(self, x0, y0, x1, y1, r):
        px, py = self.X - x0, self.Y - y0
        bx, by = x1 - x0, y1 - y0
        t = clamp((px * bx + py * by) / max(1e-9, bx * bx + by * by))
        return np.hypot(px - bx * t, py - by * t) - r

    def taper(self, x0, y0, r0, x1, y1, r1):
        px, py = self.X - x0, self.Y - y0
        bx, by = x1 - x0, y1 - y0
        t = clamp((px * bx + py * by) / max(1e-9, bx * bx + by * by))
        return np.hypot(px - bx * t, py - by * t) - (r0 + (r1 - r0) * t)

    def poly(self, pts):
        """Signed distance to a polygon."""
        X, Y = self.X, self.Y
        n = len(pts)
        d = np.full(X.shape, 1e9, F)
        s = np.ones(X.shape, F)
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[i - 1]
            ex, ey = xj - xi, yj - yi
            wx, wy = X - xi, Y - yi
            t = clamp((wx * ex + wy * ey) / max(1e-12, ex * ex + ey * ey))
            bx, by = wx - ex * t, wy - ey * t
            d = np.minimum(d, bx * bx + by * by)
            c1, c2, c3 = Y >= yi, Y < yj, ex * wy > ey * wx
            flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            s = np.where(flip, -s, s)
        return s * np.sqrt(d)

    def regular(self, n, r, rot=0.0, x=0.0, y=0.0):
        return self.poly([(x + math.sin(rot + i * TAU / n) * r, y - math.cos(rot + i * TAU / n) * r) for i in range(n)])

    def star(self, n, r, inner, rot=0.0, x=0.0, y=0.0):
        pts = []
        for i in range(2 * n):
            a, q = rot + i * math.pi / n, (r if i % 2 == 0 else inner)
            pts.append((x + math.sin(a) * q, y - math.cos(a) * q))
        return self.poly(pts)

    def gear(self, teeth, r, depth, x=0.0, y=0.0, rot=0.0, duty=0.5, round_=0.2):
        """Distance-like field of a gear with trapezoid teeth."""
        px, py = self.X - x, self.Y - y
        rr = np.hypot(px, py)
        a = np.arctan2(px, -py) - rot
        p = TAU / teeth
        q = np.abs((a / p) - np.round(a / p)) * p * r    # distance along the rim from a tooth's middle
        half = p * r * 0.5 * duty
        slope = 0.35
        flank = (q - (half + (r - rr) * slope)) * 0.94
        body = rr - (r - depth * 0.5)
        tooth = smax(rr - (r + depth * 0.5), flank, depth * round_)
        return smin(body, smax(tooth, body - depth * 1.2, depth * 0.1), depth * round_)

    def sector(self, a0, a1):
        """Distance-like field of the angular sector a0..a1 (clockwise from up)."""
        mid, half = (a0 + a1) / 2, (a1 - a0) / 2
        d = (self.A - mid + math.pi) % TAU - math.pi
        return (np.abs(d) - half) * self.R

    def text(self, s, size, x=0.0, y=0.0, font='georgia.ttf', rot=0.0, anchor='mm'):
        """Coverage of a line of text; size in canvas units."""
        im = Image.new('L', (self.w, self.h), 0)
        f = load_font(font, size / self.px)
        cx, cy = (x / self.extent + 1) * self.w / 2, (y / (self.extent * self.aspect) + 1) * self.h / 2
        if rot:
            pad = int(size / self.px * (len(s) + 3))
            t = Image.new('L', (pad, pad), 0)
            ImageDraw.Draw(t).text((pad / 2, pad / 2), s, font=f, fill=255, anchor=anchor)
            t = t.rotate(-math.degrees(rot), Image.BICUBIC)
            im.paste(t, (int(round(cx - pad / 2)), int(round(cy - pad / 2))))
        else:
            ImageDraw.Draw(im).text((cx, cy), s, font=f, fill=255, anchor=anchor)
        return np.asarray(im, F) / 255

    def ring_text(self, s, size, radius, mid=0.0, font='georgia.ttf', spacing=1.0, inside=False):
        """Text that follows a circle; letters stand outward."""
        out = np.zeros(self.shape, F)
        f = load_font(font, size / self.px)
        widths = [f.getlength(ch) * self.px * spacing for ch in s]
        total = sum(widths)
        at = -total / 2
        for ch, w in zip(s, widths):
            a = (at + w / 2) / radius
            ang = mid + (-a if inside else a)
            at += w
            if ch.strip():
                x, y = self.polar(ang, radius)
                pad = int(size / self.px * 2.2)
                t = Image.new('L', (pad, pad), 0)
                ImageDraw.Draw(t).text((pad / 2, pad / 2), ch, font=f, fill=255, anchor='mm')
                t = t.rotate(-math.degrees(ang + (math.pi if inside else 0)), Image.BICUBIC)
                ix = int(round((x / self.extent + 1) * self.w / 2 - pad / 2))
                iy = int(round((y / (self.extent * self.aspect) + 1) * self.h / 2 - pad / 2))
                a0 = np.asarray(t, F) / 255
                y0, x0 = max(0, iy), max(0, ix)
                y1, x1 = min(self.h, iy + pad), min(self.w, ix + pad)
                if y1 > y0 and x1 > x0:
                    out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], a0[y0 - iy:y1 - iy, x0 - ix:x1 - ix])
        return out

    # -------------------------------------------------------------- layering
    def put(self, col, cov, height=None, emit=None):
        """Lays a surface on top: colour (linear), coverage 0..1, optional absolute height."""
        c = np.broadcast_to(V(col), self.col.shape) if np.ndim(col) < 3 else col
        k = cov[..., None]
        a = self.alpha[..., None]
        out_a = cov + self.alpha * (1 - cov)
        self.col = (c * k + self.col * a * (1 - k)) / np.maximum(out_a, 1e-6)[..., None]
        self.alpha = out_a
        if height is not None:
            self.H = mix(self.H, height, cov)
        if emit is not None:
            self.emit = self.emit * (1 - k) + np.broadcast_to(V(emit), self.col.shape) * k

    def shade_mul(self, m):
        self.col = self.col * (m[..., None] if m.ndim == 2 else m)

    def add(self, light, cov=None):
        """Light on top of what is there (does not change the silhouette)."""
        l = np.broadcast_to(V(light), self.col.shape) if np.ndim(light) < 3 else light
        self.col = self.col + (l * cov[..., None] if cov is not None else l)

    # -------------------------------------------------------------- output
    def image(self, exposure=1.0, tone=True, bloom=0.0, bloom_sigma=0.02, grade=None, dither=True):
        """Final RGBA image at the requested size."""
        col = self.col + self.emit
        if bloom > 0:
            hot = self.emit * self.alpha[..., None]
            glow = blur(hot, bloom_sigma / self.px) * bloom
            col = col + glow
            ga = clamp(glow.max(axis=2))
            # light spills past the silhouette as well
            a = np.maximum(self.alpha, ga * 0.0 + self.alpha)
            self.alpha = a
        col = col * exposure
        if tone:
            col = film(col)
        if grade is not None:
            col = grade(col)
        pm = col * self.alpha[..., None]
        s = self.ss
        h, w = self.h // s, self.w // s
        pm = pm.reshape(h, s, w, s, 3).mean(axis=(1, 3))
        al = self.alpha.reshape(h, s, w, s).mean(axis=(1, 3))
        c = pm / np.maximum(al, 1e-5)[..., None]
        out = to_srgb(c)
        if dither:
            out = out + (rng(1).random(out.shape) - 0.5) / 255
        rgba = np.concatenate([clamp(out), clamp(al)[..., None]], axis=2)
        return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')


_fonts = {}


def load_font(name, px):
    key = (name, int(round(px)))
    if key not in _fonts:
        path = name if os.path.isabs(name) else os.path.join(r'C:\Windows\Fonts', name)
        _fonts[key] = ImageFont.truetype(path, max(4, int(round(px))))
    return _fonts[key]


# ------------------------------------------------------------------ profiles: distance to height
def bevel(d, width, depth, kind='round'):
    """Height of a plate whose edge is at d = 0, rising to `depth` over `width` inside."""
    t = clamp(-d / width)
    if kind == 'round':
        return depth * np.sqrt(clamp(1 - (1 - t) ** 2))
    if kind == 'cove':
        return depth * (1 - np.sqrt(clamp(1 - t * t)))
    if kind == 'ogee':
        return depth * (t * t * (3 - 2 * t))
    if kind == 'step':
        return depth * smooth(0, 0.25, t)
    return depth * t                               # chamfer


def dome(d_center, r, depth):
    return depth * np.sqrt(clamp(1 - (d_center / r) ** 2))


# ------------------------------------------------------------------ lighting
def normals(H, px, strength=1.0):
    gy, gx = np.gradient(H, px)
    nx, ny = -gx * strength, -gy * strength
    inv = 1 / np.sqrt(nx * nx + ny * ny + 1)
    return (nx * inv).astype(F), (ny * inv).astype(F), inv.astype(F)


class Studio:
    """Analytic surroundings, sampled by direction. Directions: x right, y down, z toward the viewer."""

    def __init__(self, lights=None, sky='#AEBDD6', floor='#2A2622', horizon=0.35, ambient=0.35):
        self.sky, self.floor, self.horizon, self.ambient = rgb(sky), rgb(floor), horizon, ambient
        # direction (x, y, z), angular width, colour, strength
        self.lights = lights or [
            ((-0.45, -0.70, 0.60), 0.42, '#FFF6E8', 5.2),
            ((0.75, -0.25, 0.55), 0.26, '#DCE9FF', 2.0),
            ((0.15, 0.85, 0.45), 0.34, '#FFD9AE', 0.9),
            ((-0.90, 0.25, 0.25), 0.20, '#CFE0FF', 1.2),
        ]
        self.lights = [(np.array(d, F) / np.linalg.norm(d), w, rgb(c) if isinstance(c, str) else V(c), s) for d, w, c, s in self.lights]

    def reflect(self, nx, ny, nz, rough):
        """Mirror-ish reflection seen from above."""
        rx, ry, rz = 2 * nz * nx, 2 * nz * ny, 2 * nz * nz - 1
        out = np.zeros(nx.shape + (3,), F)
        up = clamp(0.5 - 0.5 * ry)                # sky comes from the top of the picture
        t = smooth(0.5 - 0.5 * self.horizon - 0.25 * rough, 0.5 + 0.5 * self.horizon + 0.25 * rough, up)
        base = self.floor * (1 - t[..., None]) + self.sky * t[..., None]
        out += base * (0.25 + 0.75 * clamp(0.35 + 0.65 * rz))[..., None] * self.ambient
        for d, w, c, s in self.lights:
            cosang = clamp(rx * d[0] + ry * d[1] + rz * d[2], -1, 1)
            ang = np.arccos(cosang)
            ww = math.hypot(w, 1.1 * rough)
            k = np.exp(-(ang / ww) ** 4 if rough < 0.15 else -(ang / ww) ** 2) * (w / ww) ** 1.2
            out += c * (s * k)[..., None]
        return out

    def diffuse(self, nx, ny, nz):
        out = np.zeros(nx.shape + (3,), F)
        t = clamp(0.5 - 0.5 * ny)[..., None]
        out += (self.floor * (1 - t) + self.sky * t) * self.ambient
        for d, w, c, s in self.lights:
            k = clamp((nx * d[0] + ny * d[1] + nz * d[2] + 0.12) / 1.12)
            out += c * (s * 0.16 * k * (0.5 + w))[..., None]
        return out

    def brushed(self, tx, ty, nx, ny, nz, rough, power=60):
        """Streaked highlight of brushed metal; (tx, ty) is the brushing direction."""
        out = np.zeros(nx.shape + (3,), F)
        for d, w, c, s in self.lights:
            hx, hy, hz = d[0], d[1], d[2] + 1.0
            l = math.sqrt(hx * hx + hy * hy + hz * hz)
            hx, hy, hz = hx / l, hy / l, hz / l
            th = tx * hx + ty * hy
            nh = clamp(nx * hx + ny * hy + nz * hz)
            p = power / (1 + 12 * rough)
            k = np.power(clamp(1 - th * th), p * 2) * np.power(nh, 2.0)
            out += c * (s * k * 0.42)[..., None]
        return out


def shade(studio, nx, ny, nz, albedo, metal=0.0, rough=0.35, spec=0.04, ao=None, sh=None, aniso=None, clear=0.0, sheen=0.0):
    """Physically flavoured shading for a straight-down view."""
    albedo = np.broadcast_to(V(albedo), nx.shape + (3,)) if np.ndim(albedo) < 3 else albedo
    metal = np.broadcast_to(V(metal), nx.shape)[..., None]
    refl = studio.reflect(nx, ny, nz, rough if np.ndim(rough) == 0 else float(np.mean(rough)))
    if aniso is not None:
        tx, ty, amt = aniso
        refl = refl * (1 - 0.75 * amt) + studio.brushed(tx, ty, nx, ny, nz, 0.3) * amt
    f0 = spec * (1 - metal) + albedo * metal
    fres = f0 + (1 - f0) * np.power(clamp(1 - nz), 5)[..., None]
    dif = studio.diffuse(nx, ny, nz) * albedo * (1 - metal)
    if sh is not None:
        k = (0.35 + 0.65 * sh)[..., None]
        dif = dif * (0.28 + 0.72 * sh[..., None])
        refl = refl * k
    if ao is not None:
        dif = dif * ao[..., None]
        refl = refl * (0.4 + 0.6 * ao[..., None])
    out = dif + refl * fres
    if clear > 0:
        cf = 0.04 + 0.96 * np.power(clamp(1 - nz), 5)
        out = out + studio.reflect(nx, ny, nz, 0.03) * (cf * clear)[..., None]
    if sheen > 0:
        out = out + albedo * (sheen * np.power(clamp(1 - nz), 2))[..., None]
    return out.astype(F)


def occlusion(H, px, radii=(0.01, 0.03, 0.08), strength=1.0):
    """Darkening of corners and recesses, at several sizes."""
    ao = np.ones(H.shape, F)
    for r in radii:
        s = r / px
        diff = blur(H, s) - H
        ao *= 1 / (1 + strength * 2.2 * clamp(diff / r, 0, 4))
    return ao.astype(F)


def cast(H, px, direction=(-0.5, -0.7), slope=0.9, reach=0.25, steps=48, soft=0.06):
    """Soft shadow from a light standing in `direction`; slope: light height per distance."""
    l = math.hypot(*direction)
    dx, dy = direction[0] / l, direction[1] / l
    lit = np.ones(H.shape, F)
    for i in range(1, steps + 1):
        t = reach * (i / steps) ** 1.4
        sx, sy = int(round(dx * t / px)), int(round(dy * t / px))
        if sx == 0 and sy == 0:
            continue
        s = shift(H, -sx, -sy)                     # the surface that lies toward the light
        over = s - (H + t * slope)
        lit = np.minimum(lit, clamp(1 - over / (soft * (0.15 + t))))
    return blur(lit, 0.8).astype(F)


def shift(a, dx, dy):
    """Moves the picture by whole samples, repeating the border."""
    h, w = a.shape[:2]
    yi = np.clip(np.arange(h) - dy, 0, h - 1)
    xi = np.clip(np.arange(w) - dx, 0, w - 1)
    return a[yi][:, xi]


# ------------------------------------------------------------------ textures
def scratches(shape, seed, count=160, length=(0.03, 0.25), width=1.2, soft=0.6):
    im = Image.new('L', (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(im)
    r = rng(seed)
    n = max(shape)
    for _ in range(count):
        x, y = r.random() * shape[1], r.random() * shape[0]
        a, l = r.random() * TAU, n * (length[0] + (length[1] - length[0]) * r.random() ** 2)
        bend = (r.random() - 0.5) * 0.4
        pts = []
        for k in range(9):
            t = k / 8
            pts.append((x + math.cos(a + bend * t) * l * t, y + math.sin(a + bend * t) * l * t))
        d.line(pts, fill=int(60 + 195 * r.random()), width=max(1, int(round(width * (0.5 + r.random())))))
    return blur(np.asarray(im, F) / 255, soft)


def circular_streaks(c, seed, density=1500, sharp=1.0):
    """Fine concentric lathe marks."""
    n = int(density)
    prof = rng(seed).standard_normal(n).astype(F)
    prof = prof * 0.6 + np.interp(np.arange(n), np.arange(0, n, 7), rng(seed + 1).standard_normal(len(range(0, n, 7)))) * 0.6
    idx = c.R / (c.extent * 1.5) * (n - 2)
    i0 = np.floor(idx).astype(np.int32)
    f = idx - i0
    i0 = np.clip(i0, 0, n - 2)
    return (prof[i0] * (1 - f) + prof[i0 + 1] * f).astype(F) * sharp


def radial_streaks(c, seed, density=2400):
    """Rays, as on a sunburst dial."""
    n = int(density)
    prof = rng(seed).standard_normal(n).astype(F)
    idx = (c.A / TAU + 0.5) * (n - 1)
    i0 = np.clip(np.floor(idx).astype(np.int32), 0, n - 1)
    f = idx - i0
    return (prof[i0] * (1 - f) + prof[(i0 + 1) % n] * f).astype(F)


def linear_streaks(shape, seed, length=140, angle=0):
    n = white(shape, seed)
    s = blur1(n, length, 1) * math.sqrt(length) * 1.6
    return s.astype(F)


def wood(c, seed, scale=2.2, light='#8A5A32', dark='#3A2212', stretch=7.0, rot=0.0, ring=9.0):
    """Planed wood: stretched, warped growth rings plus pores."""
    X, Y = c.X, c.Y
    if rot:
        cs, sn = math.cos(rot), math.sin(rot)
        X, Y = X * cs + Y * sn, -X * sn + Y * cs
    sh = c.shape
    warp = fbm(sh, 3 * scale, seed, 4) * 0.22 + fbm(sh, 1.2 * scale, seed + 5, 2) * 0.35
    v = Y * ring * scale + warp * stretch * 0.30 + X * 0.35 * scale
    g = np.abs((v % 1.0) * 2 - 1)
    g = g ** 1.5
    fine = blur1(white(sh, seed + 9), 60 * c.ss, 1) * 8
    pores = clamp(blur1((white(sh, seed + 11) > 2.6).astype(F), 9 * c.ss, 1) * 9)
    t = clamp(0.55 * g + 0.20 * fine + 0.28 * (fbm(sh, 5 * scale, seed + 3, 4) * 0.5 + 0.5))
    col = rgb(dark) * (1 - t[..., None]) + rgb(light) * t[..., None]
    col = col * (1 - 0.45 * pores[..., None])
    return col.astype(F), (t * 0.6 - pores).astype(F)


def save(im, path, quality=88):
    """RGBA picture as colour JPEG plus mask when that is smaller, otherwise PNG. Returns the files written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return [path]


def bleed(im, rounds=24):
    """Extends colours past the silhouette, so that filtering and JPEG do not pull in black."""
    a = np.asarray(im, F) / 255
    c, al = a[..., :3].copy(), a[..., 3]
    w = (al > 0.02).astype(F)
    acc = c * w[..., None]
    for s in (1, 2, 4, 8, 16, 32):
        b = blur(acc, s)
        bw = blur(w, s)
        fill = b / np.maximum(bw, 1e-5)[..., None]
        need = (w < 0.5) & (bw > 1e-4)
        c = np.where(need[..., None], fill, c)
        acc = np.where(need[..., None], fill, acc)
        w = np.where(need, 1.0, w).astype(F)
    out = np.concatenate([c, al[..., None]], axis=2)
    return Image.fromarray((clamp(out) * 255 + 0.5).astype(np.uint8), 'RGBA')


def on(im, bg=(92, 104, 128), checker=True):
    """Preview over a neutral background."""
    w, h = im.size
    b = Image.new('RGBA', (w, h), bg + (255,))
    if checker:
        d = ImageDraw.Draw(b)
        for y in range(0, h, 32):
            for x in range(0, w, 32):
                if (x // 32 + y // 32) % 2:
                    d.rectangle([x, y, x + 31, y + 31], fill=tuple(int(v * 0.9) for v in bg) + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')
