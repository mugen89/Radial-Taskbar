"""Pictures of a skin as the program draws it, without opening anything on screen.

    python shot.py clockwork out.png --items 10 --hover 3          one picture, any --snapshot option
    python shot.py clockwork out.png --sheet                       twelve situations on one sheet
    python shot.py clockwork out.png --opening                     the first half second, frame by frame
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXE = os.environ.get('RT_EXE') or os.path.join(ROOT, 'build', 'RadialTaskbar.exe')


def run(skin, out, *opts):
    d = os.path.join(tempfile.gettempdir(), 'rt2_shot_%d' % os.getpid())
    os.makedirs(d, exist_ok=True)
    log = os.path.join(d, 'log.txt')
    if os.path.exists(log):
        os.remove(log)
    env = dict(os.environ, RADIALTASKBAR_DATA=d, RADIALTASKBAR_LOG=log, RadialTaskbar_SKINS=os.path.join(ROOT, 'skins-extra' if os.path.isdir(os.path.join(ROOT, 'skins-extra', skin)) else 'skins'))
    r = subprocess.run([EXE, '--snapshot', os.path.abspath(out), '--skin', skin] + [str(o) for o in opts], env=env, timeout=120)
    lines = [l.rstrip() for l in open(log, errors='replace')] if os.path.exists(log) else []
    for l in lines:
        if ('skin' in l and 'icons:' not in l) or 'bench' in l:
            print(l)
    if r.returncode:
        print('FAILED with', r.returncode)
    return r.returncode == 0


SITUATIONS = [
    ('idle, 10 entries', '--items 10 --profiles 3'.split()),
    ('hover, groups', '--items 10 --groups --profiles 3 --hover 3'.split()),
    ('5 entries', '--items 5 --hover 1'.split()),
    ('two rings', '--items 17 --groups --profiles 3 --hover 12'.split()),
    ('group open', '--items 10 --groups --hover 2 --kid 1 --t 2.2'.split()),
    ('opening, 0.10 s', '--items 10 --t 0.10'.split()),
    ('bright desktop', '--items 12 --hover 4 --light'.split()),
    ('launching', '--items 10 --hover 3 --closing 0.06'.split()),
    ('numbers and names', '--items 8 --numbers --labels --hover 2'.split()),
    ('cards', '--items 11 --groups --hover 4 --layout cards'.split()),
    ('board', '--items 14 --groups --hover 4 --layout board'.split()),
    ('side flow', '--items 10 --groups --hover 3 --layout flow --edge right'.split()),
]


def sheet(skin, out, jobs, size=(860, 760), tile=(480, 424), cols=4):
    tmp = out + '.part.png'
    rows = (len(jobs) + cols - 1) // cols
    s = Image.new('RGB', (tile[0] * cols, tile[1] * rows), (20, 22, 28))
    for i, (name, opts) in enumerate(jobs):
        if not run(skin, tmp, '--w', size[0], '--h', size[1], *opts):
            continue
        im = Image.open(tmp).convert('RGB').resize(tile, Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), name, fill=(255, 240, 120))
        s.paste(im, ((i % cols) * tile[0], (i // cols) * tile[1]))
    os.remove(tmp)
    s.save(out)
    print('wrote', out)


if __name__ == '__main__':
    skin, out, opts = sys.argv[1], sys.argv[2], sys.argv[3:]
    if '--sheet' in opts:
        sheet(skin, out, SITUATIONS)
    elif '--opening' in opts:
        sheet(skin, out, [('%.2f s' % t, ['--items', '10', '--profiles', '3', '--t', '%.3f' % t]) for t in (0.03, 0.06, 0.10, 0.15, 0.20, 0.28, 0.38, 0.55)])
    else:
        run(skin, out, *opts)
