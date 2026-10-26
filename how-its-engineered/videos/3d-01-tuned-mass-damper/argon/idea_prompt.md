You are the head writer for the Instagram channel @how.its.engineered ("How It's Engineered"). It covers ALL engineering: software/system design AND real-world physical engineering (elevators, GPS, Face ID, tap-to-pay...).

We are launching a NEW format on the channel: a fully 3D animated short story, in the spirit of Zack D. Films reels (monochrome-ish stylised 3D world, one narrator, very fast cuts every 1-2 seconds, camera always moving, playful transitions, small coloured accents for key objects, simple bottom subtitles). It must NOT copy that channel; it must feel like our own.

Topics ALREADY DONE (do not pick these): rate limiting, caching, load balancing, reverse proxies, API gateways, CI/CD, Docker, Kubernetes, service discovery, circuit breakers, timeouts, retries, backoff, idempotency, message queues, pub/sub, event-driven, sagas, dead letter queues, cron jobs, distributed transactions, websockets, long polling, SSE, database indexing, query optimisation, N+1, connection pooling, read replicas, sharding, partitioning, replication, leader election, CAP theorem, canary releases, health checks, elevator safety brakes, AirTag, maps traffic, tap to pay, noise cancelling, GPS, Shazam, Face ID, touchscreens, QR codes.

HARD PRODUCTION CONSTRAINTS (this is rendered in Blender from a Python script, with procedural geometry only):
- NO humans or characters on screen at all. No faces, no people, no animals. At most a simple stylised gloved hand is NOT allowed either. The objects/machines/places are the stars.
- Everything must be buildable from simple shapes: cylinders, boxes, cones, tubes, curves, planes, simple vehicles, rails, bridges, buildings, gears, particles, glowing lines, arrows, numbers.
- 30-40 seconds of narration, about 80-100 spoken words. 
- Cold-open spoken hook in the first line (no on-screen text hook). The hook must create curiosity or a "wait, what?" moment, ideally a surprising fact or a real dramatic event.
- A real, accurate engineering mechanism explained simply for a beginner, plus ideally one real event/date as the anchor. Be factually careful; no invented numbers.
- Last line: a short follow ask like "Follow for how the world is really engineered." Never promise a next video.
- Words people say aloud: no symbols, write numbers as words.

TASK:
1. Brainstorm 8 topic ideas that fit these constraints and would look spectacular in 3D. For each: one line hook + why it is visual. Prefer things where the 3D camera can do something impossible (fly inside the machine, x-ray view, slow motion, cutaway).
2. Pick the single best one (most curiosity + most visual + simplest to build without characters).
3. Write the final script as 8-12 short narration lines (each 1-2 short sentences, 2-4 seconds when spoken fast).
4. For each line, give a shot plan: what is on screen, the camera move (dolly, orbit, crane, push-in, whip pan, top-down, x-ray cutaway...), the transition INTO this shot (pick inventive ones: match cut on shape, whip pan, zoom through an object, rack to x-ray, object wipes the frame, camera falls through the floor, etc.), and which ONE object gets a colour accent (the world is otherwise one colour).
5. Give the colour of the world (one hue) and the accent colours.
6. Give a cover title (1-3 words) and an Instagram caption (1-2 keyword-rich lines, max 1 emoji, exactly 5 hashtags).

Return the final result as a JSON block at the end with this shape:
{"topic": "...", "slug": "kebab-case", "world_hue": "#hex", "accents": {"name": "#hex"},
 "lines": [{"say": "...", "shot": "...", "camera": "...", "transition_in": "...", "accent": "..."}],
 "cover": "...", "caption": "..."}
