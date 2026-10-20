The strongest ending: **Cleo finally gets the green button working, then admits she preferred blue. Claude: “Good thing you made backups.”** It pays off her earlier excuse for having three project folders and keeps the technical fix intact.

Primary goal: **shares**. Saves come from the practical diagnosis; follower interest comes from the characters and recurring developer mishaps.

**Phase 1 — Audience problem research**

These are audience hypotheses informed by your brief and a small qualitative source check—not measured audience frequencies or survey findings.

The situation has recognizable real-world counterparts: one learner’s browser displayed a different copy from the file they were editing; another developer reported seeing an unexpected Vite project at the default port. These support the scenario’s plausibility, not its prevalence or a universal diagnosis. [Learner discussion](https://www.reddit.com/r/learnprogramming/comments/1au9snh/), [Vite discussion](https://github.com/vitejs/vite/discussions/20046)

The technical foundation is verified: Vite defaults to port `5173`, tries the next available port when occupied under its default configuration, and normally starts with the current directory as its project root. [Vite server options](https://vite.dev/config/server-options#server-port), [Vite project roots](https://vite.dev/guide/#index-html-and-project-root)

Ten likely problems, frustrations and desired outcomes:

| # | Common problem | Frustration | Desired outcome |
|---|---|---|---|
| 1 | Editing a different copy from the running app | “Nothing I change matters.” | See the actual edit immediately |
| 2 | Leaving several dev servers running | “Which terminal is doing what?” | Know which server belongs to which project |
| 3 | Overlooking a changed port | “It says localhost. That should be enough.” | Open the correct app reliably |
| 4 | Collecting nearly identical project folders | “Which ‘final’ is final?” | Have one clear working folder |
| 5 | Asking AI for fixes before checking context | “It keeps fixing the wrong thing.” | Give the agent useful evidence |
| 6 | Changing several things between checks | “I don’t know what helped.” | Isolate one cause |
| 7 | Treating every stale page as a cache issue | “I already hard-refreshed.” | Know what to inspect next |
| 8 | Skimming terminal output | “Apparently it told me already.” | Recognize the relevant message |
| 9 | Applying increasingly forceful CSS changes | “Even `!important` did nothing.” | Confirm the browser receives the file |
| 10 | Losing an evening to a tiny task | “This was supposed to take a minute.” | Finish small changes without spiraling |

Ten likely questions, mistakes and limiting beliefs:

| # | Repeated question | Common mistake | Objection or limiting belief |
|---|---|---|---|
| 1 | “Why aren’t my changes showing?” | Checking styling before checking the served project | “It must be the CSS.” |
| 2 | “Why did the port change?” | Ignoring the printed URL | “The URL is always the same.” |
| 3 | “Which server can I stop?” | Stopping one without identifying its folder | “They’re interchangeable.” |
| 4 | “Which folder am I editing?” | Keeping indistinguishable editor windows | “I’ll remember.” |
| 5 | “Why didn’t the AI fix it?” | Supplying code without runtime context | “The agent already knows what I’m viewing.” |
| 6 | “Should I restart everything?” | Restarting before inspecting | “Starting again is quicker.” |
| 7 | “Is the browser caching this?” | Repeating refreshes without new evidence | “One more refresh might work.” |
| 8 | “Why does the terminal say it’s running?” | Assuming a running server is the intended server | “Running means correct.” |
| 9 | “Why does the old version keep appearing?” | Reusing an old browser tab | “Same-looking page means same project.” |
| 10 | “How did one button take this long?” | Accumulating guesses instead of testing one | “Checking basics would waste time.” |

**Emotional drivers:** embarrassment over a “simple” task; urgency to finish; fear of breaking the working copy; relief from delegating uncertainty to AI; sunk-cost frustration after many failed attempts.

**Likely audience language, written as illustrative phrases:** “It worked five minutes ago”; “I literally saved it”; “Which terminal?”; “Just make it green”; “It’s probably cache”; “Why is it still blue?”; “That’s the backup”; “This is the final final”; “The AI broke it”; “I’ve tried everything.”

Editorial scoring below uses **hypothesized frequency**, not measured prevalence.

| Problem | Frequency | Emotion | Niche fit | Content potential | Short-reel clarity |
|---|---:|---:|---:|---:|---:|
| Editing one copy while viewing another | 7 | 9 | 10 | 10 | 10 |
| Losing track of running dev servers | 8 | 8 | 10 | 9 | 9 |
| Asking AI to fix an unverified diagnosis | 8 | 9 | 10 | 9 | 7 |
| Repeated cache-clearing without diagnosis | 8 | 8 | 9 | 8 | 9 |
| Confusion between “final” folders | 7 | 8 | 9 | 9 | 10 |

**Selected problem:** editing one project copy while viewing another. It connects the unchanged button, three terminals and wasted effort through one visible cause.

**Phase 2 — Content angle**

| Element | Direction |
|---|---|
| A. Core problem | Cleo’s edits work in a project her browser isn’t showing. |
| B. Core insight | Before changing more code, match the editor folder, running server and browser URL. |
| C. New belief | “No visible change” can mean I’m watching the wrong app. |
| D. Transformation | From blaming every tool to identifying exactly what is running. |
| E. Unique angle | Her “backups” are simultaneously serving three versions of the same button. |
| F. One-sentence promise | Watch a forty-minute CSS crisis collapse into one wrong browser address—and one regrettable colour preference. |

**Phase 3 — Hook creation**

Each verbal option is a possible first line from Cleo. Text hooks are independent options.

| # | Verbal hook | Text hook |
|---|---|---|
| 1 | “Forty minutes. One button. Still blue.” | THE FIX WAS WORKING SOMEWHERE |
| 2 | “Claude, I think you broke CSS.” | ONE BUTTON. THREE SERVERS. |
| 3 | “I changed the colour. The button disagrees.” | WRONG TAB. LONG EVENING. |
| 4 | “I’ve cleared the cache. I’m clearing my evening next.” | THE CACHE WAS INNOCENT |
| 5 | “How is the button winning?” | A VERY SMALL CODING CRISIS |
| 6 | “I asked for green. That was forty minutes ago.” | THE TERMINAL HAD A CLUE |
| 7 | “Even the other browser hates me.” | EVERY FIX. WRONG AUDIENCE. |
| 8 | “Before you ask: yes, I saved.” | CHECK WHICH APP YOU’RE WATCHING |
| 9 | “One colour. That’s all I asked.” | THREE COPIES. ONE CONFUSED DEV. |
| 10 | “The button is blue out of spite.” | WHEN ‘FINAL’ IS A FOLDER NAME |

**Best verbal:** “Forty minutes. One button. Still blue.”

**Best text:** “THE FIX WAS WORKING SOMEWHERE.”

**Best combination:** those two together—the dialogue establishes the frustration while the text opens a truthful mystery without revealing the folder mismatch.

**Phase 4 — Script structure**

This is the working draft; the tightened, authoritative recording script appears last.

**HOOK**

Cleo: Forty minutes. One button. Still blue.  
Claude: Did you save?  
Cleo: Saved. Cleared the cache. Changed browsers. You broke CSS.

**VALUE**

Claude: Let me look at the terminals you have running.  
Cleo: Don't judge the folder names.  
Claude: You have three dev servers running from three different project folders.  
Cleo: They're backups.  
Claude: They're all running.  
Cleo: So which one's my website?  
Claude: You're editing the final folder, but your browser is showing the original.  
Cleo: But they both say localhost.  
Claude: Different ports. Vite picks the next free one when one's busy.  
Cleo: So I've been fixing a website I'm not even looking at?

**SOLUTION**

Claude: Yes. Open the URL printed in the terminal for your final folder.  
Cleo: It's green!  
Claude: Stop the other two servers. Keep editing this folder.  
Cleo: All that. For one button.  
Claude: Was it worth it?  
Cleo: Actually... I liked the blue.  
Claude: Good thing you made backups.

**CTA**

[SCREEN: Send this to your “final_final” friend.]

The CTA is an editorial overlay, so neither character addresses the audience.

**Recording target for the tightened version:** 20 spoken lines, approximately **118 words**, roughly **44–48 seconds of speech** and **51–56 seconds including reactions and the end overlay**. Actual TTS timing needs checking.

**Pauses:** a small beat after “They’re all running”; a relief beat after “It’s green”; half a second after “Actually”; a short deadpan hold after “backups.”

**Emphasis:** “forty minutes,” “three different project folders,” “editing,” “looking,” “different ports,” “green,” “blue,” “backups.”

**Phase 5 — Retention engineering**

| Audit point | Assessment and edit |
|---|---|
| 1. First 1–3 seconds | Open on the visibly blue button and Cleo already frustrated. No series introduction. |
| 2. Curiosity gap | The text promises her fix exists somewhere. Viewers want to locate it. |
| 3. Reason to continue | Escalate from one button to three servers, then reveal different folders. |
| 4. Strongest payoff | Green finally appears; Cleo immediately prefers blue; “backups” returns. |
| 5. Likely drop-off | The technical explanation. Show the folder-to-port mapping while Claude speaks. |
| 6. Sentences to shorten | “Let me look at the terminals you have running” becomes “Let me check your terminals.” |
| 7. Lines to remove | Remove any extra cache explanation, port-number recitation or lesson after the punchline. |
| 8. Pattern interrupts | Three terminal panels; a brief silent stare; browser address change; green-button reveal. |

Additional tightening:

- “You have three dev servers running from three different project folders” → “Three dev servers. Three different project folders.”
- “You’re editing the final folder, but your browser is showing the original” → “You’re editing ‘final.’ You’re looking at the original.”
- “Open the URL printed in the terminal for your final folder” → “Open the link from ‘final’s’ terminal.”

The retention-optimized version is the final ready-to-record script below.

**Phase 6 — CTA optimization**

Ten options across the stated goals; each would be used alone:

| # | CTA | Goal |
|---|---|---|
| 1 | Send this to your “final_final” friend. | Shares |
| 2 | Send this to the friend who blames the cache first. | Shares |
| 3 | Send this to your “one quick change” friend. | Shares |
| 4 | Send this to the friend with three dev terminals open. | Shares |
| 5 | Send this to your coding partner before the next CSS crisis. | Shares |
| 6 | Save this: folder → server URL → browser tab. | Saves |
| 7 | Save this for the next “my changes aren’t showing.” | Saves |
| 8 | Follow Cleo & Claude for the coding mistakes you recognize one second too late. | Followers |
| 9 | Follow Cleo & Claude. Every coding disaster comes with a clue. | Followers |
| 10 | Follow for the next tiny change that ruins Cleo’s evening. | Followers |

**A. Best follower CTA:** “Follow Cleo & Claude for the coding mistakes you recognize one second too late.”

**B. Best comment CTA:** “What’s your most ridiculous ‘final’ folder name?”

**C. Best save/share CTA:** “Send this to your ‘final_final’ friend.”

**Why follow after this Reel?** The series offers recurring character comedy built around recognizable developer mistakes, with a useful clue inside each episode.

**Final selection:** “Send this to your ‘final_final’ friend.” It gives viewers a specific recipient and extends the folder-name joke.

**Phase 7 — Animated shot plan**

All shots stay in the existing room. Cleo uses the desktop keyboard and mouse. Claude only looks, tilts and hops; his terminal inspection happens through his coding-agent access.

The table uses the final dialogue. Times are edit targets, subject to the rendered voices.

| Time | Spoken lines | On-screen text | Visual / framing / interrupt |
|---|---|---|---|
| 0–4s | **Cleo:** “Forty minutes. One button. Still blue.” **Claude:** “Did you save?” | THE FIX WAS WORKING SOMEWHERE | Tight over-shoulder: blue button. Cleo manually refreshes; it stays blue. Cut to Claude looking up at her. |
| 4–8s | **Cleo:** “Saved. Cleared the cache. Changed browsers. You broke CSS.” | Emphasize YOU BROKE CSS in subtitles | Cleo close-up. She turns from monitor to Claude on the accusation. |
| 8–12s | **Claude:** “Let me check your terminals.” **Cleo:** “Don't judge the folder names.” | Subtitle emphasis: FOLDER NAMES | Desk two-shot. Claude tilts toward the monitor; Cleo becomes defensive. |
| 12–16s | **Claude:** “Three dev servers. Three different project folders.” **Cleo:** “They're backups.” | `my-app → 5173` / `my-app-v2 → 5174` / `my-app-final → 5175` | Screen insert: three terminal panels. Reveal each folder and URL in sequence. |
| 16–19s | **Claude:** “They're all running.” **Cleo:** “So which one's my website?” | Emphasize ALL RUNNING | Claude close-up and a short silent stare; cut to Cleo. |
| 19–24s | **Claude:** “You're editing ‘final.’ You're looking at the original.” **Cleo:** “But they both say localhost.” | EDITING: `my-app-final` / VIEWING: `my-app` | Screen insert: editor breadcrumb and browser URL. Underline `5173` in the address bar. |
| 24–28s | **Claude:** “Different ports. Vite picks the next free one when one's busy.” | `5173 → 5174 → 5175` | Keep the three terminal URLs visible. Briefly highlight each port; do not add a new metaphor. |
| 28–33s | **Cleo:** “So I've been fixing a website I'm not even looking at?” | Regular subtitles only | Slow, small push toward Cleo as the realization lands. |
| 33–37s | **Claude:** “Yep. Open the link from ‘final's’ terminal.” **Cleo:** “It's green!” | `localhost:5175` | Over-shoulder. Cleo opens the printed URL. The correct page appears with a green button. |
| 37–41s | **Claude:** “Now stop the other two servers. Keep editing this folder.” | KEEP: `my-app-final` | Screen insert: Cleo interrupts the two old server processes; their terminals return to prompts. `5175` remains running. |
| 41–45s | **Cleo:** “All that. For one button.” **Claude:** “Was it worth it?” | Regular subtitles only | Two-shot. Cleo relaxes. Claude looks from her to the button. |
| 45–50s | **Cleo:** “Actually... I liked the blue.” **Claude:** “Good thing you made backups.” | Emphasize BLUE, then BACKUPS | Cleo close-up; half-second hesitation. Cut to Claude’s dry delivery. |
| 50–54s | No speech | Send this to your “final_final” friend. | Hold the two-shot. Cleo slowly turns toward Claude. Small `@talkingagents` signature. |

**Subtitle treatment:** short phrase groups, at most two lines. Keep the terminal details above the subtitle area. Use text labels as well as colour to distinguish the edited and viewed projects.

**Screen continuity:**

- `my-app` serves the original blue button on `5173`.
- `my-app-v2` also retains blue on `5174`.
- `my-app-final` contains the green edit on `5175`.
- The old browser tab does not automatically reload because she saves another copy. Her opening refresh is manual.
- Opening `5175` reveals an already-correct edit.
- Stopping the older servers does not delete the backup folders or move the surviving server to `5173`.

The folder and URL pairing follows Vite’s documented project-root and port behavior. [Project roots](https://vite.dev/guide/#index-html-and-project-root), [Port selection](https://vite.dev/config/server-options#server-port)

Leave the phone, pencil cup, succulent and sticky notes as set dressing. No phone insert is needed.

**Phase 8 — Final Reel package**

| Deliverable | Final choice |
|---|---|
| 1. Title/topic | **Cleo & Claude — Three Dev Servers** |
| 2. Text hook | **THE FIX WAS WORKING SOMEWHERE** |
| 3. Verbal hook | **“Forty minutes. One button. Still blue.”** |
| 4. Final script | The 20-line ready-to-record version at the end |
| 5. Final CTA | **Send this to your “final_final” friend.** |
| 6. Shot list | The 13-shot sequence above |
| 7. Main overlays | Opening hook; three folder/port pairs; EDITING / VIEWING; KEEP: `my-app-final`; final CTA |

**8. Caption**

Forty minutes of CSS debugging. The button was in another folder.

Before another fix: match your editor folder, that folder’s terminal URL, and your browser tab.

Send this to your “final_final” friend.

Cleo & Claude, episode 5. Fan-made developer comedy.

#DeveloperHumor #CodingHumor #ViteJS #WebDevelopment #AICoding

**9. Five caption hooks**

1. The fix worked. Cleo wasn’t watching it.
2. Three dev servers. One very personal argument with a button.
3. Somewhere, her code was doing exactly what she asked.
4. Her backups had become live demonstrations.
5. “Final” was a folder name. An optimistic one.

**10. Ten relevant keywords/search phrases**

Vite changes not showing; localhost wrong project; Vite port 5173; multiple dev servers; editing the wrong folder; CSS changes not updating; junior developer mistakes; AI coding humor; developer life animation; Cleo and Claude.

**11. Hashtags**

Use the five in the caption. They describe the content; no reach uplift is assumed.

**12. Pinned comment**

The clue is the folder AND the port. These are three separate project copies. Refreshing the original won’t show an edit saved in “final.”

**13. Three alternative endings**

Each replaces the final four spoken lines.

**A — Ownership joke**

Cleo: So the code was fine?  
Claude: This edit was.  
Cleo: Then who wasted forty minutes?  
Claude: Shall I check the room?

**B — CSS callback**

Cleo: So you didn't break CSS?  
Claude: No.  
Cleo: Can we still blame it?  
Claude: It wasn't even in this tab.

**C — Another process**

Cleo: I opened another terminal.  
Claude: Please tell me you didn't start it.  
Cleo: It says five-one-seven-six.  
Claude: The button has a fourth address.

For C, show a fourth server explicitly started from the existing `my-app-final` folder. It adds a server, not a fourth project copy; its edits would match that folder. The selected ending is cleaner.

**14. Three alternative hooks**

- Cleo: Before you ask: yes, I saved.
- Cleo: Claude, I think you broke CSS.
- Cleo: I changed the colour. The button disagrees.

**15. Thumbnail / cover**

**Cover quote:** “FORTY MINUTES. ONE BUTTON. STILL BLUE.”

Visual: Cleo glaring at the blue button, Claude looking toward three terminal tabs. Keep the episode number small so it does not imply required viewing.

**Phase 9 — Quality control**

Editorial scores, not performance predictions:

| Criterion | Score |
|---|---:|
| Hook strength | 9/10 |
| Audience relevance | 9/10 |
| Clarity | 9/10 |
| Value | 8/10 |
| Specificity | 10/10 |
| Retention potential | 9/10 |
| Originality | 8/10 |
| CTA strength | 9/10 |
| Follower-conversion potential | 7/10 |
| Overall Reel potential | 9/10 |

Follower conversion scores lower because the single explicit CTA prioritizes sharing.

**The three production changes with the most upside:**

1. Make the folder-to-port mapping readable on a phone. The whole explanation depends on it.
2. Keep Claude’s technical line calm and visual; shorten reaction holds before accelerating the speech.
3. Give “Actually...” and “backups” room to land. The ending needs a preference reversal, then a callback—not two rushed lines.

**FINAL READY-TO-RECORD VERSION**

[SCREEN: THE FIX WAS WORKING SOMEWHERE]

[ACTION: Cleo refreshes the page on her desktop monitor. The button stays blue.]

Cleo: Forty minutes. One button. Still blue.

Claude: Did you save?

Cleo: Saved. Cleared the cache. Changed browsers. You broke CSS.

Claude: Let me check your terminals.

Cleo: Don't judge the folder names.

[ACTION: Claude tilts toward the monitor as his coding-agent inspection brings the terminal details into view.]

[SCREEN: Three running terminals: my-app → localhost:5173; my-app-v2 → localhost:5174; my-app-final → localhost:5175.]

Claude: Three dev servers. Three different project folders.

Cleo: They're backups.

Claude: They're all running.

[ACTION: Cleo stops defending herself.]

Cleo: So which one's my website?

[SCREEN: Editor: my-app-final. Browser: localhost:5173 → my-app.]

Claude: You're editing “final.” You're looking at the original.

Cleo: But they both say localhost.

[SCREEN: Highlight the different ports: 5173, 5174, 5175.]

Claude: Different ports. Vite picks the next free one when one's busy.

Cleo: So I've been fixing a website I'm not even looking at?

Claude: Yep. Open the link from “final's” terminal.

[ACTION: Cleo opens the terminal link with her mouse.]

[SCREEN: localhost:5175. The button is green.]

Cleo: It's green!

Claude: Now stop the other two servers. Keep editing this folder.

[ACTION: Cleo stops the servers in my-app and my-app-v2. The my-app-final server stays running.]

Cleo: All that. For one button.

Claude: Was it worth it?

[ACTION: Cleo studies the green button. Half a beat.]

Cleo: Actually... I liked the blue.

[ACTION: Claude looks up at her.]

Claude: Good thing you made backups.

[ACTION: Cleo slowly turns toward him. Hold.]

[SCREEN: Send this to your “final_final” friend.]

[SCREEN: @talkingagents]

