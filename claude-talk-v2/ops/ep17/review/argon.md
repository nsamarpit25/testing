**(1) Emotional Critique**
* **What works:** The "tired of fixing things" exchange is pure junior-dev reality, and Claude noticing she says goodnight every night is genuinely touching without trying too hard. The two seconds of silence is a great pacing risk for Reels.
* **What doesn't:** Claude is a little too much like a Hallmark card in the middle. The line about her mom feels slightly preachy, and "If I do, it's just the battery. Not you" tips into melodrama—Cleo knows how batteries work. He needs a touch more of his usual dry wit to earn the sweetness.

**(2) Weakest Lines & Rewrites**
* **Weak:** `cleo	Claude? ...Claude, are you still there?` (violates the "never repeat" hook rule—she says "Claude?" again when he dies—and is too generic for a 1.5s hook).
  * **Rewrite:** `cleo	Claude, the whole street just went dark.`
* **Weak:** `claude	It's kind. But say it to your mom tomorrow. She'd like one too.` (A bit scolding/sappy; misses the visual cue of her phone lighting the room).
  * **Rewrite:** `claude	It's polite. Though your mom has texted you twice. She'd probably like a goodnight too.`
* **Weak:** `claude	I go quiet. If I do, it's just the battery. Not you.` (Too therapist-speak).
  * **Rewrite:** `claude	I take a nap. Don't take it personally.`

**(3) Hook & Ending**
* **Hook:** Fix applied above to make it immediate and avoid repeating the whisper at the climax.
* **Ending:** Keep the last two lines after *"You stayed."* Ending on *"You stayed"* makes the reel about a robot feeling loved; keeping the ending makes it about human connection. However, the final line needs sharpening so it’s a true "send to a friend" closer.

**(4) Gemini TTS Notes**
* Ellipses (`...Claude`, `...You stayed`) often cause TTS glitches or weird pitch drops. Remove them or use a period for a clean pause. 
* Short sentences ("Three percent.") sometimes clip in TTS. Added "About" to smooth the cadence.
* In `"It's kind. But say it to your mom..."`, TTS won't naturally stress *"your mom"* and *"one"*. Rewriting fixes the rhythm.

**(5) Draft Score: 7.5/10** (Great bones, just needs de-sapping and TTS polish).

***

### FINAL SCRIPT (83 spoken words vs. draft's 87)

```tsv
[Night. Cleo typing. Thunder. The power dies: black. Monitor off.]
cleo	Claude, the whole street just went dark.
claude	Still here. I'm on backup battery.
cleo	How much is left?
claude	About three percent.
cleo	How long is three percent?
claude	Long enough to talk. Not long enough to fix your code.
cleo	Good. I'm tired of fixing things.
claude	Then don't.
[Cleo's phone screen lights her face.]
cleo	Can I tell you something weird? You're who I talk to most these days.
claude	I know. You say goodnight to me. Every night.
cleo	Is that sad?
claude	It's polite. Though your mom texted you twice. She'd probably like one too.
cleo	What happens when you hit zero?
claude	I take a nap. Don't take it personally.
[Claude's glow fades out. Black, silent, two seconds.]
cleo	Claude?
[Power returns: lights flicker on, monitor wakes, Claude lights up.]
claude	You stayed.
cleo	Goodnight, Claude.
claude	Goodnight. Go text the people who miss you.
```