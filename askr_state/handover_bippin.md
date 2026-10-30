# Handover: bippin

Last updated: 2026-10-30 16:19

*Source of truth: `handover_bippin.json`*


## Task
Built a complete voice interface for askr with local Whisper STT, wake-word detection, automatic user-specific calibration, live Terminal window with status display, and end-to-end delivery of spoken requests to Claude Code sessions.

## Discussion
The project fixed three critical issues blocking the user: random session kills (PreCompact hook was killing sessions during compaction), terminal windows opening unexpectedly (test harness was spawning real Terminal.app), and lack of voice support. Voice stages 1–7 are now complete: mic listener with adaptive noise floor, local Whisper transcription, fuzzy wake-word matching with per-user calibration, session digest and talker agent, delivery via terminal typing (primary) and Stop-hook inbox (fallback), live narration of responses, and a dedicated Terminal.app window with pinned status line showing listening state, mic level meter, and live partial transcription. All 746 tests pass. The user's feedback that the wake word wasn't heard and nothing was visible led directly to stages 6–7 (Terminal window, status display, calibration guards).

## Accomplishments
- [x] Stage 1: MicListener with adaptive energy segmenter, 600ms pre-roll, and Whisper STT with initial_prompt tuning
- [x] Stage 2: Talker agent with session digest, intent classification (instruction/question/clarify/chat), and Haiku 4.5 response generation
- [x] Stage 3: Delivery via Cursor extension terminal typing (primary) and Stop-hook inbox fallback
- [x] Stage 4: Narrator that streams session responses back as spoken audio via macOS say with voice lock
- [x] Stage 5: askr voice CLI command with profile loading and inline/window modes
- [x] Stage 6: Own Terminal.app window with pinned status line (listening/hearing/transcribing/thinking/speaking/sending), mic level meter with threshold marker, and live partial transcription
- [x] Stage 7: Fuzzy wake-word matching (one edit distance, filler skipping, exclusion of asked/asks) and automatic calibration on first launch learning user's Whisper spelling and speech floor
- [x] Calibration guards: rejects sentences, non-askr samples, background audio; requires ≥3 clean samples; deleted bogus profile from smoke test
- [x] Fixed PreCompact hook to observe-only (no kills); removed idle-session kill; removed mid-turn kill
- [x] Fixed test harness spawning real Terminal windows; added conftest sweep of uppercase config constants to tmp_path
- [x] Verified all 746 tests pass after voice subsystem completion
- [x] Committed and pushed stages 1–7 (commit aa7d16d)

## Next Actions
1. Run `cd ~/Desktop/grid && askr voice` and allow Terminal microphone access when prompted; say 'askr' 5 times during calibration
   *Why: Live verification of calibration on user's actual voice and speech floor learning*
2. Reload the Cursor window (Developer: Reload Window) so the updated extension loads and terminal typing works
   *Why: Extension changes in this session require reload; without it, voice prompts won't type into the terminal*
3. Test wake-word detection by saying 'askr, what's it doing?' and paste the 'heard: …' lines from the Terminal window if it still misses
   *Why: Diagnose whether Whisper's spelling of user's pronunciation matches the fuzzy matcher; if not, the exact spelling helps refine variants*
4. Monitor daemon.log for next PreCompact event to confirm Stage 1 diagnostics are working and determine whether Trigger A is losing the race (already_companioned=False) or opening companion but still losing (already_companioned=True)
   *Why: Verify that the observe-only PreCompact hook is logging correctly and diagnose any remaining session-targeting issues*
5. Monitor daemon.log for next slow cont recovery to confirm Stage 3 diagnostics show whether askr was legitimately waiting for a future reset_at or actually stalled mid-wait
   *Why: Verify that slow recovery diagnostics are working and identify any stalls in the continuation logic*

## Decisions
- Use local Whisper base.en int8 with initial_prompt 'Askr, run the tests.' for STT — Measured best accuracy on user's voice; avoids cloud latency and privacy concerns
- Fuzzy wake-word matching: one edit distance from asker/askr, after filler skipping (hey/ok/so/um/uh/etc.), excluding asked/asks/aster/ashes/asset — Fixed spelling list tuned on say(1) voice missed user's pronunciation; fuzzy matching + per-user calibration learns actual Whisper output
- Automatic calibration on first launch: user says 'askr' 5 times, learns Whisper's spelling and sets speech floor from user's volume — Eliminates fixed thresholds that don't adapt to user's mic, room, and voice; guards prevent background audio contamination
- Calibration only counts askr-like single words; rejects sentences, common words (you, the, asked, okay, hello, banana, a), and non-learnable spellings — Smoke test accidentally learned 'you' from YouTube audio; guards prevent similar contamination
- Calibration requires ≥3 clean samples before saving profile; otherwise prints hint about mic permissions — Prevents saving incomplete or noisy profiles; user can retry if needed
- askr voice opens own Terminal.app window (--here flag runs inline instead) — User feedback: no visibility into listening state; own window eliminates ambiguity about which terminal to use
- Pinned status line shows state (listening/hearing/transcribing/thinking/speaking/sending) with live mic level meter and threshold marker — User feedback: no indication of listening or transcription; visual feedback confirms the system is working
- Every heard line printed including ignored ones with reason (e.g. 'no wake word, ignored') — Debugging: user can see exactly what Whisper heard and why it was rejected
- PreCompact hook is observe-only; no kills, no checkpoints, only logging — Kills were firing on wrong sessions (cwd-based PID guess), killing idle sessions, and killing mid-turn sessions; logging is sufficient for diagnostics
- Delivery via Cursor extension terminal typing (primary) and Stop-hook inbox fallback — PostToolUse additionalContext is refused as prompt injection; terminal typing is reliable; inbox handles mid-turn fallback
- Talker enforces intent field and send/say rules: instruction always sent, say <30 words, never second-guess off-topic instructions — Early runs withheld off-topic instructions; enforcement ensures consistent behavior
- Use Haiku 4.5 for talker (not haiku-5-5 or sonnet models which return 429 over OAuth token) — Measured: haiku-4-5 works; haiku-5-5 and sonnet-5-5/4-6 return 429 over OAuth transport

