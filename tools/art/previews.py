"""Makes preview.jpg (the picture in the gallery) for the named skins, or for all of them.

    python previews.py                 all
    python previews.py clockwork vinyl
"""
import os
import sys

from PIL import Image

from shot import ROOT, run

names = sys.argv[1:] or sorted(d for d in os.listdir(os.path.join(ROOT, 'skins')) if os.path.exists(os.path.join(ROOT, 'skins', d, 'skin.json')))
for n in names:
    out = os.path.join(ROOT, 'skins-extra' if os.path.isdir(os.path.join(ROOT, 'skins-extra', n)) else 'skins', n, 'preview.jpg')
    tmp = out + '.part.png'
    if not run(n, tmp, '--items', 10, '--groups', '--profiles', 3, '--hover', 3, '--w', 1000, '--h', 750, '--scale', 1.9, '--t', 1.7):
        continue
    im = Image.open(tmp).convert('RGB').resize((640, 480), Image.LANCZOS)
    im.save(out, quality=86, optimize=True)
    os.remove(tmp)
    print(n, os.path.getsize(out) // 1024, 'KB')
