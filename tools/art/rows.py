"""Several skins at a glance: one row per skin.

    python rows.py out.png porcelain blueprint roulette
"""
import os
import sys

from PIL import Image, ImageDraw

from shot import run

JOBS = [
    ('idle', '--items 10 --profiles 3'.split()),
    ('hover', '--items 10 --groups --profiles 3 --hover 3'.split()),
    ('two rings', '--items 17 --groups --hover 12 --light'.split()),
    ('group', '--items 8 --groups --hover 2 --kid 1 --t 2.2'.split()),
    ('launch', '--items 9 --hover 2 --closing 0.09 --numbers'.split()),
    ('board', '--items 12 --groups --hover 4 --layout board'.split()),
]
TW, TH = 400, 360
out, names = sys.argv[1], sys.argv[2:]
s = Image.new('RGB', (TW * len(JOBS), TH * len(names)), (20, 22, 28))
tmp = out + '.part.png'
for y, n in enumerate(names):
    for x, (label, opts) in enumerate(JOBS):
        if run(n, tmp, '--w', 800, '--h', 720, '--scale', 1.05, *opts):
            im = Image.open(tmp).convert('RGB').resize((TW, TH), Image.LANCZOS)
            if x == 0:
                ImageDraw.Draw(im).text((8, 6), n, fill=(255, 240, 120))
            s.paste(im, (x * TW, y * TH))
if os.path.exists(tmp):
    os.remove(tmp)
s.save(out)
print('wrote', out)
