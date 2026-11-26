"""How skins open: one row per skin, six moments of the first half second.

    python opens.py out.png vinyl reactor ...
"""
import os
import sys

from PIL import Image, ImageDraw

from shot import run

TIMES = (0.03, 0.08, 0.14, 0.21, 0.30, 0.45)
TW, TH = 300, 270
out, names = sys.argv[1], sys.argv[2:]
s = Image.new('RGB', (TW * len(TIMES), TH * len(names)), (20, 22, 28))
tmp = out + '.part.png'
for y, n in enumerate(names):
    for x, t in enumerate(TIMES):
        if run(n, tmp, '--w', 720, '--h', 648, '--items', 10, '--profiles', 3, '--t', '%.3f' % t):
            im = Image.open(tmp).convert('RGB').resize((TW, TH), Image.LANCZOS)
            if x == 0:
                ImageDraw.Draw(im).text((6, 4), n, fill=(255, 240, 120))
            s.paste(im, (x * TW, y * TH))
if os.path.exists(tmp):
    os.remove(tmp)
s.save(out)
print('wrote', out)
