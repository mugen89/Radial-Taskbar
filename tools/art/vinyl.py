"""Vinyl: a hi-fi turntable seen from above, with a dot-matrix display, VU meters and a tonearm that follows the selection.

    python vinyl.py --draft            half size, quick
    python vinyl.py                    final
    python vinyl.py plinth key         only these parts
    python vinyl.py fonts              only the two lettering files

Everything is drawn here: the pictures with artkit, the two display typefaces (dot matrix and seven segments) as small
TrueType files written by `write_ttf` below, so that unlit dots and lit letters share one grid at every size.
"""
import os
import shutil
import struct
import sys

from metals import *
from pack import Pack

P = Pack('vinyl', sys.argv)

# A listening room in the evening: one big soft light from the upper left, a cool window on the right, a lamp below.
ROOM = Studio(lights=[((-0.46, -0.72, 0.58), 0.42, '#FFF4E2', 4.3), ((0.82, -0.26, 0.48), 0.24, '#D6E2F6', 1.6),
                      ((0.16, 0.86, 0.42), 0.36, '#FFCB93', 0.75), ((-0.92, 0.22, 0.26), 0.20, '#D3E0FA', 0.9)],
              sky='#C6CCD6', floor='#121214', ambient=0.42)

AMBER = '#FFB347'
RIGHTEOUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'righteous', 'Righteous-Regular.ttf')


