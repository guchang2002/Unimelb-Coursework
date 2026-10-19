"""VADER sentiment analysis — singleton wrapper."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score(text):
    """Return VADER compound/pos/neg/neu + label, or None if text too short."""
    if not text or len(text.strip()) < 5:
        return None

    s = _analyzer.polarity_scores(text)

    if s["compound"] >= 0.05:
        label = "positive"
    elif s["compound"] <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "compound": s["compound"],
        "pos":      s["pos"],
        "neg":      s["neg"],
        "neu":      s["neu"],
        "label":    label,
    }
