from app.services.tag_generator import _normalize_tags, _parse_tag_array


def test_lowercases_and_dedupes():
    assert _normalize_tags(["Fantasy", "fantasy", "FANTASY"]) == ["fantasy"]


def test_hyphens_collapse_whitespace():
    assert _normalize_tags(["coming of age"]) == ["coming-of-age"]


def test_accepts_already_hyphenated():
    assert _normalize_tags(["sci-fi", "coming-of-age"]) == ["sci-fi", "coming-of-age"]


def test_rejects_punctuation_other_than_hyphen():
    # sci-fi is fine, sci_fi and sci/fi are not
    assert _normalize_tags(["sci-fi", "sci_fi", "sci/fi"]) == ["sci-fi"]


def test_drops_meta_tags():
    assert _normalize_tags(["fantasy", "favorites", "to-read", "tbr", "recommended"]) == ["fantasy"]


def test_drops_uk_spelling_meta_tag():
    assert _normalize_tags(["favourites", "fantasy"]) == ["fantasy"]


def test_caps_at_five():
    result = _normalize_tags(["a", "b", "c", "d", "e", "f", "g"])
    assert len(result) == 5
    assert result == ["a", "b", "c", "d", "e"]


def test_rejects_too_long():
    assert _normalize_tags(["a" * 31]) == []


def test_allows_max_length():
    assert _normalize_tags(["a" * 30]) == ["a" * 30]


def test_rejects_empty_strings():
    assert _normalize_tags(["", " ", "fantasy"]) == ["fantasy"]


def test_rejects_non_string_entries():
    # Defensive — should not crash on mixed types
    assert _normalize_tags(["fantasy", None, 42, {"x": 1}]) == ["fantasy"]


def test_preserves_order_of_first_occurrence():
    assert _normalize_tags(["scifi", "fantasy", "scifi", "literary"]) == ["scifi", "fantasy", "literary"]


def test_rejects_leading_hyphen():
    # Regex requires [a-z0-9] as the first character
    assert _normalize_tags(["-fantasy"]) == []


def test_empty_input():
    assert _normalize_tags([]) == []


def test_parse_strips_json_fence():
    assert _parse_tag_array('```json\n["scifi", "dystopia"]\n```') == ["scifi", "dystopia"]


def test_parse_strips_bare_fence():
    assert _parse_tag_array('```\n["fantasy"]\n```') == ["fantasy"]


def test_parse_extracts_embedded_array():
    assert _parse_tag_array('Sure! Here you go: ["scifi", "dystopia"] hope that helps') == ["scifi", "dystopia"]


def test_parse_returns_empty_on_garbage():
    assert _parse_tag_array("not json at all") == []


def test_parse_returns_empty_on_object_shape():
    # Claude sometimes slips into {"tags": [...]} despite the prompt.
    # We return [] rather than silently extracting — the warning log on
    # empty normalization in generate_book_tags will reveal it.
    assert _parse_tag_array('{"tags": ["scifi"]}') == []