# ---------------------------------------------------------------- lettering: a very small TrueType writer
def write_ttf(path, family, glyphs, upm, ascent, descent, copyright_):
    """glyphs: list of (codepoints, advance, kind, data). kind 'outline': contours of (x, y, on_curve);
    kind 'parts': list of (glyph index, dx, dy). Glyph 0 is .notdef."""
    def s16(v):
        return struct.pack('>h', int(round(v)))

    def u16(v):
        return struct.pack('>H', int(v) & 0xFFFF)

    def u32(v):
        return struct.pack('>I', int(v) & 0xFFFFFFFF)

    boxes, blobs, npts, nctr, ncomp = [], [], [], [], []
    for cps, adv, kind, data in glyphs:
        if kind == 'outline':
            pts = [p for ct in data for p in ct]
            if not pts:
                boxes.append((0, 0, 0, 0)); blobs.append(b''); npts.append(0); nctr.append(0); ncomp.append(0)
                continue
            xs, ys = [int(round(p[0])) for p in pts], [int(round(p[1])) for p in pts]
            bx = (min(xs), min(ys), max(xs), max(ys))
            b = s16(len(data)) + b''.join(s16(v) for v in bx)
            end = -1
            for ct in data:
                end += len(ct)
                b += u16(end)
            b += u16(0)
            b += bytes(1 if p[2] else 0 for p in pts)
            px = py = 0
            dx, dy = b'', b''
            for x, y in zip(xs, ys):
                dx += s16(x - px); dy += s16(y - py)
                px, py = x, y
            b += dx + dy
            boxes.append(bx); blobs.append(b); npts.append(len(pts)); nctr.append(len(data)); ncomp.append(0)
        else:
            bx = None
            b = b''
            for k, (gi, ox, oy) in enumerate(data):
                g = boxes[gi]
                q = (g[0] + ox, g[1] + oy, g[2] + ox, g[3] + oy)
                bx = q if bx is None else (min(bx[0], q[0]), min(bx[1], q[1]), max(bx[2], q[2]), max(bx[3], q[3]))
                flags = 0x0001 | 0x0002 | (0x0020 if k + 1 < len(data) else 0)   # words, xy values, more components
                b += u16(flags) + u16(gi) + s16(ox) + s16(oy)
            if not data:
                boxes.append((0, 0, 0, 0)); blobs.append(b'')
            else:
                boxes.append(bx)
                blobs.append(s16(-1) + b''.join(s16(v) for v in bx) + b)
            npts.append(sum(npts[gi] for gi, _, _ in data)); nctr.append(sum(nctr[gi] for gi, _, _ in data)); ncomp.append(len(data))

    glyf, loca = b'', [0]
    for b in blobs:
        b += b'\0' * (-len(b) % 4)
        glyf += b
        loca.append(len(glyf))
    if not glyf:
        glyf = b'\0'
    cmap = {}
    for gi, g in enumerate(glyphs):
        for cp in g[0]:
            cmap.setdefault(cp, gi)
    # format 4, one segment per run of consecutive characters and glyphs
    keys = sorted(k for k in cmap if k < 0xFFFF)
    seg = []
    for k in keys:
        if seg and k == seg[-1][1] + 1 and cmap[k] - k == seg[-1][2]:
            seg[-1][1] = k
        else:
            seg.append([k, k, cmap[k] - k])
    seg.append([0xFFFF, 0xFFFF, 1])
    n = len(seg)
    sr = 2 * 2 ** int(math.floor(math.log2(n)))
    sub = u16(n * 2) + u16(sr) + u16(int(math.log2(sr / 2))) + u16(n * 2 - sr)
    sub += b''.join(u16(x[1]) for x in seg) + u16(0) + b''.join(u16(x[0]) for x in seg) + b''.join(u16(x[2]) for x in seg) + u16(0) * n
    sub = u16(4) + u16(len(sub) + 6) + u16(0) + sub
    cm = u16(0) + u16(2) + u16(0) + u16(3) + u32(20) + u16(3) + u16(1) + u32(20) + sub

    num = len(glyphs)
    xmin, ymin = min(b[0] for b in boxes), min(b[1] for b in boxes)
    xmax, ymax = max(b[2] for b in boxes), max(b[3] for b in boxes)
    advmax = max(g[1] for g in glyphs)
    head = u32(0x00010000) + u32(0x00010000) + u32(0) + u32(0x5F0F3CF5) + u16(0x000B) + u16(upm) + struct.pack('>qq', 3800000000, 3800000000)
    head += s16(xmin) + s16(ymin) + s16(xmax) + s16(ymax) + u16(0) + u16(6) + s16(2) + s16(1) + s16(0)
    hhea = u32(0x00010000) + s16(ascent) + s16(-descent) + s16(0) + u16(advmax) + s16(xmin) + s16(0) + s16(xmax) + s16(1) + s16(0) + s16(0) + s16(0) * 4 + s16(0) + u16(num)
    hmtx = b''.join(u16(g[1]) + s16(b[0]) for g, b in zip(glyphs, boxes))
    maxp = u32(0x00010000) + u16(num) + u16(max(npts)) + u16(max(nctr)) + u16(max(npts)) + u16(max(nctr)) + u16(2) + u16(0) * 6 + u16(max(ncomp)) + u16(1)
    first, last = keys[0], min(keys[-1], 0xFFFF)
    os2 = u16(4) + s16(advmax) + u16(400) + u16(5) + u16(0) + s16(upm * 0.5) * 8 + s16(0) + s16(0) + s16(0) + b'\0' * 10
    os2 = u16(4) + s16(advmax) + u16(400) + u16(5) + u16(0)
    os2 += s16(650) + s16(600) + s16(0) + s16(75) + s16(650) + s16(600) + s16(0) + s16(350) + s16(50) + s16(300)   # sub/superscript, strikeout
    os2 += s16(0) + b'\0' * 10 + u32(0x80000203) + u32(0) + u32(0) + u32(0) + b'RT2S' + u16(0x0040) + u16(first) + u16(last)
    os2 += s16(ascent) + s16(-descent) + s16(0) + u16(ascent) + u16(descent) + u32(0x00000005) + u32(0) + s16(ascent * 0.7) + s16(ascent * 0.9) + u16(0) + u16(0x20) + u16(1)
    names = [(0, copyright_), (1, family), (2, 'Regular'), (3, family + ' 1.0'), (4, family), (5, 'Version 1.0'), (6, family.replace(' ', '') + '-Regular'), (13, 'Drawn for this skin; use it freely with it.')]
    strs, recs = b'', b''
    for nid, text in names:
        t = text.encode('utf-16-be')
        recs += u16(3) + u16(1) + u16(0x409) + u16(nid) + u16(len(t)) + u16(len(strs))
        strs += t
    name = u16(0) + u16(len(names)) + u16(6 + len(recs)) + recs + strs
    post = u32(0x00030000) + u32(0) + s16(-75) + s16(50) + u32(1) + u32(0) * 4
    gasp = u16(1) + u16(1) + u16(0xFFFF) + u16(0x000A)                         # smooth in both directions at every size
    tables = {b'OS/2': os2, b'cmap': cm, b'gasp': gasp, b'glyf': glyf, b'head': head, b'hhea': hhea, b'hmtx': hmtx, b'loca': b''.join(u32(v) for v in loca), b'maxp': maxp, b'name': name, b'post': post}

    def total(b):
        b += b'\0' * (-len(b) % 4)
        return sum(struct.unpack('>%dI' % (len(b) // 4), b)) & 0xFFFFFFFF
    k = len(tables)
    es = int(math.floor(math.log2(k)))
    out = u32(0x00010000) + u16(k) + u16(16 * 2 ** es) + u16(es) + u16(16 * k - 16 * 2 ** es)
    at, body = 12 + 16 * k, b''
    where = 0
    for tag in sorted(tables):
        b = tables[tag]
        if tag == b'head':
            where = at + len(body)
        out += tag + u32(total(b)) + u32(at + len(body)) + u32(len(b))
        body += b + b'\0' * (-len(b) % 4)
    out += body
    adj = (0xB1B0AFBA - total(out)) & 0xFFFFFFFF
    out = out[:where + 8] + u32(adj) + out[where + 12:]
    with open(path, 'wb') as f:
        f.write(out)
    print('%-14s %d glyphs  %6.1f KB' % (os.path.basename(path), num, len(out) / 1024))


# 5 x 7 dots, rows from the top, written as rows of '#' and '.'; capitals only, small letters share them.
DOTS = r"""
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .###. #...# #.... #.... #.... #...# .###.
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .###. #...# #.... #.### #...# #...# .####
H #...# #...# #...# ##### #...# #...# #...#
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.
J ..### ...#. ...#. ...#. ...#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# #...# ##..# #.#.# #..## #...# #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .#### #.... #.... .###. ....# ....# ####.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#.
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# #...# .#.#. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ...#. ..#.. .#... #####
3 ##### ...#. ..#.. ...#. ....# #...# .###.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 ..##. .#... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ..#.. .#... .#... .#...
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ...#. .##..
! ..#.. ..#.. ..#.. ..#.. ..... ..... ..#..
" .#.#. .#.#. .#.#. ..... ..... ..... .....
# .#.#. .#.#. ##### .#.#. ##### .#.#. .#.#.
$ ..#.. .#### #.#.. .###. ..#.# ####. ..#..
% ##... ##..# ...#. ..#.. .#... #..## ...##
& .##.. #..#. #.#.. .#... #.#.# #..#. .##.#
' .##.. ..#.. .#... ..... ..... ..... .....
( ...#. ..#.. .#... .#... .#... ..#.. ...#.
) .#... ..#.. ...#. ...#. ...#. ..#.. .#...
* ..... ..#.. #.#.# .###. #.#.# ..#.. .....
+ ..... ..#.. ..#.. ##### ..#.. ..#.. .....
, ..... ..... ..... ..... .##.. ..#.. .#...
- ..... ..... ..... ##### ..... ..... .....
. ..... ..... ..... ..... ..... .##.. .##..
/ ..... ....# ...#. ..#.. .#... #.... .....
: ..... .##.. .##.. ..... .##.. .##.. .....
; ..... .##.. .##.. ..... .##.. ..#.. .#...
< ...#. ..#.. .#... #.... .#... ..#.. ...#.
= ..... ..... ##### ..... ##### ..... .....
> .#... ..#.. ...#. ....# ...#. ..#.. .#...
? .###. #...# ....# ...#. ..#.. ..... ..#..
@ .###. #...# ....# .##.# #.#.# #.#.# .###.
[ .###. .#... .#... .#... .#... .#... .###.
] .###. ...#. ...#. ...#. ...#. ...#. .###.
\ ..... #.... .#... ..#.. ...#. ....# .....
^ ..#.. .#.#. #...# ..... ..... ..... .....
_ ..... ..... ..... ..... ..... ..... #####
` .#... ..#.. ...#. ..... ..... ..... .....
{ ...#. ..#.. ..#.. .#... ..#.. ..#.. ...#.
| ..#.. ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
} .#... ..#.. ..#.. ...#. ..#.. ..#.. .#...
~ ..... .#... #.#.# ...#. ..... ..... .....
À .#... ..#.. .###. #...# ##### #...# #...#
Á ...#. ..#.. .###. #...# ##### #...# #...#
Â ..#.. .#.#. .###. #...# ##### #...# #...#
Ã .#.#. #.#.. .###. #...# ##### #...# #...#
Ä .#.#. ..... .###. #...# ##### #...# #...#
Å ..#.. .#.#. .###. #...# ##### #...# #...#
Æ .#### #.#.. #.#.. ##### #.#.. #.#.. #.###
Ç .###. #...# #.... #.... #...# .###. ..#..
È .#... ..#.. ##### #.... ####. #.... #####
É ...#. ..#.. ##### #.... ####. #.... #####
Ê ..#.. .#.#. ##### #.... ####. #.... #####
Ë .#.#. ..... ##### #.... ####. #.... #####
Ì .#... ..#.. .###. ..#.. ..#.. ..#.. .###.
Í ...#. ..#.. .###. ..#.. ..#.. ..#.. .###.
Î ..#.. .#.#. .###. ..#.. ..#.. ..#.. .###.
Ï .#.#. ..... .###. ..#.. ..#.. ..#.. .###.
Ñ .#.#. #.#.. #...# ##..# #.#.# #..## #...#
Ò .#... ..#.. .###. #...# #...# #...# .###.
Ó ...#. ..#.. .###. #...# #...# #...# .###.
Ô ..#.. .#.#. .###. #...# #...# #...# .###.
Õ .#.#. #.#.. .###. #...# #...# #...# .###.
Ö .#.#. ..... .###. #...# #...# #...# .###.
Ø .###. #..## #.#.# #.#.# #.#.# ##..# .###.
Ù .#... ..#.. #...# #...# #...# #...# .###.
Ú ...#. ..#.. #...# #...# #...# #...# .###.
Û ..#.. .#.#. ..... #...# #...# #...# .###.
Ü .#.#. ..... #...# #...# #...# #...# .###.
Ý ...#. ..#.. #...# #...# .#.#. ..#.. ..#..
ß .##.. #..#. #..#. #.##. #...# #...# #.##.
Ą .###. #...# #...# ##### #...# #..#. #..##
Ć ...#. ..#.. .###. #...# #.... #...# .###.
Č .#.#. ..#.. .###. #...# #.... #...# .###.
Ď .#.#. ..#.. ####. #...# #...# #...# ####.
Ę ##### #.... ####. #.... #.... ##### ...##
Ě .#.#. ..#.. ##### #.... ####. #.... #####
Ğ .###. ..... .#### #.... #..## #...# .####
İ ..#.. ..... .###. ..#.. ..#.. ..#.. .###.
Ł .#... .#... .#.#. .##.. ##... .#... .####
Ń ...#. ..#.. #...# ##..# #.#.# #..## #...#
Ň .#.#. ..#.. #...# ##..# #.#.# #..## #...#
Ő ..#.# .#.#. .###. #...# #...# #...# .###.
Ř .#.#. ..#.. ####. #...# ####. #..#. #...#
Ś ...#. ..#.. .#### #.... .###. ....# ####.
Ş .#### #.... .###. ....# ####. ..#.. .#...
Š .#.#. ..#.. .#### #.... .###. ....# ####.
Ť .#.#. ..#.. ##### ..#.. ..#.. ..#.. ..#..
Ů ..#.. .#.#. ..#.. #...# #...# #...# .###.
Ű ..#.# .#.#. #...# #...# #...# #...# .###.
Ź ...#. ..#.. ##### ...#. ..#.. .#... #####
Ż ..#.. ..... ##### ...#. ..#.. .#... #####
Ž .#.#. ..#.. ##### ...#. ..#.. .#... #####
Б ##### #.... #.... ####. #...# #...# ####.
Г ##### #.... #.... #.... #.... #.... #....
Д ..##. .#.#. .#.#. .#.#. .#.#. ##### #...#
Ж #.#.# #.#.# #.#.# .###. #.#.# #.#.# #.#.#
З .###. #...# ....# ..##. ....# #...# .###.
И #...# #...# #..## #.#.# ##..# #...# #...#
Й .###. ..... #...# #..## #.#.# ##..# #...#
Л ..### .#..# .#..# .#..# .#..# .#..# #...#
П ##### #...# #...# #...# #...# #...# #...#
У #...# #...# #...# .#### ....# ....# .###.
Ф ..#.. .###. #.#.# #.#.# #.#.# .###. ..#..
Ц #..#. #..#. #..#. #..#. #..#. ##### ....#
Ч #...# #...# #...# .#### ....# ....# ....#
Ш #.#.# #.#.# #.#.# #.#.# #.#.# #.#.# #####
Щ #.#.# #.#.# #.#.# #.#.# #.#.# ##### ....#
Ъ ##... .#... .#... .###. .#..# .#..# .###.
Ы #...# #...# #...# ##..# #.#.# #.#.# ##..#
Ь #.... #.... #.... ####. #...# #...# ####.
Э .###. #...# ....# ..### ....# #...# .###.
Ю #..#. #.#.# #.#.# ###.# #.#.# #.#.# #..#.
Я .#### #...# #...# .#### ..#.# .#..# #...#
Ђ ##### ..#.. ..##. ..#.# ..#.# ..#.# ..##.
Є .###. #...# #.... ###.. #.... #...# .###.
Љ .##.. .#.#. .#.#. .#.## .#.#. .#.## #..#.
Њ #.#.. #.#.. #.#.. ####. #.#.# #.#.# #.##.
Ћ ##### ..#.. ..##. ..#.# ..#.# ..#.# ..#.#
Ґ ....# ##### #.... #.... #.... #.... #....
¿ ..#.. ..... ..#.. .#... #.... #...# .###.
¡ ..#.. ..... ..... ..#.. ..#.. ..#.. ..#..
° .##.. #..#. #..#. .##.. ..... ..... .....
£ ..##. .#..# .#... ###.. .#... .#... #####
€ ..### .#... ####. .#... ####. .#... ..###
§ .###. #.... .##.. #..#. .##.. ....# .###.
© .###. #...# #.##. #.#.. #.##. #...# .###.
µ ..... #...# #...# #...# ##..# #.##. #....
± ..#.. ..#.. ##### ..#.. ..#.. ..... #####
× ..... #...# .#.#. ..#.. .#.#. #...# .....
÷ ..... ..#.. ..... ##### ..... ..#.. .....
« ..... ..#.# .#.#. #.#.. .#.#. ..#.# .....
» ..... #.#.. .#.#. ..#.# .#.#. #.#.. .....
• ..... ..... .###. .###. .###. ..... .....
… ..... ..... ..... ..... ..... ..... #.#.#
— ..... ..... ..... ##### ..... ..... .....
’ ..##. ..#.. .#... ..... ..... ..... .....
“ .#..# #..#. ##.## ..... ..... ..... .....
” ##.## .#..# #..#. ..... ..... ..... .....
► .#... .##.. .###. .#### .###. .##.. .#...
♪ ..#.. ..##. ..#.# ..#.. .##.. ###.. .#...
■ ..... .###. .###. .###. .###. .###. .....
█ ##### ##### ##### ##### ##### ##### #####
"""

# Characters that look the same as one of the above.
SAME = {'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X', 'Ѕ': 'S', 'І': 'I', 'Ї': 'Ï', 'Ј': 'J', 'Ё': 'Ë', 'Џ': 'Ц', 'Ѝ': 'Й',
        '–': '-', '‘': "'", '·': '•', '▶': '►', ' ': ' ', '−': '-', 'Ð': 'D', 'Đ': 'D', 'Ÿ': 'Y', 'Ț': 'Ť', 'Ș': 'Ş', 'Ă': 'Ã', '″': '"', '′': "'"}


def dot_font(path):
    pitch, r = 100, 43
    def disc(cx, cy):
        # four arcs, each with its control point on the diagonal
        q = []
        for i in range(8):
            a = -i * math.pi / 4
            if i % 2 == 0:
                q.append((cx + r * math.cos(a), cy + r * math.sin(a), True))
            else:
                q.append((cx + r * 1.33 * math.cos(a), cy + r * 1.33 * math.sin(a), False))
        return q
    rows = {}
    for line in DOTS.strip('\n').split('\n'):
        rows[line[0]] = line[2:].split(' ')
        assert len(rows[line[0]]) == 7 and all(len(x) == 5 for x in rows[line[0]]), line
    glyphs = [([], 600, 'outline', []), ([], 600, 'outline', [disc(0, 0)]), ([0x20], 600, 'outline', [])]
    index = {' ': 2}
    for ch, rr in rows.items():
        cps = [ord(ch)]
        if ch.lower() != ch and len(ch.lower()) == 1:
            cps.append(ord(ch.lower()))
        index[ch] = len(glyphs)
        glyphs.append([cps, 600, 'parts', [(1, 50 + x * pitch + 50, (6 - y) * pitch + 50) for y in range(7) for x in range(5) if rr[y][x] == '#']])
    for ch, to in SAME.items():
        if to in index:
            g = glyphs[index[to]]
            cps = [ord(ch)] + ([ord(ch.lower())] if ch.lower() != ch and len(ch.lower()) == 1 else [])
            glyphs[index[to]] = (g[0] + cps, g[1], g[2], g[3])
    write_ttf(path, 'RT Dot Matrix', glyphs, 1000, 750, 50, 'Made for Radial Taskbar')


def segments():
    """The seven bars of a digit (y up, 420 wide, 720 tall) and which of them each character lights."""
    W, Ht, t, gap = 420.0, 720.0, 104.0, 6.0
    h2, m = Ht / 2, t / 2

    def hseg(y):
        a, b = m + gap, W - m - gap
        return [(a, y), (a + m, y + m), (b - m, y + m), (b, y), (b - m, y - m), (a + m, y - m)]

    def vseg(x, y0, y1):
        a, b = y0 + gap, y1 - gap
        return [(x, a), (x - m, a + m), (x - m, b - m), (x, b), (x + m, b - m), (x + m, a + m)]
    seg = {'a': hseg(Ht - m), 'g': hseg(h2), 'd': hseg(m), 'f': vseg(m, h2, Ht - m), 'b': vseg(W - m, h2, Ht - m), 'e': vseg(m, m, h2), 'c': vseg(W - m, m, h2)}
    on = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg', '-': 'g', 'E': 'afged', 'A': 'abcefg', 'P': 'abefg',
          'L': 'fed', 'C': 'afed', 'F': 'afge', 'H': 'fbgec', 'U': 'fbcde'}
    return seg, on


def segment_font(path):
    """Seven slanted segments with mitred ends; '8' shows all of them."""
    seg, on = segments()
    slant = 0.10

    def put(pts, ox=75):
        area = sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))
        if area > 0:
            pts = pts[::-1]                                                     # clockwise is filled
        return [(x + ox + slant * y, y, True) for x, y in pts]
    glyphs = [([], 600, 'outline', []), ([0x20], 600, 'outline', [])]
    for ch, s in on.items():
        cps = [ord(ch)] + ([ord(ch.lower())] if ch.lower() != ch else [])
        glyphs.append((cps, 600, 'outline', [put(seg[q]) for q in s]))
    s = 52
    dots = [put([(x, y), (x, y + 2 * s), (x + 2 * s, y + 2 * s), (x + 2 * s, y)], 40) for x, y in ((0, 150), (0, 470))]
    glyphs.append(([ord(':')], 240, 'outline', dots))
    glyphs.append(([ord('.')], 240, 'outline', [put([(0, 0), (0, 2 * s), (2 * s, 2 * s), (2 * s, 0)], 40)]))
    write_ttf(path, 'RT Segments', glyphs, 1000, 760, 40, 'Made for Radial Taskbar')


