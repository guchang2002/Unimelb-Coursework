from shared.cities import CITIES, infer_city


def test_cities_contains_four_target_cities():
    assert set(CITIES.keys()) == {"Melbourne", "Sydney", "Brisbane", "Perth"}


def test_infer_city_from_full_city_name():
    assert infer_city("It is raining in Melbourne today") == ("Melbourne", "content_keyword")


def test_infer_city_from_common_alias():
    assert infer_city("Cold morning in brissie") == ("Brisbane", "content_keyword")


def test_infer_city_uses_word_boundary_to_avoid_false_positive():
    # "vic" was deliberately removed because it is too noisy, and should not match inside words.
    assert infer_city("This service is available today") == (None, None)


def test_infer_city_returns_none_for_empty_text():
    assert infer_city("") == (None, None)