"""
Signal two: the style signal.

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures, each on its own scale, then flipped and scaled so that higher
means more AI-like, then weighted into one 0–1 score:

    sentence_length_spread   coefficient of variation of words per sentence.
                             Higher = lumpier = more human.
    type_token_ratio         moving-average TTR over 50-word windows.
                             Higher = more varied vocabulary = more human.
    punctuation_density      "expressive" marks (dashes, semicolons, colons,
                             parentheses, ? ! and quotes) per sentence.
                             Higher = more human.

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

Blind spot: this signal cannot read. Anything that changes the shape without
changing the substance moves it — typos, broken-up sentences, a pasted
quotation, a few dashes sprinkled in. It is also weak on short text: under
three sentences there's no spread to measure, so that measure goes neutral.

    python stylometry.py "some text to look at"
"""

import re
import statistics


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures ───────────────────────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    Coefficient of variation (stdev / mean) of words per sentence.

    0.0 = every sentence the same length. Higher = more varied = more human.
    Fewer than two sentences has no spread to measure, so this returns 0.0 and
    `measure_scores` treats spread as neutral below three sentences rather
    than reading a single sentence as evidence of anything.
    """
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return 0.0
    return round(statistics.stdev(lengths) / statistics.mean(lengths), 4)


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words, averaged over 50-word moving windows.

    Plain TTR falls as text gets longer, so a 300-word piece and a 100-word
    one aren't comparable on it. A fixed window fixes that. Text shorter than
    one window falls back to plain TTR. Higher = more varied = more human.
    """
    toks = words(text)
    if not toks:
        return 0.0
    window = 50
    if len(toks) <= window:
        return round(len(set(toks)) / len(toks), 4)
    ratios = [
        len(set(toks[i:i + window])) / window
        for i in range(len(toks) - window + 1)
    ]
    return round(statistics.mean(ratios), 4)


def punctuation_density(text: str) -> float:
    """
    Expressive punctuation marks per sentence.

    Counts dashes, semicolons, colons, parentheses, question and exclamation
    marks and quotes. Commas and full stops are left out because every writer
    uses them; the marks that vary between writers are the interesting ones.
    Higher = more human.
    """
    n_sentences = max(len(sentences(text)), 1)
    marks = re.findall(r"—|–|--|\s-\s|[;:()!?\"“”]", text)
    return round(len(marks) / n_sentences, 4)


# ── Combining them ───────────────────────────────────────────────────────────

# Spread and punctuation separated my calibration texts. TTR ran BACKWARDS on
# them: the clearly-AI paragraph had the most varied vocabulary (0.92) and the
# plain human one the least (0.78). It's still computed and printed so I can
# watch it, but it gets no weight — a measure pointing the wrong way only adds
# noise.
SPREAD_WEIGHT = 0.55
TTR_WEIGHT = 0.0
PUNCT_WEIGHT = 0.45


def _clamp(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def measure_scores(text: str) -> dict:
    """Each measure flipped and scaled onto 0–1, higher = more AI-like."""
    # CV of 0.15 or less -> 1.0 (sentences marching in step); 0.65+ -> 0.0.
    # Under three sentences there isn't enough to judge, so neutral 0.5.
    if len(sentences(text)) < 3:
        spread = 0.5
    else:
        spread = _clamp((0.65 - sentence_length_spread(text)) / 0.50)

    # MATTR 0.90+ -> 0.0; 0.65 or less -> 1.0.
    ttr = _clamp((0.90 - type_token_ratio(text)) / 0.25)

    # No expressive marks -> 1.0; one every two sentences or more -> 0.0.
    punct = _clamp(1.0 - punctuation_density(text) / 0.5)

    return {"spread": round(spread, 4), "ttr": round(ttr, 4), "punct": round(punct, 4)}


def style_signal(text: str) -> float:
    """The style signal as a 0–1 score. **Higher means more likely AI.**"""
    parts = measure_scores(text)
    score = (
        SPREAD_WEIGHT * parts["spread"]
        + TTR_WEIGHT * parts["ttr"]
        + PUNCT_WEIGHT * parts["punct"]
    )
    return round(_clamp(score), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"scaled (higher = AI)     {measure_scores(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