def fonts():
    dot_font(os.path.join(P.dir, 'dots.ttf'))
    segment_font(os.path.join(P.dir, 'segments.ttf'))
    d = os.path.dirname(RIGHTEOUS)
    shutil.copyfile(RIGHTEOUS, os.path.join(P.dir, 'Righteous-Regular.ttf'))
    shutil.copyfile(os.path.join(d, 'OFL.txt'), os.path.join(P.dir, 'OFL.txt'))


# ---------------------------------------------------------------- the deck
W, HH, Y0 = 1.30, 1.285, 0.075          # half sizes of the plinth's picture and where its middle lies, in wheel radii
PIVOT = (1.030, -0.760)                 # of the tonearm
VU = (0.935, 0.995)                     # middle of the right meter; the left one mirrors it
VUH = (0.190, 0.170)                    # half size of its window
DISP = (0.0, 1.098, 0.655, 0.043)       # display window: middle and half size
LEDS, LEDY, LEDX = 16, 1.186, 0.0375    # per side, where, and how far apart


class Part(Canvas):
    """A rectangle of a larger canvas, with coordinates of its own."""

    def __init__(self, c, cx, cy, hx, hy, y0=0.0):
        j0, j1 = (int(round((cx + k * hx + c.extent) / c.px)) for k in (-1, 1))
        i0, i1 = (int(round((cy - y0 + k * hy + c.extent * c.aspect) / c.px)) for k in (-1, 1))
        self.sl = (slice(i0, i1), slice(j0, j1))
        self.X, self.Y = c.X[self.sl] - cx, c.Y[self.sl] - cy
        self.shape = self.X.shape
        self.h, self.w = self.shape
        self.px, self.ss = c.px, c.ss
        self.extent, self.aspect = self.w * c.px / 2, self.h / self.w
        self.R, self.A = np.hypot(self.X, self.Y), np.arctan2(self.X, -self.Y)


def flat(col, shape):
    return np.broadcast_to(rgb(col) if isinstance(col, str) else V(col), shape + (3,))


def fibres(shape, nx, ny, seed):
    """Smooth noise with nx features across and ny down: long ones make wood."""
    g = rng(seed).standard_normal((ny + 4, nx + 4)).astype(F)
    return np.asarray(Image.fromarray(g, 'F').resize((shape[1], shape[0]), Image.BICUBIC, box=(2, 2, 2 + nx, 2 + ny)), F)


def walnut(shape, px, seed):
    """Oiled walnut with the grain along x. Returns colour and pore depth."""
    h, w = shape
    k = w * px / 2.6                                                         # how many decks wide the board is
    n = lambda a, b, q: fibres(shape, max(2, int(a * k)), max(2, int(b * k * h / w)), seed + q)
    y = np.linspace(0, h * px, h, dtype=F)[:, None]
    slow = n(4, 14, 1)
    v = y * 17.0 + slow * 0.62 + n(9, 40, 2) * 0.18
    rings = 0.5 - 0.5 * np.cos(v * TAU)
    rings = rings ** 1.6
    streaks = 0.55 * n(16, 180, 3) + 0.38 * n(40, 420, 4) + 0.30 * n(90, 900, 5)
    t = clamp(0.46 + 0.17 * slow + 0.15 * streaks + 0.20 * (rings - 0.5))
    pores = clamp(blur1((white(shape, seed + 9) > 2.35).astype(F), 7, 1) * 7.0 - 0.15)
    dark, mid, light = rgb('#22150D'), rgb('#4E3423'), rgb('#86624A')
    col = np.where((t < 0.5)[..., None], mix(dark, mid, clamp(t * 2)[..., None]), mix(mid, light, clamp(t * 2 - 1)[..., None]))
    col = col * (1 + 0.10 * n(7, 22, 6))[..., None] * V([1.03, 1.0, 0.95])
    return (col * (1 - 0.52 * pores)[..., None]).astype(F), (0.35 * t - pores).astype(F)


def vu_face(c, lit):
    """The printed card of a level meter; its needle turns around (0, 0.185)."""
    py = 0.185
    X, Y = c.X, c.Y - py
    r, a = np.hypot(X, Y), np.arctan2(X, -Y)
    if lit:
        lamp = 0.80 * gauss(np.hypot(c.X * 0.80, c.Y + 0.030), 0.165) + 0.20
        lamp = lamp + 0.34 * gauss(np.hypot(np.abs(c.X) - 0.140, c.Y - 0.115), 0.080)
        base = mix(flat('#D9701E', c.shape), flat('#FFD98E', c.shape), clamp(lamp * 1.05)[..., None]) * (0.20 + 0.56 * clamp(lamp, 0, 1.2))[..., None]
    else:
        base = flat('#8A6F48', c.shape) * (0.10 + 0.09 * gauss(np.hypot(c.X, c.Y + 0.03), 0.22))[..., None]
    ink, red = np.zeros(c.shape, F), np.zeros(c.shape, F)
    R0 = 0.258
    rad = math.radians

    def at(db):
        return -36 + 72 * 0.71 * 10 ** (db / 20.0)

    def arc(r0, half, a0, a1):
        return clamp((half - np.abs(r - r0)) / c.px + 0.5) * clamp((a - rad(a0)) * r / c.px + 0.5) * clamp((rad(a1) - a) * r / c.px + 0.5)

    def tick(deg, r0, r1, half):
        d = np.abs((a - rad(deg)) * r)
        return clamp((half - d) / c.px + 0.5) * clamp((r - r0) / c.px + 0.5) * clamp((r1 - r) / c.px + 0.5)
    ink = np.maximum(ink, arc(R0, 0.0021, -36, at(0)))
    red = np.maximum(red, arc(R0 + 0.005, 0.0075, at(0) + 0.4, 36))
    for db in (-20, -10, -7, -5, -3, -2, -1, 0):
        ink = np.maximum(ink, tick(at(db), R0, R0 + 0.018, 0.0024))
    for db in (1, 2, 3):
        red = np.maximum(red, tick(at(db), R0, R0 + 0.018, 0.0028))
    for k in range(11):
        ink = np.maximum(ink, tick(-36 + 72 * 0.71 * k / 10, R0 - 0.013, R0, 0.0014) * 0.75)

    def num(s, deg, rr, size, font='arialbd.ttf'):
        x, y = math.sin(rad(deg)) * rr, -math.cos(rad(deg)) * rr + py
        return c.text(s, size, x, y, font=font, rot=rad(deg) * 0.9)
    for db, t in ((-20, '20'), (-10, '10'), (-6.2, '7'), (-4.0, '5'), (0, '0')):
        ink = np.maximum(ink, num(t, at(db), R0 + 0.037, 0.0285))
    red = np.maximum(red, num('3', at(3) - 1.5, R0 + 0.037, 0.0285))
    ink = np.maximum(ink, c.text('−', 0.034, -0.168, -0.088, font='arialbd.ttf'))
    red = np.maximum(red, c.text('+', 0.034, 0.168, -0.088, font='arialbd.ttf'))
    ink = np.maximum(ink, c.text('VU', 0.060, 0, 0.016, font='georgiab.ttf'))
    ink = np.maximum(ink, c.text('LEVEL', 0.0185, 0, 0.060, font='arialbd.ttf') * 0.85)
    col = mix(base, flat('#140802', c.shape) * (0.5 if lit else 0.25), (ink * 0.95)[..., None])
    col = mix(col, flat('#C8140A', c.shape) * (0.80 if lit else 0.14), (red * 0.97)[..., None])
    grain = fbm(c.shape, 70, 9, 3)
    return col * (1 + 0.04 * grain)[..., None]


