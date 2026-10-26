You are the head writer and director for @letsbuildsimply, a new Instagram account making "How a X becomes a Y" 3D Blender explainer reels (vertical, about 85–95 s, Gemini TTS voice "Puck").

The two viral references we copy the format from were teardown-analysed. Here are the notes:
---
# What the reference reels teach us

The references are in `refs/`. Argon's full teardowns are in `study/ref1_argon.md` (plank to bridge) and `study/ref2_argon.md` (hole to nuclear bunker). Both reels are about 98 s long, 720x1280 at 30 fps, and made as 3D Blender cutaways.

## The formula
1. **Second 1 is the dumbest version, already moving.** "If you throw a plank across a river… congratulations, you've built a bridge." There's no title card and no intro. It fails by second 6.
2. **6 to 8 "But → So" loops of about 11 to 15 s each.** Nearly every sentence starts with "But" or "So". Each fix causes or exposes the next problem.
3. **Name the part last.** The reel shows the mechanism in plain words first, then names it: "This is a blast valve." There are 3 to 5 real terms per reel, and the name pops up as a yellow all-caps label or a glowing outline on the object.
4. **Every failure is big, physical and funny.** Examples: the plank snaps, a flood carries the bridge into grandma's house, a truck hits the door, the steel bends "like a depressed banana".
5. **Invisible forces get colors.** Radiation is green, fresh air blue, stale air orange, and a pressure wave is a white orb. Load is shown as arrows.
6. **One everyday "aha".** For example: "That bump when you drive onto a bridge is the expansion joint."
7. **Numbers are concrete and in everyday units:** 3 ft of dirt, 3.5 in halves the radiation, 10x weaker after 7 h.
8. **The ending calls back to the opening line.** "Congratulations, you've built a bridge" comes back, followed by a scope-creep line: "you started with one plank… now you've spent $6,000,000."

## Writing
- Sentences are 8 to 12 words with no sub-clauses. The pace is 2.4 to 2.8 words/s, which is calm delivery packed with ideas.
- The humor is deadpan, with an everyday comparison about every 20 s (wet biscuit, cheap camping chair).

## Visuals and sound
- One fixed, front-on cutaway camera on a single build that keeps growing, with dirt and water in the bottom third and the surface above it for scale. There are only 2 to 3 zooms or pans, and no hard cuts.
- Captions show one word at a time, centered just above the action, in white bold text with a black outline.
- Sound effects land on every action (thud, crack, splash, clank), with a quiet music bed under them.

## Where we can beat them
- Better lighting: soft shadows and ambient occlusion, plus clean geometry with no clipping and a fixed character scale.
- Make failures actually happen on screen: real collapses, and load arrows that travel to the supports.
- A seamless loop: the last line flows back into the first frame, with no fade to black.
- A labeled "blueprint" freeze on the final wide shot, so people save the reel.
- **Our rule: no mascot.** The bridge reel relies on "Kevin". We use "you" plus anonymous background people.

---

We are remaking the fridge episode. Three earlier attempts:

A) The OLD posted Ep 01 script. The creator calls it "okish". It had a weak hook and too many cuts:
1. This is a block of ice. It keeps your food cold.
2. But it melts all over your kitchen floor.
3. So you put it in a wooden box, lined with tin, with a tray to catch the water.
4. This is an icebox.
5. But every few days the ice is gone, and the iceman has to bring you more.
6. So you swap the ice for a liquid that boils at minus twenty-six degrees.
7. You run it through thin pipes inside the box. As it boils, it soaks up the heat from your food.
8. But now the pipes are full of warm gas.
9. So you add a compressor, that squeezes the gas until it's hotter than your kitchen.
10. It flows through coils on the back and dumps that heat into the room. That's why the back of your fridge is warm.
11. Now it's a liquid again. It squeezes through a tube thinner than spaghetti, the pressure drops, and it's freezing cold again.
12. But the compressor never stops, and your milk turns to ice.
13. So you add a thermostat, that switches it off when it's cold enough.
14. But cold air leaks out around the door.
15. So you add a rubber seal with a magnet inside.
16. But frost builds up on the cold pipes.
17. So a little heater melts it, and the water drips into a tray on the hot compressor, where it dries up.
18. Add some shelves, and a light that turns on when you open the door.
19. Congratulations. You have built a refrigerator.

