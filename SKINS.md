# Skins

A skin replaces the whole look of the launcher: artwork, materials, motion, lettering, sounds, even the pointer.
(A *style*, on the Look page, only changes shapes, colours and effects.)

A skin is **data, never code**: pictures, sounds, fonts and one text file with numbers and formulas. The worst a skin
from a stranger can do is look bad.

- [Using and importing skins](#using-and-importing-skins)
- [Make your own in ten minutes](#make-your-own-in-ten-minutes)
- [How a skin is put together](#how-a-skin-is-put-together)
- [skin.json reference](#skinjson-reference)
- [Formulas](#formulas)
- [Making artwork](#making-artwork)
- [Checking, packing, sharing](#checking-packing-sharing)
- [The skins that come with the program](#the-skins-that-come-with-the-program)

## Using and importing skins

Settings > **Skins**. Click one and it is applied at once. The sliders below the gallery turn its colours (hue,
saturation, brightness), so every skin has many variants. The wheel's right-click menu and the tray menu switch skins
too. The skin you choose is the main skin; on Settings > **Profiles** every profile can use it, use no skin, or wear one of
its own. Layout, sizes and effects stay the same for all of them.

Ways to add one:

| | |
|---|---|
| **Double-click** a `.rskin` file | asks once, then adds and applies it |
| **Drop** it on the settings window | the same |
| Settings > Skins > **Import skin** | pick one or several files |
| Copy it into the **skins folder** | Settings > Skins > Open folder. It appears by itself |

Skins live in two places: `skins` beside the program (the ones it came with) and `%APPDATA%\RadialTaskbar\skins` (yours).
A newer copy of a skin (same id, name and author) replaces the old one, which goes to the recycle bin; somebody else's skin that happens to
have the same id gets a number. A folder or file of yours with the id of a skin that came with the program is used instead of it.
The bin on a card removes a skin: one of yours goes to the recycle bin, one that came with the program only leaves the list,
and "Bring back" at the bottom of the gallery shows it again.

A `.rskin` file is an ordinary ZIP file with another ending. Rename it to `.zip` to look inside.

## Make your own in ten minutes

1. Settings > Skins > pick the skin closest to your idea > **Make a copy to edit**. Its folder opens.
2. Open `skin.json` in any text editor. Change a number, save. The preview in Settings follows within a second, and the
   next time the launcher opens it has the change too.
3. Replace pictures with your own (PNG, JPEG, WebP ...). Any size works; 2 to 3 times the size on screen looks best.
4. If something is wrong, the Skins page says what and where ("slot > under 3: unknown name hott").
5. Done? **Share** writes a single `.rskin` file to send to others.

`skin.json` may contain `// remarks` and a comma after the last entry. Keys starting with `_` and `note` are ignored.

## How a skin is put together

Everything is a list of **layers**, drawn from back to front:

```
back       behind everything, once                         unit: wheel
ring       once for every ring of entries, outermost first unit: ring
slot       for every entry: under layers, icon, over layers unit: cell
fan        behind the members of an open group             unit: px
over       on top of the entries, under the hub            unit: wheel
hub        the centre                                      unit: hub
           (built-in text, profile ring and buttons, unless switched off)
front      on top of everything                            unit: wheel
```

A layer is an **image**, a **shape** or a **text**. Positions and sizes are relative to a **unit**, so artwork fits
whatever the person sets in Settings, and however many entries there are:

| `in` | 1.0 means |
|---|---|
| `wheel` | the radius of the whole wheel, including `wheel.rim` |
| `ring` | the outer radius of this ring, including `wheel.rim` |
| `hub` | the radius of the hub |
| `cell` | the radius of one entry |
| `px` | one pixel at 100% |

`"size": 1` is the full diameter of that circle (for `px` it is pixels). `x`, `y` move by units, y points down.

Almost every number can be a **formula** in quotes: `"rotate": "second*6"`, `"opacity": "hot*(0.8+0.2*noise(time*9))"`.

## skin.json reference

```jsonc
{
  "format": 1,
  "id": "my-skin",              // small letters, digits, dashes; unique
  "name": "My skin",
  "author": "", "version": "1.0", "license": "", "about": "One line", "tags": ["brass", "clock"],
  "preview": "preview.jpg",     // shown in the gallery, 4:3

  "style": { },                 // see Style
  "wheel": { },                 // see Wheel
  "colors": { "ink": "#2B1B0E" },
  "fonts": { "title": "Palatino Linotype, Georgia", "digits": { "file": "fonts/x.ttf", "weight": 600 } },
  "images": { "plate": { "file": "plate.jpg", "mask": "plate-mask.png" }, "glass": "glass.png" },

  "back": [], "ring": [], "over": [], "hub": [], "front": [], "fan": [],
  "slot": { }, "kid": { },      // kid: members of an open group; left out, they look like slots
  "pinbutton": { }, "settingsbutton": { },
  "panel": { }, "tag": { }, "tile": { },
  "particles": [], "onlaunch": [], "onhover": [], "onopen": [],
  "sounds": { "open": "open.wav", "move": "move.wav", "launch": "launch.wav", "close": "close.wav", "profile": "profile.wav" },
  "cursor": { "image": "cursor", "size": 32, "hot": [0.1, 0.1] },
  "tabs": { "inset": 8, "text": "ink", "fill": "#7A5A2A/60", "on": "profile" },
  "draw": { "title": true, "clock": true, "buttons": true, "tabs": true, "shadow": true, "fan": true, "text": "ink" }
}
```

### Style

The same settings as a style, used for everything the artwork does not cover (name tags, menus of groups, other layouts):

`shape` wedge, blade, orb, hex, petal, none (decides the outline of `"shape": "slot"` and the size of a cell) ·
`material` frosted, liquid, solid, outline · colours `base`, `accent`, `accent2`, `text`, `border` ·
`opacity`, `blur`, `corner`, `borderWidth`, `borderOpacity`, `gap`, `shadow` · `font` (a name from `fonts` or an installed one) ·
`open` bloom, spin, unfold, zoom, fade · `speed` · `hoverGrow` (pixels a hovered entry moves outward) · `iconZoom` · `glow` ·
`tilt` (3D tilt toward the pointer, 0 to 1) · `pointer` (the built-in needle; usually `false`) · `burst` (the built-in spark burst) ·
`dim` (how much the desktop darkens) · `iconTone`

### Wheel

| key | |
|---|---|
| `hub`, `thickness` | radius of the hub and depth of a ring, in pixels. The person's own sliders scale them |
| `gap`, `ringgap` | space between entries, between rings (give `ringgap` at least the size of `rim`) |
| `rim` | how far the wheel's artwork reaches past the entries |
| `icon` | icon size |
| `crowd` | how much room along the ring an entry wants, in icon sizes (1.26 is dense, 1.6 airy) |
| `area` | how far artwork reaches, in wheel radii: one number or `[left, top, right, bottom]`. Outside it nothing is drawn |
| `hubkeep` | part of the hub the built-in text and buttons may use |
| `shadow` | strength of the built-in shadow under the wheel |

### Images

`"name": "file.png"`, or

| key | |
|---|---|
| `file`, `mask` | a picture and optionally a black and white one for its transparency. JPEG plus mask is far smaller than PNG |
| `cols`, `rows`, `frames` | a sheet of frames |
| `light` | `true`: adds light instead of covering (glows, beams, sparks) |
| `sharp` | `true`: pixel art, enlarged in whole steps and never smoothed |
| `keep` | `true`: not touched by the hue and brightness sliders |

### Layers: what all have

| key | |
|---|---|
| `in` | unit, see above |
| `x`, `y` | offset from the centre (or from the middle of the entry) |
| `angle`, `radius` | offset as an angle in degrees, clockwise from straight up, and a distance |
| `size` | one number, or `[width, height]` |
| `rotate` | degrees, around `pivot` |
| `pivot` | `[0.5, 0.5]` is the middle of an image; `[0.5, 1]` its bottom edge (clock hands, needles) |
| `scale` | one number or `[x, y]`, on top of size. For things that grow and shrink a lot: the picture is kept in the size that `size` says |
| `opacity` | 0 to 1. Light images may go above 1 |
| `when` | drawn only while this is above 0 |
| `turns` | `true`: turned along with its entry (or its own `angle`), and its offset too |
| `depth` | moves against the pointer, which makes layers float above each other (0.3 to 2) |
| `copies` | draws it several times; `j` counts 0, 1, 2 ... and `m` is how many |
| `only` | for other layouts, see below |
| `intro` | how it arrives |

**intro** says where it comes from; it always ends in place:
`delay`, `time` (seconds), `ease` linear, out, inout, back, elastic, bounce, quint · `x`, `y`, `radius`, `angle`, `scale`, `rotate`, `opacity` (0 unless given) ·
`stagger` (seconds between copies or entries) · `order` both, ring, reverse, random, pairs.
Keep the whole thing under about 0.6 s: a launcher has to be quick.

### Image layers

`image` · `frame` (for sheets), `fps` · `tint` (paints its shape in one colour; light pictures shine in that colour) · `round: true` (clips to a circle, good for JPEG discs) ·
`detail` (extra resolution kept for growing, 1.1 to 1.3 for things that scale on hover)

### Shape layers

`shape`: `circle`, `rect` (with `corner`), `ring` (`inner`, `outer`, `from`, `to` in degrees), `arc` (`r`, `from`, `to`), `line` and `poly` (`points`, `closed`, `curve`),
`ticks` (`inner`, `outer`, `count`, `major`), `star` (`count`, `inner`, `outer`), `slot` (the outline of the entry itself; `inset` shrinks it).

`fill` and `stroke` take a colour, a gradient, a picture or the desktop:

```jsonc
"fill": "accent/40"
"fill": { "type": "linear", "from": [0, -1], "to": [0, 1], "stops": [[0, "#FFE"], [1, "#840"]] }   // in half sizes of the shape
"fill": { "type": "radial", "from": [-0.3, -0.4], "radius": 1.2, "stops": [[0, "white"], [1, "base"]] }
"fill": { "image": "water", "tile": true, "zoom": 0.5, "u": "time*0.02", "v": "time*0.01", "turn": 0 }
"fill": { "image": "window", "wheel": true }      // the picture stays with the wheel; every entry shows its own part of it
"fill": "glass"                                   // the blurred desktop (needs style.material frosted or liquid)
```

`width` (stroke, pixels), `dash` `[on, off]`, `caps` (round ends), `glow` (pixels of blur) and `glowcolor`. A glow in slots and copies is an approximation, because a real blur is too slow for every entry; a light picture looks better there.

### Text layers

`text`, `font` (a name from `fonts` or an installed font), `px` or `em` (size in pixels, or relative to the unit), `weight`, `italic`, `upper`, `tracking`,
`color`, `align` left center right, `valign` top middle bottom, `box` `[width, height]` in units, `wrap`, `fit` (shrinks to the box, on by default),
`marquee` (scrolls when too long), `shadow` `{x, y, blur, color}`, `outline` `{width, color}`, `ring: true` with `r` (follows a circle), `pixel` (drawn that many times smaller and blown up: screens and pixel art).

Placeholders: `{title}` `{sub}` (name and state of what is selected; they cross-fade by themselves) · `{label}` `{number}` `{windows}` (inside a slot) · `{profile}` `{count}` ·
`{time}` `{hh}` `{h12}` `{mm}` `{ss}` `{ampm}` `{date}` `{weekday}` `{wd}` `{day}` `{month}` `{mon}` `{year}` · `{cpu}` `{ram}` `{battery}` · `{page}` `{pages}`

When any layer shows `{title}`, the built-in name in the hub is switched off. Set `"draw": { "clock": false }` when the skin has its own clock.
`"draw": { "text": "ink" }` is the colour of everything the program itself writes or draws in the hub (clock, buttons, "No pins yet").

### Slots

```jsonc
"slot": {
  "under": [ ... ], "over": [ ... ],      // layers below and above the icon
  "icon": { "size": 1.1, "x": 0, "y": 0, "rotate": 0, "opacity": 1, "zoom": 1.15,
            "tone": "engrave", "hot": "original", "ink": "#E8C27A", "paper": "#3A2510",
            "round": false, "shadow": { "y": 2, "blur": 3, "color": "black/60" }, "glow": "hot", "glowcolor": "item" },
  "intro": { "time": 0.35, "ease": "back", "scale": 0.1, "radius": -0.3, "stagger": 0.02, "order": "both" },
  "marks": false, "chevron": false, "badge": false,   // switch off the built-in running marks, group arrow and number
  "names": 1.1                                        // where names go when they are always shown (on plates of their own, in style.base and style.text)
}
```

Icon `tone`: original, muted (grey), mono (one colour), duo (two colours: ink and paper), ink (printed), engrave (stamped into metal), neon (bent tube), pixel, sticker (white outline).
`hot` is the tone while hovered. `icon.size` is relative to the cell: 1.0 is half its diameter.

Show the states yourself when you switch the built-in marks off: `when: "running"`, `"active"`, `"group"`, `"numbers && number<10"`.

### Panels

`panel` is used for the background of the other layouts and of open groups, `tag` for name tags, `tile` for cards (Hand of cards).
Either a picture cut in nine: `image`, `cut` (one number or left, top, right, bottom in pixels of the picture), `scale`, `pad`;
or drawn: `fill`, `stroke`, `width`, `corner`, `cutcorner`. `text` is the colour of text on it.

### Particles

`particles` run all the time, `onlaunch`, `onhover` and `onopen` are bursts.
`image` or none (a dot), `color`, `light`, `rate` (per second), `max`, `count` (in a burst), `area` wheel ring hub rim slot stage pointer,
`life`, `size`, `speed`, `dir` (degrees, 0 is up), `spin`: `[least, most]` · `outward` (dir counts from the direction away from the centre) · `gravity`, `drag`, `sway`, `swayhz`, `swirl`,
`fadein`, `fadeout` (parts of the life), `grow` (size at the end), `stretch`, `opacity`, `when`

### Background motion

`screen`: motion over the darkened desktop while the wheel is open, behind everything else. `effect` is one of `rain`, `stars`, `snow`,
`fireflies`, `embers`, `bubbles`, `petals`, `bats`; `color` and `color2` colour it, `density`, `speed` and `size` (1 is normal) shape it.
People can turn it off, or choose another one for every skin, under Settings > Effects.

### Buttons

`pinbutton` and `settingsbutton`: `in`, `x`, `y`, `size` (radius in pixels), `layers` (with `hot` while the pointer is on it), `hidden`.

### Other layouts

A skin's slots, panels, tags, colours and sounds are used in every layout. Layers in `back`, `over`, `hub` and `front` are drawn in the wheel only,
unless they say `"only": ["orbit", "galaxy"]` (or `"all"`). Layouts: radial, flow, strip, orbit, comb, carousel, globe, cards, corner, galaxy, board, drum.

### Colours

`#RRGGBB`, `white`, `black`, `none`, `accent`, `accent2`, `text`, `base`, `border`, `profile` (of the profile in use), `item` (the main colour of the entry's icon),
or a name from `colors`; `/40` after any of them is 40% opacity.

## Formulas

Operators `+ - * / % ^`, comparisons, `&& || !`, `condition ? a : b`. Angles of positions are degrees; `sin` and `cos` take radians (`rad()` converts).

| the launcher | |
|---|---|
| `time` | seconds since it opened |
| `open` | 0 to 1 while opening, with a little overshoot |
| `fade`, `closing`, `launch` | overall opacity; 0 to 1 while closing; 0 to 1 while launching (in a slot: only for the one launched) |
| `sel`, `on` | angle of the selection in degrees (moves smoothly), and 0 to 1 whether there is one |
| `selindex` | number of the selected entry, from 0 |
| `idle` | 1 while nothing is selected, 0 while a name is shown |
| `px`, `py`, `pdist`, `pangle` | the pointer, in wheel radii from the centre, and its angle |
| `page`, `pages`, `profile`, `profiles`, `items`, `rings` | counts, from 0 |
| `radius`, `hub`, `ringin`, `ringout` | sizes in pixels at 100% |
| `sticky` | 1 when it stays open, 0 while the shortcut is held |
| `numbers` | 1 when the person wants numbers on entries |
| `motion` | 0 when the person has animations switched off |
| `turn` | -1 to 1 while another page or profile slides in |

| the world | |
|---|---|
| `hour` (0 to 12), `minute`, `second` | running smoothly; `tick` is the second with a mechanical jump; `day`, `month` |
| `cpu`, `ram`, `battery`, `charging` | 0 to 1 |
| `sound`, `soundl`, `soundr`, `beat` | how loud the computer's sound is right now (Windows' own level meter; nothing is recorded) |

| one entry (in slots) | |
|---|---|
| `hot` | 0 to 1 while hovered, overshoots slightly |
| `press` | 0 to 1 while the button is down on it |
| `i`, `n`, `ring`, `a`, `span` | number in its ring, how many, which ring, its angle and width in degrees |
| `running`, `windows`, `active`, `group`, `kid`, `number` | state |
| `seed` | a fixed random number 0 to 1 for this entry |
| `near` | 1 at the selection, fading over the neighbours |
| `in` | 0 to 1 while arriving |

| functions | |
|---|---|
| `sin cos tan atan2 abs sign floor ceil round fract mod pow sqrt exp log min max` | |
| `clamp(x,a,b)` `mix(a,b,t)` `smooth(a,b,x)` `step(edge,x)` `sat(x)` `wrap(deg)` `deg()` `rad()` | |
| `noise(x)` | smooth wobble 0 to 1 · `rnd(x)` a fixed random number · `wave(x)` a sine 0 to 1, once per unit · `tri(x)` |
| `outcubic(t)` `outback(t)` `outelastic(t)` `outbounce(t)` `inout(t)` | easing |
| `if(c,a,b)` | |

In a `ring` layer `a` is the angle of the first entry and `span` the step between entries, so `"copies": "n", "angle": "a+j*span+span/2"` puts something between all of them.
In a `fan` layer `a`, `span`, `ringin`, `ringout` describe the open group and `in` how far it is open.

## Making artwork

Anything that makes pictures will do: Photoshop, GIMP, Blender, Inkscape, an image generator, a photograph. What helps:

- Light comes from the **upper left**, shadows fall to the lower right. Everything is seen straight from above.
- Draw the wheel's plate as a **plain disc**: the number of entries changes, so sockets, buttons and dividers belong to the slot artwork (or to `copies` in a ring layer).
- Give slot artwork its own rim and contact shadow, so it looks set into the plate.
- Round JPEG plus a mask keeps a 1000 pixel plate around 300 KB. Aim for 1 to 2 MB for a whole skin.
- Use only work that is yours or whose licence allows sharing, and put the licence text in the folder. No logos, characters or screenshots of other products.

The artwork of the bundled skins is made by the scripts in `tools/art` (Python with numpy and Pillow): `artkit.py` is a small renderer for metal, wood, stone,
glass and paper (shapes as distance fields, bevels, studio lighting, soft shadows), `metals.py` has ready materials, `sounds.py` makes the sounds and `pack.py` writes the files.

```
cd tools\art
python clockwork.py --draft        half size, seconds instead of minutes
python clockwork.py                final
python clockwork.py plate dial     only these parts
```

The quickest way to a new skin: copy one of the short scripts (`zen.py`, `gummy.py`, `sushi.py` ...). They are built on `skinkit.py`, where one file
makes the pictures, the sounds and `skin.json`, and `img`, `soft`, `words`, `badge`, `running` write the layers every skin needs.
`rows.py` shows several skins in six situations, `opens.py` how they open, `others.py` how they look in other layouts, `zoom.py` close-ups, `previews.py` makes the gallery pictures.

## Checking, packing, sharing

```
RadialTaskbar.exe --check-skin <folder or file>          lists every problem and unused file
RadialTaskbar.exe --pack-skin <folder> <file.rskin>      one file to share
RadialTaskbar.exe --snapshot out.png --skin my-skin --items 10 --groups --profiles 3 --hover 3
```

`--snapshot` draws the launcher into a picture without opening it: `--layout orbit`, `--w 900 --h 900`, `--scale 1.6`, `--t 0.12` (seconds after opening), `--hover 3`
(entry 3 selected), `--kid 2` (inside a group), `--numbers`, `--labels`, `--light` (bright desktop), `--perring 8`, `--overflow unfold`, `--closing 0.08`, `--hue 40`.
It looks for skins in the `skins` folder beside the program and in yours (the environment variable `RadialTaskbar_SKINS` names another folder).
`tools/art/shot.py` wraps this: `python shot.py my-skin out.png --sheet` draws twelve situations on one sheet, `--opening` the opening frame by frame.

A skin that cannot be drawn is left out: the wheel opens with your style, and the skin is tried again when its file changes.

Limits, so that a broken or hostile file cannot do harm: 48 MB per file, 96 MB unpacked, 600 files, pictures up to 4096 pixels, 120 images, 400 layers, formulas up to 600 characters.

## The skins that come with the program

| Skin | id | What it is |
|---|---|---|
| **Alchemist** | `alchemist` | A bench of bubbling flasks that fill up with the colour of what you point at |
| **Aperture** | `aperture` | The front of a camera lens: coated glass for every app, numbers on the barrel, an iris that opens around the name |
| **Arcade** | `arcade` | Lit buttons, running bulbs and a joystick that leans toward the pointer |
| **Art Deco** | `deco` | Black lacquer with brass sunbursts and stepped arcs; apps sit in brass octagons |
| **Balloons** | `balloons` | Shiny foil balloons against a soft sky; they bob and tug at their strings, confetti on launch |
| **Beehive** | `beehive` | Wax comb full of honey: apps sit in honey-filled cells and a bee walks to your choice |
| **Billiards** | `billiards` | Blue cloth in a cherry-wood rail with pockets; polished balls carry the apps, the cue ball sits in the middle |
| **Blueprint** | `blueprint` | White lines on blue paper; circles and dimensions draw themselves |
| **Chalkboard** | `chalk` | A slate board in a wooden frame; apps sit in hand-drawn chalk circles |
| **Cherry Blossom** | `sakura` | A dark branch across a soft spring sky; apps sit in blossoms while pink petals ride the wind |
| **Clay** | `clay` | Modelling clay with fingerprints, never quite the same from frame to frame |
| **Clockwork** | `clockwork` | Walnut, brass and porcelain, with a clock that keeps time |
| **Cockpit** | `cockpit` | An artificial horizon follows the pointer; the gauges show processor, memory, sound and time |
| **Coffee** | `coffee` | A cosy cup in the middle, small cups of espresso, latte and cappuccino round it, and steam |
| **Comic** | `comic` | Pop-art print: fat ink, four colours slightly out of place, and a lot of dots |
| **Compass** | `compass` | A ship's brass compass with its card floating in oil; the needle swings round to your choice |
| **Coral Reef** | `coral` | Blue water in a ring of corals, small fish, and a pearl in the middle |
| **Crypt** | `crypt` | Worn flagstones under wrought iron; violet soul flames burn over stone plaques and the gate swings open |
| **Cyber Alley** | `cyber` | A wet street at night: neon smears across the puddles, apps hang on holographic signs, rain streaks down |
| **Dartboard** | `darts` | Sisal, wire and numbers: apps sit in wire rings round the bull while a dart points at your choice |
| **Digital Rain** | `rain` | Green signs pour down the screen behind a dark glass terminal wheel |
| **Doughnuts** | `donut` | Iced doughnuts with sprinkles on a cake plate; the app sits in the hole and a bite goes on launch |
| **Dragon Scale** | `dragon` | Overlapping scales shimmer from green to bronze; a dragon eye watches from the middle while embers rise |
| **Elven Grove** | `elven` | A silver tree spreads over a moonlit grove; apps ride on its leaves while fireflies gather |
| **Embroidery Hoop** | `hoop` | Linen stretched in a wooden hoop; apps sit in cross-stitched rings while a threaded needle points |
| **Factory** | `factory` | A conveyor belt runs round a steel floor with hazard stripes; apps ride on crates, a big gear turns in the middle |
| **Film Reel** | `film` | A metal reel turns behind a strip of film; every app is a frame, and the picture flickers with dust |
| **Folk Pattern** | `folk` | Red, black and white Balkan cross-stitch in bands and rosettes, inside a carved wooden frame |
| **Frost** | `frost` | Ice crystals grow in from the rim of a frozen disc; apps rest on clear ice while snow falls outside |
| **Grimoire** | `grimoire` | An open spellbook by candlelight, with a circle that wakes up |
| **Gummy** | `gummy` | Glossy jelly sweets on a lollipop; they wobble when you point at them |
| **Halloween** | `halloween` | A spider's web across the night, grinning jack-o'-lanterns, a full moon and bats |
| **Hologram** | `hologram` | Thin figures of light above a small projector, with scan lines and glitches |
| **Ink Wash** | `inkwash` | Brush strokes and bleeding ink on rice paper: misty mountains, a red seal, apps in brushed circles |
| **Jukebox** | `jukebox` | Chrome, cherry wood and bubbling tubes of coloured light that dance to the sound |
| **Koi Pond** | `pond` | A quiet garden pond: lily pads, lotus flowers and koi under moving light |
| **Lacquer Box** | `lacquer` | Deep red and black lacquer sprinkled with gold dust; apps rest on black lacquer framed in gold |
| **Lava** | `lava` | Cracked black crust over glowing rock; apps rest on basalt veined with fire while embers rise |
| **Leather Atelier** | `leather` | Stitched saddle leather with brass rivets; apps sit on leather patches sewn with cream thread |
| **Living Cell** | `cell` | A view down a microscope: breathing vesicles carry the apps, a nucleus in the middle sends pulses outward |
| **Marble and Gold** | `marble` | Polished white stone with inlaid gold lines and black marble medallions; very quiet |
| **Moonlight** | `moonlight` | A night sky over a ring of trees; apps sit on the moon's phases while an owl blinks in the dark |
| **Morning Dew** | `dew` | A web strung with dew in soft morning light; every app is a clear drop that magnifies it |
| **Mosaic** | `mosaic` | An antique floor of small stone tiles; an app's tile turns over to show glass and gold beneath |
| **Neon** | `neon` | A bar sign at night: bent glass tubes on a round brick wall |
| **Nixie** | `nixie` | Glowing glass tubes on walnut and copper |
| **Origami** | `origami` | Folded patterned paper that opens like a flower; cranes fly off when you launch |
| **Orrery** | `orrery` | Planets on brass arms round a glowing sun |
| **Papercut** | `paper` | Layers of cut coloured paper, light and soft |
| **Phosphor** | `terminal` | A round green terminal that remembers the eighties |
| **Pinball** | `pinball` | A playfield under glass: pop bumpers carry the apps and flash, a dot display sits in the middle |
| **Pocket Console** | `console` | A grey handheld with a greenish dot screen in the middle and chunky coloured buttons round it |
| **Poker Table** | `poker` | Green felt inside a padded rail; chips carry the apps, the dealer button sits in the middle |
| **Porcelain** | `porcelain` | White glaze, cobalt painting, and cracks mended with gold |
| **Reactor** | `reactor` | A machined weapon wheel around a plasma core |
| **Rotary** | `rotary` | An old dial telephone: chrome, cream and mint |
| **Roulette** | `roulette` | Walnut, brass and felt; the ball rolls to your choice |
| **Runestone** | `runestone` | A broken stone disc from an old ruin, held together by iron, torchlight and what was carved into it |
| **Ship's Wheel** | `pirate` | A mahogany helm over the deep sea; apps ride on gold coins, a brass compass sits in the middle |
| **Silken Caves** | `silk` | Dark blue rock strung with silk threads; apps sit on spools of thread while pale moths glow |
| **Slot Machine** | `slots` | A red and chrome cabinet with chasing bulbs; every app sits in a reel window and coins burst on a win |
| **Space Colony** | `colony` | A cut through an asteroid with a colony inside: rock layers, tunnels, lit round rooms and an airlock |
| **Space Station** | `station` | A hatch with a wide window: a planet turns slowly behind the apps while stars rush past |
| **Sticker Album** | `stickers` | A scrapbook page with washi tape; every app is a die-cut sticker with a corner curling up |
| **Sunflower** | `sunflower` | Seeds in a golden spiral and petals that open with the wheel; little flowers carry the apps |
| **Sushi Belt** | `sushi` | Plates ride round the counter and chopsticks reach for your choice |
| **Synthwave** | `synthwave` | A striped sun, dark hills and a glowing grid that rolls toward you |
| **Tarot** | `tarot` | Gold line art on midnight blue; cards turn over when you point at them, a sun shines in the middle |
| **Terrarium** | `terrarium` | Moss, ferns and log slices under glass, with a ladybird and a butterfly |
| **Treasure Map** | `treasure` | Burnt parchment, islands and a compass; X marks your choice |
| **Vampire** | `vampire` | Crimson velvet under black wrought iron; apps rest on garnets set in silver while bats cross the dark |
| **Vault** | `vault` | A vault door of brushed steel with heavy bolts; the combination dial in the middle turns to your choice |
| **Viking Shield** | `viking` | A painted round shield of planks with an iron boss and rawhide rim; apps sit on small shields |
| **Vinyl** | `vinyl` | A hi-fi turntable with a dot-matrix display and meters that dance to your sound |
| **Wild West** | `western` | A revolver cylinder of blued steel; apps sit in brass cartridges, sheriff stars ride the outer ring |
| **Zen Garden** | `zen` | Raked sand, smooth stones and a drifting petal |

The artwork of each is made by the script of the same name in `tools/art`.

Not part of the setup program, handed out as single files to import (`skins to import`):

| Skin | id | What it is |
|---|---|---|
| **Fireworks** | `fireworks` | A city by the water at night, where every launch is a rocket |
| **Pumpkin Night** | `pumpkin` | A carved pumpkin by candlelight, gravestones, bats and fog under a big moon |
| **Winter Wreath** | `winter` | A fir wreath with glass baubles, blinking lights and falling snow |
