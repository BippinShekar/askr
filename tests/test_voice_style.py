from askr.voice.style import SILENT, concise


def test_concise_caps_sentences_and_words():
    para = ("I've gone ahead and sent the instruction. The tests are now running in the session. "
            "I'll let you know when they finish. Here are the details.")
    assert concise(para) == "I've gone ahead and sent the instruction. The tests are now running in the session."
    long = " ".join(["word"] * 50)
    assert concise(long, max_words=10).endswith("…") and len(concise(long, max_words=10).split()) == 10


def test_concise_strips_markdown_and_silence():
    assert concise("**done**, it's on `main`") == "done, it's on main"
    assert concise(SILENT) == "" and concise("") == ""
