# Ep 5 shot plan: The bullet train that copied a bird
About 29 s spoken in total (92 words at the fast pace). Durations are approximate and get re-timed to the TTS word timings. Vertical 9:16. No people, no characters. No fluid sims.

## Look
- Premium studio-product-film look, like ep 3. Golden-hour sun low and warm from frame left, soft volumetric haze (a volume scatter cube with low density), filmic/AgX high contrast, shallow DOF on close-ups, subtle motion blur. No low-poly scenery.
- **Two trains, one hero.** (A) "Old blunt nose": a generic 0-Series-like rounded snub nose. Ivory/white body with a blue band, no logos. (B) The 500 Series hero: a long 15 m nose that is nearly round in cross-section, ending in a needle-like tip, with a bubble canopy cockpit set far back. Metallic blue-grey body, a dark blue window band, a thin white pinstripe and a slight clearcoat. Both are built from one sweep-along-curve or Geometry Nodes body with a profile curve and swappable nose profiles, so the morph in line 7 is a shape key or a lerp between two nose profile curves.
- **Countryside.** Noise-displaced terrain with rice-terrace steps (stepped noise in Geometry Nodes), instanced cedar/pine trees, and a mountain ridge with a concrete tunnel portal (a bevelled arch with a hood). Slab track on a low viaduct, with catenary masts instanced along the curve.
- **X-ray mode.** The tunnel turns to dark glass/wireframe with a faint cyan Fresnel edge. Air is drawn as thin translucent rings instanced every ~0.5 m along the tunnel. Each ring's emission and scale are driven by a pressure value (a 1D wave function of distance from the nose, animated in Geometry Nodes): compressed rings bunch together and glow amber to red, and calm air stays faint cyan. The wavefront is a bright, thin, sharp band (steep = blunt nose) or a wide soft gradient (gentle = beak nose).
- **Shock ring.** At the tunnel exit, an expanding emissive torus plus a ripple displacement on a haze card. A quick scale-up from 0 to 6x and fade over 10 frames, with a slight camera shake.
- **Kingfisher beak.** A stylised beak only, no bird: two tapered, slightly curved mandibles (a lofted curve profile), polished dark gunmetal with an iridescent teal-to-orange thin-film sheen. Water is an Ocean-modifier plane or a displaced plane with an animated radial ripple texture. No fluid sim.
- Payoff numbers and the "300 km/h" tag are on-screen overlays added in post (labels.json/overlay.py as in ep 3), not 3D text. The hook stays spoken only, with no text hook.
- Palette: warm gold/amber for the world and for pressure "danger", cool cyan/teal for x-ray and calm air. The kingfisher sheen bridges the two.

## Shots

### L1 (~3.8 s) "Four hundred metres from a tunnel, homes heard Japan's bullet train boom."
- 1a (1.6 s): Wide aerial at golden hour over terraced countryside. Train A streaks along the viaduct toward a mountain tunnel portal. Camera: slow drone push-in with a slight descent, long lens, haze layers.
- 1b (1.2 s): Low angle near the track as Train A blasts past toward the portal. Camera: fast lateral track that whips with the nose and ends framing the dark portal.
- 1c (1.0 s): Far side of the mountain, the exit portal, with a few small distant house shapes (simple gable blocks, warm windows) in the foreground valley. A dust/haze puff and a quick shock ring burst from the exit (a preview of the boom). Camera: locked-off with a small shake on the burst.

### L2 (~2.9 s) "Its blunt nose squeezed the air inside the tunnel."
- 2a (1.4 s): The tunnel dissolves to x-ray. Side cutaway as Train A's blunt nose enters the tunnel, and the rings ahead of it bunch up and turn amber. Camera: tracking side-on, matching speed.
- 2b (1.5 s): Close-up on the blunt nose face with rings compressing hard against it, glowing red. Camera: slow push-in toward the nose, shallow DOF.

### L3 (~2.8 s) "That squeeze raced ahead at the speed of sound"
- 3a (1.4 s): A thin, sharp, bright wavefront detaches from the nose and runs away down the tunnel, outpacing the train. Camera: whip-pan to follow the wavefront, leaving the train behind.
- 3b (1.4 s): The camera rides just ahead of the wavefront looking back as the band steepens (narrows and brightens). Camera: fast backward dolly down the tunnel axis.

### L4 (~2.0 s) "and burst from the exit. Boom."
- 4a (0.9 s): Inside the tunnel looking out at the bright daylight exit as the wavefront hits the portal. Camera: rushes toward the exit.
- 4b (1.1 s): Outside, at a 3/4 view of the portal, a bright shock ring blasts out, haze ripples and the treeline sways (a wind modifier on the tree instances). Camera: hard shake on "Boom", then settle. Cut exactly on "Boom".

### L5 (~2.9 s) "Engineer Eiji Nakatsu, a birdwatcher, thought of the kingfisher,"
- 5a (1.5 s): A calm change of pace. A riverbank at golden hour, still water, reeds (instanced curves), and a bare branch over the water. Camera: slow push along the water surface.
- 5b (1.4 s): The stylised beak form appears high above the water, catching the sun with its iridescent sheen. Camera: slow orbit around the beak, macro DOF.

### L6 (~3.2 s) "which dives from air into water with barely a splash."
- 6a (1.4 s): The beak plunges, tip first, toward the water. Camera: tilts down with the dive, then holds at water level.
- 6b (1.8 s): Slow motion (0.25x) as the tip pierces the surface with only a tiny, clean radial ripple and almost no spray. Camera: low, at water level, side-on. Optional split second: an x-ray overlay shows smooth flow lines parting around the beak.

### L7 (~3.8 s) "So the five hundred Series got a fifteen-metre beak for a nose."
- 7a (1.6 s): Studio void with a dark gradient backdrop and a rim light. The beak rotates to horizontal and morphs/scales into the 15 m nose profile of Train B (shape key between the two profile curves). Camera: slow orbit, product-film style.
- 7b (1.2 s): The body extrudes back from the nose to reveal the full 500 Series leading car. Camera: a long dolly along the side from the tip to the cockpit canopy. The "15 m" dimension line is drawn on in post.
- 7c (1.0 s): Back in the golden-hour world, Train B rockets toward the same tunnel portal. Camera: low front 3/4, the nose filling the frame, then rushing past. Optional "300 km/h" tag in post.

### L8 (~2.9 s) "Now the air is squeezed gently. The boom fades."
- 8a (1.5 s): X-ray tunnel again, same framing as 2a. Train B's long nose eases the rings apart gradually, with a wide soft cyan-to-amber gradient and no sharp band. Camera: matching side track (a deliberate visual rhyme with 2a).
- 8b (1.4 s): Exit portal, same framing as 4b. Only a faint, soft ring that dissolves before it grows. The haze barely moves, and the houses in the valley sit quiet. Camera: gentle, no shake.

### L9 (~2.6 s) "Ten percent faster, on fifteen percent less power."
- 9a (1.3 s): Train B bursts out of the portal into the golden light, with a motion blur streak. Camera: whip-follow along the viaduct. Overlay "+10% speed".
- 9b (1.3 s): Close-up on the pantograph and catenary with a small warm spark glint, then pulling off. Overlay "-15% power".

### L10 (~2.5 s) "Follow for how the world is really engineered."
- 10a (2.5 s): A big pull-back and rise. Train B threads through the terraced valley toward the next mountain as the sun flares. Camera: a crane-up aerial pull-out to a wide establishing frame (bookending 1a). Hold for the end card/handle in post.
