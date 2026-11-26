These run the real program on a hidden desktop: nothing appears on the screen and the mouse is not touched.
Build first (build.ps1); they use dist\RadialTaskbar.exe and a settings folder of their own in the temp folder.

python -X utf8 skins_page.py                         the Skins page, adding by double-click, copying version 1's pins
python -X utf8 stress.py none,clockwork 3            every layout, without and with a skin, 3 openings each
python -X utf8 stress.py vinyl,comic 3 radial        only the wheel, these skins
python -X utf8 leak.py paper 80                      80 openings: handles and memory
python -X utf8 open_times.py clockwork radial 6      opening and frame times

python -X utf8 settings_pace.py vinyl                how fast the settings window opens, scrolls and follows the mouse
python -X utf8 hostile.py                            skins that want to do harm: memory, a lying sound file, impossible slowness

Frame times mean nothing while the PC is locked (locked_or_idle.py tells).
