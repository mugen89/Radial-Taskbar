"""Close-ups side by side: python zoom.py out.png skin skin skin [-- snapshot options]"""
import sys
from PIL import Image
from shot import run
a = sys.argv[1:]
opts = '--items 10 --groups --profiles 3 --hover 3'.split()
if '--' in a:
    opts = a[a.index('--') + 1:]
    a = a[:a.index('--')]
out, names = a[0], a[1:]
s = Image.new('RGB', (700 * len(names), 622))
for i, k in enumerate(names):
    run(k, out + '.p.png', '--w', 900, '--h', 800, '--scale', 1.45, *opts)
    s.paste(Image.open(out + '.p.png').convert('RGB').resize((700, 622), Image.LANCZOS), (i * 700, 0))
import os
os.remove(out + '.p.png')
s.save(out)