## Failed Approaches
- Fixed spelling list for wake-word matching (askr, asker, askher, askar, ascar, oscar, aska, asca, askedr, askedher, asgar, asgr, askur) — Tuned on say(1) voice; missed user's actual pronunciation; no feedback when rejected
- Fixed speech threshold (0.004 RMS) — Doesn't adapt to user's mic, room, or voice; too high for some users, too low for others
- No visible status or transcription display — User had no way to know if system was listening or what it heard; led to confusion and false negatives
- Inline voice loop in the user's terminal — User feedback: ambiguous which terminal to use; own window eliminates confusion
- PostToolUse additionalContext for delivery — Claude treats it as prompt injection inside tool result and refuses; terminal typing is primary route
- Smoke-test harness without process isolation — Hung and left background processes; killed bash wrapper but not python child; fixed with start_new_session and killpg
- speech_rms using top 30% of frames — Silence diluted the measurement; switched to 90th percentile for more accurate floor
- PreCompact hook killing sessions on compaction — Killed wrong sessions (cwd-based PID guess), killed idle sessions, killed mid-turn sessions; removed entirely

## Files In Play
- `askr/voice/__init__.py`
- `askr/voice/calibrate.py`
- `askr/voice/listener.py`
- `askr/voice/loop.py`
- `askr/voice/stt.py`
- `askr/voice/wake.py`
- `askr/voice/session.py`
- `askr/voice/talker.py`
- `askr/voice/inbox.py`
- `askr/voice/terminal.py`
- `askr/voice/speaker.py`
- `askr/voice/narrator.py`
- `askr/voice/ui.py`
- `askr/hooks/pre_compact.py`
- `askr/hooks/stop.py`
- `askr/hooks/session_start.py`
- `askr/hooks/user_prompt_submit.py`
- `askr/cli/askr.py`
- `askr/ide/vscode-extension/extension.js`
- `tests/conftest.py`
- `tests/test_voice_calibrate.py`
- `tests/test_voice_listener.py`
- `tests/test_voice_talker.py`
- `tests/test_voice_delivery.py`
- `tests/test_voice_narrator.py`
- `tests/test_voice_loop.py`
- `tests/test_hook_capture.py`
- `tests/test_pre_compact.py`
- `requirements.txt`

## Relational Files
- `askr/voice/loop.py` (imports): Main entry point; orchestrates listener, transcriber, talker, speaker, narrator
- `askr/voice/calibrate.py` (imported_by): Called by loop.py on first launch or explicit request
- `askr/voice/listener.py` (imported_by): Provides MicListener and Segmenter for audio capture
- `askr/voice/stt.py` (imported_by): Provides Transcriber for Whisper STT
- `askr/voice/wake.py` (imported_by): Provides WakeGate for fuzzy wake-word matching
- `askr/voice/session.py` (imported_by): Provides Digest for session context
- `askr/voice/talker.py` (imported_by): Provides Talker for intent classification and response generation
- `askr/voice/speaker.py` (imported_by): Provides Speaker for TTS via macOS say
- `askr/voice/narrator.py` (imported_by): Provides Narrator for streaming session responses
- `askr/voice/terminal.py` (imported_by): Provides terminal typing and PID tracking
- `askr/voice/inbox.py` (imported_by): Fallback delivery route via Stop hook
- `askr/hooks/stop.py` (imports): Drains voice inbox as fallback when mid-turn
- `askr/hooks/session_start.py` (imports): Records session PID for voice targeting
- `askr/hooks/user_prompt_submit.py` (imports): Records session PID for voice targeting
- `askr/ide/vscode-extension/extension.js` (configures): Watches voice_prompt.json and types into terminal
- `tests/conftest.py` (tested_by): Isolates voice tests from real config and Terminal spawning
- `requirements.txt` (configures): Declares sounddevice and faster-whisper dependencies
