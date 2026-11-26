"""Writes the files of one skin: pictures as small as they can be without showing it, sounds as WAV."""
import os
import struct
import sys
import time

import numpy as np
from PIL import Image

from artkit import F, bleed, blur

if os.name == 'nt':      # the person may be working: drawing can wait
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Pack:
    def __init__(self, name, argv):
        self.name = name
        extra = os.path.join(ROOT, 'skins-extra', name)           # not part of the setup program, handed out on its own
        self.dir = extra if os.path.isdir(extra) else os.path.join(ROOT, 'skins', name)
        os.makedirs(self.dir, exist_ok=True)
        self.draft = 0.5 if '--draft' in argv else 1.0
        self.only = [a for a in argv[1:] if not a.startswith('--')]
        self.files = {}
        self.t = time.time()
        self.todo = None

    def px(self, n):
        return max(16, int(n * self.draft))

    def ss(self, n):
        return max(1, n if self.draft == 1 else n - 1)

    def run(self, jobs):
        for j in jobs:
            nm = getattr(j, '__name__', '')
            if self.only and nm not in self.only and nm != '<lambda>':
                continue
            j()

    def want(self, name):
        return not self.only or name in self.only

    def save(self, im, name, quality=90, how='auto'):
        """RGBA in, files out. Opaque or large pictures become a JPEG plus a mask, small ones stay PNG."""
        p = os.path.join(self.dir, name)
        for ext in ('.png', '.jpg', '-mask.png'):
            if os.path.exists(p + ext) and how != 'keep':
                os.remove(p + ext)
        a = np.asarray(im.getchannel('A'))
        opaque = a.min() == 255
        if how == 'auto':
            full = im.size[0] * im.size[1] / self.draft ** 2     # the file type must not depend on draft mode
            how = 'jpg' if full > 130 * 130 else 'png'
        if how == 'png':
            im.save(p + '.png', optimize=True)
            size = os.path.getsize(p + '.png')
        else:
            (im if opaque else bleed(im)).convert('RGB').save(p + '.jpg', quality=quality, subsampling=2 if max(im.size) >= 500 else 0, optimize=True)
            size = os.path.getsize(p + '.jpg')
            if not opaque:
                im.getchannel('A').save(p + '-mask.png', optimize=True)
                size += os.path.getsize(p + '-mask.png')
        print('%-14s %4dx%-4d %6.1f KB  %5.1fs' % (name, im.size[0], im.size[1], size / 1024, time.time() - self.t), flush=True)
        self.t = time.time()

    def wav(self, name, pcm, rate=24000):
        pcm = np.clip(pcm, -1, 1)
        data = (pcm * 32000).astype('<i2').tobytes()
        with open(os.path.join(self.dir, name + '.wav'), 'wb') as f:
            f.write(b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) + b'data' + struct.pack('<I', len(data)) + data)

    def sounds(self, kind):
        import sounds
        for k, pcm in sounds.make(kind).items():
            self.wav(k, pcm)

    def finish(self):
        total = 0
        for f in os.listdir(self.dir):
            total += os.path.getsize(os.path.join(self.dir, f))
        print('%s: %.0f KB in all' % (self.name, total / 1024))
