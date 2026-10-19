from shared.sentiment import score


def test_score_returns_none_for_empty_or_too_short_text():
    assert score("") is None
    assert score("ok") is None


def test_score_positive_text():
    result = score("I love this beautiful sunny day in Melbourne")
    assert result is not None
    assert result["label"] == "positive"
    assert result["compound"] >= 0.05


def test_score_negative_text():
    result = score("I hate this horrible storm and awful weather")
    assert result is not None
    assert result["label"] == "negative"
    assert result["compound"] <= -0.05