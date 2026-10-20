# Cleo & Claude — Ep. 4: "You are DDoSing yourself"

TEXT HOOK (first frame): 45,000 database reads. 1 user.

[INSERT: Her phone on the desk: database dashboard, "Reads today 45,112", the graph shooting up.]
Cleo: Claude! Forty-five thousand database reads in three minutes! We're going viral!
Claude: Cleo... you haven't deployed it yet.
Cleo: Then who's reading it?
Claude: Your app only runs on localhost. Every one of those reads came from this desk.
Cleo: ...From me?
Claude: From you. You're DDoSing yourself.
Cleo: I'm not even touching anything! The page is just sitting there!
Claude: Look at the Network tab.
[INSERT: DevTools Network: GET /api/tasks over and over, the request counter spinning.]
Cleo: Why is it counting like a slot machine?!
Claude: I wrote your useEffect with an empty array, so it fetched once. Did you touch it?
Cleo: I made it refresh whenever the tasks changed. That's called being responsive!
[INSERT: useEffect(... , [tasks]) with [tasks] pulsing red.]
Claude: So it fetches your tasks, gets a brand-new array, thinks the tasks changed, and fetches again. Forever.
Cleo: Make it stop! Make it stop!
[INSERT: [tasks] -> [], reload, Network: 1 request.]
Claude: Done. The empty array is back. One request. Next time, test with the Network tab open.
Cleo: Phew. At least we caught it before it cost anything.
[INSERT: phone buzzes: "Daily read limit reached. Reads blocked until tomorrow."]
Cleo: "Daily read limit reached. Reads blocked until tomorrow."
Cleo: Claude... can you rewind the database too?
Claude: I can rewind my edits, Cleo. Not the calendar.

[END TEXT: Send this to a dev who DDoSed themselves · @talkingagents]

Fixes vs the Argon draft: Cleo adds [tasks] herself (no false lint claim); the "I live in there" ending is replaced by a
callback to Ep 3's checkpoint rewind. 45k (not 50k) at the open so the free tier's 50k/day read limit runs out later.