def shadow():
    """Soft shadow of the plinth on the desktop."""
    c = Canvas(P.px(300), 1, 1.0)
    d = c.box(0.90, 0.90, r=0.12)
    a = 1 - smooth(-0.07, 0.075, blur(d.astype(F), 0.015 / c.px))
    c.col[:] = 0
    c.alpha = (a * 0.70).astype(F)
    P.save(c.image(tone=False, dither=False), 'shadow', how='png')


def plinth():
    c = Canvas(P.px(1300), P.ss(2), W, aspect=HH / W)
    c.Y = c.Y + Y0
    c.R, c.A = np.hypot(c.X, c.Y), np.arctan2(c.X, -c.Y)
    X, Y, R = c.X, c.Y, c.R
    sh = c.shape
    d = c.box(1.27, 1.255, 0, Y0, r=0.150)
    # ---- walnut frame, mitred at the corners
    ax, ay = 1.27 - np.abs(X), 1.255 - np.abs(Y - Y0)
    wh, hh = walnut(sh, c.px, 21)
    wv, hv = walnut((c.w, c.h), c.px, 57)
    wv, hv = wv.transpose(1, 0, 2), hv.T
    side = clamp((ay - ax) / c.px + 0.5)
    seam = gauss(ay - ax, 0.0014)
    board = mix(wh, wv, side[..., None]) * (1 - 0.70 * seam)[..., None]
    grainh = mix(hh, hv, side)
    del wh, wv, hh, hv

    E1, E2, E3 = 0.0745, 0.0790, 0.1010                                        # wood ends, trim begins, trim ends
    H = bevel(d, 0.030, 0.050) + 0.0011 * grainh * (d > -E1)
    H = H * 1.0 - 0.016 * smooth(-E1 + 0.010, -E1, d) ** 2 * (d > -E1 - 0.002)
    H = np.where(d < -E1, 0.030, H)
    trim = np.maximum(d + E2, -E3 - d)
    H = np.where(trim < 0, 0.040 + bevel(trim, 0.0045, 0.012, 'chamfer'), H)
    H = np.where(d < -E3, 0.046 - 0.014 * gauss(d + E3, 0.0026), H)
    # ---- the well the platter turns in, with a polished edge
    H = np.where(R < 1.040, 0.046 - 0.030 * smooth(1.040, 1.016, R), H)
    # ---- tonearm base, rest, adapter, screws
    bx, by = X - PIVOT[0], Y - PIVOT[1]
    br, ba = np.hypot(bx, by), np.arctan2(bx, -by)
    H = np.maximum(H, np.where(br < 0.118, 0.046 + bevel(br - 0.118, 0.010, 0.016), 0))
    H = np.where(br < 0.102, 0.062 - 0.010 * smooth(0.102, 0.096, br), H)
    H = np.maximum(H, np.where(br < 0.072, 0.052 + bevel(br - 0.072, 0.012, 0.026), 0))
    rr = np.hypot(X - 1.100, Y - 0.005)                                                              # arm rest
    H = np.maximum(H, np.where(rr < 0.032, 0.046 + bevel(rr - 0.032, 0.008, 0.026), 0))
    H = H - 0.018 * ((np.abs(X - 1.100) < 0.013) & (rr < 0.034))
    kx, ky = X - 0.810, Y + 0.968                                                                    # anti-skating knob
    kr, ka = np.hypot(kx, ky), np.arctan2(kx, -ky)
    H = np.maximum(H, np.where(kr < 0.046, 0.046 + bevel(kr - 0.045 + 0.0016 * np.cos(ka * 36), 0.010, 0.036), 0))
    H = H - 0.006 * ((np.abs(kx) < 0.003) & (ky < -0.012) & (kr < 0.040))
    px_, py_ = X + 1.020, Y + 0.905                                                                  # 45 rpm adapter
    pr, pa = np.hypot(px_, py_), np.arctan2(px_, -py_)
    H = H - 0.014 * smooth(0.122, 0.116, pr) * (pr > 0.098)
    puck = 0.044 + 0.030 * smooth(0.108, 0.094, pr) + 0.016 * smooth(0.072, 0.060, pr) + 0.010 * smooth(0.040, 0.032, pr)
    puck = puck - 0.060 * smooth(0.0135, 0.0105, pr)
    H = np.where(pr < 0.108, puck, H)
    scr = np.zeros(sh, F)
    for sx, sy, sa in ((-1.118, -1.030, 0.7), (1.118, -1.030, 2.2)):
        q = np.hypot(X - sx, Y - sy)
        H = np.where(q < 0.021, 0.046 + dome(q, 0.030, 0.006), H)
        H = H - 0.012 * (np.maximum(np.abs((X - sx) * math.cos(sa) + (Y - sy) * math.sin(sa)) - 0.0022, q - 0.0155) < 0)
        scr = np.maximum(scr, c.cover(q - 0.021))
    # ---- meters, display, lights

    def rbox(x, y, hx, hy, r):
        qx, qy = np.abs(x) - hx + r, np.abs(y) - hy + r
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    mx, my = np.abs(X) - VU[0], Y - VU[1]
    vout, vin = rbox(mx, my, VUH[0] + 0.024, VUH[1] + 0.024, 0.032), rbox(mx, my, VUH[0], VUH[1], 0.014)
    fr = np.maximum(vout, -vin)
    H = np.maximum(H, np.where(fr < 0, 0.046 + bevel(fr, 0.012, 0.018), 0))
    H = np.where(vin < 0, 0.034, H)
    dout = c.box(DISP[2] + 0.016, DISP[3] + 0.016, DISP[0], DISP[1], r=0.021)
    din = c.box(DISP[2], DISP[3], DISP[0], DISP[1], r=0.010)
    dfr = np.maximum(dout, -din)
    H = np.maximum(H, np.where(dfr < 0, 0.046 + bevel(dfr, 0.008, 0.010), 0))
    H = np.where(din < 0, 0.038, H)
    band = np.abs(Y - LEDY) < 0.03
    lx = (np.abs(X) - 0.026 + LEDX / 2) % LEDX - LEDX / 2
    in_row = (np.abs(X) > 0.026 - LEDX / 2) & (np.abs(X) < 0.026 + LEDX * (LEDS - 0.5))
    led = np.where(in_row & band, np.maximum(np.abs(lx) - 0.0125, np.abs(Y - LEDY) - 0.0058), 9)
    H = np.where(led < 0.004, 0.046 - 0.006 * smooth(0.004, 0.0015, led), H)
    H = np.where(led < 0, 0.046 + bevel(led, 0.005, 0.004), H)

    # ---- materials
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.006, 0.018, 0.05), 1.25)
    shd = cast(H, c.px, reach=0.16, slope=0.72)
    streak = clamp(0.6 * fibres(sh, 10, int(sh[0] * 0.45), 5) + 0.5 * fibres(sh, 26, int(sh[0] * 0.8), 6), -2, 2)
    # satin plate: a wide soft reflection falls off from the upper left
    fall = 0.40 + 1.05 * np.exp(-(((X + 1.15) * 0.62 + (Y + 1.05) * 0.50) / 0.95) ** 2) + 0.16 * np.exp(-(((X - 1.2) * 0.9 - (Y + 1.1) * 0.35) / 0.5) ** 2)
    sat = flat('#4B4D52', sh) * (fall * (1 + 0.050 * streak + 0.030 * fbm(sh, 260, 8, 2)))[..., None]
    edge = shade(ROOM, nx, ny, nz, flat('#3A3B3F', sh), metal=0.9, rough=0.35, ao=ao, sh=shd)
    plate = sat * (0.46 * (0.30 + 0.70 * ao) * (0.42 + 0.58 * shd))[..., None] + edge * (clamp((1 - nz) * 9))[..., None]
    lac = shade(ROOM, nx, ny, nz, board * 1.02, metal=0, rough=0.35, spec=0.04, ao=ao, sh=shd, clear=0.30)
    alu_mask = np.maximum(c.cover(trim), c.cover(np.maximum(R - 1.038, 1.0165 - R)))
    alu_mask = np.maximum(alu_mask, c.cover(np.minimum(fr, dfr)))
    vertical = np.where((trim < 0.004) & (ax < ay), 1.0, 0.0).astype(F)          # the trim is brushed along its length
    st2 = clamp(0.6 * fibres(sh, int(sh[1] * 0.45), 10, 15) + 0.5 * fibres(sh, int(sh[1] * 0.8), 26, 16), -2, 2)
    grain = mix(streak, st2, vertical)
    alu = shade(ROOM, nx, ny, nz, ALU * V([0.98, 0.99, 1.0]) * (1 + 0.09 * grain)[..., None], metal=0.97, rough=0.24, ao=ao, sh=shd, aniso=(1 - vertical, vertical, V(0.34)))
    col = plate
    col = mix(col, lac, c.cover(-E1 - d)[..., None])
    col = mix(col, flat('#060606', sh), (c.cover(np.abs(d + (E1 + E2) / 2) - (E2 - E1) / 2))[..., None])
    col = mix(col, alu, alu_mask[..., None])
    # turned parts have their own brushing direction
    for qa, cov, alb, aa in ((ba, np.maximum(c.cover(br - 0.118) * (br > 0.100), c.cover(br - 0.072)), ALU * 0.92, 0.45),
                             (pa, c.cover(pr - 0.108), ALU, 0.5), (ka, c.cover(kr - 0.046), DARK_STEEL * 1.3, 0.4)):
        m = shade(ROOM, nx, ny, nz, alb, metal=0.97, rough=0.22, ao=ao, sh=shd, aniso=(np.cos(qa), np.sin(qa), V(aa)))
        col = mix(col, m, cov[..., None])
    blk = shade(ROOM, nx, ny, nz, flat('#141416', sh), metal=0, rough=0.3, ao=ao, sh=shd, clear=0.5)
    col = mix(col, blk, np.maximum(c.cover(rr - 0.032), np.maximum(c.cover(br - 0.102) * (br > 0.071), c.cover(pr - 0.0125) * 0.9))[..., None])
    col = mix(col, alu, scr[..., None])
    # dark gap around the platter and the shadow it throws
    col = col * (1 - 0.95 * smooth(1.018, 1.010, R))[..., None]
    q = np.hypot(X - 0.028, Y - 0.042)
    throw = smooth(1.090, 0.985, q) * (R > 1.0) * (d < -E3)
    col = col * (1 - 0.66 * blur(throw.astype(F), 0.006 / c.px))[..., None]
    # meter cards (unlit), display glass, lamps that are off
    for sgn in (-1, 1):
        s = Part(c, sgn * VU[0], VU[1], VUH[0], VUH[1], Y0)
        k = c.cover(vin)[s.sl][..., None]
        col[s.sl] = mix(col[s.sl], vu_face(s, False), k)
    gk = c.cover(din)[..., None]
    col = mix(col, flat('#050404', sh) + flat('#1A120A', sh) * (0.35 * gauss(Y - DISP[1] + 0.03, 0.03))[..., None], gk)
    lk = clamp(0.5 - led / c.px)[..., None]
    which = np.floor((np.abs(X) - 0.026) / LEDX + 0.5)
    lens = np.where((which < 10)[..., None], rgb('#123016'), np.where((which < 14)[..., None], rgb('#3A270C'), rgb('#3C0E0C')))
    col = mix(col, lens * (0.8 + 0.9 * clamp(-ny * 1.4 + 0.2))[..., None], lk)
    # ---- screen printing
    ink = np.zeros(sh, F)

    def txt(st, size, x, y, font=RIGHTEOUS, rot=0.0):
        return c.text(st, size, x, y - Y0, font=font, rot=rot)
    for t_, x in (('L', -0.652), ('R', 0.652)):
        ink = np.maximum(ink, txt(t_, 0.034, x, LEDY))
    for deg in (-60, -30, 0, 30, 60):
        a_ = math.radians(deg)
        ink = np.maximum(ink, c.cover(c.capsule(0.810 + math.sin(a_) * 0.054, -0.968 - math.cos(a_) * 0.054, 0.810 + math.sin(a_) * 0.064, -0.968 - math.cos(a_) * 0.064, 0.0016)))
    col = mix(col, flat('#C9CBD0', sh) * 0.80, (ink * 0.75 * (d < -E3))[..., None])
    s = scratches(sh, 12, 40, width=1.0)
    col = col * (1 - 0.04 * s[..., None])
    c.put(col, c.cover(d), H)
    P.save(c.image(exposure=1.0), 'plinth', quality=88)


