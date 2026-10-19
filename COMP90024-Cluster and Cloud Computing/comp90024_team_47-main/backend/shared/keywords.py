"""Topic keyword buckets — for tagging posts.

Uses word-boundary regex matching to avoid false positives like
'rain' matching 'Ukraine' or 'vic' matching 'service'.
"""

import re

WEATHER_KEYWORDS = {
    "rain":    ["rain", "raining", "rainy", "wet", "drizzle", "shower"],
    "cold":    ["cold", "freezing", "chilly", "frost", "shiver", "frigid"],
    "hot":     ["hot", "heat", "heatwave", "scorching", "boiling", "sweltering", "melting"],
    "storm":   ["storm", "thunder", "lightning", "tempest", "hail"],
    "wind":    ["wind", "windy", "gale", "breeze", "gusty"],
    "snow":    ["snow", "snowy", "blizzard"],
    "sunny":   ["sunny", "sunshine", "blue sky", "clear sky"],
    "cloudy":  ["cloud", "cloudy", "overcast", "grey sky"],
    "weather": ["weather", "forecast", "climate"],
}

BEVERAGE_KEYWORDS = {
    "coffee":     ["coffee", "espresso", "latte", "cappuccino",
                   "flat white", "long black", "macchiato"],
    "tea":        ["tea", "chai"],
    "hot_choc":   ["hot chocolate", "hot cocoa"],
    "cold_drink": ["iced coffee", "cold brew", "smoothie", "milkshake"],
    "beer":       ["beer", "lager", "ale"],
    "wine":       ["wine", "wines"],
}


# Pre-compile regex patterns for each (category, keyword) pair to avoid
# re-compiling on every call. \b = word boundary (no false positive on
# substrings like 'rain' in 'Ukraine').
def _compile_patterns(keyword_dict):
    compiled = {}
    for category, words in keyword_dict.items():
        compiled[category] = [
            re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
            for w in words
        ]
    return compiled


_WEATHER_PATTERNS  = _compile_patterns(WEATHER_KEYWORDS)
_BEVERAGE_PATTERNS = _compile_patterns(BEVERAGE_KEYWORDS)


def extract_keywords(text, keyword_dict):
    """Return list of category names whose keywords appear as full words in text.
    
    Each category counted at most once. Uses word-boundary matching:
    'rain' matches 'rain', 'rains', 'rained' as separate words but NOT 'Ukraine'.
    """
    if not text:
        return []
    
    # Pick pre-compiled pattern table by identity (or fallback for new dicts)
    if keyword_dict is WEATHER_KEYWORDS:
        patterns = _WEATHER_PATTERNS
    elif keyword_dict is BEVERAGE_KEYWORDS:
        patterns = _BEVERAGE_PATTERNS
    else:
        patterns = _compile_patterns(keyword_dict)
    
    matched = []
    for category, regex_list in patterns.items():
        for rx in regex_list:
            if rx.search(text):
                matched.append(category)
                break  # category counted once
    return matched
