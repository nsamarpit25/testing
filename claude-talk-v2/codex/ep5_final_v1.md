# Cleo & Claude — Ep. 5: "Three dev servers"

TEXT HOOK (first frame): THE FIX WAS WORKING SOMEWHERE

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


COVER: "FORTY MINUTES. ONE BUTTON. STILL BLUE."

CAPTION:

Forty minutes of CSS debugging. The button was in another folder.

Before another fix: match your editor folder, that folder’s terminal URL, and your browser tab.

Send this to your “final_final” friend.

Cleo & Claude, episode 5. Fan-made developer comedy.

#DeveloperHumor #CodingHumor #ViteJS #WebDevelopment #AICoding

PINNED COMMENT:

The clue is the folder AND the port. These are three separate project copies. Refreshing the original won’t show an edit saved in “final.”

Fact-check: Vite defaults to 5173 and moves to the next free port when it is taken (unless strictPort); edits only differ between servers because they are separate project copies.