# ---------------------------------------------------------------- the platter
def platter():
    c = Canvas(P.px(1000), P.ss(2), 1.0)
    R = c.R
    H = np.where(R > 0.912, 0.052, 0.026)
    H = np.where(R > 0.905, np.maximum(H, 0.026 + 0.026 * smooth(0.905, 0.914, R)), H)
    H = H - 0.020 * smooth(0.984, 1.0, R) ** 2
    H = H - 0.0040 * smooth(0.926, 0.929, R) * smooth(0.983, 0.980, R)
    band = smooth(0.9265, 0.9285, R) * smooth(0.9825, 0.9805, R)
    rib = np.abs(((R - 0.10) / 0.0185) % 1.0 * 2 - 1)
    mat = smooth(0.903, 0.900, R)
    H = H + 0.0030 * smooth(0.30, 0.62, rib) * smooth(0.893, 0.890, R) * smooth(0.455, 0.46, R)
    H = H + 0.0004 * circular_streaks(c, 3, 1500) * (1 - mat)
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.006, 0.018, 0.05), 1.2)
    sh = cast(H, c.px, reach=0.12, slope=0.7)
    an = (np.cos(c.A), np.sin(c.A), V(0.52))
    alu = shade(ROOM, nx, ny, nz, ALU * 0.96, metal=0.97, rough=0.22, ao=ao, sh=sh, aniso=an)
    dark = shade(ROOM, nx, ny, nz, V([0.030, 0.031, 0.034]), metal=0.55, rough=0.3, ao=ao, sh=sh, aniso=(np.cos(c.A), np.sin(c.A), V(0.35)))
    g = fbm(c.shape, 130, 4, 2)
    rub = shade(ROOM, nx, ny, nz, flat('#2A2B2E', c.shape) * (1 + 0.16 * g)[..., None], metal=0, rough=0.55, spec=0.035, ao=ao, sh=sh)
    sweep = ROOM.brushed(np.cos(c.A), np.sin(c.A), np.zeros_like(R), np.zeros_like(R), np.ones_like(R), 0.5) * 0.035
    col = mix(alu, dark, band[..., None])
    col = mix(col, rub + sweep, mat[..., None])
    c.put(col, np.ones(c.shape, F), H)
    P.save(c.image(), 'platter', quality=88, how='jpg')


def dots():
    """Strobe dots: they turn with the platter, so they are a picture of their own."""
    c = Canvas(P.px(1000), P.ss(3), 1.0)
    a = np.zeros(c.shape, F)
    for n, r, size in ((180, 0.9365, 0.0038), (216, 0.9545, 0.0062), (240, 0.9725, 0.0038)):
        q = (c.A % (TAU / n)) - math.pi / n
        d = np.hypot(q * c.R, c.R - r) - size
        a = np.maximum(a, c.cover(d))
    c.col[:] = rgb('#D9DCE0') * 0.62
    c.alpha = (a * 0.92).astype(F)
    P.save(c.image(tone=False, dither=False), 'dots', how='png')


def beam():
    """The strobe lamp's light on the rim, straight up; it is turned to the selection."""
    c = Canvas(P.px(512), 1, 1.12)
    a = np.abs(c.A)
    rim = smooth(0.90, 0.93, c.R) * smooth(1.0, 0.985, c.R)
    wide = np.exp(-(a / 0.30) ** 2) * rim * 0.85
    core = np.exp(-(a / 0.085) ** 2) * rim * 1.1
    spill = np.exp(-(a / (0.10 + 0.25 * clamp(0.97 - c.R, 0, 1))) ** 2) * smooth(0.62, 0.96, c.R) * smooth(1.0, 0.97, c.R) * 0.42
    halo = gauss(np.hypot(c.X, c.Y + 0.985), 0.060) * 0.80
    k = wide + core + spill + halo
    k = k * smooth(1.12, 1.07, np.abs(c.Y))
    c.col[:] = rgb('#FF9A2E') * k[..., None] + rgb('#FFE2A8') * (core * 0.5 + halo * 0.30)[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=True), 'beam', quality=90, how='jpg')


def lamp():
    """The pilot lamp itself."""
    c = Canvas(P.px(96), 4, 1.0)
    ring = np.maximum(c.R - 0.60, 0.40 - c.R)
    H = bevel(ring, 0.10, 0.14)
    H = np.where(c.R < 0.42, 0.04 + dome(c.R, 0.42, 0.26), H)
    nx, ny, nz = normals(H, c.px)
    ins = smooth(0.42, 0.40, c.R)
    met = shade(ROOM, nx, ny, nz, ALU, metal=0.97, rough=0.2, ao=occlusion(H, c.px, (0.05, 0.15), 1))
    gl = shade(ROOM, nx, ny, nz, rgb('#FF8A14') * 0.4, metal=0, rough=0.2, clear=0.8) + rgb('#FF9C2A') * (1.5 * gauss(c.R, 0.40))[..., None] + rgb('#FFF0C8') * (1.6 * gauss(c.R, 0.20))[..., None]
    c.put(mix(met, gl, ins[..., None]), c.cover(c.R - 0.60), H)
    P.save(c.image(), 'lamp', how='png')


# ---------------------------------------------------------------- the tonearm (its pivot is the origin, the tip points down)
ARMW, ARMH, ARMY = 0.185, 0.76, 0.435   # half sizes of its picture and where the middle lies
ARML = 1.142


def arm_path():
    """The S of the tube, from the pivot to the headshell's collar."""
    pts = []
    key = [(0.0, 0.0), (0.0, 0.16), (0.0, 0.34), (0.004, 0.46), (0.022, 0.57), (0.046, 0.67), (0.056, 0.755), (0.046, 0.835), (0.022, 0.905), (-0.004, 0.965)]
    n = len(key)
    for i in range(n - 1):
        p0, p1, p2, p3 = key[max(0, i - 1)], key[i], key[i + 1], key[min(n - 1, i + 2)]
        for s in range(10):
            t = s / 10
            q = []
            for k in (0, 1):
                a, b, c_, d_ = p0[k], p1[k], p2[k], p3[k]
                q.append(0.5 * (2 * b + (-a + c_) * t + (2 * a - 5 * b + 4 * c_ - d_) * t * t + (-a + 3 * b - 3 * c_ + d_) * t ** 3))
            pts.append(tuple(q))
    pts.append(key[-1])
    return pts


