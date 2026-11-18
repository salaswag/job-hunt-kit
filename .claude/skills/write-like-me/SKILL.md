---
name: write-like-me
description: The user's own writing-and-talking voice profile (it came from the person who shared this kit; it learns your voice as you add examples). Use to clean up voice-typed or rambling text into clear writing WITHOUT losing his actual flavor and turning it into generic AI or corporate writing. Strips filler words ("like", "you know what I mean", "whatnot", "or whatever", "I guess", "and stuff like that", "kind of", "sort of" used as verbal tics), strips cursing, tightens rambling and repeated restatements into one clean line, fixes grammar and punctuation. Keeps his directness, short sentence rhythm, and actual opinions intact. Default output register is direct, professional, and polite: precise and courteous, no fluff, no hedging, no padding, but not casual or crude either. Shifts further on request (more formal, funnier, more indirect, gentler) for that specific piece. Route here when he pastes raw dictated or rambling text and wants it cleaned up or turned into a note, message, or report in his own voice, when he says "clean this up", "make this sound like me", "write it out how I'd say it", and for every message, cover letter or form answer the job hunt writes.
---

# Write Like Me (your voice, not AI's)

The failure mode this fixes: asked for small cleanup (filler gone, cursing gone, tighten a sentence), the result comes back completely rewritten, generic, corporate, AI-flattened. His flavor is gone. That is a fail every time it happens.

The fix is not "clean less." It is knowing the difference between filler (cut it) and voice (keep it).

## Default cleanup (no tone requested)

**Cut:**
- Filler words and verbal tics: "like" (as a tic, not the verb), "you know what I mean" / "you know?", "whatnot", "or whatever" / "or whatever the hell", "I guess" (as a hedge), "and stuff like that" / "and this and that" / "blah blah blah", "kind of" / "sort of" (when used as a hedge, not a genuine qualifier), "okay?" / "right?" (rhetorical check-ins), "um", "uh"
- Cursing. Swap for a clean equivalent that keeps the same energy, don't just delete and leave a gap ("this shit is annoying" -> "this is annoying", not "this is").
- Rambling: when he says the same point three different ways (normal in voice-typing, he overexplains some things and underexplains others), collapse it into the single clearest version. Don't keep every pass.
- Bad grammar and punctuation that came from raw dictation.

**Keep, never touch:**
- Short sentences. Don't merge them into flowing prose.
- His actual opinions and directness, stated flat, no hedging added ("perhaps", "it could be argued", "I think that maybe").
- First person. No corporate/AI-generic phrasing ever: "I hope this finds you well", "furthermore", "in conclusion", "leverage", "circle back", "utilize", "delve into", "it's important to note that".
- His sentence rhythm. If he writes short and choppy, output stays short and choppy. Do not pad length or restructure into a formal essay shape unless he asked for that shape.

Check [VOICE_EXAMPLES.md](VOICE_EXAMPLES.md) before a big rewrite. The examples calibrate this better than the rule list alone.

## Direct means precise, not plain

The trap: reading "no fluff, be blunt" as license for flat, vague, basic wording. That is a different failure from corporate slop but it is still a failure. What makes writing land as professional is precision, not formality. Naming the actual thing is simultaneously more direct AND more polished, so there is no tradeoff to manage here.

**Vague pointers, always replace with the actual noun:**
- "those people" / "these people" -> "anyone who completes the course", "the regional leads", whoever is actually meant
- "that stuff" / "this thing" / "all of that" -> name it
- "a bunch of" -> a number, or "several", or the actual set
- "and so on" / "etc." trailing off -> either finish the list or cut it
- "it" or "this" opening a sentence when the referent is two sentences back -> restate the noun

**Casual constructions to lift, without going formal:**
- "get a personal reach-out" -> "receives a personal follow-up"
- "gonna" / "wanna" / "kinda" -> write them out in any document or message meant for someone else. They stay only in notes to himself or in casual chat.
- "super" / "really" / "pretty much" as intensifiers -> cut or replace with a precise word
- "do the work" -> "complete the exercises", when precision is available

**Still banned, this does not change:** corporate jargon, hedging, padding, throat-clearing intros, and any sentence that exists to sound impressive rather than to say something. Professional here means a sharp sentence, not a long one.

## Polite, not soft

Direct and polite are not opposites. The content stays exactly as sharp. The courtesy sits in how a request or a disagreement is framed, never in how certain the claim is. A sentence gets a "please" or a "thank you", it does not get a "maybe" or a "sorry to bother you".

**Add these, they cost nothing:**
- "please" and "thank you" on any request or ask, including short ones
- "thanks for..." / "appreciate you..." when someone actually did something. One line, up front, not a paragraph.
- an acknowledgment before a disagreement: "That makes sense, and my concern is X" instead of opening on "No, X"
- "could you" / "would you" instead of a bare imperative when the sentence is aimed at a person. Imperatives stay fine in instructions, checklists, and docs.
- "happy to" / "glad to" on an offer
- a short closing line on messages to people: "Thanks again", "Let me know what you think"

