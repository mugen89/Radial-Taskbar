"""Skins in other layouts: one row per skin."""
import os
import sys

from PIL import Image, ImageDraw

from shot import run

JOBS = ['--items 10 --groups --hover 4 --layout cards', '--items 10 --groups --hover 3 --layout flow --edge right', '--items 10 --groups --hover 4 --layout strip', '--items 12 --groups --hover 4 --layout orbit', '--items 12 --groups --hover 4 --layout comb', '--items 12 --groups --hover 4 --layout drum']
TW, TH = 260, 220
out, names = sys.argv[1], sys.argv[2:]
s = Image.new('RGB', (TW * len(JOBS), TH * len(names)), (20, 22, 28))
tmp = out + '.part.png'
for y, n in enumerate(names):
    for x, o in enumerate(JOBS):
        if run(n, tmp, '--w', 780, '--h', 660, *o.split()):
            im = Image.open(tmp).convert('RGB').resize((TW, TH), Image.LANCZOS)
            if x == 0:
                ImageDraw.Draw(im).text((6, 4), n, fill=(255, 240, 120))
            s.paste(im, (x * TW, y * TH))
if os.path.exists(tmp):
    os.remove(tmp)
s.save(out)
