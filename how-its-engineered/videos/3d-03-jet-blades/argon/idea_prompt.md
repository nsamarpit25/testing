You are the head writer and director for the Instagram channel @how.its.engineered ("How It's Engineered"), which covers all engineering, software and physical.

This is episode 3 of our fully 3D animated reel series (ep 1: Taipei 101's tuned mass damper; ep 2: Kingda Ka's magnetic brakes). Topic is FIXED:

**"Jet engine turbine blades that run hotter than their melting point."**

The owner's feedback on ep 2: "still not very premium" and "slow". A reviewer blamed low-poly cone trees and grey boxes, a boxy faceted train, and wide outdoor shots that looked like a blockout. Ep 3 must be the most premium video on the channel: a high-end PRODUCT FILM (think Rolls-Royce, GE Aerospace or Apple commercial). One hero object in a dark studio, no outdoor world, no scenery. Smooth bevelled, subdivided geometry; real materials (polished and brushed nickel superalloy, matte off-white ceramic coating, anodised titanium disc); soft area lights plus coloured rim lights; a gradient backdrop with a glossy floor reflection; shallow depth of field, macro lenses; slow precise camera moves (orbit, push-in, rack focus) cut fast with a few hard match cuts. Heat is shown as a thermal colour ramp, glowing flow ribbons or heat haze; cooling air is a second accent colour. No fluid or fire simulations.

HARD PRODUCTION CONSTRAINTS (Blender, procedural geometry from a Python script, Eevee):
- No humans, hands, faces, characters. The engine and the blade are the stars.
- Buildable procedurally: engine nacelle/casing (lathe profiles), fan, a bladed turbine disc (arrayed airfoils), a single blade with fir-tree root, platform, airfoil, internal serpentine channels, rows of film-cooling holes, a ceramic coating layer that can peel off, grain structures (Voronoi crystals vs one smooth crystal), flow ribbons (curves), particles.
- About 30 seconds of narration, 85-95 spoken words total, dense and punchy (narration will be sped up to ~1.3x).
- 8-10 narration lines. Cuts every 1-2 seconds, so give 2-3 shots per line where useful.
- Cold-open spoken hook in line 1 (no on-screen text hook). It must create a "wait, what?" moment for someone who has never seen the channel.
- Story beats that MUST appear: (a) the whole engine and the spinning turbine disc, (b) one blade lifting out into the studio, (c) the gas is hotter than the metal's melting point (thermal view), (d) many grains vs one single crystal (why: grain boundaries are weak points that creep/crack at high temperature), (e) x-ray of the internal serpentine cooling channels, (f) cool air leaving hundreds of tiny film-cooling holes and blanketing the surface in a thin film, (g) the ceramic thermal barrier coating peeling away as a layer, (h) ONE scale fact (power extracted per blade, or centrifugal load per blade, or rpm/tip speed) ONLY if a manufacturer (Rolls-Royce, GE, Pratt & Whitney, Safran) or university source backs it. If you are not sure of a sourced number, leave it out and say so.
- Last line, exactly: "Follow for how the world is really engineered."
- Words as spoken aloud: write numbers as words, no symbols, no degree signs.
- Be factually careful. Typical claims to verify or correct: turbine entry gas temperature (around 1,500-1,700 C in modern large engines?), nickel superalloy melting point (around 1,300 C?), how much hotter the gas is than the melting point, single-crystal blades (who introduced them, e.g. Pratt & Whitney in the 1980s?), ceramic TBC = yttria-stabilised zirconia, how much the coating lowers metal temperature, how many cooling holes per blade, a Rolls-Royce claim that each HP turbine blade produces as much power as a Formula One car (or similar), and a claim that the centrifugal load on a blade equals hanging a double-decker bus or a heavy truck from it. For each, say whether you are confident and what kind of source states it (name the organisation and the document/page type).

TASK:
1. A numbered fact list: each fact, the number, the source (organisation + document/page type), and your confidence (high/medium/low).
2. Three alternative spoken hook lines (line 1 options), each under 14 words.
3. The final script: 8-10 lines, 85-95 words total, counted. Punchy, documentary register, no filler, no jargon a beginner can't follow without seeing it on screen (single crystal, film cooling, thermal barrier coating are fine because the visuals explain them).
4. For each line, a shot plan: 1-3 shots, each with what's on screen, lens (mm), camera move, transition in (hard cut, match cut on shape, rack focus, x-ray wipe, push through), and what glows (thermal ramp / cooling accent).
5. A look note: backdrop gradient colours, key/fill/rim light colours and placement, material notes (base colour, metallic, roughness, anisotropy for brushed metal), thermal ramp colour stops, cooling-air accent colour, depth of field settings, and what makes it feel like a Rolls-Royce product film rather than a blockout.
6. A cover title (1-3 words, topic only) and an Instagram caption (1-2 keyword-rich lines, at most 1 emoji, exactly 5 hashtags).

End with a JSON block:
{"topic": "...", "slug": "3d-03-jet-blades", "hooks": ["...","...","..."],
 "lines": [{"say": "...", "shots": [{"what": "...", "lens": 85, "camera": "...", "transition_in": "...", "glow": "..."}]}],
 "look": {...}, "cover": "...", "caption": "..."}
