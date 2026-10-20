# Cleo & Claude — Ep. 5: "Three dev servers" (v2)

TEXT HOOK (first frame): 40 minutes. 1 button. Still blue.

[SCREEN: Browser, localhost:5173 "My Tasks": a calm blue "Add task" button. Next to it, her editor: `.add-btn { background: green !important; }`]
[ACTION: Cleo stabs Ctrl+S, glares. Nothing changes.]
Cleo: Claude. I have made this button green eleven times.
Claude: And?
Cleo: It's blue. It's been blue for forty minutes. It's doing it on purpose.
Claude: Did you save?
Cleo: I saved! I hard-refreshed! I switched browsers! I put "important" on everything!
Claude: Everything?
[SCREEN: Editor: `!important` on every line; the button label changed to "PLEASE WORK"; font-size: 64px.]
Cleo: I even changed the text to "PLEASE WORK." Look! It still says "Add task"! You broke CSS.
Claude: Let me look at your terminals.
Cleo: Wait. Don't judge the folder names.
[SCREEN: Three terminal tabs: my-app → localhost:5173 · my-app-v2 → localhost:5174 · my-app-final → localhost:5175]
Claude: "my-app." "my-app-v2." "my-app-final."
Cleo: They're backups!
Claude: They're all running. Three copies. Three servers.
[SCREEN: Editor title bar: my-app-final. Browser tab: localhost:5173 → my-app.]
Claude: You're editing "final." Your browser is showing the original.
Cleo: But it says localhost!
Claude: Different ports. When 5173 was taken, Vite just took the next one.
Cleo: So every fix I made went... somewhere else?
Claude: Every single one. Open 5175.
[ACTION: Cleo clicks the link in my-app-final's terminal.]
[SCREEN: localhost:5175. A giant neon-green button fills half the page, 64px bold text: "PLEASE WORK".]
[ACTION: Long beat. Green light on her glasses.]
Cleo: ...Oh no.
Claude: Forty minutes of fixes. They all worked.
Cleo: Can we go back to blue?
Claude: Sure. Which folder?
[ACTION: Cleo slowly turns to him. Then back to the screen.]
Cleo: ...I'm calling the next one my-app-final-final.

[END TEXT: Send this to your "final_final" friend · @talkingagents]

COVER: "40 MINUTES. 1 BUTTON. STILL BLUE."

CAPTION:
Forty minutes of CSS fixes. Every single one worked. In another folder.
Check which folder your terminal is serving before you blame CSS.
#claude #claudecode #vibecoding #developerhumor #webdev

Fact-check notes:
- Vite's dev server defaults to port 5173; if it's taken it moves to the next free port (5174, 5175...) and prints the URL (unless strictPort is set).
- The bug only happens because the three servers run from three separate copies of the project; each one watches only its own folder.
- Every save in my-app-final hot-reloads localhost:5175, so all her edits really are sitting there when she finally opens it.
- Hard refresh and switching browsers can't help: both still load localhost:5173, the old copy.