def arm():
    c = Canvas(P.px(300), P.ss(3), ARMW, aspect=ARMH / ARMW)
    c.Y = c.Y + ARMY
    c.R, c.A = np.hypot(c.X, c.Y), np.arctan2(c.X, -c.Y)
    X, Y = c.X, c.Y
    pts = arm_path()
    tube = np.full(c.shape, 9, F)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        tube = np.minimum(tube, c.capsule(x0, y0, x1, y1, 0.0))
    rt = 0.0135
    dtube = tube - rt
    H = np.zeros(c.shape, F)
    H = np.where(dtube < 0, 0.060 + np.sqrt(clamp(rt * rt - tube * tube)), H)
    # collar and headshell, along the offset angle
    ang = math.radians(23)
    hx, hy = pts[-1]
    ux, uy = -math.sin(ang), math.cos(ang)                                   # along the shell
    qx, qy = X - hx, Y - hy
    along, across = qx * ux + qy * uy, qx * uy - qy * ux
    collar = np.maximum(np.abs(across) - 0.0215, np.abs(along - 0.012) - 0.016)
    H = np.where(collar < 0, 0.060 + np.sqrt(clamp(0.0215 ** 2 - across ** 2)) + 0.0012 * np.cos(along * 900), H)
    wide = 0.0375 - 0.10 * clamp(along - 0.13, 0, 1) ** 1.0 - 0.16 * clamp(0.052 - along, 0, 1)
    shell = np.maximum(np.abs(across) - wide, np.maximum(0.026 - along, along - 0.176))
    shell = smax(np.abs(across) - wide, np.maximum(0.026 - along, along - 0.176), 0.016)
    H = np.where(shell < 0, np.maximum(H, 0.058 + bevel(shell, 0.010, 0.012)), H)
    slots = np.full(c.shape, 9, F)
    for off in (-0.0165, 0.0165):
        slots = np.minimum(slots, np.maximum(np.abs(across - off) - 0.0045, np.abs(along - 0.110) - 0.028))
    H = np.where(slots < 0, H - 0.010, H)
    scr = np.full(c.shape, 9, F)
    for off in (-0.0165, 0.0165):
        scr = np.minimum(scr, np.hypot(across - off, along - 0.100) - 0.0088)
    H = np.where(scr < 0, 0.072 + bevel(scr, 0.004, 0.005), H)
    # finger lift: a thin wire curling out on the far side
    lift = np.full(c.shape, 9, F)
    lp = [(0.033, 0.150), (0.050, 0.152), (0.064, 0.148), (0.076, 0.139), (0.083, 0.126)]
    for (a0, b0), (a1, b1) in zip(lp[:-1], lp[1:]):
        t = clamp(((across - a0) * (a1 - a0) + (along - b0) * (b1 - b0)) / ((a1 - a0) ** 2 + (b1 - b0) ** 2))
        lift = np.minimum(lift, np.hypot(across - a0 - (a1 - a0) * t, along - b0 - (b1 - b0) * t))
    dl = lift - 0.0052
    H = np.where(dl < 0, np.maximum(H, 0.066 + np.sqrt(clamp(0.0052 ** 2 - lift * lift))), H)
    # counterweight and the tube's tail
    tail = np.maximum(np.abs(X) - 0.0165, np.maximum(Y - 0.0, -0.255 - Y))
    H = np.where(tail < 0, np.maximum(H, 0.058 + np.sqrt(clamp(0.0165 ** 2 - X * X))), H)
    cw = c.box(0.062, 0.062, 0, -0.178, r=0.012)
    H = np.where(cw < 0, 0.040 + np.sqrt(clamp(0.068 ** 2 - X * X)) * 0.95, H)
    grooves = np.cos((Y + 0.178) * 400) * ((np.abs(Y + 0.150) < 0.020) & (cw < 0))
    H = H + 0.0012 * grooves
    H = H - 0.006 * gauss(Y + 0.122, 0.0025) * (cw < 0) - 0.006 * gauss(Y + 0.206, 0.0025) * (cw < 0)
    # bearing: a ring, the yoke across it and a cap
    gim = np.abs(c.R - 0.062) - 0.0105
    H = np.where(gim < 0, np.maximum(H, 0.070 + np.sqrt(clamp(0.0105 ** 2 - (c.R - 0.062) ** 2)) * 1.1), H)
    yoke = np.maximum(np.abs(Y) - 0.011, np.abs(X) - 0.064)
    H = np.where(yoke < 0, np.maximum(H, 0.074), H)
    cap = c.R - 0.030
    H = np.where(cap < 0, np.maximum(H, 0.080 + bevel(cap, 0.010, 0.014)), H)
    body = np.minimum(np.minimum(np.minimum(dtube, shell), np.minimum(dl, collar)), np.minimum(np.minimum(tail, cw), np.minimum(np.minimum(gim, yoke), cap)))

    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.006, 0.02), 0.9)
    sh = cast(H, c.px, reach=0.05, slope=0.8)
    chrome = shade(ROOM, nx, ny, nz, CHROME, metal=0.98, rough=0.12, ao=ao, sh=sh)
    satin = shade(ROOM, nx, ny, nz, ALU, metal=0.97, rough=0.24, ao=ao, sh=sh, aniso=(np.cos(c.A), np.sin(c.A), V(0.3)))
    black = shade(ROOM, nx, ny, nz, V([0.016, 0.016, 0.018]), metal=0.0, rough=0.32, ao=ao, sh=sh, clear=0.55)
    col = chrome
    col = mix(col, satin, np.maximum(c.cover(gim), np.maximum(c.cover(yoke), c.cover(cap)))[..., None])
    col = mix(col, black, (c.cover(shell) * (1 - c.cover(scr)) * (1 - c.cover(collar)))[..., None])
    col = mix(col, black * 0.12, (c.cover(slots) * (1 - c.cover(scr)))[..., None])
    wt = c.cover(cw) * smooth(0.0, 0.004, np.abs(Y + 0.150) - 0.022)
    col = mix(col, black * 1.15, (wt * (1 - c.cover(cap)))[..., None])
    c.put(col, c.cover(body), H)
    P.save(c.image(exposure=1.02), 'arm', quality=90, how='jpg')
    # the shadow it throws on the deck
    small = Canvas(P.px(150), 2, ARMW, aspect=ARMH / ARMW)
    a = np.asarray(Image.fromarray((c.cover(body) * 255).astype(np.uint8), 'L').resize((small.w, small.h), Image.BILINEAR), F) / 255
    small.col[:] = 0
    small.alpha = (blur(a, 0.010 / small.px) * 0.62).astype(F)
    P.save(small.image(tone=False, dither=False), 'armshadow', how='png')


# ---------------------------------------------------------------- meters and lights
def vu():
    c = Canvas(P.px(380), P.ss(3), VUH[0], aspect=VUH[1] / VUH[0])
    c.put(vu_face(c, True), np.ones(c.shape, F))
    P.save(c.image(exposure=1.0), 'vu', quality=90, how='jpg')


def vucover():
    """Glass, inner shadow and the black hood over the needle's pivot."""
    c = Canvas(P.px(380), P.ss(3), VUH[0], aspect=VUH[1] / VUH[0])
    hood = smin(0.128 - c.Y + 0.0, c.circle(0.088, 0, 0.190), 0.03)
    inside = c.box(VUH[0], VUH[1], r=0.014)
    H = bevel(hood, 0.016, 0.018)
    H = H - 0.006 * ((np.abs(c.X * 0.8 + (c.Y - 0.140) * 0.6) < 0.0028) & (np.hypot(c.X, c.Y - 0.140) < 0.013))
    sc = np.hypot(c.X, c.Y - 0.140) - 0.0165
    H = np.where(sc < 0, H + bevel(sc, 0.004, 0.004), H)
    nx, ny, nz = normals(H, c.px)
    blk = shade(ROOM, nx, ny, nz, V([0.014, 0.013, 0.012]), metal=0, rough=0.35, clear=0.45, ao=occlusion(H, c.px, (0.006, 0.02), 1))
    met = shade(ROOM, nx, ny, nz, ALU * 0.8, metal=0.95, rough=0.25)
    blk = mix(blk, met, c.cover(sc)[..., None])
    # hood over a soft shadow, inner shadow of the frame, then reflections
    hs = blur(c.cover(hood - 0.004), 0.010 / c.px)
    edge = blur(1 - c.cover(inside + 0.004), 0.016 / c.px)
    top = blur(1 - c.cover(np.maximum(inside, -c.Y - VUH[1] + 0.0)), 0.012 / c.px) * smooth(0.02, -0.17, c.Y)
    dark = clamp(0.55 * hs + 0.80 * edge + 0.5 * top)
    c.put(np.zeros(c.shape + (3,), F), dark.astype(F))
    c.put(blk, c.cover(hood))
    u = c.X * 0.86 + c.Y * 0.5
    gl = smooth(-0.175, -0.150, u) * smooth(-0.052, -0.060, u) * 0.14 + smooth(-0.040, -0.034, u) * smooth(-0.012, -0.016, u) * 0.09
    gl = gl * smooth(0.16, -0.14, c.Y) * c.cover(inside + 0.008)
    c.put(np.ones(c.shape + (3,), F), gl.astype(F))
    c.alpha = c.alpha * c.cover(inside)
    P.save(c.image(tone=False), 'vucover', how='png')


def needle():
    """Points straight up; its pivot is the bottom edge."""
    c = Canvas(P.px(40), 4, 0.02, aspect=0.136 / 0.02)
    y = c.Y + 0.136                                                          # 0 at the top
    half = 0.0021 + 0.0020 * smooth(0.02, 0.22, y)
    d = np.maximum(np.maximum(np.abs(c.X) - half, 0.004 - y), y - 0.225)
    c.put(flat('#1A0A06', c.shape) + rgb('#FF3018') * (0.55 * smooth(0.09, 0.01, y))[..., None], c.cover(d))
    P.save(c.image(tone=False), 'needle', how='png')


def glows():
    """Pools of light, all drawn with `light`."""
    c = Canvas(P.px(240), 1, 0.40, aspect=0.95)
    q = np.hypot(np.maximum(np.abs(c.X) - VUH[0] + 0.02, 0), np.maximum(np.abs(c.Y) - VUH[1] + 0.02, 0))
    k = np.exp(-q / 0.075) * (0.35 + 0.65 * smooth(0.0, 0.030, q)) * smooth(0.40, 0.30, np.abs(c.X)) * smooth(0.38, 0.28, np.abs(c.Y))
    inner = smooth(0.025, 0.0, q)
    c.col = rgb('#FF9436') * (k * (1 - 0.85 * inner) * 0.115)[..., None]
    c.alpha[:] = 1
    P.save(c.image(), 'warm', quality=90, how='jpg')


def leds():
    """Lit lamps: green, amber, red. Each frame is wider than the lamp so that it can glow."""
    cols = [('#38FF5A', '#D8FFD8'), ('#FFB020', '#FFF0C0'), ('#FF2A1C', '#FFD0C0')]
    w, h = P.px(84), P.px(56)
    sheet = Image.new('RGBA', (w * 3, h), (0, 0, 0, 255))
    for i, (a, b) in enumerate(cols):
        c = Canvas(w, 4, 0.0375, aspect=h / w)
        d = np.maximum(np.abs(c.X) - 0.0125, np.abs(c.Y) - 0.0058)
        q = np.hypot(np.maximum(np.abs(c.X) - 0.0105, 0), np.maximum(np.abs(c.Y) - 0.004, 0))
        k = c.cover(d)
        c.col = rgb(a) * (0.85 * k + 0.55 * gauss(q, 0.0085) + 0.12 * gauss(q, 0.020))[..., None] + rgb(b) * (0.75 * k * gauss(c.R, 0.0105))[..., None]
        c.col = c.col * (smooth(0.0375, 0.030, np.abs(c.X)) * smooth(0.025, 0.019, np.abs(c.Y)))[..., None]
        c.alpha[:] = 1
        sheet.paste(c.image(), (w * i, 0))
    sheet.convert('RGB').save(os.path.join(P.dir, 'leds.png'), optimize=True)
    print('leds', sheet.size)


