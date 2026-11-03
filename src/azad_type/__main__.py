"""Desktop entry point and pipe-friendly, offline conversion commands."""
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="Azad Type — offline Persian/English typing")
    sub = parser.add_subparsers(dest="command")
    for name in ("convert", "manual"):
        p = sub.add_parser(name)
        p.add_argument("text", nargs="?", help="Text; omit to read stdin")
        if name == "manual":
            p.add_argument("--direction", choices=("toggle", "fa", "en"), default="toggle")
    sub.add_parser("doctor", help="Report local prerequisites without starting a keyboard hook")
    args = parser.parse_args()
    if args.command == "doctor":
        import importlib.util
        print(json.dumps({"python": sys.version.split()[0], "windows": sys.platform == "win32",
                          "tkinter": importlib.util.find_spec("tkinter") is not None,
                          "network_required": False, "hook_started": False}, indent=2))
    elif args.command in ("convert", "manual"):
        from .engine import Engine
        from .dictionary import Dictionary
        # CLI is deterministic: use built-in original vocabulary; no profile reads.
        engine = Engine(Dictionary())
        text = args.text if args.text is not None else sys.stdin.read()
        result = (engine.manual_convert(text, direction=args.direction) if args.command == "manual"
                  else engine.convert_text(text))
        sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
        sys.stdout.write(result + ("\n" if args.text is not None else ""))
    else:
        from .app import launch
        launch()


if __name__ == "__main__":
    main()
