**Make the second leak the twist:** Cleo revokes the exposed key, creates another, and immediately pushes that one too. The lesson lands through the mistake: **putting a key in `.env` does not automatically keep it out of Git.**

Target: **about 56 seconds, 99 spoken words, one share CTA.**

## PHASE 1 — AUDIENCE PROBLEM RESEARCH

**Research basis:** GitHub documents accidental credential exposure, persistence in Git history, and resulting unauthorized usage. A community question also describes accidentally committing `.env` and not knowing how to stop tracking it. These support the topic; they do not establish how frequently your specific audience experiences it. The audience descriptions and scores below are **editorial hypotheses, not survey findings**. [GitHub security guidance](https://docs.github.com/en/enterprise-cloud@latest/code-security/concepts/secret-security/secret-leakage-risks), [first-person community question](https://github.com/orgs/community/discussions/189770)

| # | Common problems | Frustrations | Desired outcomes |
|---|---|---|---|
| 1 | Accidentally publishing API keys | “It worked locally.” | Ship without exposing credentials |
| 2 | Misunderstanding `.env` | Tutorials skip configuration details | Understand where secrets belong |
| 3 | Committing files without reviewing changes | Git feels harder than coding | Know exactly what gets pushed |
| 4 | Misunderstanding Git history | Deleted files still matter | Understand what deletion changes |
| 5 | Unexpected API usage | A side project becomes expensive | Keep spending predictable |
| 6 | Copying AI-generated setup blindly | Working code hides unfamiliar decisions | Use AI without losing understanding |
| 7 | Not knowing incident-response order | Every possible fix feels urgent | Know the first useful action |
| 8 | Repeating the leak during rotation | A rushed fix creates another problem | Replace keys safely |
| 9 | Confusing public visibility with popularity | “Nobody even knows my repo exists.” | Share work confidently |
| 10 | Avoiding help after a mistake | Fear of looking incompetent | Recover without humiliation |

| # | Likely repeated questions | Common mistakes | Objections or limiting beliefs |
|---|---|---|---|
| 1 | “Did I just leak my key?” | Pushing a real credential | “It’s only a student project.” |
| 2 | “Isn’t `.env` private?” | Treating a filename as protection | “Dotfiles are hidden.” |
| 3 | “Can I delete the file?” | Only removing the latest copy | “Deleted means gone.” |
| 4 | “Should I make the repo private?” | Treating privacy as revocation | “Nobody can use it now.” |
| 5 | “Do I need a new key?” | Leaving the exposed key active | “It was public for barely any time.” |
| 6 | “Why is Git still uploading it?” | Ignoring an already tracked file without untracking it | “I added it to `.gitignore`.” |
| 7 | “How did anyone find my repo?” | Assuming obscurity prevents discovery | “I have zero followers.” |
| 8 | “Will the charges disappear?” | Assuming revocation reverses usage | “Stopping it should undo it.” |
| 9 | “Won’t GitHub catch it?” | Depending entirely on automated detection | “The platform handles security.” |
| 10 | “Can my AI agent fix this?” | Giving vague instructions without checking results | “It generated the project, so it knows.” |

**Emotional drivers:** pride in finally shipping; anxiety about money; embarrassment about an apparently basic mistake; pressure to build quickly; dependence on unfamiliar tools; relief when someone gives a concrete next step.

**Likely audience language — suggested phrasing, not research quotes:**

“It’s just a side project.” · “I literally just pushed.” · “But it’s in dot env.” · “Nobody uses this.” · “Am I cooked?” · “Can I undo that?” · “It worked five minutes ago.” · “I thought Git ignored that.” · “Please tell me that’s not real.” · “Okay, I made it worse.”

**Problem scoring — editorial estimates, including frequency:**

| Problem | Frequency | Emotional intensity | Niche relevance | Content potential | Short-Reel clarity |
|---|---:|---:|---:|---:|---:|
| Leaking keys through a misunderstood `.env` workflow | 8 | 10 | 10 | 10 | 9 |
| Unexpected API spending | 7 | 10 | 9 | 9 | 9 |
| Blindly accepting AI-generated setup | 9 | 7 | 10 | 8 | 7 |
| Assuming deletion removes Git history | 7 | 8 | 9 | 8 | 7 |
| Not knowing what to do after exposure | 7 | 9 | 10 | 9 | 9 |

**Selected problem:** accidentally exposing credentials because the developer thinks `.env` is automatically excluded from Git.

It gives you one understandable mistake, a believable repeat mistake, financial stakes, and a useful correction.

## PHASE 2 — CONTENT ANGLE

| Element | Direction |
|---|---|
| **A. Core problem** | Cleo puts secrets in a file Git is already tracking. |
| **B. Core insight** | `.env` is a configuration convention, not automatic protection from commits. |
| **C. New belief** | “I need to check what Git tracks, not trust the filename.” |
| **D. Transformation** | From panic-pushing replacements to revoking the exposed key and fixing the publishing workflow. |
| **E. Unique angle** | The rescue is interrupted by Cleo proudly announcing she has leaked the replacement. |
| **F. One-sentence promise** | Watch Cleo make the same expensive mistake twice—and learn what stops the second repeat. |

**Technical decisions for the story:**

- Revoke exposed credentials first. Deleting commits or changing visibility cannot invalidate copies already obtained. [GitHub remediation guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- An already tracked `.env` needs to be untracked; adding an ignore rule alone does not stop tracking it. [GitHub ignoring-files guide](https://docs.github.com/en/get-started/git-basics/ignoring-files)
- Remove the stars-as-bots exchange. Stars do not establish that a credential was harvested.
- Use a fictional API provider and clearly fabricated credentials. The $2,000 is fictional accrued usage, discovered after an overnight exposure.
- Claude works through an authorized, connected computer session. This is a story setup, not a claim that a mascot or ordinary chat automatically has account access.
- Do not imply scanners catch every secret. GitHub’s protection has coverage boundaries. [GitHub push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)

## PHASE 3 — HOOK CREATION

**10 verbal hooks**

1. Cleo: Claude... did I push my API key?
2. Cleo: Please tell me that key was fake.
3. Cleo: Why is my free app costing me money?
4. Cleo: Claude, why is my API bill four digits?
5. Cleo: I deleted the key. We’re good, right?
6. Cleo: Nobody uses my app. Who’s using my API?
7. Cleo: Dot env means private... right?
8. Cleo: I fixed the leak. I pushed a new key.
9. Cleo: How expensive can one Git push be?
10. Cleo: Please tell me “public” means something else.

**10 text hooks**

1. Zero users. One leaked key.
2. The expensive part wasn’t the code.
3. Her fix needs a fix.
4. A very public side project.
5. The filename fooled her.
6. One push. Two problems.
7. The replacement is about to escape.
8. Nobody downloaded the app.
9. This repo came with spending money.
10. The panic commit.

**Best verbal hook:** “Claude... did I push my API key?”

**Best text hook:** “Zero users. One leaked key.”

**Best combination:** those two together—the dialogue introduces the immediate fear, while the text establishes the developer-life irony.

## PHASE 4 — FINAL SCRIPT

This is the structural draft; the tightened recording version is last.

**HOOK**

Cleo: Claude... did I push my API key?  
Claude: Yeah.  
Cleo: Was the repo public?  
Claude: Very public.

**VALUE**

Cleo: But nobody uses my app.  
Claude: They don’t need your app to use your key.

[PHONE: Accrued API usage: $2,000.]

Cleo: Two thousand dollars?!  
Claude: Revoke the key. Now.

[ACTION: Cleo revokes it, generates a replacement, edits `.env`, and pushes.]

Cleo: Revoked. Replaced. Pushed. Fixed.  
Claude: You pushed the replacement?  
Cleo: It’s in dot env!  
Claude: Git was already tracking it.

**SOLUTION**

Cleo: Please take over.  
Claude: Okay. I’ve got this from here.

[SCREEN: Cleo authorizes the connected agent. Second key revoked; repo made private.]

Cleo: So making it private fixes it?  
Claude: No. Revoking stops that key.  
Claude: Untrack dot env. Ignore it. Then replace the key.

Cleo: And the charges?  
Claude: Still there.  
Cleo: Can you fix that?  
Claude: I’m an agent. Not a coupon.

**CTA**

[SCREEN: Send this to your “just one quick push” friend.]

**Timing:** approximately 110 spoken words; about 40–46 seconds of speech and 52–59 seconds with actions and reactions.

**Pause points:** after “Very public”; on the usage alert; after the replacement-key question; before “Not a coupon.”

**Emphasis:** **public**, **two thousand**, **revoke**, **new key**, **already tracking**, **still there**, **coupon**.

## PHASE 5 — RETENTION ENGINEERING

| Audit item | Finding and edit |
|---|---|
| **1. First 1–3 seconds** | Start on Cleo already frozen. Her first line names the mistake immediately. |
| **2. Open loop** | Has the key leaked—and how bad is it? |
| **3. Reason to continue** | The apparent fix becomes another leak. |
| **4. Strongest payoff** | “I’m an agent. Not a coupon.” The key is stopped; the financial consequence remains. |
| **5. Drop-off points** | A long dashboard sequence or Git-history explanation would stall the comedy. |
| **6. Sentences to shorten** | “Was the repo public?” becomes “Public repo?” |
| **7. Lines to remove** | Stars, a numerical bot count, reassurance speeches, and any “everything is safe now” claim. |
| **8. Pattern interrupts** | Phone buzz; rapid keyboard montage; laptop slam; Claude’s silent stare; hands-off agent activity. |

**Retention-optimized replacements:**

Cleo: But I have no users.  
Claude: Bots don’t need your app. Just your key.

Cleo: Revoked. New key. Pushed. Fixed.  
Claude: You pushed the new key?

Cleo: And the two thousand?  
Claude: Still there.

The complete optimized version appears last. It has **99 spoken words**: approximately **36–42 seconds of speech**, with actions and holds bringing it to **52–56 seconds**.

## PHASE 6 — CTA OPTIMIZATION

**10 options**

1. Send this to your “just one quick push” friend.
2. Send this to the friend shipping their first AI app.
3. Send this to whoever says, “It’s only a side project.”
4. Send this to your hackathon teammate before demo night.
5. Send this to the friend who thinks dot env means invisible.
6. Save this for your next “did I just push that?” moment.
7. Save the order: revoke, untrack, ignore, replace.
8. Follow Cleo & Claude for the mistakes between “it works” and “it’s public.”
9. Follow for tiny developer disasters with fixes you can actually use.
10. What was your first “I should not have pushed that” moment?

**A. Best follower-growth CTA:**  
“Follow Cleo & Claude for the mistakes between ‘it works’ and ‘it’s public.’”

**Why follow?** Recurring characters turn recognizable developer mistakes into funny stories with a practical takeaway.

**B. Best comment CTA:**  
“What was your first ‘I should not have pushed that’ moment?”

**C. Best save/share CTA:**  
“Send this to your ‘just one quick push’ friend.”

**Final selection:** the share CTA. It names a recognizable friend without interrupting the characters’ conversation. Keep it on screen after the punchline; do not add a spoken follow request.

## PHASE 7 — VISUAL EXECUTION

Use the existing room, four reusable camera positions, laptop inserts, and one phone insert. Cleo stays in glasses and her lavender hoodie. Claude only hops, tilts, and looks.

| Time | Spoken line | On-screen text | Animated visual / framing | Interrupt |
|---|---|---|---|---|
| **0–6s** | Cleo: “Claude... did I push my API key?” Claude: “Yep.” Cleo: “Public repo?” Claude: “Very public.” | **Zero users. One leaked key.** | Tight Cleo close-up; cut to Claude looking toward the laptop. | Begin mid-crisis, with no title animation. |
| **6–12s** | Cleo: “But I have no users.” Claude: “Bots don’t need your app. Just your key.” | Subtitles only | Desk two-shot. Brief laptop insert: `Public`, `Last push: yesterday`. | Claude tilts on “Just your key.” |
| **12–16s** | Cleo: “Two thousand dollars?!” Claude: “Revoke the key. Now.” | **$2,000**; then subtitle emphasis on **REVOKE** | Phone lights up on desk; immediate cut to Claude. | Buzz cuts through the room tone. |
| **16–21s** | Cleo: “Revoked. New key. Pushed. Fixed.” | `Key A: revoked` → `Key B: created` → `Push complete` | Over-shoulder montage: revoke, create, paste into tracked `.env`, push. Cleo slams laptop shut. | Four rapid visual beats, then silence. |
| **21–26s** | Claude: “You pushed the new key?” Cleo: “It’s in dot env!” Claude: “Git was already tracking it.” | **Already tracked.** | Claude close-up; Cleo defensive close-up; laptop reopens. | Hold Claude’s stare for about half a second. |
| **26–31s** | Cleo: “Please take over.” Claude: “Okay. I’ve got this from here.” | `Connected agent: authorized` | Cleo clicks approval for account and repository actions, then pulls her hands away. | Cursor continues while her hands remain visibly still. |
| **31–36s** | Claude: “Second key revoked. Repo private.” Cleo: “So private fixes it?” Claude: “No. Revoking stops that key.” | `Key B: revoked`, then `Repository: private` | Screen insert followed by two-shot. | Show revocation confirmation before privacy changes. |
| **36–44s** | Claude: “Untrack dot env. Ignore it. Then replace the key.” | **Untrack → Ignore → Replace** | Three readable screen states: stop tracking `.env`; add ignore rule and verify exclusion; store replacement locally. | One change per phrase. |
| **44–49s** | Cleo: “And the two thousand?” Claude: “Still there.” Cleo: “Can you fix that?” | Phone still shows **$2,000 accrued usage** | Cleo looks from phone to Claude. He looks back. | Music drops away. |
| **49–53s** | Claude: “I’m an agent. Not a coupon.” | Subtitle emphasis: **Not a coupon.** | Claude close-up, tiny apologetic tilt. Cut to Cleo sinking into hoodie. | Brief pause between the two sentences. |
| **53–56s** | No dialogue | **Send this to your “just one quick push” friend.** | Hold two-shot; small `Cleo & Claude · EP 02 · @talkingagents`. | Let the joke breathe. |

**Subtitle treatment:** sentence case, no more than two lines, with selective emphasis. Keep subtitles clear of the phone alert and laptop status text.

**Screen examples:** use fabricated UI and placeholder credentials, never a real key. Do not depend on viewers reading terminal commands.

**Agent montage detail:** untracking affects future tracking; it does not erase old commits. Show no “history erased” or “incident fully resolved” badge. The replacement belongs in local/server secret configuration, not client-facing code.

## PHASE 8 — FINAL REEL PACKAGE

**1. Title/topic**  
**Cleo & Claude, Episode 2: The Replacement Key**

**2. Best text hook**  
“Zero users. One leaked key.”

**3. Best verbal hook**  
“Claude... did I push my API key?”

**4. Final script**  
The complete copy-ready version is the last section below.

**5. Final CTA**  
“Send this to your ‘just one quick push’ friend.”

**6. Shot list**  
Cleo close-up → Claude close-up → desk two-shot → phone alert → keyboard montage → laptop slam → awkward stare → authorized agent session → cleanup inserts → bill callback → punchline → share card.

**7. Essential on-screen text**

- Zero users. One leaked key.
- Accrued API usage: $2,000.
- Already tracked.
- Key B: revoked.
- Repository: private.
- Untrack → Ignore → Replace.
- Send this to your “just one quick push” friend.

**8. Caption**

> She rotated the key. Then gave everyone the replacement.
>
> Dot env is a filename, not a force field.
>
> Revoke exposed keys first. If `.env` is already tracked, untrack it and add an ignore rule before storing a replacement there. Deleting a file or making the repo private doesn’t invalidate a leaked key.
>
> Send this to your “just one quick push” friend.
>
> Cleo & Claude, episode 2. Fan-made developer comedy. The $2,000 usage alert is fictional.
>
> #DeveloperHumor #GitHub #APIKeys #AICoding #JuniorDeveloper

**9. Five caption hooks**

1. She rotated the key. Then gave everyone the replacement.
2. Zero users. Somehow, plenty of usage.
3. The replacement key also wanted to be open source.
4. Her emergency fix needed an emergency fix.
5. Dot env is a filename, not a force field.

**10. Ten relevant keywords/search phrases**

API key leak; accidentally committed .env; GitHub secrets; revoke API key; Git ignore tracked file; AI coding mistakes; junior developer mistakes; developer comedy; unexpected API usage; Cleo and Claude.

**11. Hashtags**  
Use the five in the caption. They describe the content; they are not a reach guarantee.

**12. Pinned comment**

> Recovery order: revoke every exposed key first. For an already tracked `.env`, use `git rm --cached .env`, add `.env` to `.gitignore`, and commit the tracking change. Verify it’s ignored before putting a replacement there. This keeps the local file; it does not erase Git history. Review usage and activity logs, assess what was accessed, and contact the provider about unexpected charges—refunds aren’t guaranteed.

The untracking command and its local-file behavior follow [GitHub’s ignoring-files guidance](https://docs.github.com/en/get-started/git-basics/ignoring-files). Broader cleanup depends on the exposure; follow [GitHub’s remediation guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

**13. Three alternative endings**

**Ending A — strongest callback**

Cleo: So I finally have users?  
Claude: Your key does.

**Ending B — warm**

Cleo: Am I a terrible developer?  
Claude: No. But we’re reviewing the next push together.

**Ending C — portfolio joke**

Cleo: Can I put incident response on my résumé?  
Claude: Let’s finish the incident first.

**14. Three alternative hooks**

Cleo: Dot env means private... right?

Cleo: Nobody uses my app. Who’s using my API?

Cleo: I fixed the leak. I pushed a new key.

**15. Thumbnail/cover quote**

**“It’s in dot env!”**

Visual: Cleo defending herself in the foreground; Claude giving her a quiet, concerned look. Small series label: **Cleo & Claude · 02**.

## PHASE 9 — QUALITY CONTROL

These are creative judgments, not predictions of measured performance.

| Criterion | Score |
|---|---:|
| Hook strength | 9 |
| Audience relevance | 10 |
| Clarity | 9 |
| Value | 9 |
| Specificity | 10 |
| Retention potential | 9 |
| Originality | 8 |
| CTA strength | 9 |
| Follower-conversion potential | 7 |
| Overall Reel potential | 9 |

**Top three improvements to prioritize in production:**

1. **Make the second leak unmistakable.** Show the replacement entering the same tracked `.env` before “Push complete.”
2. **Give the misconception room to land.** Hold the reaction after “Git was already tracking it”; avoid adding another joke there.
3. **Time the actual voices before animating.** Preserve the alert, silent stare, and final pause. Shorten interface footage if the cut exceeds 60 seconds.

## FINAL READY-TO-RECORD VERSION

[SCREEN: Zero users. One leaked key.]

[ACTION: Cleo freezes at her laptop. Claude looks up from the desk.]

Cleo: Claude... did I push my API key?

Claude: Yep.

Cleo: Public repo?

Claude: Very public.

Cleo: But I have no users.

Claude: Bots don’t need your app. Just your key.

[SCREEN: Public repository. Last push: yesterday.]

[PHONE: Buzz. Accrued API usage: $2,000.]

Cleo: Two thousand dollars?!

Claude: Revoke the key. Now.

[ACTION: Cleo frantically types.]

[SCREEN: Key A revoked. Key B created. Replacement pasted into tracked .env. Push complete.]

Cleo: Revoked. New key. Pushed. Fixed.

[ACTION: Cleo slams the laptop shut. Claude stares.]

Claude: You pushed the new key?

Cleo: It’s in dot env!

Claude: Git was already tracking it.

[ACTION: Cleo slowly reopens the laptop.]

Cleo: Please take over.

Claude: Okay. I’ve got this from here.

[ACTION: Cleo approves the connected agent’s account and repository access, then pulls her hands away.]

[SCREEN: Agent running. Key B revoked. Repository changed to private.]

Claude: Second key revoked. Repo private.

Cleo: So private fixes it?

Claude: No. Revoking stops that key.

Claude: Untrack dot env. Ignore it. Then replace the key.

[SCREEN: .env untracked. Ignore rule added and verified. Replacement stored locally, excluded from Git.]

[ACTION: Cleo glances at her phone.]

Cleo: And the two thousand?

[PHONE: $2,000 accrued usage remains.]

Claude: Still there.

Cleo: Can you fix that?

[ACTION: Claude gives a tiny apologetic tilt.]

Claude: I’m an agent. Not a coupon.

[ACTION: Cleo sinks into her hoodie. Hold the two-shot.]

[SCREEN: Send this to your “just one quick push” friend.]

[SCREEN: Cleo & Claude · EP 02 · @talkingagents]