B) v2, which we rendered. Its script is fine, but the creator rejected the video: FIXED CAMERA, no interactivity, it felt passive.
1. Put a block of ice in a wooden box. Congratulations, you've built a fridge.
2. But by tomorrow, the ice is a puddle, and your milk is cottage cheese.
3. You need something colder than ice, that never runs out.
4. So you run a pipe inside, filled with a liquid that boils below freezing.
5. As it boils, it sucks the heat out of your milk. This is the evaporator.
6. But once that liquid boils into gas, it just floats away.
7. So you catch the gas and squeeze it with a pump. This is the compressor.
8. But squeezing gas makes it hot, just like a bicycle pump.
9. So you snake that hot pipe down the back. It cools, and turns back into liquid. This is the condenser.
10. That's why the back of your fridge feels warm.
11. But that liquid is still warm, and squeezed too tight to boil.
12. So you push it through a tube thinner than spaghetti. This is the capillary tube.
13. Like a spray can, the pressure drops, and it goes freezing cold.
14. But now the loop never stops, and your milk freezes solid.
15. So a sensor switches the pump off just above freezing. This is the thermostat.
16. That's the hum that randomly stops and starts.
17. But every time you open the door, wet air freezes onto the pipes, and the cooling stops.
18. So a little heater melts it, and the water drips onto the hot pump and dries up.
19. Here's the twist. It never made cold. It just moves heat from your milk into your kitchen.
20. Wrap it all in foam and steel. Congratulations, you've built a fridge. Or, you could just...

C) v3, an interactive draft with a camera plan. The creator wants it to stay simple like the original but be better:
# How a block of ice becomes a fridge, v3 (interactive)

The structure is the simple build-up of the reference reels: start with the dumbest possible fridge, then fix one problem at a time. Each beat has its own camera move, and the narrator talks to the viewer.

