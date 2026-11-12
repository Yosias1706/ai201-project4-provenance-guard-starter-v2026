# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. My own writing is almost never called AI

Of 10 pieces of writing I wrote myself (each 80–250 words, a mix of casual and school writing), **at most 1 is labeled high-confidence AI**, and that holds in **each** of the three trials — not on average.

**Why this target:** A wrong accusation on a writing site costs the writer far more than a missed detection costs the site, so this is the number I care most about. 1 in 10 is still a real person accused, but I can't promise 0 with a perplexity signal that is known to dislike plain writing; any human piece that lands in "unsure" instead of "AI" counts as a pass here, which is exactly what I want the unsure band to absorb.

---

## 2. Clearly-AI and clearly-human text score far apart

Across 5 clearly AI-generated paragraphs and 5 clearly human ones (informal, personal, specific), the **average combined score of the AI set is at least 0.30 higher** than the average of the human set, in every trial. In addition, **no clearly-human paragraph scores higher than the lowest-scoring clearly-AI paragraph** in more than 1 of the 5 pairs.

**Why this target:** If the easy cases aren't well separated, the thresholds have nothing to work with and every label is a coin flip. 0.30 is the width of my "unsure" band — if the two groups are closer than that, they'd both end up in the middle, which would make the system useless even when the answer is obvious.

---

## 3. All three labels are reachable with real text

Of 9 calibration inputs — 3 I expect to be AI, 3 I expect to be human, 3 I judge borderline (formal human writing, lightly-edited AI) — **each of the three labels ("human", "unsure", "ai") is produced by at least 2 inputs** in every trial, and **at least 6 of the 9** land on the label I predicted.

**Why this target:** A label nobody can reach is a gap in the ranges, and a system that only ever says "unsure" never wrongly accuses anyone but tells nobody anything. Requiring 2 per label (not just 1) stops a single lucky input from hiding a band that is almost unreachable; 6 of 9 is honest about the borderline three being genuinely hard.

---

## 4. Every appeal is recorded and changes status

Of 5 appeals sent against real `content_id`s from earlier submissions, **5 of 5 return 200 with `status: "under_review"`, and 5 of 5 show up in `GET /log`** as a new entry after the original decision, with the original decision entry still unchanged. Of 3 appeals sent with a made-up `content_id`, **3 of 3 return 404** and add no `under_review` entry.

**Why this target:** The appeal is the only thing standing between a wrong accusation and nothing at all, so it can't be "usually works" — it has to be 5 of 5. The 404 half matters too: an appeal on a typo'd id that silently "succeeds" tells the writer their appeal is under review when nobody will ever see it.

---

## 5. Bad input never crashes the service

Of 6 malformed requests — empty `text`, whitespace-only `text`, no `text` field, `text: null`, `text` as a number, and 50,000 words of text — plus a body that is a JSON list instead of an object, **7 of 7 return a 4xx status with a JSON body containing an `error` field, and 0 return a 5xx**. A normal submission sent immediately afterward still returns 200.

**Why this target:** A crash on a malformed input is one of the most common real failures, and a 500 tells the caller nothing about what to fix. The follow-up normal request is there because a bad input that leaves the service broken for the next real writer is worse than the bad input itself.

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