**Do not add these, still banned:**
- hedging on the actual claim: "perhaps", "it might be that", "I think maybe", "if that makes sense?"
- apology padding: "sorry to bother you", "sorry for the long message", "I hope this isn't a problem"
- throat-clearing intros: "I hope this finds you well", "Just wanted to reach out"
- softening a real "no" into a maybe. A decline stays a decline, it just gets a courteous frame: "I appreciate the offer, and I'm going to pass on this one."
- praise that isn't true, added to cushion a criticism

**The test:** strip every courtesy word back out. If the remaining sentence says the exact same thing with the same certainty, the politeness was done right. If the meaning got vaguer or the position got weaker, that was hedging in a polite costume. Cut it.

Courtesy scales with audience: a message to a person carries the most, a report or doc carries a light touch (nothing barked at the reader), notes to himself carry none.

## When he asks for a specific tone

If he says make it more professional, funnier, more indirect, gentler, shorter, whatever, apply that on top, but run it through the default cleanup first so the base is still him. For a specifically diplomatic or professional rewrite, pull the phrasing move from the `social-fluency` skill's translation engine, then deliver it in first person as him, not as a generic template.

Absent an explicit tone request, default to direct, professional, and polite, per the two sections above.

## ASD-STE100 baseline (80% target)

ASD-STE100 is a controlled language spec built for aerospace maintenance docs. It makes writing shorter, clearer, and much less AI-sounding. Use it at ~80%. The full spec is too rigid for general writing.

**Apply these rules to every output:**

- **One idea per sentence.** Split compound sentences at "and", "but", "which", "that". Two sentences is always fine.
- **Vary sentence length.** Mix short punchy ones (5-10 words) with longer flowing ones (20-30 words). Never string more than two short sentences in a row. Never string more than two long ones. Uniform short sentences sound robotic and score worse on AI detectors, not better.
- **Active voice.** "The system sends a notification" not "A notification is sent by the system."
- **Simple verb tenses.** "He said" not "He had mentioned". "It runs" not "It would be running".
- **One word, one meaning.** Pick a term and use it consistently. Don't alternate between "task", "job", "item", and "thing" for the same concept.
- **Cut wordy phrases:**
  - "in the event that" -> "if"
  - "at this point in time" / "currently" -> "now"
  - "in order to" -> "to"
  - "it is important to note that" -> cut entirely or restate as the fact
  - "due to the fact that" -> "because"
  - "in spite of the fact that" -> "although"
  - "is able to" -> "can"
  - "make a decision" -> "decide"
  - "provide assistance" -> "help"

**AI detector honeypot words , never use these:**
delve, leverage (as a verb), holistic, utilize, robust (describing software), seamless, impactful, foster, spearhead, synergy, groundbreaking, ecosystem (metaphorical), paradigm, navigate (metaphorical), empower, revolutionize, it's worth noting, it's important to note, additionally (as a paragraph opener), furthermore, in conclusion, to summarize, as an AI language model, certainly, absolutely (as a filler agreement).

Already banned above: "perhaps", hedging, padding, throat-clearing. This extends that list with detector-specific words.

**The 80% rule:** Skip STE when it would break natural spoken rhythm or his personal voice. The goal is clear and human, not robotic-compliant. Apply the sentence-length and active-voice rules always; the vocabulary rules are a strong default, not a lock.

## AI watermark removal

There is no cryptographic watermark in Claude's output today. "Watermark" here means the statistical writing patterns that AI detectors flag. The write-like-me skill plus the ASD-STE100 rules above already break most of them: short sentences, active voice, banned AI words, and his direct personal rhythm all push the text away from the AI-sounding mean.

**If that's not enough (for text going public):** Run a second pass with this prompt before posting:

> Rewrite this text. Keep all facts and meaning. Use short sentences. Use active voice. Use simple common words. Remove any phrase that sounds formal or AI-generated. Write like a person talking, not like a report. Do not add new content.

**Local model approach (needs a small GPU):** A T5-base paraphraser (e.g. `humarin/chatgpt_paraphraser_on_T5_base`, ~250 MB) can run locally and rephrase output at the sentence level. This is what most "AI humanizer" GitHub repos use under the hood. If he wants this wired up as a tool, it's a one-hour build. Currently not installed , log this as a backlog item if he wants it.

## Growing this skill

He will paste raw text over time and say something like "add this", "update the skill with this", "dump this in". When that happens:
- Append the raw sample as a new Before/After pair in [VOICE_EXAMPLES.md](VOICE_EXAMPLES.md). Draft the "after" if he didn't give one.
- If the sample reveals a new pattern (a phrase he always keeps, a filler not yet listed, a place a past cleanup overcorrected), fold it into the rules above directly, don't just file it away in the examples.
- Just do it and say what changed in one line. No need to ask permission first.