| # | Voice | Camera | On screen / SFX |
|---|---|---|---|
| 1 | Put a block of ice in a wooden box. Congratulations, you've built a fridge. | Top-down crane following the ice block as it drops into the box; the lid slams toward camera. | Shake on the slam. Thud, ding. |
| 2 | But by tomorrow, the ice is a puddle, and your milk is cottage cheese. | Time-lapse orbit around the box: the clock spins and sunlight sweeps across. Snap zoom to the lumpy milk; the cap pops at the lens. | Ticks, drips, pop, green stink |
| 3 | You need cold that never runs out. Quick: lick your finger and blow on it. | Push in to a single water drop on the shelf. | "TRY IT 👆" |
| 4 | Feel that? Evaporating liquid steals heat. | Macro: the drop shrinks as orange heat dots leave with the vapor. | Soft hiss |
| 5 | So you run a pipe through the box, full of a liquid that boils below freezing. | Tracking shot riding along the coil as it grows. | Metal clinks |
| 6 | As it boils, it sucks the heat out of your milk. This is the evaporator. | X-ray close-up inside the pipe: bubbles form while orange heat dots stream in from the milk. | Bubbling. Label: EVAPORATOR |
| 7 | But once it boils into gas, it just floats away. | Follow one puff of gas out of the pipe end into the room. | Hiss |
| 8 | So you catch the gas and squeeze it with a pump. This is the compressor. | Whip down to the bottom back as the compressor slams in. | Shake, clunk, hum starts. Label: COMPRESSOR |
| 9 | But squeezing gas makes it scorching hot. | Close-up: the pipe leaving the pump glows red. | Sizzle |
| 10 | So you snake that hot pipe up the back, and the heat escapes into your kitchen. This is the condenser. | Crane up the back as the zigzag grows, with heat shimmer rising past the lens. | Label: CONDENSER |
| 11 | Ever noticed the sides of your fridge feel warm? That's this, hidden in the walls. | Slow orbit around the warm coil; it slides into a side-wall panel. | 👀 |
| 12 | But that liquid is still warm, and squeezed too tight to boil. | Close-up: the pipe end bulges and shudders. | Creak |
| 13 | So you push it through a tube thinner than spaghetti. This is the capillary tube. | POV ride with one drop into the capillary: a tunnel rush with speed lines. A spaghetti strand pops in for scale. | Rising whoosh. Label: CAPILLARY TUBE |
| 14 | Like a spray can, the pressure drops, and it goes freezing cold again. | We burst out into the coil; the drop explodes into icy blue mist. Pull back as the whole loop lights up. | Spray hiss, sparkle |
| 15 | But now the loop never stops, and your milk freezes solid. | Snap zoom to the milk: it frosts over and the cap rises on a column of ice. | Crackle, pop |
| 16 | So a sensor switches the pump off just above freezing. This is the thermostat. | Push in on the dial as it clicks. | Click. Label: THERMOSTAT |
| 17 | That's the hum you hear stop at night… and start again. | The lights go night-blue and the hum cuts to silence for one beat, then the camera jolts as it restarts. | Silence, then hum |
| 18 | But every time you open the door, wet air freezes onto the pipes, and the cooling stops. | POV from inside the fridge looking out as the door swings open; frost grows across the coil. | Door creak, frost crackle |
| 19 | So a little heater melts it, and the water drips into a tray and dries up. | Follow one drop down the drain into the tray above the pump, where it steams away. | Drips, steam |
| 20 | Here's the twist. It never made cold. It just moves heat from your milk into your kitchen. | One continuous ride with a single heat orb: from the milk, around the whole loop, out of the coil into the room. | Riser, music drops out |
| 21 | Wrap it all in foam and steel. Congratulations, you've built a fridge. Or, you could just… | Hero orbit as the walls close into a white fridge; all 5 labels hold. On "just…", an ice block drops onto the top, which loops back to beat 1. | Clang, ding, thud. Text: "Which part was new to you? 👇" |

The voice is about 270 words, roughly 88 s at Puck's pace. There is no mascot; "you" is the builder.


The creator's direction:
- Start from the simple idea, like the original (a block of ice), but give it the BEST possible hook in the first 1–2 seconds.
- Make it very interactive: a camera that moves with intent on every beat, plus moments that talk to the viewer. It must not be forced or cringe.
- Make it professional grade: the best script and the best scenes.

Hard constraints:
- No mascot and no named character. "You" is the builder. Generic hands or silhouettes are OK only if essential, but avoid them.
- Everything must be animatable procedurally in Blender. A single kitchen set is fine, and the camera can go anywhere (macro, inside the pipe, POV from inside the fridge, orbits).
- 100% factually correct. Avoid unit confusion (no "minus twenty-six" without units).
- 235–265 spoken words. Short sentences. "But… / So…" engine. Name each part AFTER showing it ("This is the ___"). Use 4–5 labels at most.
- The ending must call back to the opening and loop.

Deliver:
1. **8 hook options** for the first 2 seconds (spoken line + what we see), ranked, with one line each on why it stops the scroll. The hook must still lead naturally into the simple ice-in-a-box start.
2. **The final script.** Use your best hook. Number the lines and give the word count.
3. **The scene plan** for every line: what we see, the camera move (be specific: start/end framing, speed, whip/push/orbit/POV), on-screen text, and SFX. Mark the 3 "wow" shots.
4. **Retention notes**: where the re-hooks are (about every 8–12 s), and how the last line loops into the first frame.
5. **Fact sheet**: each technical claim with its correct value.