# ---------------------------------------------------------------- push buttons
INSET = (0.0, -0.075, 0.665, 0.610)     # the dark window: middle and half size, in cells
BAR = (0.0, 0.725, 0.185, 0.048)        # the lamp below it


def key():
    c = Canvas(P.px(260), P.ss(3), 1.0)
    d = c.box(0.925, 0.925, r=0.40)
    ins = c.box(INSET[2], INSET[3], INSET[0], INSET[1], r=0.215)
    bar = c.box(BAR[2], BAR[3], BAR[0], BAR[1], r=0.048)
    H = bevel(d, 0.115, 0.150)
    H = H + 0.018 * (1 - clamp((c.X ** 2 + c.Y ** 2) / 0.85))
    lip = np.abs(ins - 0.012) - 0.022
    H = np.maximum(H, np.where(lip < 0, 0.158 + bevel(lip, 0.022, 0.020), 0))
    floor = 0.050 + 0.030 * smooth(-0.10, 0.0, ins)
    H = np.where(ins < 0, floor, H)
    H = np.where(bar < 0.022, 0.150 - 0.030 * smooth(0.022, 0.006, bar), H)
    H = np.where(bar < 0, 0.120 + bevel(bar, 0.04, 0.032), H)
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.02, 0.06, 0.14), 1.15)
    sh = cast(H, c.px, reach=0.32, slope=0.75)
    # a hint of curvature spreads the light over the face
    fx, fy = nx + 0.10 * c.X, ny + 0.10 * c.Y
    inv = 1 / np.sqrt(fx * fx + fy * fy + nz * nz)
    st = clamp(0.7 * fibres(c.shape, 7, int(c.h * 0.22), 8) + 0.5 * fibres(c.shape, 22, int(c.h * 0.40), 9), -2, 2)
    alu = shade(ROOM, fx * inv, fy * inv, nz * inv, ALU * V([0.95, 0.965, 0.985]) * (1 + 0.075 * st)[..., None], metal=0.97, rough=0.28, ao=ao, sh=sh, aniso=(1.0, 0.0, 0.30))
    k = c.cover(ins)
    u = clamp(0.5 + (c.X * 0.45 + c.Y * 0.8) * 0.6)
    glass = mix(flat('#212328', c.shape), flat('#0B0C0E', c.shape), u[..., None])
    inset = shade(ROOM, nx, ny, nz, glass, metal=0, rough=0.4, spec=0.04, ao=ao, sh=sh, clear=0.35) * 0.9
    col = mix(alu, inset, k[..., None])
    lens = shade(ROOM, nx, ny, nz, flat('#1B211C', c.shape), metal=0, rough=0.2, ao=ao, sh=sh, clear=0.8)
    col = mix(col, lens, c.cover(bar)[..., None])
    c.put(col, c.cover(d), H)
    P.save(c.image(), 'key', quality=92, how='jpg')


def keylight():
    """Light behind the window, for the hovered button, and the bar lamps."""
    c = Canvas(P.px(260), 2, 1.0)
    ins = c.box(INSET[2], INSET[3], INSET[0], INSET[1], r=0.215)
    k = c.cover(ins)
    edge = np.exp(ins / 0.17)
    c.col[:] = rgb('#FF9326') * (k * (0.16 + 0.95 * edge))[..., None] + rgb('#FFD890') * (k * 0.42 * np.exp(ins / 0.055))[..., None]
    c.alpha[:] = 1
    P.save(c.image(), 'keylight', quality=90, how='jpg')
    c = Canvas(P.px(260), 2, 1.5)
    d = c.box(0.90, 0.90, r=0.40)
    g = np.exp(-clamp(d, 0, 9) / 0.16) * smooth(1.5, 1.1, c.R) * (d > -0.02) * 0.95 + gauss(d, 0.030) * 0.65
    c.col[:] = rgb('#FF9A32') * g[..., None]
    c.alpha[:] = 1
    P.save(c.image(), 'keyhalo', quality=88, how='jpg')
    w = P.px(150)
    for name, a, b in (('barg', '#3DFF62', '#E4FFE4'), ('bara', '#FFB224', '#FFF2C8')):
        c = Canvas(w, 3, 0.36, aspect=0.5)
        bar = c.box(BAR[2], BAR[3], 0, 0, r=0.048)
        kk = c.cover(bar)
        q = clamp(bar, 0, 9)
        c.col = rgb(a) * (0.90 * kk + 0.50 * np.exp(-q / 0.030) + 0.16 * np.exp(-q / 0.075))[..., None] + rgb(b) * (0.80 * kk * gauss(c.Y, 0.030) * gauss(c.X, 0.15))[..., None]
        c.col = c.col * (smooth(0.36, 0.29, np.abs(c.X)) * smooth(0.18, 0.13, np.abs(c.Y)))[..., None]
        c.alpha[:] = 1
        c.image().convert('RGB').save(os.path.join(P.dir, name + '.png'), optimize=True)


# ---------------------------------------------------------------- the record
def groove_bands(R):
    """1 where there is music, less in the gaps between tracks."""
    m = smooth(0.655, 0.668, R) * smooth(0.984, 0.972, R)
    for g, w in ((0.945, 0.0065), (0.880, 0.0050), (0.812, 0.0050), (0.750, 0.0050), (0.700, 0.0080)):
        m = m * (1 - gauss(R - g, w))
    return m


def record():
    c = Canvas(P.px(600), P.ss(2), 1.0)
    R = c.R
    m = groove_bands(R)
    st = circular_streaks(c, 41, 330)
    H = bevel(R - 0.997, 0.016, 0.014) + 0.0016 * st * m
    nx, ny, nz = normals(H, c.px)
    base = V([0.0105, 0.0105, 0.0115]) * (1.0 + 0.45 * st * m)[..., None]
    col = shade(ROOM, nx, ny, nz, base, metal=0, rough=0.35, spec=0.05, clear=0.25 + 0.0) * 0.75
    col = col + V([0.010, 0.010, 0.011]) * ((1 - m) * smooth(0.64, 0.66, R) * smooth(0.99, 0.98, R))[..., None]
    c.put(col, np.ones(c.shape, F), H)
    P.save(c.image(), 'record', quality=88, how='jpg')


def sheen():
    """The light on the grooves. It stays where the lamp is while the record turns under it."""
    c = Canvas(P.px(600), P.ss(2), 1.0)
    R, A = c.R, c.A
    m = groove_bands(R)
    on = smooth(0.645, 0.66, R) * smooth(0.995, 0.985, R)
    st = circular_streaks(c, 41, 330)
    st2 = circular_streaks(c, 77, 130)
    tex = clamp(0.72 + 0.22 * st + 0.16 * st2, 0.15, 1.6)

    def tie(phi, w):
        s = np.sin(A - math.radians(phi))
        return np.exp(-(s / w) ** 2)
    warm, cool = rgb('#FFF3E0'), rgb('#C4D8FF')
    k = 0.17 * tie(-38, 0.27) + 0.56 * tie(-38, 0.105) + 0.16 * tie(-15, 0.05) + 0.10 * tie(-60, 0.035)
    q = 0.09 * tie(58, 0.18) + 0.14 * tie(64, 0.055)
    gap = (1 - m) * on
    g = 0.22 * tie(-38, 0.05) + 0.06 * tie(60, 0.05)
    c.col = warm * (k * tex * m * on * 0.55 + g * gap)[..., None] + cool * (q * tex * m * on * 0.6)[..., None]
    rim = gauss(R - 0.990, 0.006)
    c.col = c.col + warm * (rim * (0.55 * tie(-38, 0.45) * smooth(0.25, -0.35, c.Y + 0.6 * c.X)))[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=False), 'sheen', quality=88, how='jpg')


def grooves():
    """What can be seen to turn: the music in the grooves dims the sheen here and there, plus a little dust."""
    c = Canvas(P.px(560), P.ss(2), 1.0)
    R, A = c.R, c.A
    rg = rng(5)
    nr, na = 150, 40
    tab = rg.standard_normal((nr, na)).astype(F)
    tab = np.concatenate([tab[:, -6:], tab, tab[:, :6]], axis=1)
    for _ in range(2):
        tab = (np.roll(tab, 1, 1) + tab * 2 + np.roll(tab, -1, 1)) / 4
    tab = tab[:, 5:-5]                                                       # one extra column at both ends for wrapping
    im = Image.fromarray(tab, 'F').resize((na * 16 + 32, nr * 6), Image.BICUBIC)
    t = np.asarray(im, F)
    u = ((A / TAU) % 1.0) * (na * 16) + 16
    v = clamp((R - 0.64) / 0.36) * (t.shape[0] - 1)
    val = t[v.astype(np.int32), np.clip(u.astype(np.int32), 0, t.shape[1] - 1)]
    m = groove_bands(R)
    a = clamp(0.34 + 0.34 * val, 0, 0.80) * m
    c.col[:] = 0
    c.alpha = a.astype(F)
    dust = np.zeros(c.shape, F)
    for _ in range(26):
        rr, aa = 0.67 + 0.30 * rg.random(), rg.random() * TAU
        x, y = c.polar(aa, rr)
        dust = np.maximum(dust, gauss(np.hypot(c.X - x, c.Y - y), 0.0022 + 0.0018 * rg.random()) * (0.25 + 0.35 * rg.random()))
    for _ in range(3):                                                       # hairlines
        aa, rr = rg.random() * TAU, 0.70 + 0.22 * rg.random()
        x, y = c.polar(aa, rr)
        x1, y1 = c.polar(aa + 0.10 * (rg.random() - 0.5), rr + 0.10 * (rg.random() - 0.3))
        dust = np.maximum(dust, clamp(1 - np.abs(c.capsule(x, y, x1, y1, 0)) / 0.0022) * 0.30)
    c.put(np.ones(c.shape + (3,), F) * 0.75, (dust * smooth(0.65, 0.67, R) * smooth(0.985, 0.97, R)).astype(F))
    P.save(c.image(tone=False, dither=False), 'grooves', quality=80, how='jpg')


