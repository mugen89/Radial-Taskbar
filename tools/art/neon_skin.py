"""skin.json of Neon; its pictures come from neon.py."""
from skinkit import *

K = Kit('neon', 'Neon', 'A bar sign at night: bent glass tubes on a round brick wall', ['neon', 'night', 'glow'], 'Fonts Pacifico and Tilt Neon: SIL Open Font License, see OFL.txt')
K.flag(lit1='light', lit2='light', lit3='light', spill='light', spillin='light', hublit='light', ringv='light', ringy='light', dash='light', dashp='light', swooshlit='light', arrowlit='light', spark='light')
T, S = 'sign', 'small'
# tubes strike, go out and catch; one of them is getting old
start = '(time>%g)*(time<%g ? step(0.45,fract(time*%g)) : 1)'
on1 = start % (0.05, 0.30, 13) + '*(0.94+0.06*noise(time*27))'
on2 = start % (0.10, 0.42, 11) + '*(1-0.75*step(0.965,noise(time*5+3))*step(0.45,noise(time*43)))'
on3 = start % (0.08, 0.36, 9) + '*(0.94+0.06*noise(time*31+9))'
onh = start % (0.12, 0.34, 15) + '*(0.95+0.05*noise(time*29+4))'
K.write(
    style=dict(shape='orb', material='solid', base='#12101C', accent='#FF2D86', accent2='#18E6FF', text='#FFE9F6', border='#7C4DFF', opacity=0.97, corner=10, font='Tilt Neon', open='fade', speed=1.1, hoverGrow=3,
               iconZoom=1.12, glow=0.8, tilt=0.5, pointer=False, burst=False, shadow=0.75, dim=0.46),
    wheel=dict(hub=94, thickness=92, gap=6, ringgap=10, rim=40, icon=42, crowd=1.5, area=1.14, hubkeep=0.72),
    colors=dict(pink='#FF8FC2', cyan='#9AF4FF', white='#FFF4FB'), fonts=dict(sign=dict(file='Pacifico-Regular.ttf', family='Pacifico'), small=dict(file='TiltNeon.ttf', family='Tilt Neon')),
    back=[soft(1.10, 0.03, 72), img('wall', 1.09, intro=intro(0.22, 'out', scale=0.94)), img('spill', 1.09, opacity='0.95*(' + on1 + ')'), img('tubes', 1.09, intro=intro(0.22, 'out', scale=0.94)), img('lit1', 1.09, opacity=on1), img('lit2', 1.09, opacity=on2), img('lit3', 1.09, opacity=on3)],
    slot=dict(intro=intro(0.24, 'out', 0.06, scale=0.85, stagger=0.02, order='random'),
              under=[soft(1.10, 0.07, 60, 0.80), img('cup', '1.06*(1-0.03*press)', rotate='0'), img('ringv', '1.60*(1-0.03*press)', opacity='(1-sat(hot))*(0.62+0.10*near)*smooth(0.15,0.3,time-0.02*i)*(0.94+0.06*noise(time*23+i*7))'), img('ringy', '1.60*(1-0.03*press)', opacity='sat(hot*1.3)*(0.95+0.05*noise(time*33+i))+launch*1.5')],
              icon=dict(size=0.98, zoom=1.12, tone='neon', hot='original', ink='item', paper='#FFFFFF', glow='0.5*hot', glowcolor='#FFC42E'),
              over=[img('dash', [0.36, 0.18], y=0.905, opacity='active ? 1.1 : 0.75', when='running'), img('dashp', [0.36, 0.18], y=-0.905, opacity=0.9, when='group')] + badge('#12101C', 'white', S, stroke='#FF2D86'), marks=False, chevron=False, badge=False),
    over=[soft(1.14, 0.05, 66, 0.80, **{'in': 'hub'}), img('spillin', 1.48, **{'in': 'hub'}, opacity='0.85*(' + onh + ')')],
    hub=[img('hubplate', 1.0), img('hubtube', 1.0), img('hublit', 1.45, opacity=onh), img('arrow', 0.20, angle='sel', radius=0.70, turns=True, opacity='on'), img('arrowlit', 0.20, angle='sel', radius=0.70, turns=True, opacity='on*(0.9+0.1*noise(time*30))')]
    + [dict(l, font=T if i in (0,) else S, weight=400) for i, l in enumerate(words('#FFD6EA', 'cyan', S, px=19, y=-0.08, box=(1.06, 0.66), subpx=11.5, suby=0.33, clockpx=33, clocky=-0.08, datey=0.20, datepx=12, shadow=dict(x=0, y=0, blur=7, color='#FF2D86')))]
    + [img('swoosh', [0.46, 0.1725], y=0.53), img('swooshlit', [0.46, 0.1725], y=0.53, opacity='(0.25+0.75*on)*(' + onh + ')')],
    draw=dict(clock=False, shadow=False, text='#FFD6EA'), tabs=dict(inset=24, text='#FFE9F6', fill='#7C4DFF/22', on='#D81CFF/70'),
    panel=dict(fill={'type': 'linear', 'stops': [[0, '#221A2E'], [1, '#100C18']]}, stroke='#FF2D86', width=2, corner=12, text='white'), tag=dict(fill='#12101C', stroke='#18E6FF', width=1.6, corner=10, text='white'), tile=dict(fill={'type': 'linear', 'stops': [[0, '#2A2038'], [1, '#12101C']]}, stroke='#7C4DFF', width=2, corner=10, text='white'),
    onlaunch=[dict(image='spark', light=True, count=34, area='slot', life=[0.25, 0.6], size=[4, 9], speed=[140, 480], outward=True, dir=[-90, 90], gravity=620, drag=1.8, fadein=0, fadeout=0.5)],
    onhover=[dict(image='spark', light=True, count=3, area='slot', life=[0.2, 0.4], size=[2, 4], speed=[50, 140], outward=True, dir=[-70, 70], gravity=500, fadein=0, fadeout=0.6)])
