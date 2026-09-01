# Bongo Cat Sprite Studio

A browser pixel editor and 240×320 display-layout tool for this firmware.

The cat on the Cheap Yellow Display (CYD) is **not** one PNG. It is five
64×64 layers, all drawn at `(0, 0)` on a 64×64 canvas, then zoomed (default
4×) onto the 240×320 screen.

```
front
  effects     click sparks, Zzz, excitement sparkles
  paws
  table       the keyboard
  face
  body
back
```

This studio lets you paint those layers, preview poses at real screen size,
and drag CPU / RAM / WPM / time around the TFT. Saving writes both the PNG
and the LVGL C array the firmware actually compiles.

---

## Open the editor

From the repo root (needs Python 3 and Pillow — already in
`bongo_cat_app/requirements_app.txt`):

```bash
cd /path/to/bongo_cat_monitor
python3 -m pip install Pillow     # if needed
python3 tools/sprite_studio.py
```

That serves on **port 8765**, on every network interface of the machine
running the script. Plain HTTP only — there is no TLS.

On the same computer, open the editor in a browser on that port. From a
phone, tablet, or another PC, use that computer’s Tailscale or LAN address
and the same port. Loopback only works on the machine that is running
`sprite_studio.py`.

On a phone the layout stacks: editor on top, sprite strip, then layout
controls. Draw with a finger. First load only fetches the current pose so
Safari is not stuck downloading every PNG.

Stop the server with Ctrl+C in the terminal.

### CLI (no browser)

```bash
# Rebuild every catalog sprite's animations/*.c from Sprites/*.png
python3 tools/sprite_studio.py convert-all

# Import one image as a named layer (scaled to 64×64, quantized)
python3 tools/sprite_studio.py convert ~/pic.png --layer face --name wink
```

---

## Screen tour

```
┌─────────────────────────────────────────────────────────────┐
│ Bongo Cat Studio          status text     [ Save PNG + C ]  │  header
├──────────┬───────────────────────────────┬──────────────────┤
│ body     │ Pencil Eraser Fill Eyedrop    │ New sprite       │
│  thumbs  │ palette  Onion  Undo  Clear   │ layer + name     │
│ face     │                               │ [Create]         │
│  …       │  64×64 pixel grid             │ Import PNG/GIF   │
│ table    │  (onion-skins the pose)       │                  │
│ paws     │                               │ Screen layout    │
│ effects  │  240×320 TFT preview          │ Cat X/Y, zoom    │
│          │  Pose: idle / left / …        │ BG, show stats   │
│          │                               │ [Apply layout]   │
└──────────┴───────────────────────────────┴──────────────────┘
```

On a wide desktop: sprites left, editor + TFT center, create/layout right.
On a narrow phone: editor, then a horizontal sprite strip, then layout.

---

## Palette (stay on these colors)

On save, every pixel is snapped to this hardware palette. Off-palette colors
will jump to the nearest swatch, so draw with these from the start.

| Swatch | Hex | Used for |
|---|---|---|
| checkerboard | transparent | empty pixels (shows layers behind) |
| black | `#000000` | outline, eyes, keys |
| white | `#ffffff` | fur |
| gray | `#9e9e9e` | keyboard |
| pink | `#ff80ab` | paw pads, click sparks |
| orange | `#ffb74d` | sleep Z, excitement sparkles |

Click a swatch in the toolbar to pick it. Eyedrop samples from the **current
layer only**, not from onion-skin pixels.

---

## Pick a sprite and draw

1. In the left list, click a sprite (grouped by layer). The 64×64 grid loads
   that layer. The TFT on the right composites the current **pose**.
2. Choose a tool:
   - **Pencil** — paint the selected color, one cat-pixel at a time. Drag to
     scribble.
   - **Eraser** — set pixels to transparent.
   - **Fill** — flood-fill connected pixels of the same color.
   - **Eyedrop** — click a pixel to copy its color into the palette selection.
3. **Onion** (on by default) shows the other layers of the current pose under
   your grid so you can line up face, paws, and effects. Uncheck it to see
   only the layer you are editing.
4. Coordinates under the grid are `x,y` in 0–63 cat pixels.
5. **Undo** reverts the last pencil stroke, fill, or clear (about 40 steps).
   Undo is per editing session, not saved to disk.
6. **Clear layer** wipes the current sprite to fully transparent. Undo can
   bring it back until you reload.

Nothing is written to disk until you click **Save PNG + C**.

---

## Poses (TFT preview)

The pose dropdown composites stock layers the same way firmware does, so you
can check alignment before flashing.

| Pose | Layers shown |
|---|---|
| idle | body + stock face + table + both paws up |
| left paw | body + stock face + table + left paw down |
| right paw | body + stock face + table + right paw down |
| fast / streak | body + happy face + table + right paw + right-click effect |
| sleep | body + sleepy face + table + sleepy2 |
| blink | body + blink face + table (no paws — “hands under the table”) |
| ear twitch | bodyeartwitch + stock face + table + both paws up |
| extreme excitement | body + excited face + table + right paw + excited1 |