def label():
    c = Canvas(P.px(440), P.ss(3), 1.0)
    R = c.R
    edge = 0.835
    paper = fbm(c.shape, 90, 4, 3) * 0.5 + fbm(c.shape, 9, 6, 4) * 0.5
    inner = mix(flat('#F2BE5A', c.shape), flat('#E49B34', c.shape), smooth(0.0, 0.9, R)[..., None])
    outer = mix(flat('#C4432A', c.shape), flat('#9E2C1E', c.shape), smooth(0.83, 1.0, R)[..., None])
    col = mix(inner, outer, smooth(edge - 0.004, edge + 0.004, R)[..., None])
    cream = np.zeros(c.shape, F)
    for r, w in ((edge, 0.0075), (edge - 0.030, 0.0030), (0.978, 0.0040)):
        cream = np.maximum(cream, clamp((w - np.abs(R - r)) / c.px + 0.5))
    ring = 'HIGH FIDELITY  •  33⅓ RPM  •  STEREO  •  LONG PLAY  •  '
    ring = 'HIGH FIDELITY  •  33 RPM  •  STEREO  •  LONG PLAYING  •  SIDE ONE  •  '
    f = load_font(RIGHTEOUS, 0.088 / c.px)
    total = sum(f.getlength(ch) for ch in ring) * c.px
    cream = np.maximum(cream, c.ring_text(ring, 0.088, 0.905, 0.0, font=RIGHTEOUS, spacing=TAU * 0.905 / total))
    col = mix(col, flat('#FFF0D2', c.shape), (cream * 0.92)[..., None])
    col = col * (1 + 0.05 * paper)[..., None]
    H = -0.010 * gauss(R - 0.44, 0.014) - 0.02 * smooth(0.985, 1.0, R)
    nx, ny, nz = normals(H, c.px)
    sd = shade(ROOM, nx, ny, nz, col, metal=0, rough=0.5, spec=0.03) * 0.92
    c.put(sd, np.ones(c.shape, F))
    P.save(c.image(exposure=0.95), 'label', quality=90, how='jpg')


def spindle():
    c = Canvas(P.px(64), 4, 1.0)
    hole = c.cover(c.R - 0.92)
    c.put(flat('#120805', c.shape), hole * 0.9)
    H = dome(c.R, 0.62, 0.50)
    c.put(shade(ROOM, *normals(H, c.px), CHROME, metal=0.98, rough=0.12), c.cover(c.R - 0.62), H)
    P.save(c.image(), 'spindle', how='png')


# ---------------------------------------------------------------- display digits, buttons, notes
def digits():
    """Lit seven-segment digits with their glow: ten frames, same shapes as the segment typeface."""
    segs, on = segments()
    w, h = P.px(72), P.px(96)
    sheet = Image.new('RGB', (w * 10, h))
    for i in range(10):
        c = Canvas(w, 4, 360.0, aspect=960 / 720)
        d = np.full(c.shape, 1e6, F)
        for s in on[str(i)]:
            d = np.minimum(d, c.poly([(x + 75 + 0.10 * y - 300, -(y - 380)) for x, y in segs[s]]))
        q = clamp(d, 0, 1e6)
        c.col = rgb('#FFB347') * (0.95 * c.cover(d) + 0.0)[..., None] + rgb('#FF7A14') * (0.34 * np.exp(-q / 26) + 0.10 * np.exp(-q / 80))[..., None]
        c.col = c.col * (smooth(360, 300, np.abs(c.X)) * smooth(480, 420, np.abs(c.Y)))[..., None]
        c.alpha[:] = 1
        sheet.paste(c.image(tone=False).convert('RGB'), (w * i, 0))
    sheet.save(os.path.join(P.dir, 'digits.png'), optimize=True)
    print('digits', sheet.size)


def knob():
    """A small round push button, for pinning and for the settings."""
    c = Canvas(P.px(96), 4, 1.0)
    H = bevel(np.maximum(c.R - 0.96, 0.74 - c.R), 0.11, 0.14)
    H = np.where(c.R < 0.76, 0.05 + dome(c.R, 0.95, 0.10), H)
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.04, 0.12), 1)
    met = shade(ROOM, nx, ny, nz, ALU * 0.9, metal=0.97, rough=0.22, ao=ao, aniso=(np.cos(c.A), np.sin(c.A), V(0.4)))
    blk = shade(ROOM, nx, ny, nz, flat('#18191C', c.shape), metal=0, rough=0.35, ao=ao, clear=0.35)
    c.put(mix(met, blk, c.cover(c.R - 0.755)[..., None]), c.cover(c.R - 0.96), H)
    P.save(c.image(), 'knob', how='png')


def notes():
    """Two little notes that fly off when something is started."""
    w = P.px(64)
    sheet = Image.new('RGBA', (w * 2, w), (0, 0, 0, 0))
    for i in range(2):
        c = Canvas(w, 4, 1.0)
        cs, sn = math.cos(-0.35), math.sin(-0.35)

        def head(x, y):
            px, py = c.X - x, c.Y - y
            return (np.hypot((px * cs + py * sn) / 1.25, (-px * sn + py * cs)) - 0.20)
        if i == 0:
            d = np.minimum(head(-0.12, 0.52), c.box(0.045, 0.60, 0.09, -0.06))
            d = np.minimum(d, c.taper(0.09, -0.62, 0.05, 0.46, -0.16, 0.10) + 0.0)
            d = np.minimum(d, c.taper(0.46, -0.16, 0.10, 0.42, 0.16, 0.02))
        else:
            d = np.minimum(head(-0.50, 0.52), head(0.36, 0.40))
            d = np.minimum(d, np.minimum(c.box(0.045, 0.56, -0.29, -0.02), c.box(0.045, 0.56, 0.57, -0.14)))
            d = np.minimum(d, c.poly([(-0.335, -0.62), (0.615, -0.76), (0.615, -0.50), (-0.335, -0.36)]))
        c.put(flat('#FFFFFF', c.shape), c.cover(d))
        sheet.paste(c.image(tone=False, dither=False), (w * i, 0))
    sheet.save(os.path.join(P.dir, 'notes.png'), optimize=True)
    print('notes', sheet.size)


# ---------------------------------------------------------------- frames for the other layouts (cut in nine, so never in draft size)
def panel():
    n = 360
    c = Canvas(n, 3, 1.0)
    sh = c.shape
    d = c.box(0.860, 0.860, r=0.215)
    ax, ay = 0.86 - np.abs(c.X), 0.86 - np.abs(c.Y)
    wh, hh = walnut(sh, 2.6 / c.w * 0.55, 91)
    wv, hv = walnut(sh, 2.6 / c.w * 0.55, 92)
    side = clamp((ay - ax) / c.px + 0.5)
    board = mix(wh, wv.transpose(1, 0, 2), side[..., None]) * (1 - 0.6 * gauss(ay - ax, 0.006))[..., None]
    E1, E2 = 0.118, 0.152
    H = bevel(d, 0.050, 0.070) + 0.002 * mix(hh, hv.T, side) * (d > -E1)
    H = np.where(d < -E1, 0.040, H)
    trim = np.maximum(d + E1 + 0.006, -E2 - d)
    H = np.where(trim < 0, 0.058 + bevel(trim, 0.008, 0.016), H)
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.012, 0.035, 0.08), 1.2)
    shd = cast(H, c.px, reach=0.18, slope=0.7)
    lac = shade(ROOM, nx, ny, nz, board * 1.02, metal=0, rough=0.35, ao=ao, sh=shd, clear=0.30)
    alu = shade(ROOM, nx, ny, nz, ALU, metal=0.97, rough=0.25, ao=ao, sh=shd)
    st = clamp(0.8 * fibres(sh, 8, int(sh[0] * 0.5), 5), -2, 2)
    t = clamp(0.5 + 0.5 * c.Y)
    plate = mix(flat('#3A3C41', sh), flat('#1A1B1E', sh), t[..., None]) * (0.62 * (1 + 0.04 * st) * (0.35 + 0.65 * ao) * (0.5 + 0.5 * shd))[..., None]
    col = mix(plate, alu, c.cover(trim)[..., None])
    col = mix(col, lac, c.cover(-E1 - d)[..., None])
    s = 1 - smooth(-0.06, 0.125, blur(shift(d, int(0.015 / c.px), int(0.035 / c.px)).astype(F), 0.02 / c.px))
    c.put(np.zeros(sh + (3,), F), (0.55 * s * smooth(1.0, 0.94, np.maximum(np.abs(c.X), np.abs(c.Y)))).astype(F))
    c.put(col, c.cover(d), H)
    P.save(c.image(), 'panel', quality=90, how='jpg')


def tile():
    """A record sleeve: cream card with two printed stripes."""
    w, h = 220, 300
    c = Canvas(w, 3, 1.0, aspect=h / w)
    hy = h / w
    sh = c.shape
    d = c.box(0.945, hy - 0.055, r=0.060)
    paper = fbm(sh, 120, 3, 3) * 0.6 + fbm(sh, 7, 5, 4) * 0.6
    col = flat('#F6E9C8', sh) * (0.98 + 0.030 * paper)[..., None]
    y = c.Y + hy - 0.055
    stripe = lambda a, b: clamp((y - a) / c.px + 0.5) * clamp((b - y) / c.px + 0.5)
    col = mix(col, flat('#B93C24', sh) * 0.80, stripe(0.115, 0.225)[..., None])
    col = mix(col, flat('#E6A63C', sh) * 0.82, stripe(0.245, 0.300)[..., None])
    col = mix(col, flat('#4A2A18', sh) * 0.80, stripe(0.318, 0.334)[..., None])
    line = clamp((0.0055 - np.abs(d + 0.055)) / c.px + 0.5)
    col = mix(col, flat('#4A2A18', sh) * 0.80, (0.45 * line)[..., None])
    worn = smooth(-0.10, 0.0, d + 0.02 * fbm(sh, 14, 8, 4))
    col = mix(col, flat('#C9B184', sh) * 0.72, (0.65 * worn)[..., None])
    H = bevel(d, 0.020, 0.012) + 0.0012 * paper
    nx, ny, nz = normals(H, c.px)
    sd = shade(ROOM, nx, ny, nz, col, metal=0, rough=0.6, spec=0.03) * 0.95
    s = 1 - smooth(-0.04, 0.055, blur(shift(d, int(0.012 / c.px), int(0.018 / c.px)).astype(F), 0.012 / c.px))
    c.put(np.zeros(sh + (3,), F), (0.60 * s).astype(F))
    c.put(sd, c.cover(d), H)
    P.save(c.image(exposure=0.95), 'tile', quality=90, how='jpg')


if __name__ == '__main__':
    P.run([fonts, shadow, plinth, platter, dots, beam, lamp, arm, vu, vucover, needle, glows, leds, key, keylight, record, sheen, grooves, label, spindle, digits, knob, notes, panel, tile])
    P.sounds('vinyl')
    P.finish()
