"""What the skins of 26 November share: one call writes skin.json with the usual words, badges and panels.

    from lineup import *
    K = Kit(...)
    ... pictures ...
    finish(K, P, back=[...], under=[...], hub=[...], sounds='term')

P is the palette: base, accent, accent2, text (on the hub), sub (smaller text), ink (on light panels),
panel (two colours), stroke, tile (two colours), dim, font.
"""
from skinkit import *


def grad(a, b):
    return {'type': 'linear', 'stops': [[0, a], [1, b]]}


def finish(K, P, back, under, hub, over=None, slot_over=None, icon=None, front=None, particles=None, onlaunch=None, onhover=None, onopen=None, screen=None, wheel=None, style=None,
           sounds=None, slot_intro=None, tabs=None, words_kw=None, badge_kw=None, running_kw=None, kid=None, marks=None, fonts=None):
    if sounds:
        K.sounds(sounds)
    T = 'title'
    font = P.get('font', 'Segoe UI')
    fam = font['family'] if isinstance(font, dict) else font.split(',')[0].strip()
    st = dict(shape='orb', material='solid', base=P['base'], accent=P['accent'], accent2=P['accent2'], text=P['text'], border=P.get('border', P['accent']), opacity=0.98, corner=14,
              font=fam, open='bloom', speed=1, hoverGrow=3, iconZoom=1.12, glow=0, tilt=0.4, pointer=False, burst=False, shadow=0.5, dim=P.get('dim', 0.3))
    st.update(style or {})
    wh = dict(hub=90, thickness=92, gap=5, ringgap=10, rim=32, icon=42, crowd=1.45, area=1.10, hubkeep=0.76)
    wh.update(wheel or {})
    wk = dict(px=17, box=(1.26, 0.60), clockpx=31, datepx=12, shadow=dict(x=0, y=1, blur=3, color='black/70'))
    wk.update(words_kw or {})
    bk = dict(x=0.64, y=-0.64)
    bk.update(badge_kw or {})
    slot = dict(intro=slot_intro or intro(0.42, 'back', 0.06, scale=0.3, stagger=0.02, order='both'), under=under,
                icon=icon or dict(size=0.92, zoom=1.14, shadow=dict(x=1, y=2, blur=3, color='black/50')),
                over=(slot_over or []) + running(P['accent'], P.get('hot', P['accent2']), **(running_kw or {})) + badge(P.get('badge', P['accent']), P.get('badgeink', P['base']), T, **bk)
                + groupmark(P['text'], -0.80, 0.12), marks=False, chevron=False, badge=False)
    parts = dict(style=st, wheel=wh, colors=dict(text=P['text'], sub=P['sub']), fonts=dict(title=font, **(fonts or {})), back=back, slot=slot,
                 hub=hub + words('text', 'sub', T, **wk),
                 draw=dict(clock=False, shadow=False, text='text'),
                 tabs=tabs or dict(inset=13, text='text', fill=P['text'] + '/14', on=P['accent'] + '/85'),
                 panel=dict(fill=grad(*P['panel']), stroke=P.get('stroke', P['accent']), width=3, corner=14, text=P.get('paneltext', 'text')),
                 tag=dict(fill=grad(*P['panel']), stroke=P.get('stroke', P['accent']), width=2, corner=13, text=P.get('paneltext', 'text')),
                 tile=dict(fill=grad(*P['tile']), stroke=P.get('tilestroke', P.get('stroke', P['accent'])), width=2.4, corner=12, text=P.get('ink', P['base'])))
    if kid:
        parts['kid'] = kid
    if over:
        parts['over'] = over
    if front:
        parts['front'] = front
    for k, v in (('particles', particles), ('onlaunch', onlaunch), ('onhover', onhover), ('onopen', onopen), ('screen', screen)):
        if v:
            parts[k] = v
    K.write(**parts)


def plate(K, name, n, draw, size=230, ss=3, cols=None):
    """A sheet of n slot pictures; draw(c, k) paints the k-th on its canvas and returns it."""
    ims = []
    for k in range(n):
        c = K.canvas(size, ss)
        ims.append(draw(c, k).image())
    cols = cols or n
    K.sheet(ims, cols, name)
    if n > 1:
        rows = (n + cols - 1) // cols
        K.flags[name] = dict(K.flags.get(name, {}), cols=cols, **({'rows': rows} if rows > 1 else {}), **({'frames': n} if n < cols * rows else {}))


def roundel(c, d, H, alb, studio=SOFT, rough=0.4, metal=0.0, clear=0.0, reach=0.12):
    """Shades and puts something round: d its distance field, H its height."""
    col = surface(c, H, alb, studio, metal=metal, rough=rough, clear=clear, reach=reach)
    c.put(col, c.cover(d), H)
    return c


def lens(t, depth=0.3, power=2.2):
    """Height of a domed button: t is 0 at the edge and 1 in the middle."""
    return depth * np.sqrt(clamp(1 - (1 - clamp(t)) ** power))
