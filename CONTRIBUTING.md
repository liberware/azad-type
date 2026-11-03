# Contributing to Azad Type

Bug reports, vocabulary improvements and code are all welcome.

## Before you open a pull request

Azad Type needs Python 3.11+ with Tkinter and has no third-party runtime dependencies. Please keep it that way.

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

Run the tests on Windows if your change touches `windows.py`, because the Win32 tests are skipped on other systems. Add a test for any change to how a word is converted.

## Ground rules

- Keep it offline: no network clients, telemetry or automatic updates.
- Never log or save what people type.
- Only submit code and word lists you have the right to release under the MIT license, and say where a word list came from.
- Global typing must fail safe. If a field can't be verified, leave it alone.

By contributing, you agree that your work is released under the [MIT license](LICENSE).
