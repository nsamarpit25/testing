# 19 Event-Driven Architecture — art direction: "The Event Yard"

## 0. Hook choice

Hooks considered (the script uses the fourth):
1. **"Your package shipped at 3 AM. How did your phone know before you did?"** Rejected. It points at push
   notifications, which is reel 18's territory (one message to many phones), and it can't show the log or replay.
2. **"Right now, your app is asking the server 'anything new?' every second. The answer is almost always no."**
   Rejected as the hook. It is the strongest *pain*, but it opens on a problem with no picture of the payoff, and
   "your app" is vague. The idea is kept as line 1 (the slow way).
3. **"You tap Buy. In one second you get an email, a tracking page and 50 points. The order service didn't call any
   of them."** Close, but "didn't call" is jargon in the first 3 seconds, and the line runs too long.
4. **Chosen: "You tap Place Order. One second later, your email, tracking page and reward points all update. Nobody
   asked them to."** Everyone has tapped Place Order. The three things that update become the three services, so
   the hook *is* the cast. "Nobody asked them to" is a small mystery. It flips straight into line 1 ("they keep
   *asking*") and is solved at "announces a fact".

Why this reel is not a Pub/Sub repeat:
- **Polling is the villain.** Cars drive back and forth asking. Reel 18's villain was a monolith doing every job.
- **The event is a kept fact.** Tablets stay on a numbered row; reel 18's card was used up once it was delivered.
- **Services react on their own rhythm.** They are deliberately *not* in sync. Reel 18 stamped everything on one
  frame.
- **New here:** offline catch-up and history replay.

Script: 12 lines, 162 words. That is about 59–60 s of voice at reel 18's measured pace (3.0 words/s plus pauses).

---

One world, no options. "The Event Yard" is a bright 1960s Swiss-modernist railway depot: board-formed pale concrete,
sawtooth north-light roof, a steel window wall onto a cool morning sky. It looks like a polished model railway built
full size.
- **Events** are chunky signal-yellow enamel tablets reading ORDER PLACED. They stand forever in a numbered row on a
  raised platform: the EVENT LOG.
- **Services** are small teal rail cars on stepped tracks in front of the log. A car rolls under each tablet, stops,
  and does its job (an envelope pops, a pin drops, a coin stacks, a bar grows). **Where a car stands is how far it
  has read.**
- **The producer** is the ORDERS press at the left end. It never moves.

Conventions:
- Metres, Z up, floor at Z = 0. +Y points into the hall (toward the window wall) and +X is to the right. Hex values
  are sRGB, converted with `hx()`.
- Blender 5.2, EEVEE, **1080×1920, 30 fps**. The camera sensor is 36 mm with AUTO fit, so in 9:16 the frame height
  is **H = d × 36 / f** and the frame width is **W = d × 20.25 / f**.
- Times are **estimates** from the word count (3.15 words/s plus the generator's pauses). Every cut is anchored to a
  *word*, so re-time from `voice/words.json` once the voice exists.
- Safe zones are the same as reel 18: the HUD covers the top 16 %, captions sit at 80–88 %, and anything that must be
  read goes between 18 % and 77 % of the frame height.

---

## 1. World and palette

### 1.1 Set map

| Item | Position | Notes |
|---|---|---|
| Hall shell | floor X −11…13, Y −10…7; ceiling Z 7 | Closed box. Back wall at Y 7 is a steel window wall (Z 0.9–5.2) |
| **ORDERS press** | X −7.10…−5.60, Y −0.25…0.95 (centre −6.35, 0.35) | Faces −Y. Never translates |
| **ENQUIRY buffer beam** | X −5.80…−5.55, Y −2.95…−0.55 | Stepped teal beam with one buffer head per lane. Polling phase only; retracts into the floor in line 9 |
| **Stepped track tiers** | X −5.80…7.60 | Concrete terraces, rising toward the log (table below) |
| **EVENT LOG platform** | X −5.20…7.50, Y −0.55…0.95, top Z 1.80 | Tablets stand at Y −0.30 (Z 1.80–2.60). Delivery rail behind them at Y +0.45, rail top Z 2.10 |
| Slot centres | **x_n = −4.70 + 0.62 (n − 1)**, n = 1…20 | x_1 −4.70, x_3 −3.46, x_8 −0.36, x_9 0.26, x_10 0.88. **Park (slot 0) = −5.10** |
| EVENT LOG blade sign | (1.0, −0.40, 3.85) | Hangs from 2 rods. Edge-on (yaw 90°) until line 4 |
| Platform lamps ×10 | x = −4.39 + 1.24k (k = 0…9), lamp head at (x, −0.05, 3.25) | Brass goosenecks rising from the platform's back edge |
| Station clock | (−2.0, 6.85, 4.3), faces −Y | Cream dial r 0.45 |
| Maker's pier | (8.40, −1.40), 0.70 × 0.40 × 1.70 | Two oval builder's plates on its −Y face |
| **Door island** | X 38…42, own lights and haze | Doorbell vignette (§5.9) |

Tiers: each tier is a concrete box from the floor to its top, with a 0.04 brass nosing on its front edge.

| Tier | Lane (car) | Front edge Y | Lane centre Y | Top Z |
|---|---|---|---|---|
| A | ANALYTICS (empty until line 7) | −2.95 | −2.65 | 0.00 (floor) |
| B | REWARDS | −2.35 | −2.05 | 0.34 |
| C | TRACKING | −1.75 | −1.45 | 0.68 |
| D | EMAIL | −1.15 | −0.85 | 1.02 |

The log platform's front face rises from Z 1.02 to 1.80 at Y −0.55. Seen straight on, the composition is a vertical
stack, which suits 9:16:
- car nameplates, one tier above the next (each 0.34 higher);
- the slot ruler on the platform face;
- the tablet frieze;
- the platform lamps and sign.

### 1.2 Palette (no other hues; nothing green, purple or cyan)

| Name | Hex | Role |
|---|---|---|
| Teal lacquer | `#1F5F66` | Machines: ORDERS, car bodies, sign, beam. **This is the cool counter-colour.** If it drifts green in stills, shift it to `#1E5A6E` |
| Teal deep | `#143F45` | Chassis trims, window mullions, lamp shades (outside) |
| Signal yellow | `#F0B429` | **Events only**: tablets, the PLACE ORDER button, the parcel, the TRACKING pin |
| Cream enamel | `#EEE6D6` | Nameplates, ruler band, dials, tags. A neutral cream, not beige |
| Paper | `#F5F0E6` | Envelopes |
| Ink | `#1B2A2F` | All printed text and digits on cream or yellow |
| Vermilion | `#D2452E` | **Problems only**: NO flaps, SWAMPED, OFFLINE, the hatch lamp |
| Brass | `#C6A15B` | Thin trims, nosings, hooks, bars, tokens |
| Concrete | `#BEB8AD` | Walls, tiers (tier risers `#A9A398`) |
| Floor screed | `#B3ACA0` | Floor |
| Oak | `#A47A52` | Sleepers, platform top slab, door-island floor |
| Steel | `#55595B` | Rails, rods, chain |
| Charcoal | `#262829` | Tyres, cables, slots, recesses |
| Sky (emission) | `#CFE0EE` → horizon `#F4E6CF` | Window backdrop |
| Skylight (emission) | `#E6F0F8` | North-light strips |
| Practical (emission) | `#FFE3B3` | Platform-lamp bulbs. Warm cream, not orange |
| Lamp states (emission) | amber `#FFB547` / cream `#FFF1D6` / vermilion `#FF5A3C` | Reading / idle / problem |

Colour logic: **yellow = a fact that happened**, teal = machinery, vermilion = waste or failure. Warmth comes from the
practicals on the tablets; coolness comes from the skylights, the window wall and the teal. The result reads as
morning daylight, not sunset.

### 1.3 Materials (Principled BSDF; unlisted values stay default; no coat, no glass)

| Material | Base | Rough | Metal | Notes |
|---|---|---|---|---|
| `teal` | `#1F5F66` | 0.40 (Noise scale 8 → 0.36–0.46) | 0 | All boxes: Bevel 0.025, 3 segments, angle limit 30° |
| `teal_deep` | `#143F45` | 0.50 | 0 | |
| `yellow` | `#F0B429` | 0.45 | 0 | Tablets bevel 0.02, 3 segments. **Never emissive** |
| `cream` | `#EEE6D6` | 0.50 | 0 | Plates 0.012 thick, bevel 0.004 |
| `paper` | `#F5F0E6` | 0.75 | 0 | Noise bump 0.03 |
| `ink` / `ink_red` | `#1B2A2F` / `#C8432C` | 0.60 | 0 | Text |
| `vermilion` | `#D2452E` | 0.45 | 0 | |
| `brass` | `#C6A15B` | 0.32 | 1.0 | Only on parts ≤ 4 cm wide |
| `brass_satin` | `#B8955A` | 0.48 | 1.0 | Tokens, bars, pier plate rims, hoist hook |
| `concrete` | `#BEB8AD` | 0.88 | 0 | Board marks: Wave texture (bands, scale 0.9 per m, Z direction) at ±4 % value, plus Noise ±3 % |
| `riser` | `#A9A398` | 0.85 | 0 | Tier fronts |
| `screed` | `#B3ACA0` | 0.70 | 0 | Voronoi (scale 140) speckle `#8E887E` at 10 % coverage, bump 0.015 |
| `oak` | `#A47A52` | 0.55 | 0 | Noise stretched ×8 along the grain for streaks |
| `steel` | `#55595B` | 0.40 | 0.85 | Rails get roughness 0.30 for one thin top glint |
| `charcoal` | `#262829` | 0.65 | 0 | |
| `lamp_*` | `#E2DCCF` | 0.30 | 0 | Status domes r 0.03. Emission 4 in the state colour |

Emission is allowed in only these places:
- platform-lamp bulbs and the lamp-shade insides (strength 0.3);
- status domes;
- skylight strips, the sky backdrop and the door-island daylight plane;
- the door-island answer lamp.

Text is never emissive. There is no bloom.

### 1.4 Shell and set dressing
- **Window wall** (Y 7): teal-deep mullion grid, 1.2 m bays and 0.08 bars, between concrete piers 0.5 × 0.5 every
  4 m.
- **Window backdrop** at Y 16: a gradient-emission plane (strength 1.3). In front of it are flat dark silhouettes in
  `#6F7C86`:
  - 3 signal gantries (thin boxes);
  - a water tower (a cylinder on 4 legs);
  - two low sheds.
  These defocus into cool shapes behind everything.
- **Roof**: 3 sawtooth ridges running along X at Y −4, 0 and 4. Each is a tilted concrete box with a 12 × 1.2
  skylight emission strip on its +Y face.
- **Station clock** (back wall):
  - cream dial with 12 ink bar markers, ink hands and a teal rim (torus);
  - a brass hub;
  - no brand and no red second hand.
- **Tracks** (per lane):
  - two steel rails, 0.025 × 0.03, gauge 0.36;
  - oak sleepers 0.50 × 0.08 × 0.02 every 0.31 (array or loop), from X −5.45 to 7.6;
  - a charcoal ballast strip 0.56 wide, 5 mm proud.
- **Brass slot ticks**: a 0.012-wide inlay on every tier nosing at each x_n, so slots read down every tier.
- **Riser lettering**: cream paint (a flat text mesh, 1 mm proud) on the front faces of tiers B, C and D: "REWARDS",
  "TRACKING", "EMAIL", DIN Alternate Bold, cap 0.16, repeated every 3.1 m. **This identifies a lane even when its car
  is small in frame.**
- **Spare-tablet crate** at (−7.7, −1.5): a teal-framed crate holding 6 blank yellow tablets.
- **Haze**: one volume cube for the hall (Principled Volume, density 0.007, anisotropy 0.5, colour `#DDE4E8`). It is
  cool-neutral, never sepia.

---

## 2. Lighting

Exposure intent:
- AgX with the look **"AgX - Medium High Contrast"**, exposure 0. Ease to −0.3 EV under the CTA (from 53.6).
- Lit cream plates should read about 0.75–0.80 and stay near-neutral (R − B ≤ 0.08 on a lit plate).
- Lit yellow tablets peak at about 0.85 and must never clip.
- Teal faces sit at about 0.25–0.32. Shadows are cool-neutral grey, never black (no value below 0.05).

| ID | Type | Colour | Energy | Placement → aim | Purpose |
|---|---|---|---|---|---|
| KEY | Area disk 3 m | `#FFDDB8` (≈4300 K) | 700 W | (−3.5, −6.5, 4.2) → (0, −1.0, 1.2) | Soft modelling on car faces and plates |
| SKY ×3 | Area 12 × 1.2, facing down | `#D9E7F4` | 350 W each | Under each skylight, Z 6.8 | Cool top-light; neutralises warmth |
| BACK | Area 20 × 4 behind the window wall, facing −Y | `#CFE0F2` | 3 kW, volume_factor 1.0 | Y 7.6, Z 3.0 | Cool backlight shafts through the haze; rims the tablets |
| LAMP ×10 | Point r 0.04 inside each shade | `#FFE3B3` | 55 W, volume_factor 0.25 | Platform lamps | Warm pools on the tablets. Off during polling |
| RIM | Spot 50°, blend 0.7 | `#C4D8EE` | 450 W | (5.0, 4.0, 4.5) → (0, −1.6, 0.8) | Cool edge on car roofs and devices |
| FILL | Area 4 × 4, shadows off | `#FFF1E0` | 80 W | (4.5, −6.0, 1.2) → (0, −1.5, 0.6) | Lifts the tier risers |
| ORDERS-KEY | Area 1.2 × 1.2 | `#FFE6C8` | 160 W | (−5.0, −2.8, 3.0) → (−6.35, −0.25, 1.6) | Keeps the ORDERS face readable |
| World | `#2B2F33` | – | strength 0.3 | – | Neutral ambient |

Settings for all of these lights:
- Every hall light: `use_custom_distance = True`, `cutoff_distance = 30`. The door island (§5.9) has its own lights
  with a cutoff of 12.
- EEVEE: raytracing on, Fast GI on, shadows on.
- Volumetrics: tile 4 for finals (8 for previews), 64 samples, start 0.1, end 60, volumetric shadows on.
- Motion blur on, shutter 0.5. Raise `motion_blur_shutter` to 1.0 on whip frames and during the polling shuttles
  (7.9–13.1).
- Final ffmpeg pass: `vignette=angle=PI/6, noise=alls=3:allf=t`. No other grade.

---

## 3. Typography in world

Fonts (same paths as reel 18; never Bfont):
- Instrument Serif: `node_modules/@fontsource/instrument-serif/files/instrument-serif-latin-400-{normal,italic}.woff2`.
- Inter: `videos/18-pub-sub/fonts/Inter-SemiBold.ttf`.
- JetBrains Mono: `~/Library/Fonts/JetBrainsMono-Medium.ttf`.
- DIN Alternate Bold and DIN Condensed Bold: `/System/Library/Fonts/Supplemental/`.

| Role | Font | Style | Used on |
|---|---|---|---|
| Machine names | DIN Alternate Bold | CAPS, `space_character` 1.15 (1.05 for 8 or more letters), ink on cream | ORDERS, EMAIL, TRACKING, REWARDS, ANALYTICS, riser lettering |
| Descriptor | Instrument Serif Italic | lowercase, ink | "order service", "from orders", "event log" on the plates |
| Event words | DIN Condensed Bold | CAPS, ink on yellow | ORDER / PLACED on tablets, the parcel tag |
| Small labels | Inter SemiBold | CAPS, `space_character` 1.35 | EVENT, ASKED, POINTS, CALL LIST, PLACE ORDER, PLACED / PACKED / SHIPPED |
| Serials | JetBrains Mono Medium | – | `#0001`…`#0020` on tablets |
| Digits | DIN Alternate Bold | ink on cream wheels | Slot ruler `0001`…`0020`, ASKED, POINTS |
| Problem words | DIN Condensed Bold | CAPS, cream on vermilion (NO is vermilion on cream) | NO, SWAMPED, OFFLINE |
| Sign | DIN Condensed Bold, raised 0.012 | cream on teal | EVENT LOG |

How text is presented physically:
- Printed text is extruded 0.0006 and sits 0.0008 proud of its surface, with `align_x/y = 'CENTER'`. Text is never
  emissive.
- **Legibility rule**: when reading is the point of the shot, cap height must be ≥ 2.2 % of H, with the text plane
  within 30° of facing the camera. Quick check:

  | Text | Cap | Readable at 35 mm up to | at 50 mm up to |
  |---|---|---|---|
  | Car names | 0.085 | 3.8 m | 5.4 m |
  | Tablet words | 0.14 | 6.2 m | 8.8 m |
  | Riser names | 0.16 | 7.0 m | 10.1 m |

---

## 4. Component kit

Build these once and reuse them everywhere.

- **`tier(y_front, top_z)`**: a concrete box with a brass nosing (0.04 × 0.04) and slot ticks.
- **`track(y, z)`**: rails, sleepers and ballast as in §1.4.
- **`plate(name, desc=None, w, h, cap)`**: a cream enamel plate.
  - Behind it sits a brass rim (a box 0.012 larger).
  - Two brass screw heads (r 0.01).
  - The name is centred. If `desc` is given, it goes below the name at 0.38 × the cap height.
- **`lamp()`**: a half-sphere status dome (r 0.03) with a brass ring. One material per lamp; keyframe the emission
  colour and strength. States: off, amber, cream, vermilion. It ignites with a 1-frame flicker.
- **`wheels(n, cap)`**: exposed number wheels (no window housing, unlike reel 18).
  - Each wheel is a decagonal prism (radius 1.62 × cap) in cream, with ink digits on its facets, set in a teal slot
    with brass cheeks.
  - Ticks roll 36° with ease-out-back (overshoot ≤ 5 %). Long counts are baked per frame, odometer style.
- **`tablet(n)`**: an event.
  - Body: yellow, 0.50 W × 0.07 D × 0.80 H, standing, face −Y.
  - Face layout (local Z from the centre):
    - "EVENT" in Inter SemiBold, cap 0.032, at +0.33;
    - "ORDER" in DIN Condensed, cap 0.14, at +0.17;
    - "PLACED" in DIN Condensed, cap 0.13, at −0.01;
    - an ink rule 0.40 × 0.004 at −0.12;
    - `#00nn` in mono, cap 0.055, at −0.21;
    - "from orders" in Instrument Serif Italic, cap 0.03, at −0.31.
  - Share **one** linked "EVENT / ORDER / PLACED / rule / from orders" mesh; only `#00nn` is unique per tablet. Text
    is converted to mesh.
  - It stands in a brass groove (0.56 × 0.10 × 0.02) at its slot.
- **`car(name, device)`**: a service car.
  - Wheels: four, r 0.07 (brass hub, charcoal tyre), at x ±0.22, y ±0.18. Wheel centres sit at tier + 0.12. Wheels
    rotate with travel (angle = distance / 0.07).
  - Chassis: charcoal, 0.70 × 0.40 × 0.08, at tier + 0.14…0.22.
  - Body: teal, 0.66 L × 0.44 W × 0.30 H, at tier + 0.22…0.52. A brass belt line runs at tier + 0.24.
  - Buffers: brass discs (r 0.04) at both ends.
  - **Nameplate** on the −Y face: 0.58 × 0.17, name cap 0.085, centred at tier + 0.37.
  - `lamp()` on the roof at the front-left corner.
  - Device on the roof (§5.4). **At rest, a device is at most 0.14 m tall**, so it never covers the nameplate of
    the car on the tier behind. Only the moment of reacting (a rising envelope) may poke higher.
  - **Hop** (reading one slot): move +0.62 in X over 0.22 s (ease in-out, wheels turning), a 2-frame settle of 6 mm,
    the lamp goes amber, the device fires, then the lamp goes cream 0.3 s later. **Idle cars never move.**
- **`tag(text, w, h)`**: a vermilion enamel tag with cream DIN Condensed text, hung from a brass hook by two short
  steel rods. It drops in with a damped swing (±5°, decaying over 1 s).
- **`platform_lamp(x)`**:
  - a gooseneck: a bevelled curve r 0.012 in brass, from (x, 0.90, 1.80) up to Z 3.45 and over to (x, −0.05, 3.25);
  - an open cone shade (r 0.16 bottom, 0.05 top, 0.20 tall), teal-deep outside and cream inside;
  - a bulb (sphere r 0.035);
  - a point light.

---

## 5. Objects

### 5.1 ORDERS press (the producer), faces −Y. Never moves, never changes after the whip at 22.8
- **Body**: a teal box with charcoal plinth, X −7.10…−5.60, Y −0.25…0.95, Z 0.12…2.62. On top, a crown 1.30 × 1.00 ×
  0.14 and a sloped console wedge at the front.
- **PLACE ORDER button** at (−6.35, −0.05, 2.86):
  - yellow dome r 0.10 (a cylinder plus a squashed sphere cap, roughness 0.35);
  - brass bezel (torus 0.13 / 0.018);
  - a cream tab "PLACE ORDER" (cap 0.035) in front of it.
  - Press: anticipation +3 mm, then down 2 cm in 2 frames, back up in 6.
- **Front face** (Y −0.25), top to bottom:
  - nameplate 1.10 × 0.30 at Z 2.30: "**ORDERS**" (cap 0.14) with "*order service*" (cap 0.05);
  - status `lamp()` (r 0.045) at x −5.78;
  - "ASKED" label above a `wheels(4, 0.09)` counter with a brass comma plate, housing 0.62 × 0.20 at Z 1.85;
  - **CALL LIST** board 0.80 × 0.55 at Z 0.70–1.25: a cream enamel header "CALL LIST" and 4 brass hooks in 2 rows.
    Tags are 0.32 × 0.09, cream with ink text (cap 0.05).
  - **Service hatch** 0.40 × 0.30 to the right of the board. Its lid is hinged at the top. Inside: charcoal, with 4
    tangled cable loops.
- **Outlet**: a brass-lipped opening on the +X face at (−5.60, 0.45, 2.15). A short brass chute bridges to the
  delivery rail at X −5.20.
- **SWAMPED** `tag` (0.70 × 0.16, cap 0.10) hangs over the nameplate's lower half from 18.6 to 22.8.

### 5.2 ENQUIRY buffer beam (polling)
- A stepped teal beam at X −5.80…−5.55 that follows the tier profile.
- At each lane, a buffer head faces +X at Z tier + 0.30: a brass disc r 0.08 on a 0.10 plunger, protruding to
  x −5.43.
- **NO flap** above each buffer: cream 0.22 × 0.12, hinged at its bottom edge, flat (rotated 90°) at rest.
  - It flips upright in 3 frames when bumped, showing "NO" in vermilion (cap 0.08) to −Y.
  - It falls back after 0.4 s.
  - The ASKED counter on ORDERS adds 1 per bump.
- **Retract** in line 9: the whole beam sinks 0.8 m into the floor in 0.4 s, with the flaps folded.

### 5.3 EVENT LOG platform
- **Body**: a concrete box with an oak top slab (0.06).
- **Slot ruler**: a cream enamel band 0.20 tall on the front face at Z 1.55, the whole length. It carries ink
  `0001`…`0020` (DIN Alternate, cap 0.07) centred on each x_n, with a brass tick above each number.
- **Delivery**: a brass rail along Y +0.45 with a brass_satin **carrier** sled (0.50 × 0.10 × 0.04) holding a tablet
  upright, so the tablet spans Z 2.15–2.95. **Its top 0.35 m ("ORDER") shows above the standing row while it
  travels.**
  - Travel: up to 6 m/s with ease in/out. It stops behind the target slot.
  - **Set**: the tablet arcs to its slot over 0.30 s (−0.75 Y, −0.35 Z, ease-in). It lands with 4 mm of settle, and
    the camera gets a 2-frame jolt of 3 mm in close shots.
  - The carrier then returns in 0.6 s.
- **Sign** "EVENT LOG": a teal enamel blade 2.2 × 0.50 × 0.05 with a 0.012 cream inset line, letters cap 0.28,
  hanging on two steel rods.
  - It turns from edge-on to face −Y between 23.60 and 24.00, overshooting 3° once.

### 5.4 Cars (services), all built with `car()`

| Car | Lane | Device on the roof (tier + 0.52) | On read |
|---|---|---|---|
| **EMAIL** | D | A teal slot housing 0.30 × 0.18 × 0.08 with brass lips, plus a low brass wire out-tray at the rear | A paper envelope (0.24 × 0.14) rises 0.16 in 4 frames, pauses 3 frames, then tips back into the tray (the tray stack grows 3 mm) |
| **TRACKING** | C | A cream map panel 0.46 × 0.22 set like a lectern (tilted back 55°, so 0.13 tall, facing up toward the camera). A teal route line (3 thin boxes) joins three stop dots labelled PLACED, PACKED, SHIPPED (cap 0.025) | The yellow pin (sphere r 0.025 on a brass needle) lifts and drops onto **PLACED** (3 frames down) and the stop dot ring flashes amber |
| **REWARDS** | B | Left: a "POINTS" `wheels(4, 0.05)` in a low lectern housing (0.10 tall). Right: a brass column of star tokens (r 0.045 × 0.012, raised 5-point star), 3 tokens at the start and never more than 11 | A token pops from a roof slot, arcs 0.15 m onto the stack (+1 token), and POINTS rolls +50 |
| **ANALYTICS** | A | A cream lectern plate 0.44 × 0.22 (tilted back 55°) with an ink grid, and 6 brass_satin bars (0.045 wide) standing on it, max 0.12 tall | Bar (n mod 6) grows by 0.015–0.025 m (a fixed table, so the bars build into a rising chart) |

- **OFFLINE**: REWARDS gets a vermilion lamp and an `OFFLINE` tag (0.30 × 0.09, cap 0.06) hung on a roof hook. Its
  device is frozen.
- **ANALYTICS** arrives on a **hoist**: a steel chain (a cylinder r 0.012 from Z 6.8) with a brass_satin hook (a
  part-torus) holding a lifting eye on the car's roof. Once the car lands, the hook opens and rises out of frame.

### 5.5 Direct-call cables (line 3, phrase 2 only)
- Three charcoal cables (bevelled bezier curves, r 0.022) with brass plugs.
- Route: out of the service hatch, down to the floor, along each tier just in front of its rails, ending at the −X
  buffer of each car at the depot (x +0.6).
- They **unreel**: `bevel_factor_end` goes 0 → 1 over 0.4 s. They **reel in** 1 → 0 over 0.25 s at the 22.8 whip.

### 5.6 Station clock
Normal time is 7:42. During "All day." the hands sweep 10 hours in 1.0 s (motion blur), then settle with a tiny bounce.

### 5.7 Maker's pier
- A concrete pillar 0.70 × 0.40 × 1.70 with two **oval builder's plates** on its −Y face.
- Each plate is a cylinder scaled to a 0.62 × 0.32 ellipse, 0.025 thick, with an ink field, a brass_satin rim (torus
  scaled to the same ellipse) and 2 rivets.
  - **Upper**, centre Z 1.38: "APACHE" (Inter SemiBold, cream, cap 0.03) over "Kafka" (Instrument Serif, cream, cap
    0.09).
  - **Lower**, centre Z 0.95: "AMAZON" over "EventBridge" (cap 0.072).
- The text is raised cream lettering on the ink field (the only cream-on-ink text, to look like cast plates).

### 5.8 What is visible when

| Phase | Time | Log state | Cars | Other |
|---|---|---|---|---|
| Hook (flash-forward) | 0–7.4 | #0001–#0008 standing, #0009 lands at 2.40 | E/T/R at slot 8 → 9 | ANALYTICS hidden, lamps on, sign face-on, CALL LIST empty |
| Polling | 7.5–22.7 | Empty (tablets hidden), lamps off | Depot x +0.6, then shuttling | Sign edge-on, beam active |
| Event-driven | 22.8 onward | Fills #0001… | Start at park, slot 0 | Beam present until 49.1, then sunk |

### 5.9 Door island (X 38…42): the doorbell metaphor
- **Wall**: a concrete wall slab at Y 0 (X 38–42, Z 0–3) with a 1.00 × 2.15 opening at X 39.6–40.6.
- **Door**: teal, 0.96 × 0.05 × 2.12, in a cream frame, with a brass lever handle. It is hinged at X 39.62 and opens
  toward −Y (rotation about Z).
- **Bell** inside, at (41.05, −0.06, 1.95):
  - a teal backplate 0.22 × 0.30;
  - a brass gong (a sphere r 0.10 scaled 0.45 in Y);
  - a brass hammer arm with a ball;
  - a small cream plate "BELL" (cap 0.03).
  - Ring: the hammer strikes 3 times in 0.3 s, and the gong shivers (scale ±1.5 %, decaying).
- **Answer lamp**: a cream dome r 0.06 above the door at (40.1, −0.08, 2.45).
- **Inside**: an oak floor and a teal bench at (38.6, −1.2).
- **Outside**:
  - an oak doorstep;
  - **a yellow parcel** (0.36 × 0.28 × 0.24) tied with cream twine, with a cream tag "ORDER PLACED" (cap 0.03);
  - a low concrete garden wall;
  - a daylight backdrop plane at Y 6 (sky gradient, strength 1.5).
- **Lights**:
  - SUN-D: an area 3 × 3 outside, `#E3EEF8`, 400 W, aimed in through the door.
  - KEY-D: an area 1 × 1, `#FFDDB8`, 120 W, inside, front-left.
  - Haze cube: density 0.004.

---

## 6. Shot list

Cut points are written as **line.phrase "word"**. Every shot moves: at least a 3 % framing change, landing with an
ease-out over the first 40 % and then drifting. Focus uses a keyed empty. Aperture blades: 7. `→` means camera
position → target.

| # | Cut on (≈ s) | Camera (pos → target, lens, f-stop, move) | Action | Viewer gets |
|---|---|---|---|---|
| 01 | 0.0 "You" (0.00) | (−6.05, −1.05, 3.22) → (−6.35, −0.05, 2.86), **85 mm f/2.0**, push 4 % | The PLACE ORDER button fills about 45 % of the width; platform lamps and cool windows as bokeh. **Press on "tap" (0.35)**, with a 2-frame camera jolt | I placed an order |
| 02 | 0.1 "One" (1.57) | Follow truck: (−4.6, −2.3, 2.6) → (0.6, −2.3, 2.6), target leads the carrier at (x+0.4, 0.2, 2.45), **40 mm f/2.4** | The carrier streaks from the outlet along the row (motion blur) and **sets #0009 into slot 9 on "later" (2.40)**. It ends framed on the tablet, with ORDER PLACED readable | A fact lands in a row |
| 03 | 0.1 "email" (2.6) | (0.55, −2.05, 1.95) → (0.26, −0.85, 1.62), **50 mm f/2.0** | EMAIL hops 8 → 9 at 2.55; **envelope pops at 2.80**. Nameplate EMAIL big in the lower third; TRACKING's lectern is soft foreground at the bottom edge | Email reacted |
| 04 | 0.1 "tracking" (3.3) | (0.60, −2.60, 1.60) → (0.26, −1.45, 1.30), **50 mm f/2.0** | TRACKING hops at 3.25; **pin drops on PLACED at 3.50** | Tracking reacted |
| 05 | 0.1 "reward" (4.1) | (0.60, −3.25, 1.25) → (0.26, −2.05, 0.95), **50 mm f/2.0** | REWARDS hops at 3.95; **token stacks at 4.30**; POINTS 0400 → 0450 | Rewards reacted |
| 06 | 0.1 "all update" (4.8) | (1.5, −6.4, 2.6) → (0.1, −1.2, 1.6), **35 mm f/3.5**, pull back 0.6 m | The three cars at slot 9 stacked on their tiers, tablet #0009 above them; all three lamps settle to cream | All three at once |
| 07 | 0.2 "Nobody" (5.68) | (−4.4, −5.6, 2.9) → (−2.6, −0.6, 1.6), **32 mm f/3.2**, slow crane +0.3 m | ORDERS in the left third (plate cap ≈ 2.3 % of H) with an **empty CALL LIST**. The cars far right, never near it. Nothing moves | ORDERS called no one |
| 08 | 1.0 "The slow" (7.50) | **Whip left.** Low along the lanes: (2.6, −3.6, 1.35) → (−5.6, −1.5, 1.1), **35 mm f/2.8**, push 0.4 m | World changed in the whip: log dark and empty, sign edge-on, cars at the depot. **REWARDS launches at 8.2, TRACKING 8.5, EMAIL 8.8**, racing away from camera | They go and ask |
| 09 | 1.0 "asking" (9.4) | (−4.70, −3.50, 1.40) → (−5.60, −1.60, 1.00), **50 mm f/2.2** | Buffer heads and NO flaps. **Bumps at 10.30, 10.62 and 10.95 ("new?")**: buffer compresses 3 cm, **NO** flips up, the car reverses | Ask… "no" |
| 10 | 1.1 "Anything" (11.29) | High: (1.4, −7.8, 4.8) → (−2.3, −1.0, 1.1), **28 mm f/4**, crane up 0.4 m | All three cars shuttle, desynchronised (round trips 1.7 / 1.9 / 2.1 s); flaps flicker; ASKED climbs | Endless trips |
| 11 | 1.1 "All day" (12.2) | (−2.0, 4.6, 4.3) → (−2.0, 6.85, 4.3), **50 mm f/2.8**, 5 % push | **Clock hands spin 10 h in 1.0 s.** Cool window bokeh around the dial | All day long |
| 12 | 2.0 "Spot" (13.11) | Smash cut. Orbit 25° around the EMAIL car frozen at the buffer: (−4.4, −2.3, 1.75) → (−5.40, −0.85, 1.35), **35 mm f/2.8**, 2° dutch | **Freeze.** Every machine holds mid-action (EMAIL buffer compressed, NO half-raised, REWARDS mid-trip, wheels blurred). All hall lights at 35 % within 3 frames; RIM and BACK stay. Restore at 14.95 | Pause and think (bullet-time, not reel 18's spotlight) |
| 13 | 3.0 "Almost" (14.96) | (−5.20, −3.10, 1.55) → (−5.62, −1.45, 1.18), **65 mm f/2.2** | The three NO flaps (at Z 0.84, 1.18, 1.52) fill the frame. They flip on 15.4 and 15.9, and **all three are up on "no" (16.3)** | The answer is always no |
| 14 | 3.1 "Thousands" (16.85) | Starts on ASKED: (−6.10, −1.30, 1.90) → (−6.35, −0.25, 1.85), **65 mm f/2.0**. Pulls back to (−5.0, −2.9, 2.1) → (−6.35, −0.25, 1.95) from 18.2 | **ASKED spins 0,013 → 4,812 (baked, 16.9–18.1).** On "drowns" (18.9): ORDERS shudders (±4 mm at 9 Hz), lamp vermilion, **SWAMPED drops at 18.6** | Waste, and the producer suffers |
| 15 | 3.2 "Calling" (19.69) | Hard cut, high along the cables: (−6.9, −3.9, 2.9) → (−1.8, −1.4, 0.9), **32 mm f/3.2**, drift right | Cars parked at the depot. **The three cables unreel from ORDERS to each car (19.75–20.15)** | Direct calls wire it to everyone |
| 16 | 3.2 "know" (21.3) | (−6.05, −1.55, 1.15) → (−6.30, −0.26, 0.97), **65 mm f/2.2** | CALL LIST shows EMAIL, TRACKING, REWARDS. **A 4th tag "ANALYTICS" lowers onto the last hook (21.45)**; the hatch lid pops open (21.75) showing the tangle; lamp vermilion | Every new service means changing ORDERS |
| 17 | 4.0 "The fix" (22.78) | **Whip right** into SYS: (1.0, −8.4, 3.4) → (0.6, −0.4, 2.0), **30 mm f/4**, crane down 0.3 m | In the whip: cables reel in, tags fly up, hatch shuts, SWAMPED gone, ASKED reset, cars to park. **"Event-driven" (23.45–24.05): the 10 platform lamps ignite left → right; the EVENT LOG sign turns face-on (23.6–24.0)** | Something new switches on |
| 18 | 4.1 "The order" (24.35) | (−5.55, −1.80, 3.20) → (−5.95, 0.20, 2.50), **50 mm f/2.4**, pan right toward the outlet | **Press on "just" (24.9)**; #0001 slides out of the outlet at 25.3 onto the carrier | ORDERS just announces |
| 19 | 4.1 "order placed" (26.3) | (−4.40, −1.45, 2.30) → (−4.70, −0.30, 2.15), **50 mm f/2.0**, rack focus from the tablet to the ruler and back | **#0001 sets into slot 1 on "placed" (26.8)**; ruler `0001` under it. The face fills 40 % of H | The event, as an object |
| 20 | 5.0 "That's" (27.76) | Low hero: (−4.25, −1.05, 1.80) → (−4.70, −0.30, 2.30), **35 mm f/2.0**, crane up 0.15 m | The tablet towers, lit by its lamp; EVENT LOG sign in soft focus above. Nothing moves except a haze drift | This is an event |
| 21 | 5.0 "A log" (28.7) | Track +X: (−4.9 → −3.0, −2.6, 2.55) → (x + 0.3, −0.3, 2.15), **40 mm f/2.8** | **#0002 lands at 29.3, #0003 at 30.1 ("order")**; the ruler reads 0001 · 0002 · 0003 | Kept, in order |
| 22 | 5.1 "Email" (30.91) | Straight on: (−4.0, −6.4, 2.2) → (−4.0, −1.2, 1.45), **50 mm f/4** (W ≈ 2.1 m: slots 1–3; the park position is just off the left edge) | All three start at park, roll into frame on their first hop, and react **on their own rhythm**: EMAIL hops 31.0 / 31.35 / 31.7; TRACKING 31.5 / 32.0 / 32.5; REWARDS 32.0 / 32.35 / 32.7 (with envelopes, pins, tokens). Riser names readable | Independent reactions |
| 23 | 6.0 "Like" (34.00) | **Whip** to the door island: (40.95, −1.55, 2.05) → (40.85, −0.06, 1.95), **65 mm f/2.2** | The bell and the door edge in warm interior light | A doorbell |
| 24 | 6.0 "You don't" (34.9) | (39.7, −3.0, 1.35) → (40.0, 0.0, 1.15), **35 mm f/2.8**, slow push | **The door opens 20° on its own at 35.3 (empty step, cool light), closes 35.8, opens 36.2, closes 36.6** | Checking is pointless |
| 25 | 6.1 "It rings" (37.16) | Starts on the bell: (40.75, −1.6, 2.0) → (41.0, −0.06, 1.95), **50 mm f/2.4**. **Whip-pans left** to the door on "answer" (37.85) | **Hammer strikes on "rings" (37.35)**, answer lamp on; **the door swings wide at 37.9–38.3** onto the yellow parcel tagged ORDER PLACED | It rings, you answer |
| 26 | 7.0 "Rewards" (38.98) | **Whip back.** Low: (−3.10, −3.95, 1.30) → (−3.46, −2.05, 0.95), **50 mm f/2.0** | REWARDS dark at slot 3: **vermilion lamp, OFFLINE tag**. EMAIL and TRACKING sit soft at slot 8 upper right; tablets #0004–#0008 stand between | One service was down |
| 27 | 7.0 "reads" (40.3) | Track with REWARDS: (x − 0.3, −4.4, 1.55) → (x + 0.6, −1.6, 1.40), x −3.46 → −0.36, **40 mm f/2.8** | 40.40 the tag lifts off and the lamp goes amber. **Hops slots 4–8 at 40.6, 40.85, 41.1, 41.35 and 41.6, a token each; POINTS 0150 → 0400.** Arrives beside the others on "up" (41.95) | It caught up from the log |
| 28 | 7.1 "New" (42.46) | (−4.55, −4.70, 1.35) → (−5.10, −2.65, 0.60), **40 mm f/2.4**, tilt down with the hoist | **ANALYTICS lowers onto lane A at park and lands at 43.10** with a 1.5 cm bounce; the hook releases; lamp cream | A new service plugs in |
| 29 | 7.1 "replays" (43.3) | **Fast parallel track** (whip-speed, shutter 1.0): (x, −5.6, 1.10) → (x + 0.4, −1.5, 1.50), x −5.0 → −0.4, **35 mm f/2.8** | **ANALYTICS replays slots 1–8 in 1.05 s (43.35–44.40)**, a bar growing each hop; tablets streak behind. It lands in line with the others | It read all of history |
| 30 | 8.0 "The order" (44.91) | Near-static: (−5.55, −2.35, 1.95) → (−6.35, −0.25, 1.70), **50 mm f/2.4**, 2 % push | ORDERS untouched: the same plate, an **empty CALL LIST**, lamp cream. Nothing on it moves | The producer never changed |
| 31 | 8.0 "doesn't" (46.8) | Over ORDERS' shoulder: (−7.35, −2.45, 2.85) → (−0.6, −1.6, 1.50), **32 mm f/3.2**. ORDERS is the soft foreground left | Press at 46.85; **#0009 lands at 47.30**; cars hop to slot 9 in loose order: EMAIL 47.45, ANALYTICS 47.6, TRACKING 47.8, REWARDS 48.0 | It doesn't know who's listening |
| 32 | 9.0 "Stop" (48.95) | (−4.85, −3.60, 1.25) → (−5.65, −1.70, 0.75), **40 mm f/2.8** | **The ENQUIRY beam sinks into the floor (49.10–49.50)**, NO flaps folded | No more asking |
| 33 | 9.0 "Start" (49.6) | SYS hero: (2.6, −8.4, 5.0) → (−0.2, −0.8, 1.6), **28 mm f/4**, crane down 0.3 m | **#0010 lands at 49.85**; four cars hop to slot 10 one after another (50.0–50.4) | Reacting |
| 34 | 10.0 "That's" (50.77) | **Whip right** to the pier: (8.05, −2.95, 1.50) → (8.40, −1.62, 1.38), **65 mm f/2.0**; tilt down to target Z 0.95 at "Amazon" (52.0), with rack focus | **APACHE / Kafka** readable, then **AMAZON / EventBridge**. Background: lit tablet row and lamp bokeh | Real tools |
| 35 | 11.0 CTA (53.54–end) | Calm orbit: (−2.6, −8.6, 4.8) → (−1.4, −8.9, 5.1), target (0.4, −0.8, 1.7), **32 mm f/3.5**. Exposure → −0.3 EV by 54.2 | **One event every 3.0 s from 54.2** (#0011…); cars react with gentle staggers; lamps steady | Calm, alive, not busy |

### 6.1 Event and state timeline
- **Tablets**:
  - hook: #0001–#0008 visible, #0009 lands at 2.40;
  - all hidden in the 7.50 whip;
  - #0001 26.8, #0002 29.3, #0003 30.1;
  - **#0004–#0008 land off-camera at 34.4, 35.2, 36.0, 36.8 and 37.6** (door island on screen);
  - #0009 47.30, #0010 49.85, then CTA every 3.0 s.
- **Car slots**:
  - hook: slot 8 → 9;
  - polling: depot x +0.6 and shuttles, all parked at the depot from 19.6;
  - 22.8: park (slot 0);
  - shot 22: → 3;
  - EMAIL and TRACKING → 8 off-camera during 34.5–37.8;
  - **REWARDS stays at 3, offline 34.2–40.4**, then → 8 by 41.95;
  - ANALYTICS hidden until 42.5, slot 0 at 43.10, → 8 by 44.40;
  - all → 9 at 47.45–48.0, → 10 at 50.0–50.4.
- **POINTS**: 0000 → 0150 in shot 22, 0150 → 0400 in shot 27, 0450 at 48.0. The hook shows 0400 → 0450.
- **ASKED**: 0000 at 7.5, +1 per bump, baked 0,013 → 4,812 from 16.9 to 18.1, hold, reset at 22.8 (off-camera).
- **ORDERS lamp**: cream; amber pulses during polling bumps; vermilion 17.0–22.8; cream after.
- **Sign** edge-on 7.5–23.6. **Platform lamps** off 7.5–23.45.
- **Beam** active until 49.10.
- **Freeze**: 13.11–14.95. Every animation curve has a hold here. Build the shuttle curves with this hold in them.

### 6.2 Transitions and motion rules
- **Whips** at 7.50, 22.78, 34.00, 38.98 and 50.77, plus the in-shot whip in 25:
  - the last 4 frames out yaw +20°, the first 4 frames in start at −20°, shutter 1.0;
  - the direction follows geography (left to ORDERS or the polling, right to the log or pier, a long right to the
    door island and a long left back).
  - **State changes** (hide tablets, teleport cars, reset counters) happen **only on whip frames**.
- **Everything else** is a hard cut on the keyword.
- **Mechanical feel**:
  - 2-frame anticipation, 2–4-frame actions, one damped overshoot ≤ 5 %.
  - Lamps flicker once when they ignite. Nothing bobs idly.
- **Independence is the motion signature**: the cars never move on the same frame (except at the frozen 12).
- **Camera height**:
  - close shots at device height (0.8–1.6 m);
  - the system shots (06, 10, 17, 33, 35) at 3–4.6 m;
  - when two tiers share a frame, keep the camera at least 0.5 m above the highest plate it must read, or the front
    car hides the plate behind it.
- **Aperture**: f/2–2.8 for closes, f/3.2–4 for wides.

---

## 7. Pitfalls

1. **Orange creep** (reel 18's first pass):
   - keep KEY at 4300 K or cooler; the skylights and BACK are the cool counterweight;
   - World `#2B2F33`; haze cool-neutral;
   - check a lit cream plate (R − B ≤ 0.08). If the frame warms up, cut LAMP energy before touching anything else.
2. **Yellow clipping**: tablets at roughness 0.45 with no emission, peaking ≤ 0.85 under AgX. If they clip, lower LAMP,
   not the base colour.
3. **Teal turning green**: watch the hue under warm lamps (keep it ≥ 186°). Never "fix" the teal with coloured light.
4. **Tier occlusion**: test shot 06 and shot 22 first. Keep devices at rest ≤ 0.14 m. If two plates overlap, raise
   the camera rather than spreading the lanes.
5. **Reel 18 look-alikes**: no cobalt, no drums in window housings, no bulb borders, no theatrical spot, no sepia, no
   synchronized stamping.
6. **Polling chaos**: only 3 cars, clean lanes, heavy blur. The NO flaps must read in shot 09 or the joke is lost.
7. **Text load**: about 20 tablets × 6 strings. Share one linked text mesh, keep only `#00nn` unique, convert to mesh.
   Never use Bfont. Keep text 0.8 mm proud of its surface.
8. **Continuity cheat**: the hook is a flash-forward of #0009 with ANALYTICS hidden. Nothing else may contradict the
   timeline.
9. **Door island**: no people, no hands, no shadows of people. The door moves by itself. It is a metaphor, and the
   caption carries it.
10. **Readability**: obey the 2.2 % cap rule. Car names must be legible in 03–05, 22 and 26–29; tablets in 02, 19–21.
    Keep tall things right of centre (the HUD is on the left).
11. **Haze**: hall density ≤ 0.009. Lamp `volume_factor` stays 0.25, or the shades become fog balls.
12. **Light leaks**: the hall is closed and every light has a cutoff. The door island sits 30 m away with its own cube.

### Caption and HUD harmonisation (2D)
- HUD kicker pill: teal `#1F5F66` with cream `#F3EDE0` text.
- Caption keywords: signal yellow `#F2C14E`.
- Problem pills (anything new, no, drowns, know everyone, down): vermilion `#C8432C` with white text.
- Other pills: cream with ink text.

## 8. Build order (one night)

1. Shell, tiers, tracks, platform, haze, lights, plus AgX check stills (cream neutrality, yellow peak, teal hue).
2. Kit: `plate`, `lamp`, `wheels` (port the decagon wheel from reel 18's kit), `tablet`, `car`, `tag`,
   `platform_lamp`.
3. ORDERS, buffer beam, carrier and set animation.
4. The four cars and devices. The hop as one function: `hop(car, slot, t)`.
5. The event schedule as data:
   - `EVENTS = [(n, t_land)]`;
   - `READS = [(car, slot, t)]`;
   - the shuttle schedule with the freeze hold baked in.
   Generate every keyframe from these tables.
6. Cables, CALL LIST tags, SWAMPED and OFFLINE tags, hoist.
7. Door island, then the maker's pier.
8. Cameras from the §6 table (a list of dicts → camera keys, focus empties, whips).

Check stills before the full render: 0.4, 2.4, 4.3, 5.9, 9.0, 10.7, 13.8, 16.3, 18.9, 21.8, 23.9, 26.9, 28.0, 30.2, 32.6,
35.4, 38.1, 39.5, 41.9, 43.2, 44.3, 47.5, 49.3, 51.2, 52.3 and 57.0.
