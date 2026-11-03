# Validation · 3 November 2026

Checked on Windows x64 with Python 3.12.10 and Tkinter.

## Checks completed

- `python -m unittest discover -s tests -v`: **39 tests passed**. The Tk GUI was instantiated in withdrawn windows under a temporary profile; no desktop typing service was started.
- `python -m compileall -q src run.py tools/build_release.py`: passed.
- CLI smart conversion `sghl GitHub API` produced `سلام GitHub API`; forced mapping `sghl` produced `سلام`.
- `python run.py doctor` reported Windows, Tkinter available, no network required and no hook started.
- The source release ZIP was built and its integrity checked. The CLI runs from a fresh extracted copy.

Language tests include English/Persian ambiguity, technical strings, punctuation-letter keys, whitespace, normalization, short words and context. Dictionary tests include disk failure without memory mutation, invalid import rollback, persistence, formula-like entry rejection and all three export round-trips. GUI tests cover selection-only changes, compound conversion undo and settings persistence without writing text. Win32 tests verify native INPUT ABI layout, supported/protected field gates, focus/suffix checks, shortcut repeat handling, injected-event invalidation, navigation resets, native selection mismatch cancellation and immediate undo.

## Limits

No live global hook, SendInput interaction, privileged process, third-party editor or native TSF runtime was tested. The Windows adapter tests replace OS-dependent operations with mocks except for checking ctypes structure layout. Unknown fields remain unsupported. GUI construction and actions were tested programmatically; the interface has not had a visual review. No whole-program security conclusion is claimed.
