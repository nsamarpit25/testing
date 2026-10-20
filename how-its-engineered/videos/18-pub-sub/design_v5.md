# 18 Pub/Sub — v5 art direction: "The Dispatch Hall"

One design, no options. A warm 1930s Art Deco dispatch hall, like a grand telegraph office, where every concept is a
heavy, satin-lacquered machine that physically does its job. The message is a printed card that rides on
conveyors. The topic is a brass-and-cobalt distribution drum. "Two million followers" is a giant mechanical
scoreboard plus a vast floor of tiny unlit bulbs that all light up at the climax. The world, palette, lighting
and information devices follow the reference closely (@charles.zhengg, LLM reel). The story mechanics are our own.

Conventions: metres, Z up, floor at Z = 0. +Y points into the hall, away from the default camera, toward the back
wall. +X is to the right. Hex colours are sRGB; convert with the existing `hx()` helper. Camera sensor is the Blender
default (36 mm, AUTO fit), so in a 9:16 frame the 36 mm is the frame height and **visible width = distance × 20.25 /
focal length** (the same maths as `place()` in 17-message-queues/mailroom). Times are seconds of the voiceover
(`voice/words.json`). The render is 1080×1920 at 24 fps.

Frame-safe zones:
- **Captions** sit at 80–88 % of the frame height. **The HUD** (kicker pill and chapter title, top-left, with a
  dark gradient over the top 20 %) occupies the top ~16 %.
- Anything the viewer must read or notice sits **between 18 % and 77 % of the frame height**. Tall elements go on
  the right side of the frame, because the HUD is on the left.

---

## 1. Why the reference looks professional (what we replicate)

Frames studied: contact sheets every 2.5 s, plus close frames at 4–6 s, 12–20 s, 40 s and 96 s.

1. **One coherent world and era.** Everything lives in a single 1930s machine-age universe: a columned hall
   (10–50 s), an Art Deco skyscraper with a split-flap board (50–70 s, 110–140 s), a sunlit library (72–80 s) and an
   "editing room" (80–105 s). No abstract UI ever appears. *We use one Deco dispatch hall plus one dusk-rooftop
   vignette for the radio metaphor.*
2. **A tight four-colour palette with colour as meaning.** Parchment cream, cobalt lacquer, brass and brick red sit
   against a sepia, desaturated environment. Red marks emphasis or problems ("penalty" gauge, red score tiles,
   "PRE-TRAINED" sign). Blue is structure. Nothing is neon. *We use the same four colours, and red only ever means
   "problem".*
3. **Warm practical lighting with backlight through haze.**
   - Cobalt-enamel pendant lamps throw warm pools of light; rows of them recede into haze and turn into bokeh.
   - Amber windows at the far end backlight everything, so columns read as silhouettes and machines get rim
     highlights.
   - Daylight scenes use hard sun through mullioned windows (82–95 s).
   - Shadows are warm brown, never blue or black. Floating dust motes catch the light.
4. **Satin materials with chunky bevels.** Machines are lacquered metal with soft, wide speculars (the cobalt
   "EMBEDDING" cabinet at 5 s, the "REWARD MODEL" cabinet at 96 s). Every edge is generously rounded and catches a
   highlight. Brass appears only as thin trims, bezels and rims, giving small glints. Paper is matte. **There is no
   glass and no mirror reflection anywhere.**
5. **Information is a physical object.**
   - Mechanical odometer drums roll with motion blur (00,541 → 12,288 at 4–6 s).
   - Split-flap boards, gauges with needles, and printed cards with editorial layouts.
   - Engraved cream nameplates with two little bulbs ("EMBEDDING", "REWARD MODEL").
   - Text is never on a glowing screen. It is lit by the scene, so it feels real.
6. **A typography system: one role, one face.**
   - Geometric bold lowercase for the "word" on a card ("was", "moon").
   - Widely tracked serif capitals for machine nameplates.
   - Condensed caps for boards and signs.
   - A newspaper serif for body text, and monospace for code-like strings.
   - Text is huge in frame and faces the camera.
7. **A real-lens camera that never stops.**
   - Every shot pushes, cranes, orbits or tracks the data. Lenses feel like 35–85 mm, with very shallow depth of
     field so the background melts into bokeh.
   - Machines are shot from low angles at machine height, which makes them monumental.
   - Rack focus moves attention from cause to effect, and fast moves carry heavy motion blur.
8. **Editing that follows the words.**
   - There is a new shot or move every ~1.5–3 s, with cuts landing on spoken keywords.
   - Section changes are whip-pans smeared with motion blur.
   - The same objects come back as callbacks (the word cards, the counters, the skyscraper board).
   - Data physically travels between machines (cards on conveyors at 2–6 s), so cause and effect are visible.
9. **Scale shown through repetition.** A field of thousands of pins (32–46 s), a drum ringed with 96 card
   columns (24–30 s), receding rows of columns and pendant lamps, and a whole city convey quantity. A single hero
   item is always set against the mass.
10. **One hero per frame, layered depth.** The subject fills 50–80 % of the frame. There are always foreground,
    midground and background layers (columns, lamps, carts, shelves, floor inlays), so the frame is never empty or
    "staged on a void".

---

## 2. World and palette

### 2.1 Setting
"The Dispatch Hall" is a tall sandstone-and-cobalt hall built like a nave.
- **Shell**: the floor runs X −17…17, Y −16…30. The back wall is at Y = 30, the side walls at X = ±17, and the
  coffered ceiling at Z = 9. The hall is fully closed (needed for light isolation, see §3).
- **Main set** is at the front of the nave: the post service, the topic hub and the subscribers.
- **Follower field** fills the nave behind the main set.
- **FOLLOWERS scoreboard** is mounted on the back wall above the windows.
- **Queue set** is in the left aisle, beyond the left column row.
- **Radio set** is a separate dusk rooftop island at X = 200.

### 2.2 Set map

| Item | Position (x, y[, z]) | Faces | Notes |
|---|---|---|---|
| POST SERVICE module | (0, 0) | −Y | Never moves, ever |
| Monolith bays (0–26.4 s) | NOTIFY (0.95, 0), EMAIL (1.90, 0), FEED (2.85, 0) | −Y | Under one long "POST SERVICE" cap. Ledge conveyor along y = −0.625, top Z 0.30, X 0.40 → 3.40 |
| Topic hub, centre **T** | (0, 2.2) | – | Hidden below the floor (top flush at Z 0) until 26.80 s |
| Subscriber arc (from 27.3 s) | NOTIFY (−1.89, 3.12), EMAIL (−0.75, 4.16), FEED (0.75, 4.16), BADGES (1.89, 3.12) | Toward T, yaw blended 25 % toward −Y | Radius 2.1 around T at −64°, −21°, +21°, +64° from +Y. The BADGES slot is empty until 43.9 s |
| Post → topic chute | (0, 0.40, 1.24) → (0, 1.52, 0.92) | – | Pub/sub phase only |
| PUB/SUB sign | (0, 2.2, 2.95) | −Y, tilted 12° down | Parked out of frame at Z 6.5 until 27.05 s |
| Vendor plaque pedestal | (−1.1, 1.1) | −Y | Plaque stays edge-on until 51.9 s |
| Follower field | X −7…7, Y 6.5…27.5 | – | Raised 0.12 m platform |
| FOLLOWERS scoreboard | centre (0, 29.55, 5.2) | −Y | 9.0 × 3.4 m, above the back-wall windows |
| Queue set | tower (−12.0, −0.6); workers NOTIFY (−13.4, 0), EMAIL (−14.4, 0), FEED (−15.4, 0) | −Y | Ledge along y = −0.625, X −12.4 → −16.0. The card travels −X |
| Radio set | étagère (200, 0); radio tower (210, 70) | −Y | Own lights, own haze |

### 2.3 Palette

