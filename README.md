# Azad Type · آزاد تایپ

An offline Persian/English typing utility, written in Python and released under the MIT license. Leave the keyboard on English (US): `sghl` becomes `سلام`, while `GitHub`, `API`, URLs and known English words stay readable.

This is a working first version of the core idea, with a deliberately small vocabulary and limited editor support. See [scope and remaining work](#scope-and-remaining-work).

## Run

Requires Python 3.11+ with Tkinter. The standard Windows Python installer includes Tkinter. There are no third-party runtime dependencies, services or administrator requirements.

```powershell
python run.py
```

The writing desk opens with global typing **off**. Try `sghl GitHub` and click **Smart convert**, or type a known word followed by Space. **Map selection / all** forces physical-key mapping in either direction; **Undo** restores the previous text.

The command line also works without starting the GUI or a keyboard hook:

```powershell
python run.py convert "sghl GitHub API"
python run.py manual --direction fa "sghl"
python run.py doctor
```

Omit the text argument to read standard input. CLI conversion uses the built-in vocabulary, regardless of desktop profile settings. Install the package optionally with `python -m pip install .`, then use `azad-type`.

## What works

- Dictionary-backed automatic English-layout → Persian conversion with an explanation for each decision.
- Known English, technical identifiers, email, URL, version and path protection. Unknown words are preserved.
- Manual bidirectional layout mapping, local writing desk, selection conversion, copy and undo.
- Optional Persian digits and punctuation; Arabic kaf/yeh normalization.
- Personal Persian/protected-English dictionary with atomic local persistence and validated JSON, CSV and TXT import/export. Exports contain **personal entries only**.
- Explicitly enabled Windows global typing for allowlisted applications and verified native text controls, with immediate conversion undo and manual shortcuts.

The seed vocabulary is intentionally small. Extend it with your own terms or appropriately licensed word lists. Automatic recognition is a deterministic heuristic, not a language model or phonetic transliterator. Manual mapping deliberately converts English terms too.

## Windows global typing

In **Windows integration**, enter application executable basenames (comma-separated), then click **Enable desktop typing**. The allowlist is saved, but the service never starts automatically. Closing the application unhooks it.

Only writable classic `Edit` / single-line `RichEdit` fields on an English layout are supported. Password, read-only, unknown, custom-rendered and multiline RichEdit fields are skipped. Browser fields, WinUI, modern Notepad, terminals and many office editors are therefore unsupported. Even an allowed executable must pass the field checks. The backend confirms the native text/selection and focus before changing text; it cannot guarantee atomicity against every possible focus race or application rewrite.

Automatic replacement occurs on **Space**. Enter and Tab always pass through because they can submit forms or move focus. Cursor navigation, mouse actions and focus changes invalidate tracked word/undo state. Native selection commands do not access the clipboard; global selection mapping is bounded to 8,192 single-line BMP characters. No global hook or injected input was exercised during validation; adapter behavior is tested with mocks. Treat broader editor compatibility as future work.

| Shortcut | Action |
|---|---|
| Backspace immediately after automatic conversion | Restore the original keys and space |
| Ctrl + Alt + Space | Map the tracked previous word |
| Ctrl + Alt + Enter | Map selected text |
| Ctrl + Alt + U | Undo the immediately preceding manual conversion |
| Ctrl + Alt + D | Add the selected word; alphabet determines its dictionary |
| Ctrl + Alt + P | Pause / resume |

## Vocabulary files

UTF-8 JSON:

```json
{"version": 1, "fa": ["واژه"], "en": ["MyProduct"]}
```

CSV uses exactly `word,language` as its header and `fa`/`en` language values. TXT accepts one word per line, infers the language from its alphabet, or accepts explicit `fa<TAB>word` / `en<TAB>word` prefixes. Imports validate the entire file before committing changes. Limit: 10 MiB / 100,000 imported entries.

## Privacy and storage

The implementation contains no network client, telemetry, updater, cloud translation or automatic startup registration. Writing-desk text is not saved. Global typing keeps transient word/undo state in memory and reads text from eligible classic controls to verify edits; it does not write keystroke logs. Copy is an explicit local clipboard action.

Settings and personal vocabulary live in `%LOCALAPPDATA%\AzadType` on Windows, or `~/.local/share/AzadType` elsewhere. These are ordinary local JSON files. The writing desk and CLI work on other platforms with Tkinter; system-wide integration is Windows-only.

## Scope and remaining work

Not implemented: a large vocabulary, morphology/frequency scoring, per-editor UI Automation, native TSF, guaranteed bidi paragraph management, direct typing/Shift/Caps modes, configurable global hotkeys, tray/startup handling, external-app font management, translation or signed updates. The writing desk relies on Tk/platform text rendering; complex mixed-direction editing can differ from native word processors. The UI is English with Persian examples rather than fully localized.

## Validate and package

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python tools/build_release.py
```

Tests cover language decisions, technical strings, dictionary transactions, GUI conversion/undo and adapter state with mocked Windows calls. They do not start a global keyboard hook. The release builder packages an explicit list of source, test and documentation files.

See [validation notes](docs/VALIDATION.md) and [how to contribute](CONTRIBUTING.md).
