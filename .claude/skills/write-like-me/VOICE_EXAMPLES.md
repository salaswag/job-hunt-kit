# Voice Examples (before -> after)

Growing bank of real before/after pairs. The first three came from the person who shared this kit; replace them with your own as you go. Add a new one every time you paste raw text and says "add this" / "update the skill" / "dump this in". Newest at the bottom. Check this file before a big rewrite, it calibrates better than the rule list in `SKILL.md` alone.

---

## Example 1 -- the original ask for this skill (2026-07-26)

**Before (raw voice-typed dictation):**

"Alright, so what I need to do is create my own style, make that into a skill, how I myself write. A lot of the times I'm gonna talk, voice type and whatnot, and I might as well have it like that. I want the main thing I'm saying to not get completely AI-manipulated and made into some corporate jargon or whatever, or even just like the way AI writes. I just don't want my flavor to go away like that. I would want it to have correction in terms of filler words and stuff like that, get rid of that. And stuff like cursing, get rid of that, and make a little bit of changes into those sentences, which is fine. But a lot of times when I tell it to make these adjustments, it just completely blows it out of the park.

So I think what I'm gonna do is I want a skill for that, and I'm gonna copy and paste certain things sometimes and be like, edit this, the skill, whatever, and dump this. Because I want things to have my twist, since I talk in a certain way, and I'd rather just have it sounding that way as well, of course without the cursing and without the filler words and without the rambling. Of course whenever I'm voice typing things are gonna go, I'm gonna overexplain some things, underexplain something, whatever. But I'm talking about how I currently write, that needs to be a skill itself.

Then what I'm gonna do is I'm gonna talk to the app, and I want that to turn into a report or something like that, written out by how I am saying it, more how I write or talk. Of course if I want things professional or whatever I'll probably say, hey, write it out first like this, however I'm kinda saying it, with good punctuation, this and that. And then I'll be like, make a little adjustment, make it more professional, or funny, or indirect. But if I don't explicitly mention that, it should just be as blunt as how I usually am.

And every time I talk to you in this project, you should basically talk like that too. Straight up, straightforward, no bullshit, unless it's mentioned otherwise that, hey, be gentle, you have this persona, whatever."

**After (cleaned, same voice):**

"I want a skill that captures how I actually write, since I'm going to be voice-typing into this a lot. When I ask for cleanup, filler words gone, cursing gone, a few sentence-level fixes, that's fine. But every time I've asked for that before, it overcorrects and wipes out my voice entirely. I want a skill that fixes that.

I'll paste in raw text over time and say 'update the skill with this', so it keeps learning my style. Voice-typing means I'll overexplain some things and underexplain others, that's normal, but the underlying style, how I actually talk, needs to be locked into a skill.

Default output: blunt, direct, no fluff, however I'd actually say it. If I want something more professional, funnier, or more indirect, I'll say so upfront. If I don't say that, keep it blunt.

And in this project, talk back to me the same way by default. Straightforward, no bullshit, unless I ask for a different tone."

**What changed:** cut filler ("like", "whatnot", "you know what I mean", "or whatever", "and stuff like that"), collapsed three restatements of the same point into one, cut the one curse, fixed run-on sentences into short paragraphs. Kept: "gonna" energy folded into plain statements since it wasn't doing real work repeated that often, first person, flat direct opinions, no hedging added, no corporate phrasing introduced.

**Note:** this pair is a first-pass calibration, not gospel. If you look at the "after" and it still feels off, that correction is the next entry, and beats this one.

---

## Example 2 -- the register correction (2026-07-28)

The owner's note, on a line written for a course proposal: "saying things like, these people get personal reach out, so 'these people' is very bad, I wouldn't actually write like this."

**The offending line:**
"Those people get a personal reach-out about volunteering, helping, or supporting the work."

**Fixed:**
"Anyone who completes the course receives a personal follow-up about volunteering, helping, or supporting the work."

**The lesson, now a rule in `SKILL.md`:** the first pass read "be blunt, no fluff" as permission to write flat and vague. "Those people" is both imprecise and casual. Naming the actual group is more direct AND more professional at the same time, so there is nothing to trade off. The default register moved from "blunt, no-bullshit" to "direct and professional": precise, no hedging, no padding, but not crude or basic either.

The distinction to hold onto: **the enemy is corporate jargon on one side and lazy vagueness on the other.** Both are failures. The target is a sharp, specific sentence.

---

## Example 3 -- the politeness correction (2026-09-09)

**Before (raw voice-typed dictation, the ask itself):**

"So you know this command... you know the skills already that I have? Can you make this skill a little bit more polite? So whatever this is, like, the straightforwardness should stay, but it should be polite, um, and have, like, words and whatnot to make things polite and courteous and everything. Okay? While still being, like, you know, straight to the point kind of thing. Okay? So update that skill, please, and thank you."

**After (cleaned, same voice):**

"Could you make this skill a little more polite, please? The straightforwardness should stay, but add the words that make it courteous. Still straight to the point. Thank you."

**What changed:** cut the filler ("like", "um", "you know", "whatnot", "and everything", "kind of thing", "okay?"), collapsed the two restatements of "polite" into one, turned the bare imperative into a request. Kept: the actual instruction, the short sentences, the "please" and "thank you" he already used, no hedging added.

**The lesson, now the `Polite, not soft` rule in `SKILL.md`:** he ends his own asks with "please, and thank you" while still stating exactly what he wants. That is the target register. Politeness is a frame around the request, not a softener on the claim. If stripping the courtesy words changes what the sentence means or how sure it sounds, the wrong thing got added.
