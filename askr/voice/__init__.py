"""
askr voice — talk to a running Claude Code session.

listener  mic -> utterances (energy segmentation, muted while askr speaks)
stt       utterance audio -> text (local faster-whisper)
wake      "askr ..." gate plus a follow-up window for back-and-forth
"""