| Name | Hex | Role |
|---|---|---|
| Cobalt lacquer | `#2547B5` | All machine bodies (if it reads navy in stills, raise toward `#2C52C4`; never add blue light) |
| Cobalt deep | `#172F7E` | Plinths, lane frames, sign chains' brackets |
| Field deck | `#182A6E` | Follower-field platform deck |
| Cream enamel | `#E8DCC2` | Nameplates, dial faces, drum faces, topic dial |
| Paper | `#F2E9D6` | Message cards, envelopes, tags |
| Navy ink | `#1C2A6B` | Text on cream/paper, dial ticks, digits |
| Brick red | `#B0302A` | POST button, enamel signs, alert drum facets, "problem" only |
| Brass | `#C99A48` | Thin trims, bezels, rails, rivets, pins |
| Charcoal | `#26221E` | Belts, recesses, plinth bands, wires, drum window interiors |
| Sandstone | `#B0936C` | Walls, columns (column bases `#8E7354`) |
| Terrazzo | `#CDB995` | Floor (speckles `#7A6650` and `#EFE5D0`) |
| Dark wood | `#4A3322` | Ceiling beams, carts, étagère |
| Walnut | `#5B3A22` | Radios |
| Bulb warm (emission) | `#FFD7A0` | Lit bulbs |
| Window amber (emission) | `#FFC27A` | Back/side window glow |
| Lamp amber / cream / red (emission) | `#FFB04A` / `#FFE6C0` / `#FF4A35` | Status lamps: working / OK / problem |

