"""4 Australian capital cities — coordinates, state, and city inference.

Uses word-boundary matching to avoid false positives like 'vic' matching 'service'.
"""

import re

CITIES = {
    "Melbourne": {"lat": -37.8136, "lon": 144.9631, "state": "VIC"},
    "Sydney":    {"lat": -33.8688, "lon": 151.2093, "state": "NSW"},
    "Brisbane":  {"lat": -27.4698, "lon": 153.0251, "state": "QLD"},
    "Perth":     {"lat": -31.9505, "lon": 115.8605, "state": "WA"},
}

CITY_NAMES = list(CITIES.keys())

# Lower-cased keywords for inferring city from text content
CITY_KEYWORDS = {
    "Melbourne": ["melbourne", "melb", "melbo", "victoria"],   # dropped "vic" — too noisy
    "Sydney":    ["sydney", "syd"],                            # dropped "nsw" — too short, too noisy
    "Brisbane":  ["brisbane", "brissie", "brizzy", "queensland"],  # dropped "qld" too
    "Perth":     ["perth"],
}


# Pre-compile word-boundary regex patterns
def _compile_patterns():
    compiled = {}
    for city, words in CITY_KEYWORDS.items():
        compiled[city] = [
            re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
            for w in words
        ]
    return compiled


_CITY_PATTERNS = _compile_patterns()


def infer_city(text):
    """Infer city from text content. Returns (city_name, source) or (None, None).
    
    Uses word-boundary matching: 'melb' matches 'melb' but not 'asselmblage'.
    """
    if not text:
        return (None, None)

    for city, regex_list in _CITY_PATTERNS.items():
        for rx in regex_list:
            if rx.search(text):
                return (city, "content_keyword")
    return (None, None)
