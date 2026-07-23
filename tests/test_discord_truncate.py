from askr.clients.discord import _truncate, _MAX_LEN


def test_short_text_untouched():
    assert _truncate("hello") == "hello"


def test_exact_limit_untouched():
    text = "a" * _MAX_LEN
    assert _truncate(text) == text


def test_long_text_cut_at_word_boundary_with_marker():
    text = ("word " * 500).strip()  # well over the limit
    result = _truncate(text)
    assert len(result) <= _MAX_LEN
    assert result.endswith("[truncated]")
    # nothing after the cut point should be a partial word fragment
    body = result.rsplit("\n… [truncated]", 1)[0]
    assert not body.endswith("wor")


def test_long_text_with_no_spaces_still_bounded():
    text = "x" * (_MAX_LEN + 500)
    result = _truncate(text)
    assert len(result) <= _MAX_LEN
    assert result.endswith("[truncated]")
