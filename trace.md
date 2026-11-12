# Trace — how a submission moves through Provenance Guard

Written before building anything (Milestone 1). This is the plan the code has to keep.

---

## 1. The path, from arriving to the label

1. **The request arrives at `POST /submit`** (`app.py::submit`). Flask parses the JSON body.
   *Adds:* nothing yet — just a dict with `text` and `creator_id`.
2. **Input check.** The route checks that `text` is a non-empty string, not absurdly long, and that `creator_id` is present. Anything bad stops here with a 400/413 and a message that says what was wrong.
   *Adds:* the guarantee that everything after this point has real text to work on.
3. **A content id is minted.** `uuid4` gives the submission an id.
   *Adds:* the handle the appeal path and the log use to find this decision again later.
4. **Signal one — `detector.model_signal(text)`.** gpt2 runs locally and measures how predictable the text is (perplexity), squashed onto 0–1.
   *Adds:* `model_score` (higher = more AI-like).
5. **Signal two — `stylometry.style_signal(text)`.** Measures the shape of the text: sentence-length spread, vocabulary variety, punctuation habits.
   *Adds:* `style_score` (higher = more AI-like).
6. **Combine — `scoring.combine_signals(model, style)`.** Turns two numbers into one, including a rule for when the two disagree.
   *Adds:* `combined_score`, which the response calls `confidence`.
7. **Label — `scoring.score_to_label(score)`.** Maps the score into one of three bands and picks the sentence a reader sees.
   *Adds:* `guess` (`human` / `unsure` / `ai`) and `label` (the full sentence).
8. **Log, then answer.** `audit.log_decision(...)` appends one JSON line to `logs/audit.jsonl` with every number above and `status: "decided"`. Then the route returns the JSON response. The reader sees the label.

If the writer disagrees, there is a second, shorter path: `POST /appeal` → check the content id exists in the log → `audit.log_appeal(...)` appends an entry with `status: "under_review"` and their reasoning → confirm to the writer.

---

## 2. The two signals

### Signal one — `detector.py` (the model signal)

- **What it measures:** how predictable the text is to gpt2 — perplexity, i.e. how surprised the model is by each next word. Low perplexity → high score.
- **Why it might differ:** a language model writes by picking likely next words, so text a model produced is text a model finds easy to predict. People wander: odd word choices, specific details, abrupt turns.
- **What it can't see:** *who wrote it.* Predictability isn't authorship. Plain writing — short sentences, common words, someone writing in a second language, a younger writer, someone being deliberately simple — is predictable too, and scores like AI. The other direction also fails: AI text asked to be ornate or full of rare words reads as surprising, so it scores human. It also can't see meaning, intent, or whether a person edited the output.

### Signal two — `stylometry.py` (the style signal)

- **What it measures:** the text as a shape, not as language. How much sentence lengths vary, what fraction of words are unique, how much (and what kind of) punctuation there is.
- **Why it might differ:** generated prose tends toward even, mid-length sentences, safe vocabulary, and tidy comma-and-period punctuation. Human writing is lumpier — a three-word sentence next to a forty-word one, dashes, parentheses, semicolons.
- **What it can't see:** *anything the text says.* It cannot read. Anything that changes the shape without changing the substance moves it — adding typos, chopping sentences up, inserting a quote or a list, adding a few dashes. That is cheap to do on purpose. It is also unreliable on short text (two sentences give almost no "spread" to measure) and type-token ratio falls naturally as text gets longer, so length alone moves it.

---

## 3. The false positive, followed through

Maria writes in English as her second language. She submits a 120-word personal essay: short sentences, everyday vocabulary she's confident about, no dashes or semicolons.

- **Signal one:** gpt2 finds her words easy to predict. Perplexity ~30 → `model_score` around 0.65.
- **Signal two:** her sentences are all similar lengths and she uses only commas and periods → `style_score` around 0.6–0.7.
- **Combined:** both signals lean AI, so they *agree*, and agreement is exactly what a combining rule trusts. If the AI threshold is low, she lands in "AI".
- **What she reads:** if the label says "This was written by AI," that is an accusation she didn't earn and can't easily argue with — she has no way to show what a perplexity is.
- **What she can do:** the only thing standing between her and nothing is `POST /appeal`. She sends her content id and a sentence of reasoning, the item moves to `under_review`, and the original decision stays in the log so a person can see both.

What this decides:
- The AI threshold has to be **high** — plain writing that both signals mildly dislike should land in *unsure*, not *AI*. "High-confidence AI" should need both signals pointing strongly the same way.
- The labels must never say "you used AI" as fact. Even the AI label says "likely" and points to the appeal.
- The response must always carry the `content_id`, because without it she can't appeal.

---

## 4. The two endpoint contracts

### `POST /submit`

**Request** (JSON body):

| Field | Type | Required | Rules |
|---|---|---|---|
| `text` | string | yes | Non-empty after trimming. Max 20,000 characters. Must be long enough for the model to score (a few words at least). |
| `creator_id` | string | yes | Non-empty. Who submitted it; recorded in the log. |

**Response — 200:**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | UUID for this submission. Needed to appeal. |
| `guess` | string | `"human"`, `"unsure"`, or `"ai"`. |
| `confidence` | float 0–1 | The combined score. 0 = confidently human, 1 = confidently AI. |
| `label` | string | The full sentence a reader sees. |
| `model_score` | float 0–1 | Signal one on its own (higher = more AI-like). |
| `style_score` | float 0–1 | Signal two on its own (higher = more AI-like). |
| `status` | string | `"decided"` on a fresh submission. |

**Errors:** every error is JSON `{"error": "<code>", "message": "<plain sentence>"}`.

| Status | `error` | When |
|---|---|---|
| 400 | `invalid_json` | Body isn't a JSON object. |
| 400 | `missing_text` | `text` absent, null, not a string, or blank. |
| 400 | `missing_creator_id` | `creator_id` absent or blank. |
| 400 | `text_too_short` | Too few words to score. |
| 413 | `text_too_long` | Over 20,000 characters. |
| 503 | `detector_unavailable` | The model couldn't load. |

### `POST /appeal`

**Request:**

| Field | Type | Required | Rules |
|---|---|---|---|
| `content_id` | string | yes | Must match a submission already in the log. |
| `reasoning` | string | yes | Non-empty; the writer's explanation. Max 5,000 characters. |

**Response — 200:**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | Echoed back. |
| `status` | string | Always `"under_review"`. |
| `original_guess` | string | What the system decided before the appeal. |
| `message` | string | Plain confirmation to the writer. |

**Errors:** 400 `invalid_json` / `missing_content_id` / `missing_reasoning` / `reasoning_too_long`; 404 `unknown_content_id` when the id isn't in the log.

Read back: someone could build a client against this without asking me — every field has a type, a direction, and an error code for each way it can go wrong.
