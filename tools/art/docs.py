"""Pictures for the README: docs/skins.png, docs/layouts.png, docs/settings.png. (docs/styles.png shows the plain styles.)"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

from shot import EXE, ROOT

DOCS = os.path.join(ROOT, 'docs')
D = os.path.join(tempfile.gettempdir(), 'rt2_docs')
os.makedirs(D, exist_ok=True)
ENV = dict(os.environ, RADIALTASKBAR_DATA=D, RadialTaskbar_SKINS=os.path.join(ROOT, 'skins'))
FONT = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 15)


def draw(*opts):
    p = os.path.join(D, 'one.png')
    subprocess.run([EXE] + [str(o) for o in opts[:1]] + [p] + [str(o) for o in opts[1:]], env=ENV, timeout=120, check=True)
    return Image.open(p).convert('RGB')


def sheet(name, cells, tile, cols, gap=6):
    rows = (len(cells) + cols - 1) // cols
    s = Image.new('RGB', (tile[0] * cols + gap * (cols + 1), tile[1] * rows + gap * (rows + 1)), (15, 17, 23))
    for i, (label, im) in enumerate(cells):
        x, y = gap + (i % cols) * (tile[0] + gap), gap + (i // cols) * (tile[1] + gap)
        s.paste(im.resize(tile, Image.LANCZOS), (x, y))
        d = ImageDraw.Draw(s, 'RGBA')
        w = d.textlength(label, font=FONT)
        d.rounded_rectangle((x + 8, y + 8, x + 22 + w, y + 32), 8, fill=(10, 12, 18, 170))
        d.text((x + 15, y + 10), label, font=FONT, fill=(255, 255, 255, 235))
    p = os.path.join(DOCS, name)
    s.save(p, optimize=True)
    print(name, s.size, os.path.getsize(p) // 1024, 'KB')


def names(folder='skins'):
    import json
    import re
    out = []
    for d in sorted(os.listdir(os.path.join(ROOT, folder))):
        p = os.path.join(ROOT, folder, d, 'skin.json')
        if os.path.exists(p):
            m = re.search(r'"name"\s*:\s*"([^"]+)"', open(p, encoding='utf-8').read())
            out.append((d, m.group(1) if m else d))
    return sorted(out, key=lambda x: x[1].lower())


which = sys.argv[1:] or ['skins', 'layouts', 'settings']
if 'skins' in which:
    cells = [(n, Image.open(os.path.join(ROOT, f, i, 'preview.jpg')).convert('RGB')) for f in ('skins', 'skins-extra') for i, n in names(f)]
    sheet('skins.png', cells, (320, 240), 5)
if 'layouts' in which:
    looks = [('radial', 'Radial wheel', 'aurora'), ('flow', 'Side flow', 'glass'), ('strip', 'Line strip', 'glass'), ('orbit', 'Orbit', 'aurora'), ('comb', 'Honeycomb', 'glass'), ('carousel', 'Carousel', 'neon'),
             ('globe', 'Globe', 'glass'), ('cards', 'Hand of cards', 'arcane'), ('corner', 'Corner fan', 'glass'), ('galaxy', 'Galaxy', 'aurora'), ('board', 'Board', 'paper'), ('drum', 'Drum', 'graphite')]
    cells = []
    for lid, n, look in looks:
        o = ['--snapshot', '--look', look, '--layout', lid, '--items', 16, '--profiles', 3, '--hover', 4, '--w', 960, '--h', 720, '--perring', 8]
        if lid == 'flow':
            o += ['--edge', 'right']
        cells.append((n, draw(*o)))
    sheet('layouts.png', cells, (330, 248), 4)
if 'settings' in which:
    a = draw('--settings-shot', '--page', 2, '--w', 1180, '--h', 780, '--skin', 'clockwork')
    b = draw('--settings-shot', '--page', 1, '--w', 1180, '--h', 780, '--layout', 'orbit', '--dark')
    sheet('settings.png', [('Skins', a), ('Layout', b)], (885, 585), 1)