Change pose anytime; it only affects the preview, not which file you are
editing.

When firmware is idle:

- short idle — paws hidden
- mid idle — sleepy face
- long idle — sleepy1/2/3 Zzz loop
- ~10 minutes idle — excited face + frantic paws + excited1/excited2 sparkles
  until typing resumes

---

## Save (existing sprites)

**Save PNG + C** writes:

| File | Role |
|---|---|
| `Sprites/<layer>/<name>.png` | indexed PNG (source of truth for the editor) |
| `animations/<layer>/<name>.c` | LVGL `RGB565A8` C array the firmware compiles |

Folder names differ slightly for faces: PNG lives in `Sprites/face/`, C lives
in `animations/faces/`.

Editing a **stock** sprite (the ones already in `animations_sprites.h`) is
enough: rebuild and flash the ESP32. No extra wiring.

---

## Create a new sprite

Right column → **New sprite**:

1. Pick a layer (`body`, `face`, `table`, `paws`, `effects`).
2. Type a name (letters, numbers, underscore; max 48 chars).
3. **Create** writes a blank 64×64 PNG + C file and selects it.
4. Draw, then **Save PNG + C**.

A new sprite will **not** appear on the device until you also:

1. Add it to `SPRITE_CATALOG` in `tools/lvgl_sprite.py` (so convert-all and
   the studio list keep it).
2. Add an `LV_IMG_DECLARE` / include in `animations_sprites.h`.
3. Hook it in `bongo_cat.ino` (sprite manager / pose).

---

## Import a PNG or GIF

1. Choose layer + name (or leave the name blank to use the file stem).
2. Pick a file with the file input.
3. **Import as new**.

The server nearest-neighbor scales to 64×64 and quantizes to the cat palette.
Start from pixel art at 64×64 if you can; photos will look muddy.

Same firmware-hook rules as Create if the name is new.

---

## Screen layout (the 240×320 preview)

This is a real-size CYD mock: 240×320 pixels, white (or your BG) panel inside
a bezel.

- **Drag the cat** to move it. Offsets are from screen center
  (`LV_ALIGN_CENTER`). Defaults: X = 12, Y = 50.
- **Drag CPU / RAM / WPM** — top-left origin. Defaults: (5,5), (5,25), (5,45).
- **Drag Time** — top-right origin, so X is usually **negative**. Default:
  (−5, 5).
- **Zoom** is LVGL units: `256` = 1×, `1024` = 4× (64 → 256 px). Step is 256.
- **BG** is the screen background RGB.
- Uncheck CPU / RAM / WPM / Time to hide them in the preview. Apply still
  writes their coordinates; firmware show/hide may still follow the sketch.

**Apply layout to firmware** writes:

- `display_layout.json` — editor state
- `display_layout.h` — `#define`s included by `bongo_cat.ino`

Do not hand-edit `display_layout.h`; it is generated. After Apply, **rebuild
and flash** the ESP32 or the device will keep the old layout.

| Item | Align | Default offset |
|---|---|---|
| cat canvas | center | (12, 50) |
| zoom | 1024 = 4× | 64 → 256 px |
| CPU / RAM / WPM | top-left | (5,5) (5,25) (5,45) |
| time | top-right | (−5, 5) |

---

## Files the studio owns

```
tools/sprite_studio.py          # HTTP server + save/convert API
tools/lvgl_sprite.py            # palette, catalog, PNG ↔ RGB565A8 C
tools/sprite_studio/index.html  # the editor UI
tools/sprite_studio/README.md   # this guide

Sprites/<layer>/*.png           # editable art
animations/<layer>/*.c          # generated firmware blobs
display_layout.json             # layout editor state
display_layout.h                # generated #defines for bongo_cat.ino
```

---

## Troubleshooting

| Symptom | What to try |
|---|---|
| Page will not load from another device | Use the host’s Tailscale or LAN address and port 8765. Loopback only works on the server itself. Confirm `sprite_studio.py` is still running. Plain HTTP only. |
| Browser shows a certificate / HTTPS error | Force plain HTTP. There is no TLS. |
| Colors look wrong after save | You used off-palette RGB. Stick to the six swatches. |
| New face never shows on the CYD | PNG+C is not enough — add it to `animations_sprites.h` and the sketch, then flash. |
| Layout looks right in the studio, wrong on device | You previewed but did not click **Apply layout to firmware**, or you did not flash after Apply. |
| `ModuleNotFoundError: PIL` | `python3 -m pip install Pillow` (or use the project venv that already has it). |
| Undo did nothing after reload | Undo is memory-only. Re-open the PNG from disk if you need the last saved version. |

---

## Related

- `animations/Animation guidelines.md` — when firmware swaps faces / paws / effects
- `animations/README.md` — sprite folders
- `LINUX.md` — Linux host + a short studio pointer