Card "payload" tiles (the reference's embedding strip, reused): `#B0302A #F4EEE2 #2547B5 #7FA0E6 #E9A48E` repeating.

**No other hues.** No green, no purple, no cyan, anywhere in 3D.

### 2.4 Material recipes (Principled BSDF; anything not listed stays at default)

| Material | Base | Rough | Metal | Notes |
|---|---|---|---|---|
| `cobalt` | `#2547B5` | 0.42 (Noise tex scale 6 → Map Range 0.38–0.48) | 0 | **No coat.** All cabinet boxes get a Bevel modifier of 0.025–0.03 m, 3 segments, limit = Angle 30° |
| `cobalt_deep` | `#172F7E` | 0.55 | 0 | |
| `cream` | `#E8DCC2` | 0.50 | 0 | |
| `paper` | `#F2E9D6` | 0.75 | 0 | Noise bump at strength 0.03 for paper grain |
| `ink` | `#1C2A6B` | 0.60 | 0 | Text |
| `ink_red` | `#A8302B` | 0.60 | 0 | Small caps labels, italic descriptors |
| `brick` | `#B0302A` | 0.50 (button 0.35) | 0 | |
| `brass` | `#C99A48` | 0.33 | 1.0 | **Only on parts ≤ 4 cm wide** (trims, rims, rails, rivets) |
| `brass_satin` | `#B8904A` | 0.48 | 1.0 | Larger brass: press columns, hooks, pins, pedestal, carriers |
| `charcoal` | `#26221E` | 0.65 | 0 | |
| `steel` | `#3A3835` | 0.45 | 0.8 | Cables, chains, hooks |
| `terrazzo` | `#CDB995` | 0.62 | 0 | Voronoi (scale 180) speckle at 15 % coverage, bump 0.02. Matte: no visible reflections |
| `sandstone` | `#B0936C` | 0.85 | 0 | Columns/walls; a faint Noise tex value ±5 % breaks up flatness |
| `wood` / `walnut` | `#4A3322` / `#5B3A22` | 0.60 / 0.42 | 0 | |
| `grille` | `#D8C7A3` | 0.90 | 0 | Radio speaker cloth |
| `bulb` | `#D9CBB0` | 0.25 | 0 | Off state. On = emission `#FFD7A0` at strength 6–10. **Only on spheres ≤ 2.5 cm** |
| `lamp_*` | `#D9CBB0` | 0.30 | 0 | Status lamp domes (r 0.022). Emission 4–5 in amber, cream or red |
| `window_glow` | – | – | – | Emission `#FFC27A` at strength 4 on planes 0.3 m behind the window mullions |

**Emission is allowed in only these places:** bulbs, status lamps, pendant bulbs, window glow planes, the radio
sky/city/dials/beacon, the broadcast ring, and the follower-field bulb heads. Text, edges and panels are never
emissive. Keep `GLOW` (the global multiplier) at 1.0 with these values; there is no bloom.

### 2.5 Environment and set dressing
- **Floor**: a 34 × 46 × 0.2 box in terrazzo, with a boolean circular hole of r 0.72 at T for the topic hatch.
  Inlays are flat boxes 2 mm proud:
  - a cobalt ring at r 1.05 (0.06 wide) around T, and a brass hatch collar at r 0.74 (0.04 wide);
  - a cobalt band around the field platform;
  - brick diamonds (0.25 m, rotated 45°) at aisle grid points every 5 m.
- **Columns**: two rows at X = ±8.8, at Y = −6, −1, 4, 9, 14, 19, 24, 29.
  - Base: 1.1 × 1.1 × 0.5 (`#8E7354`).
  - Shaft: 0.8 × 0.8 × 8.0 sandstone.
  - Stepped capital: 1.0 × 1.0 × 0.25 plus 1.15 × 1.15 × 0.2.
  - Two cobalt Deco bands (0.81 × 0.81 × 0.06) at Z 6.6 and 6.9, and a brass strip at Z 0.5.
- **Ceiling**: a slab at Z 9 with dark-wood coffer beams (0.4 × 0.6 section) every 5 m in X and Y.
- **Back wall windows**: four tall windows (2.2 × 6.5, sill at Z 1.0) at X = ±6.2 and ±12.0. Each has a cobalt
  mullion grid (3 × 6 panes, 0.06 bars) with a window-glow plane behind. The side walls get 4 high windows each
  (2 × 4 at Z 3–7), with glow at strength 2.
- **Pendant lamps** (the reference's signature):
  - Cord: cylinder r 0.006 up to the ceiling.
  - Shade: an open cone (r 0.34 bottom, 0.07 top, 0.28 tall), cobalt outside and cream inside (emission 0.3).
  - Bulb: sphere r 0.05, emission 10.
  - Light: a point light inside (§3).
  - Rows over the field at X ±4.5, Y 8, 12.5, 17, 21.5, 26, Z 4.6. Main set at (±3.2, −0.6, 4.8) and
    (±3.0, 3.8, 4.8), kept outside the central column so they never cover the sign in the system shots. Queue set
    at (−13.0, −0.9, 3.8) and (−15.0, −0.9, 3.8).
- **Mail-sorting cabinets** (fill the aisles): six units against each side wall. Each is 2.4 W × 0.5 D × 2.2 H,
  with cobalt frames, cream cubbies in an 8 × 6 grid, and a card edge (paper box 0.25 × 0.004 × 0.08) in about
  half the cubbies.
- **Brass rolling carts** at (−3.6, 1.0), (3.8, 0.4) and (−3.4, 5.4): 0.9 × 0.5 × 0.8, two dark-wood shelves,
  stacks of 20 cards tied with brick string, and four casters.
- **Card bundles**: 6 loose stacks on the floor near the carts.
- **Haze**: use **volume cubes, not a world volume**, so each set gets its own density.
  - Hall cube = the hall interior: Principled Volume, density 0.010, anisotropy 0.55, colour `#D8BC94`.
  - Radio cube (X 120…320, Y −10…200, Z 0…80): density 0.004, anisotropy 0.4, colour `#CDA9A8`.
- **Dust motes**: one mesh of ~400 tiny tetrahedra (0.004 m) in a 6 × 6 × 3 m box around the main set, plus ~300
  over the field front. Material: cream base, emission `#FFE9C4` at 0.6. Drift +Z 0.03 m/s with a slow sideways
  sine. Defocused, they become bokeh specks.
- **Scale**: machines are 1.2–1.45 m tall. Close shots keep the camera at machine-face height (0.8–1.8 m) and
  never above 2.5 m, except in the system shots.

---

## 3. Lighting recipe

Exposure intent:
- AgX view, look **"AgX - Medium High Contrast"**, exposure 0. The end hero eases to −0.35 EV from 55.4 s for the
  2D card.
- Calibrate KEY so cream nameplates in key light land at a display value of about 0.75–0.80 (never clipped).
- Lit cobalt faces should read as rich blue at about 0.28–0.35. Shadows stay warm brown, never below about 0.06.
- Lit bulbs should read as warm cream-white points, not blown blobs.
- The overall image is warm and sepia. The cool comes only from the cobalt paint.

### Hall (main set and field)

| ID | Type | Colour | Energy (start here, tune on stills) | Placement / aim | Purpose |
|---|---|---|---|---|---|
| KEY | Area, disk 2.5 m | 3800 K `#FFC690` | 900 W | (−3.6, −3.2, 5.0) → (0.4, 1.6, 0.7) | Soft modelling on machine faces from front-left |
| RIM | Spot 45°, blend 0.6 | 2400 K `#FF9C52` | 700 W, volume_factor 0.4 | (0.5, 8.5, 4.6) → (0, 2.0, 0.8) | Warm back-rim on topic, subscribers and post top; lifts haze behind the set |
| PEND-main ×4 | Point r 0.05 in shades | 2700 K `#FFB46B` | 180 W, volume_factor 0.3 | See §2.5 | Pools of light, practical bokeh |
| PEND-field ×10 | Point r 0.05 | 2700 K | 110 W, volume_factor 0.3 | See §2.5 | Receding rows, depth |
| WIN ×4 | Area 2.2 × 6.5 behind each back window, facing −Y | 2200 K `#FF9A45` | 6 kW each, volume_factor 1.0 | Y 30.6 | Backlight and haze shafts at the end of the nave |
| SIDEWIN ×8 | Area 2 × 4 behind side windows | `#FFA45A` | 1.5 kW | X ±17.3 | Side rims on columns and cabinets |
| BOARD ×2 | Spot 35° | 2700 K | 2.5 kW | (±3.0, 26.5, 0.4) → (0, 29.5, 5.2) | Up-lights the scoreboard, theatre style |
| FILL | Area 3 × 3, shadows off | `#A9B8FF` | 60 W | (4.0, −3.0, 2.0) → (0, 1.5, 0.7) | Tiny cool lift in cobalt shadows only |
| FIELD ×4 | Area 5 × 5 facing down | `#FFB868` | 0 → 350 W, keyed to follow the wave | Z 3.2, over the field at Y 9, 14, 19, 24 | Warm glow over the field when "everyone notified" |
| SPOT-PROBLEM | Spot 16°, blend 0.2 | 4000 K `#FFE2C0` | 0, then 2500 W from 14.50–15.70 | (0, −0.5, 6.2) → (0, −0.1, 1.2) | Theatrical "spot" with a visible cone in the haze |
| World | colour `#2A2018` | – | strength 0.35 | – | Warm ambient floor so shadows never go black |

### Queue set
- KEY-Q: area 1.5 m, 3800 K, 600 W, at (−10.6, −3.4, 4.2) → (−13.8, −0.3, 0.8).
- Two pendants at 160 W.

### Radio set (X = 200)
- SUN: sun lamp, strength 2.2, `#FF9F66`, angle 2°, coming from behind the tower (from +Y at about 8° elevation)
  so the radios and the tower are rim-lit. **Keyframe its strength to 0 except 38.0–43.1 s.**
- FILL-R: area 2 × 2, `#9C94D6` (dusk-sky fill), 120 W, at (199.4, −3.4, 2.2).
- KEY-R: area 1 × 1, `#FFC690`, 160 W, at (201.6, −1.9, 2.4) → radios.

### Isolation and engine settings
- Every hall and queue light: `use_custom_distance = True`, `cutoff_distance = 45`. Radio lights:
  `cutoff_distance = 250`. The hall must be a closed box.
- "Spot the problem": at 14.44 keyframe **every** hall light and the window-glow emissions down to 6 % over 3
  frames, and restore them over 4 frames at 15.70. The spinner bulbs keep running.
- EEVEE: raytracing on (screen trace), Fast GI on (gives contact darkening at machine bases), shadows on.
  Volumetrics: tile 4 for finals (8 for previews), samples 64, start 0.1, end 220, distribution 0.85, volumetric
  shadows on.
- Motion blur on, shutter 0.5. Keyframe `motion_blur_shutter` to 1.0 on whip frames.
- In the final ffmpeg mux, before the captions: `vignette=angle=PI/6, noise=alls=4:allf=t` (soft vignette, fine
  film grain). No other grade.

---

## 4. Typography in-world

Paths (Blender 5.2.2 was checked loading the woff2 and DIN Condensed files):
- Instrument Serif: `node_modules/@fontsource/instrument-serif/files/instrument-serif-latin-400-normal.woff2` and
  `…-400-italic.woff2`.
- Inter (static): `videos/18-pub-sub/fonts/Inter-{Medium,SemiBold,Bold,ExtraBold}.ttf`.
- JetBrains Mono: `~/Library/Fonts/JetBrainsMono-{Medium,Bold}.ttf`.
- DIN Alternate Bold and DIN Condensed Bold: `/System/Library/Fonts/Supplemental/`.
- **Never** use Blender's default Bfont.

| Role | Font | Style | Used on |
|---|---|---|---|
| Machine nameplates | Instrument Serif Regular | ALL CAPS, `space_character` 1.3, navy on cream enamel | POST SERVICE, NOTIFY, EMAIL, FEED, BADGES, FOLLOWERS, topic ring |
| Nameplate descriptor | Instrument Serif Italic | lowercase, brick red, 0.6 × the cap size, under the caps | "publisher", "followers", "inbox", "timeline", "new feature" |
| The message's word | Inter Bold | lowercase, `space_character` 0.98, navy | "new post" on cards |
| Small labels | Inter SemiBold | ALL CAPS, `space_character` 1.35 | TOPIC, REWRITES, NOTIFIED, LOAD, LATEST, ISSUED, card header |
| Identifiers / serials | JetBrains Mono Medium | lowercase | `new-post` on the card header, `No. 0001`, `101.1` |
| Counter digits | DIN Alternate Bold | navy on cream drum facets | Scoreboard, NOTIFIED, REWRITES, ISSUED |
| Status words and enamel signs | DIN Condensed Bold | ALL CAPS, `space_character` 1.08. Cream on charcoal facets (status), cream on brick (signs and alert facets) | PUB/SUB, MESSAGE QUEUE, NEW FEATURE, NEW-POST (radio), status words |
| Vendor plaque | Inter SemiBold caps + Instrument Serif Regular | Two-tier, like an engraved maker's plate | GOOGLE CLOUD / Pub/Sub, AMAZON / SNS |

How text is presented physically:
- **Printed ink** (cards, dials, plates) is a text object with extrude 0.0006 m, placed 0.0008 m above its surface
  (no z-fighting). Use `align_x = 'CENTER'`, `align_y = 'CENTER'`.
- **Raised sign letters** (PUB/SUB, MESSAGE QUEUE, scoreboard label, radio sign) are cut-out letters extruded
  0.012 m. They cast tiny shadows; that is the Deco signage look.
- **Text is never emissive.** Light makes it readable: put KEY or a pendant on any text that matters.
- **Every nameplate** is a cream enamel plate (`cream`, 0.012 thick, bevel 0.004) with:
  - a brass rim (a brass box 0.012 larger behind it);
  - two brass rivets;
  - **two small bulbs** (r 0.012) at the ends, as on the reference's "EMBEDDING" plate.
- **Legibility rule**: when reading text is the point of the shot, its cap height must be **≥ 2.2 % of the frame
  height** (≥ 42 px at 1920), with the text plane within 30° of facing the camera.

Exact strings:
- **Post module**: "POST SERVICE" / *publisher*. Label "REWRITES". Status words: `READY`, `SENDING...`,
  `WAITING...`, `REWRITING` (on a red facet), `PUBLISHED`.
- **Monolith cap**: "POST SERVICE".
- **Bays** (name / *descriptor*):
  - NOTIFY / *followers*
  - EMAIL / *inbox*
  - FEED / *timeline*
  - BADGES / *new feature*
- **Bay displays**: "NOTIFIED", "LOAD", "LATEST", "ISSUED".
- **Bay status words**: `IDLE`, `DONE` / `SENT` / `UPDATED` (per bay), `SLOW` (red facet), `SUBSCRIBED`,
  `RECEIVED`, `GOT IT`.
- **Card**: "TOPIC" (red small caps, left), `new-post` (mono, right), "new post" (title), `No. 0001`.
- **Topic dial**: ring "TOPIC · NEW-POST · TOPIC · NEW-POST ·"; centre "*new-post*" (Instrument Serif Italic) with a
  tiny "TOPIC" above it.
- **Signs**: "PUB/SUB", "MESSAGE QUEUE", "FOLLOWERS", "NEW FEATURE" (crate tag), "NEW-POST" plus "101.1" (radio
  tower).
- **Plaque**: front "GOOGLE CLOUD" / "Pub/Sub"; back "AMAZON" / "SNS".

---

## 5. Component kit

Build these once and reuse them everywhere. Reuse is what makes the world feel designed.

- **`cab(w, d, h)`**: a bevelled cobalt box (bevel 0.03 / 3 segments) on a charcoal plinth 0.04 larger and 0.12
  tall.
  - Brass trim strips (0.012 tall, 0.004 proud) wrap the body at the plinth line and at the top edge.
  - **Deco speed lines**: three vertical brass pinstripes (0.008 wide, 0.025 apart) near the front edge of each
    side face.
  - Optional casters: four brass cylinders (r 0.035, w 0.025) with charcoal tyres. They rotate when the cabinet
    rolls.
- **`plate(caps, italic, w, h)`**: a nameplate as specified in §4.
- **`bulb(r)` groups**: UV sphere plus a brass socket ring. Each group shares **one material whose emission is
  computed in the shader**:
  - Object Info → Location is compared with an animated Value node. For a ring, use the angle around the ring
    centre; for a sign, use the x position.
  - That gives chases, sweeps and "all on" with a single keyframed value per group, with no per-bulb materials.
  - Lamps ignite with a 1-frame flicker (on → 40 % → on).
- **`drum(labels, face_h, width)`**: real mechanical drums, so motion blur works.
  - Digits: a **decagonal prism** (radius = 1.62 × face_h) with one text object per facet, parented and rotated
    tangent to it. Words: an **octagonal prism** (radius = 1.31 × face_h) with up to 8 words.
  - Each facet has its own backing colour (material index): cream for digits; charcoal for words, or brick for
    alert words.
  - The drum sits inside a **window housing** built only from boxes, with no booleans:
    - a charcoal back box;
    - top and bottom cover blocks deep enough to hide the drum;
    - side cheeks;
    - a front plate with the window opening, made of 4 boxes around the opening;
    - a 4-bar brass bezel (0.012) around the opening.
  - The housing protrudes 0.12–0.22 m from the face, like the reference's chunky counter blocks.
  - Rolling = keyframing `rotation_euler.x` by 36° (digits) or 45° (words) per step. Use ease-out-back (overshoot
    ≤ 6 %) for single steps. Long counts are **baked per frame** in odometer fashion:
    - the lowest 3 digits spin continuously (motion blur does the rest);
    - each higher digit advances only in the last 8 % of the lower digit's cycle (smoothstep).
- **`odometer(n, face_h, label)`**: n drums with brass comma plates between digit groups and an Inter SemiBold
  label plate above.
- **`card(title='new post')`**: paper 0.30 × 0.19 × 0.004, standing upright on a **carrier sled**. The carrier is
  `brass_satin`, 0.30 × 0.05 × 0.02, with two clips, and runs on conveyors. The card face points toward the
  camera side (−Y) whatever the travel direction. Face layout:
  - Top row (y +0.075): "TOPIC" in Inter SemiBold red, 0.010 cap, on the left; `new-post` in JetBrains Mono navy,
    0.011, on the right.
  - Title "new post" in Inter Bold, navy, cap 0.036, centred at y +0.02.
  - A navy rule 0.26 × 0.0015 at y −0.015.
  - **10 payload tiles**, each 0.022 × 0.03 with 0.003 gaps, at y −0.045.
  - `No. 0001` in mono, 0.008, at the bottom right.
  - Copies are linked duplicates and look **exactly identical**.
- **`conveyor(len, kind)`**: 0.36 wide, with brass side rails (0.015 × 0.03) and a cobalt-deep underframe.
  - `roller` kind (static ledge and chutes): charcoal rollers r 0.018 every 0.06 m with brass end caps.
  - `belt` kind (subscription lanes): a charcoal belt box with a **world-space** stripe texture, so scaling the lane
    never stretches it.
- **`gate()`**: a brass arch in front of every bay's face, 0.25 m out. Two posts (0.02 × 0.02 × 0.26) at ±0.19, a
  top bar 0.40 × 0.03 × 0.03, a stamp head (0.08 × 0.05 × 0.04) under the bar, and a 0.4 m roller stub where the
  card stops. The gate belongs to the bay and moves with it. Its stub yaws independently to point at the topic.
  - **Stamp**: the head drops 0.05 in 2 frames and rises in 5. The cabinet dips 3 mm and recovers. The card jolts
    1 cm.
- **`lamp()`**: a half-sphere status lamp (r 0.022) with a brass ring. States: off, amber (working), cream (OK or
  subscribed), red (problem).

---

## 6. Objects

### 6.1 POST SERVICE module (the publisher) at (0, 0), faces −Y
- **Body**:
  - `cab(0.90, 0.80, 1.00)` (body Z 0.12–1.10).
  - A stepped crown `cab`-style box 0.80 × 0.70 × 0.16 (Z 1.10–1.26), with a brass strip at Z 1.10.
- **POST button**, centred at (0, −0.10, 1.26):
  - Brick dome: a cylinder r 0.075 × 0.035 plus a sphere cap squashed to 0.4 in Z, roughness 0.35. It travels
    down 0.018.
  - Brass bezel: torus, major 0.11, minor 0.018.
  - **16 spinner bulbs** (r 0.011) on the bezel top at radius 0.11.
  - A small cream tab engraved "POST" at the bezel front.
- **Top card slot** at (0, 0.18, 1.26): a charcoal opening 0.34 × 0.03 between two brass lips. Cards pop up out of
  it like toast.
- **Front face** (Y = −0.40):
  - Nameplate 0.70 × 0.13 at Z 1.00: "POST SERVICE" (cap 0.042) with *publisher* under it.
  - Status word drum, window 0.50 × 0.10 at Z 0.84, with a lamp at x −0.32.
  - "REWRITES" label (0.24 × 0.035) at Z 0.70, above a **2-digit odometer** with windows 0.085 × 0.12 at Z 0.58.
- **Back**: six horizontal charcoal vent bars.
- **Behaviour**:
  - The spinner is a "comet" of 5 lit bulbs with falling brightness (1.0 / 0.7 / 0.45 / 0.25 / 0.1), at 1 rev per
    0.9 s (0.7 s after 5.68).
  - Status-drum states, REWRITES ticks and card pops follow the state timeline (§7.1).
  - The module itself never translates.
- **Monolith-only side chute**: two brass rails (bevelled curves r 0.008, 0.30 apart) along the path
  (0, 0.18, 1.28) → (0.42, 0.0, 1.10) → (0.55, −0.62, 0.32), ending at the ledge start. Cards follow it on their
  carriers.

### 6.2 Monolith (0 → 26.4 s)
- **Bays**: NOTIFY, EMAIL and FEED at X 0.95, 1.90 and 2.85, touching (5 cm gaps), all facing −Y.
- **Cap**: one long box 2.90 × 0.80 × 0.14 (X 0.45 → 3.35, Z 1.30 → 1.44), cobalt with brass edges.
  - Its front carries a 2.2 × 0.11 nameplate "**POST SERVICE**" (Instrument Serif caps, cap 0.06) with 2 bulbs.
  - Four brass bolt heads (r 0.02) sit on top.
  - The cap visually makes the three jobs *part of* the post service.
- **Ledge conveyor**: `roller`, X 0.40 → 3.40 at y −0.625, top at Z 0.30, on 4 cobalt brackets.
- **Wires** (seen only when the cap lifts): 6 bevelled bezier curves (r 0.012) in brick, cobalt and cream, looping
  between the bay tops.
- **Crane rig**:
  - Two steel cables (r 0.008) from Z 9, with hooks (part-torus r 0.05), attach to the cap ends.
  - A third cable carries the **NEW FEATURE crate**: a brass skeleton cube 0.9 × 0.75 × 1.2 (12 bars, 0.025²) with
    a cream tag 0.34 × 0.12 reading "NEW FEATURE" (DIN Condensed, 0.045) hanging off it on a string. It swings as a
    damped pendulum (±6°, decay over 2 s) and hovers at the row's right end (3.85, 0), bottom at Z 1.0.

### 6.3 Subscriber bays: `cab(0.90, 0.75, 1.18)` plus casters, gate in front
- **Face layout, top to bottom**:
  - Nameplate 0.62 × 0.12 at Z 1.20.
  - Status word drum (window 0.42 × 0.09) at Z 1.05, with a lamp to its left.
  - Display zone, Z 0.58–0.95.
  - The gate's roller stub at Z 0.30.
- **NOTIFY**:
  - Display: a **7-digit odometer** "NOTIFIED" (windows 0.07 × 0.10, digit cap 0.075, two brass comma plates
    0.022 wide, about 0.60 total).
  - In the pub/sub phase, a braided cable runs from its back to the field: a bevelled curve r 0.03, charcoal, with
    3 brass clamps, from (−1.89, 3.5, 0.4) along the floor to (−0.6, 6.5, 0.12).
  - Reaction: the gate stamps, the lamp goes amber, the counter rolls, then the status changes and the lamp goes
    cream.
- **EMAIL**:
  - Left: a gauge, r 0.13. Cream face, brass bezel torus, navy ticks 0–10, a brick arc from 7.5 to 10, a brick
    needle 0.11 long, labelled "LOAD".
  - Right: an **envelope window**, a charcoal recess 0.28 × 0.20 with a brass rim. An airmail envelope rises into
    it from behind the lower lip.
  - The envelope is `paper`, 0.22 × 0.12 × 0.003, with a **red/blue/cream diagonal-stripe border**: a Wave
    texture (bands, diagonal) through a colour ramp brick → cream → cobalt, masked to a 0.012 border. It also
    has a navy "postmark" ring and a tiny red stamp square.
  - Normal reaction: the envelope rises in 0.3 s and the needle twitches to 3.
  - **Slow** reaction: the needle swings into the red and jitters ±3° at 7 Hz, the envelope crawls up and stalls
    halfway, the status reads `SLOW` on a red facet, and the lamp goes red.
- **FEED**:
  - Display: a **column window** (0.26 × 0.34, brass rim, "LATEST" above) showing 4 mini cards. Each is 0.22 ×
    0.07 at a pitch of 0.08: paper with a bold "new post" and a payload strip.
  - Reaction: the stack slides down one pitch in 0.22 s (ease-out-back). The bottom card hides behind the lip and
    a new one appears at the top.
- **BADGES** (standalone only):
  - Top-mounted coin press: two `brass_satin` columns (r 0.018, h 0.36), a press head (cylinder r 0.09, h 0.07)
    and a die (r 0.07, h 0.02).
  - Coin: brass, r 0.05 × 0.008, with a raised 5-point star made from a 10-vertex star polygon extruded 0.002.
    A stack of 6 coins sits beside the die.
  - Face display: a 4-digit odometer "ISSUED".
  - Reaction: the head slams down in 2 frames, the coin pops 0.12 m, flips 360° in X, lands on the stack, and the
    ISSUED counter ticks.
- **In the pub/sub arc**: each bay yaws toward T, blended 25 % toward −Y so its face reads from the system camera.
  The gate stub yaws to point exactly at T.

### 6.4 The message
`card()` on its carrier, as in §5. It always enters a scene by **popping up from the post module's top slot** (0.25
s, overshoot 4 %). Copies are identical linked duplicates that appear from inside the topic's ports.

### 6.5 Topic hub at T = (0, 2.2)
- **Drum**: a cylinder r 0.70, height 0.86, in cobalt. When risen it spans Z 0.04 → 0.90.
  - 24 vertical brass flutes (0.012 × 0.012) around the side.
  - A brass top ring (torus, major 0.66, minor 0.022) that **rotates** 15–30° whenever the hub distributes.
  - A brass foot ring.
- **Top dial** (Z 0.905): a cream disc of r 0.62 carrying:
  - **ring text** along a circle curve of r 0.53 (`follow_curve`): "TOPIC · NEW-POST · TOPIC · NEW-POST ·" in
    Inter SemiBold caps 0.035. Tune the size so it wraps exactly once.
  - 60 navy tick marks between r 0.44 and 0.47;
  - the centre word "*new-post*" in Instrument Serif Italic, cap 0.10, with a tiny tracked "TOPIC" above it;
  - the **intake slot** (0.34 × 0.03, brass lips) at the front, at r 0.32 toward −Y, with a brass press plate
    (r 0.2) that thumps 0.02 when stamping copies.
- **Ports**: four brass frames 0.40 × 0.20 (charcoal opening 0.36 × 0.16) at Z 0.20–0.40, at −64°, −21°, +21° and
  +64°. Each has a small lamp above it that lights when a lane connects.
- **Rise**: the drum starts with its top flush with the floor (Z −0.86 → 0) and rises 26.80 → 27.25 with ease-out
  and 1.5 % overshoot.
- **Lanes** (`belt` conveyors), one per subscriber, from its port to that bay's gate stub, with the belt top at Z
  0.30.
  - "Subscribe": the lane's origin sits at the port and its local X scale goes 0 → 1 in 0.35 s (ease-out-back).
  - The brass coupling collar at the gate pops in scale 1.15 → 1.0, the port lamp lights, and the bay lamp turns
    cream.

### 6.6 Post → topic chute (pub/sub phase)
A `roller` chute 0.38 wide from (0, 0.40, 1.24) down to (0, 1.52, 0.92). The card pops up, the carrier tips onto
the chute, slides down (gravity: ease-in), and the card drops into the intake slot.

### 6.7 PUB/SUB sign
- An enamel panel 1.90 × 0.56 × 0.06 in brick (bevel 0.01), with a cream inset border line (0.012 wide, 0.04 from
  the edge).
- "PUB/SUB" in DIN Condensed Bold, cap 0.30, cream, raised 0.012.
- **46 bulbs** (r 0.016) around the border at 0.10 spacing, in brass sockets.
- Two steel chains run up out of frame from its top corners.
- **Drop**: from Z 6.5 at 27.05 to Z 2.95 at 27.30, then two damped swings (2° and then 0.7° in X rotation, 0.5 s).
  The bulbs chase left → right from 27.30 to 27.60, then hold steady.

### 6.8 FOLLOWERS scoreboard, centre (0, 29.55, 5.2), faces −Y
- **Frame**: 9.0 × 3.4 × 0.3, cobalt (bevel 0.05), with brass edge trims.
- **Label**: a cream enamel plate 4.2 × 0.75 at the top, reading "FOLLOWERS" (Instrument Serif caps, cap 0.42,
  tracked 1.3) with 2 bulbs.
- **Digits**: 7 digit drums in windows 0.95 × 1.45, with digit cap 1.05.
  - Drum radius about 2.4 m; the drums sit behind the frame, which is legal because the back wall behind the
    board is never seen.
  - Two brass comma plates 0.35 wide.
- **Border**: ≈ 80 bulbs every 0.3 m.
- **Reads**: 0,000,000 until 1.34 s, then 2,000,000 for the rest of the reel.

### 6.9 Follower field ("two million")
- **Platform**: X −7…7, Y 6.5…27.5, 0.12 tall, with a field-deck top, cobalt rim and brass edge strip.
- **Pins** on a 0.2 m grid with ±0.03 jitter (≈ 7,300 pins), built in bmesh as **two joined meshes**:
  - stems: `brass_satin` cylinders r 0.006, random height 0.07–0.12;
  - heads: spheres r 0.016.
- **Head material** ("the wave"):
  - Texture Coordinate (Object, from an empty at (0, 6.5, 0)) → Vector Length → Map Range against an animated
    Value `wave_r`, with a 0.8 m soft edge and White Noise ±0.4 m jitter so the front isn't a perfect circle.
  - The result drives emission `#FFC27A` × 4.
  - Off-state base `#D9CBB0`, roughness 0.3: cream dots with brass glints on blue.
- `wave_r`: 0 until 50.40, then 0 → 24 m by 51.30 (ease-out). FIELD lights ramp in step with it, front ones first.

### 6.10 Queue set (left aisle)
- **Tower** at (−12.0, −0.6): `cab(0.70, 0.70, 2.30)` with brass bands at Z 0.5, 1.4 and 2.2.
  - Front slot 0.36 × 1.5 (Z 0.45–1.95, brass rim) shows a **column of 12 upright mini cards** (0.30 × 0.10 at a
    pitch of 0.12), each "new post" with a different payload strip and serials No. 0001–0012.
  - Sign on the top front: brick enamel 0.68 × 0.18, "MESSAGE QUEUE" (DIN Condensed cap 0.08, raised), with
    bulbs.
  - A brass pusher at the base shoves the bottom card onto the ledge, and the column drops one pitch with a 4 %
    bounce.
- **Workers**: linked duplicates of NOTIFY, EMAIL and FEED at X −13.4, −14.4 and −15.4. Ledge as in §2.2.

### 6.11 Vendor plaque
- A `brass_satin` pedestal at (−1.1, 1.1): column r 0.04 × 0.95 on a base disk r 0.16 × 0.03.
- The plaque is 0.62 × 0.30 × 0.025 cream enamel with a brass rim (0.012) and 4 rivets, pivoting on Z.
- **Front**: "GOOGLE CLOUD" (Inter SemiBold caps, 0.036, tracked 1.3), a brick rule, then "Pub/Sub" (Instrument
  Serif, cap 0.085).
- **Back**: "AMAZON" / "SNS".
- It stays edge-on (yaw 90°) until 51.9, turns to face the camera by 52.2, and spins 180° from 53.30 to 53.65.

### 6.12 Radio set (X = 200): the broadcast metaphor
- **Rooftop**:
  - A 30 × 30 deck (`#8C7A66`, roughness 0.9).
  - A sandstone parapet 6 × 0.45 × 0.95 at Y 0.8.
  - A walnut-and-brass **étagère**: 0.95 W × 0.40 D, walnut shelves at Z 0.72 and 1.12, brass uprights r 0.012 up
    to 1.5.
- **Four cathedral radios, 2 × 2**, centres X 199.76 / 200.24 on each shelf.
  - Body: a walnut box 0.30 × 0.18 × 0.20 topped by a half-cylinder arch (r 0.15, axis along Y, bisected).
  - An arched **grille-cloth** panel (0.22 × 0.22) with 5 vertical brass bars.
  - A round **dial** r 0.04 at the bottom centre: cream face, navy numbers 88 · 92 · 96 · 100 · 104 · 108 (DIN
    Alternate, 0.008), a brick needle, a brass bezel, and a cream "101.1" label below.
  - Two brass knobs.
  - **Tuned** radios have the needle at 101.1. The **top-right radio is untuned** (needle at 88) and never reacts.
  - "Hears it" means: dial emission `#FFC67A` 0 → 2.5 in 2 frames, plus the grille panel pulsing in Y scale
    1.00 ↔ 1.02 at 5 Hz.
- **Tower** at (210, 70): a stepped Deco stack of boxes 8×8×12, 6×6×10, 4×4×8 and 2.4×2.4×5, topped by a 14 m
  lattice mast (4 converging bars plus 8 rings, cobalt deep).
  - Beacon: sphere r 0.5, brick emission, flashing.
  - Sign at Z ≈ 28 on the front face: brick enamel 6 × 1.6, "NEW-POST" (cap 0.9, raised) over "101.1", with bulbs.
  - The tower faces get a lit window grid: a Brick texture mask with emission `#FFCE8A` at 1.5–2.
- **City**: 40 boxes (6–14 m wide, 15–60 m tall, some with stepped tops) spread over X 140…280, Y 40…200, in
  sandstone with random window grids at emission 0–2.
- **Sky**: a 180° cylinder backdrop, r 260, around (200, 60), with a gradient emission top `#4E4A7E` → 0.6
  `#B98AA0` → horizon `#F3B88A`, strength 1.2.
- **Broadcast ring** (a *single* ring, because it broadcasts "once"):
  - A torus centred on the mast top (210, 70, 48), emission `#FFE3B5` at 2.5, mixed with Transparent so it can
    fade.
  - It expands as a **descending cone wavefront**: major radius r 0.3 → 120 m from 40.04 to 42.6, Z = 48 − 0.66·r,
    minor radius 0.08 → 0.6, emission fading to 0 from 41.9.
  - It passes the radios (r ≈ 71 m, Z ≈ 1.2) at about 41.6 s.

---

## 7. Shot list

Every shot moves (at least 3 % framing change, starting with an ease-out "landing" over the first 40 % of the shot
and then drifting). Focus uses a keyed focus empty. Aperture blades 7, rotation 15°. `→` means camera position →
look-at target.

| # | Time | VO | Camera (pos → target, lens, f-stop, move) | Focus / what animates | Viewer must understand |
|---|---|---|---|---|---|
| 01 | 0.00–1.30 | "You hit post." (tap 0.44) | (0.30, −1.75, 1.72) → (0, −0.12, 1.33), **85 mm f/2.0**, push 1.75 → 1.55 m. Frame 0 is already beautiful: the button big, amber windows and pendants as bokeh in the top third | Button. 0.40 anticipation (+2 mm); **0.44 dome sinks 18 mm in 2 frames, 2-frame camera jolt of 4 mm**; 0.50 the spinner comet starts | I pressed post and the machine is working |
| 02 | 1.30–3.36 | "Two million followers need a notification." | (0.4, 5.4, 0.6) → (0, 29.6, 4.6), **50 mm f/2.8**, low over the field, dolly +1.0 m in Y, tilt down 4° after 2.48 | Scoreboard (rack to pins at 9 m by 2.9). Digits roll 1.34 → 2.05; the millions digit lands **2** at 1.94 with overshoot; board bulbs flash on at 2.0. Thousands of dark pins in the foreground | Two million people, all waiting (dark) |
| 03 | 3.36–6.66 | "And your post button… just keeps spinning." | (0.65, −1.75, 1.75) → (0, −0.3, 1.05), **50 mm f/2.2**, orbit 14° right around the button axis | Button and status drum. Status reads `SENDING...`. At 5.40 the drum tries to roll, fails, snaps back (twice). At 5.68 the comet speeds up | It's stuck |
| 04 | 6.66–10.10 | "Here's why. Your post service does every job itself." | Hard cut. Starts (0.4, −1.2, 1.7) near the button and pulls back and cranes (ease-out until 8.6) to **(−2.0, −4.6, 2.5) → (1.4, 0, 0.75), 35 mm f/3.2**, then drifts right | Cap nameplate "POST SERVICE". 8.40 the card pops from the top slot and slides down the side chute to the ledge start, then waits. **8.48–9.20 the bay nameplate bulbs light one by one: NOTIFY, EMAIL, FEED** | One big machine contains all the jobs |
| 05 | 10.10–12.94 | "Notify followers. Send emails. Update feeds." | Tracking dolly along +X: (0.95, −2.68, 0.9) → (2.85, −2.68, 0.9), target (x, −0.375, 0.73), **50 mm f/2.2**, moving in steps with the card | Card (keep it above 78 % of frame height). 10.10 card → NOTIFY gate, **stamp 10.50**, lamp amber, NOTIFIED rolls to 2,000,000 by 11.1, `DONE`. 11.15 → EMAIL, **stamp 11.52**, envelope rises, `SENT`. 12.10 → FEED, **stamp 12.58**, column shifts, `UPDATED` | Jobs run inside the post service, in order |
| 06 | 12.94–14.44 | "One after another." | Crane up and back to (−2.0, −4.6, 2.5) → (1.4, 0, 0.75), **35 mm f/3.5** | The whole row. The three bay lamps blink in sequence (13.50, 13.70, 13.90). **The spinner is still chasing** in the foreground left | The post waits for all of them |
| 07 | 14.44–15.74 | "Spot the problem?" | Smash cut. (0.35, −2.1, 0.55) → (0, −0.2, 1.05), **35 mm f/2.8**, 2° dutch, 3 % push | Post module. **14.44 all hall lights drop to 6 % (3 frames); 14.50 SPOT-PROBLEM slams on** with a visible cone in the haze; the spinner keeps chasing in the dark. 15.70 lights restore | Pause and think (pattern interrupt) |
| 08 | 15.74–16.90 | "If email is slow," | (2.25, −1.85, 1.05) → (1.85, −0.375, 0.8), **65 mm f/2.0**, 6 % push | EMAIL gauge. 15.88 the needle swings into the red and jitters; **16.38 `SLOW` on a red facet, red lamp**; the envelope stalls halfway; the card trembles in the gate | Email is the slow part |
| 09 | 16.90–17.74 | "your post waits." | (0.45, −1.35, 1.65) → (0, −0.3, 1.1), **50 mm f/2.0** | Post status. **17.38 `SENDING...` → `WAITING...`**; spinner chasing | The slow job blocks posting |
| 10 | 17.74–20.40 | "And every new feature means rewriting…" | **(−1.6, −4.9, 3.4) → (1.7, 0.1, 1.2), 32 mm f/3.5**, crane up 0.4 m | Monolith. 17.80 two hooks drop onto the cap ends. **18.56 the NEW FEATURE crate swings in** from the top right and hovers at the row end. **19.60 the cap hoists 0.9 m** (tilting 2°), exposing tangled wires; the post status goes `REWRITING` (red) | Adding a feature means opening up the post service |
| 11 | 20.40–22.04 | "…the post service. Again." | (−0.35, −1.6, 0.85) → (0, −0.4, 0.72), **65 mm f/2.2** | REWRITES counter. **20.64: 00 → 01. 21.32 "Again": 01 → 02** with a harder slam (the machine jolts 6 mm and the cables jerk in the background) | Every time |
| 12 | 22.04–23.50 | "A message queue won't fix it." | **Whip left.** (−12.9, −2.9, 0.75) → (−12.1, −0.6, 1.45), **32 mm f/2.8**, push and tilt up | Queue tower and its "MESSAGE QUEUE" sign (~21 % from top, right of centre). **22.50 the pusher ejects the bottom card**; the column drops one pitch | This is a queue |
| 13 | 23.50–26.36 | "It hands each message to just one worker." | **(−10.2, −2.6, 2.2) → (−13.9, −0.3, 0.8), 32 mm f/4** (all workers sharp). The tower is a cropped foreground edge on the right. 5 % push, ending with a slight pan toward EMAIL/FEED | The card rides the ledge from 23.6 → **NOTIFY's gate stamps at 25.14 "one"**; the card is pulled in and gone; NOTIFY lamp cream, `GOT IT`. **EMAIL and FEED: empty gates, dark lamps, `IDLE`** | A queue gives each message to one worker only |
| 14 | 26.36–27.30 | "The fix?" | **Whip right.** (−0.9, −3.8, 1.6) → (0.9, 1.0, 0.8), **35 mm f/3.2**, push | 26.40 cap and crate hoist out of frame (0.3 s). **26.46 the bays decouple**: casters spin and the bays roll +X out of frame (staggered 0.08 s, 0.6 s each). Ledge and side chute sink into the floor. **26.80–27.25 the topic drum rises** behind the post module | The jobs leave the post service; something new appears |
| 15 | 27.30–28.30 | "Pub/Sub." | Hard cut to **SYS: (0, −4.2, 6.6) → (0, 2.0, 0.6), 30 mm f/4**, crane down 0.3 m | **The sign lands at 27.30** (dropped from 27.05), swings twice, bulbs chase L → R. Bays sit on the arc, dark and unconnected; BADGES slot empty. Reads: sign ~28 %, subscribers ~37–43 %, topic ~46 %, post ~62–67 % | The new architecture |
| 16 | 28.30–30.95 | "The post service publishes one message to a topic," | Starts (0.75, −1.35, 1.85) → (0, 0.2, 1.2), **50 mm f/2.4**. A follow-pan and truck with the card ends at (0.9, 0.4, 1.9) → (0, 2.0, 0.9) | **28.68 the card pops up** (hero close-up: "new post" readable) and slides down the chute. **30.32 it drops into the topic slot**; the top ring rotates 30°; the "new-post" dial is readable | One message, handed to a named topic |
| 17 | 30.95–31.60 | "and it's done." | Shot 09 framing | **31.06 status `WAITING...` → `PUBLISHED`** (cream) | The post service is finished |
| 18 | 31.60–33.14 | "The button stops spinning." | **Shot 01 framing exactly (callback)**, 85 mm f/2.0 | **31.98 the comet stops, all 16 bulbs steady; 32.10 the button pops up** (2 mm overshoot); 32.40 bulbs fade over 0.4 s; status `READY` at 32.8 | Instant response |
| 19 | 33.14–35.50 | "Every feature subscribes to that topic." | SYS framing orbited from azimuth −14° to −4° about T: start (−1.6, −4.0, 5.6) → (0, 2.4, 0.6), **30 mm f/3.5**. Check NOTIFY's left edge stays in frame | **33.80 / 34.00 / 34.20 lanes extend** to NOTIFY, EMAIL, FEED; couplings clamp, port lamps light, bay lamps cream, `SUBSCRIBED`. 34.70 the topic ring turns 15° | Features plug themselves into the topic |
| 20 | 35.50–38.24 | "Each one gets its own copy, all at the same time." | SYS framing, **dolly in 0.8 m**, 30 mm f/4 | **36.00 the press plate thumps. 36.52 three identical copies slide out of the three ports in perfect sync. 37.54 "same": all three gates stamp on the same frame**: NOTIFY rolls, the EMAIL envelope pops, FEED shifts, all lamps flash amber → cream | Everyone gets the same message simultaneously |
| 21 | 38.24–40.50 | "Like a radio station: it broadcasts once," | **Whip up and right** to the radio set: (200, −2, 1.6) → (210, 70, 30), **50 mm f/2.8**, crane up 0.5 m and tilt 3°. Tower top ~22 %, sign ~48 % | 38.54 tower sign bulbs on. 39.62 the beacon flashes. **40.04 "once": one ring is emitted** and expands | A station sends one signal |
| 22 | 40.50–43.14 | "and every radio tuned in hears it." | (200.0, −2.45, 1.25) → (200.0, 0, 1.18), **50 mm f/2.8**, 5 % push. The 2 × 2 radios fill 34–76 % of height; the tower is a blurred shape at the upper right | **About 41.6 the ring sweeps through the frame. 41.80 "tuned": three dials ignite on the same frame** and the grilles pulse; **the untuned top-right radio stays dark and still** | Tuned in = subscribed = gets it at once |
| 23 | 43.14–44.95 | "New feature? Just subscribe it." | **Whip back.** (3.9, −0.9, 2.1) → (1.55, 2.6, 0.6), **35 mm f/2.8**, pan following BADGES | **43.14 BADGES rolls in** from (5.2, 3.6) to its slot, turning to face T, and stops at 43.90 with a 1.5 cm rock; nameplate bulbs on 43.96. **44.22 a lane extends**, clamps at 44.54, `SUBSCRIBED`. 44.70 a test coin stamps, pops and flips | Adding a feature = plugging it in |
| 24 | 44.95–47.04 | "The post service never changes." | **Deliberately near-static**: (−0.8, −2.45, 1.15) → (0.1, −0.4, 0.85), **50 mm f/2.4**, 2 % push | Post module (2.2 m). **Nothing on it moves; REWRITES stays at 02; `READY`.** BADGES, defocused at ~59 % / 40 %, stamps a coin at 45.4 | The publisher is untouched |
| 25 | 47.04–49.30 | "So those two million followers?" | **Whip.** Callback of shot 02 in reverse: (0.4, 6.4, 0.6) → (0, 29.6, 4.6), **50 mm f/2.8**, dolly back 1.0 m | Scoreboard reads 2,000,000; the field is dark | Same two million |
| 26 | 49.30–50.30 | "One publish." | **Shot 01 framing (callback)** | **49.34 a single press**: all 16 bulbs flash once together (no chase), the button returns at 49.62, and the card shoots up out of the slot at 49.54 (motion-blurred) | One action |
| 27 | 50.30–51.76 | "Everyone notified." | **(−1.0, −2.2, 2.4) → (0, 12, 0.6), 24 mm f/4, crane up to Z 3.6** | 50.30 copies arrive at all four gates (one stamp frame). **50.36 NOTIFIED rolls 0 → 2,000,000 by 51.0. 50.40 the wave of light sweeps the field front to back by 51.30**; FIELD lights ramp; scoreboard bulbs chase once | One publish reached all two million |
| 28 | 51.76–55.40 | "That's Google Cloud Pub/Sub and Amazon SNS." | **Whip.** (−1.0, −1.5, 1.45) → (−1.1, 1.1, 1.15), **65 mm f/2.0**, push 2.62 → 2.2 m | The plaque turns face-on 51.9–52.2 (**GOOGLE CLOUD / Pub/Sub** readable at 52.24), then **spins 180° 53.30–53.65 to AMAZON / SNS** (53.68). Background: lit topic, subscribers and field bokeh | Real products that do this |
| 29 | 55.40–63.60 | CTA (2D profile card overlays the centre from 55.33) | Calm hero orbit from (−3.2, −4.4, 5.6) to (−1.6, −5.0, 6.0) → (0, 2.4, 0.7), **32 mm f/3.2**, crane +0.4 m. Exposure → −0.35 EV by 56.0 | A gentle publish every 2.8 s (bulbs blink, card down the chute, four copies, synced stamps). Field lit at 70 %. Sign bulbs chase slowly every 3 s | Attractive, alive, not busy |

### 7.1 State timeline (so every machine is consistent)
- **Post status**:
  - `READY` → `SENDING...` at 0.50
  - → `WAITING...` at 17.38
  - → `REWRITING` (red) at 19.60
  - → `WAITING...` at 26.40
  - → `PUBLISHED` at 31.06
  - → `READY` at 32.8
  - → `PUBLISHED` at 49.40
  - → `READY` at 50.2
- **REWRITES**: 00 → 01 at 20.64, 01 → 02 at 21.32, then frozen.
- **Spinner**:
  - comet from 0.50 to 31.98;
  - steady, then off at 32.8;
  - single flash at 49.34;
  - soft blinks during shot 29.
- **NOTIFIED**:
  - → 2,000,000 at 10.5–11.1;
  - reset to 0 during shot 14 (off-camera);
  - partial roll at 37.54, reset off-camera at 49.4;
  - → 2,000,000 at 50.36–51.0.
- **Bay statuses**:
  - `IDLE` at start;
  - `DONE` / `SENT` / `UPDATED` at 11.0 / 11.9 / 12.85;
  - EMAIL `SLOW` at 16.38;
  - all `IDLE` with lamps off at 26.40;
  - `SUBSCRIBED` as each lane connects;
  - `RECEIVED` (amber flash, then cream) at 37.54 and 50.30.
- **Topic**: hidden until 26.80. Port lamps follow the connections.
- **Field**: dark until 50.40, full by 51.30, 70 % in shot 29.
- **Sign**: parked until 27.05.
- **Plaque**: edge-on until 51.9.
- **SUN** (radio): 0 outside 38.0–43.1.

### 7.2 Transitions and motion rules
- **Whips** (at 22.04, 26.36, 38.24, 43.14, 47.04, 51.76):
  - the last 4 frames of the outgoing shot yaw +18° (ease-in);
  - the first 4 frames of the incoming shot start at −18° and ease to 0;
  - `motion_blur_shutter` is 1.0 on those 8 frames.
  - Whip in the direction of the next place: left to the queue, right back to the main set, up to the radio.
- **Other changes**: hard cuts on the spoken keyword. Shot 07 is a smash cut with the lights going out.
- **Mechanical feel**:
  - 2-frame anticipation, fast action (2–4 frames), and a single damped overshoot of ≤ 6 % on arrival.
  - Stamps take 2 frames down and 5 up. Anything that lands makes the receiving machine dip 3 mm.
  - Lamps ignite with a 1-frame flicker. Copies move in exact sync.
  - Only the crate, the sign and the radio grilles have oscillation. Nothing bobs idly.
- **Camera**:
  - close shots sit at machine-face height, and high angles are only for system shots (15, 19, 20, 27, 29);
  - f/2.0–2.8 for close shots, f/3.5–4 for wides — never everything-sharp f/8;
  - rack focus only where the table says so.

---

## 8. Pitfalls to avoid (from v1–v4)

1. **No dark void.** v1/v2's navy stage read as "plain". Every frame shows the warm, lit hall with at least 3 depth
   layers (machines, columns and pendants, windows and haze). The world colour is warm brown, never navy.
2. **No orthographic or isometric diorama** (v3). Perspective lenses (24–85 mm) with real depth of field and motion
   blur only.
3. **No neon.** No neon edges, holographic chips or glowing outlines (v2/v3). Emission only on the list in §2.4.
   Status meaning comes from lamps plus words.
4. **No cartoon icons** (v3's bell, mailbox and medal). Subscribers are period machines; meaning comes from
   nameplates and behaviour (odometer, gauge plus airmail envelope, card column, coin press).
5. **No gloss** (v4's "reflections too much"):
   - no glass, no coat, no mirror floor;
   - every surface has roughness ≥ 0.3, and brass (0.33) only on thin trims;
   - check every still for reflection streaks on cobalt or floor.
6. **No phone or app UI.** No iOS cards, notification banners or screens in 3D. Information is printed, engraved or
   mechanical.
7. **No screen counters** (v3's "2 million" screen). All numbers are mechanical drums in DIN Alternate on cream
   facets. Never use Bfont, and never put text on an emissive panel.
8. **No static wides.** Every shot moves. Wides appear only when the system must be seen.
9. **No tiny text.**
   - Obey the 2.2 % cap-height rule and keep the text plane within 30° of the camera.
   - Don't rely on the HUD band (top 16 %) or the caption band (bottom 20 %).
   - Tall things go on the right side of the frame.
10. **No colour creep.** Nothing green, purple or cyan. Red means "problem" only (SLOW, REWRITING, the POST button,
    signs).
11. **Haze discipline.** Hall density ≤ 0.012. If blacks go milky, lower the density rather than raising contrast.
    Pendant `volume_factor` stays 0.3, or they turn into fog blobs.
12. **No light leaks.** The hall is a closed box, lights have cutoff distances, and SUN is keyed to the radio shots
    only.
13. **No sharp CG edges.** Bevel every box. No z-fighting: text is 0.8 mm proud of its surface.
14. **Don't flatten the cobalt.** It can turn monotonous. Keep it satin so the bevels catch highlights, and always
    break it with cream faces, brass trims and warm light. Never add blue lights to "fix" it.
15. **Keep the end calm.** The 3D under the CTA must not compete with the 2D card. Watch for orbit cameras clipping
    through cables, chains or pendants in shots 15, 19, 20 and 29.

### Overlay harmonisation (2D, recommended)
The HUD and caption accents (orange pill; violet, green and cyan words) will clash with this sepia world:
- Recolour the HUD kicker pill to brick `#B0302A` with cream `#F3E9D2` text.
- Make chapter-title italic words brass `#E2B65C`.
- Make caption keywords brass `#F2C46B`, and put "problem" words (slow, waits, rewriting, again) in a **brick-red
  pill** (`#A8302B` fill, white text), like the reference's red "96" and "penalty" pills.

### Build order (to stay realistic)
1. Hall shell, haze, lights and the AgX check stills.
2. Component kit (§5).
3. Post module, bays, monolith cap and ledge.
4. Topic, lanes, chute and card copies.
5. Scoreboard and follower field.
6. Sign and plaque.
7. Queue vignette (linked bay duplicates).
8. Radio island.

The kit keeps each object to tens of lines. Review full-quality stills at 0.4, 2.0, 8.6, 11.5, 14.6, 16.4, 19.9,
25.2, 27.4, 28.7, 37.6, 41.9, 44.6, 50.9 and 52.3 before rendering the animation.
