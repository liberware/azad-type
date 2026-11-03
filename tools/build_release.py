"""Build a deterministic source-only release from an explicit file list."""
from hashlib import sha256
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
PREFIX = f"AzadType-{VERSION}"


def release_files():
    paths = [ROOT / name for name in ("README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "pyproject.toml", "run.py", "tools/build_release.py", "docs/VALIDATION.md")]
    for directory in ("src", "tests"):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file()
                     and path.suffix in {".py", ".md"} and "__pycache__" not in path.parts)
    return sorted(set(paths))


def build():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    target = output / f"{PREFIX}-source.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files():
            info = zipfile.ZipInfo(f"{PREFIX}/{path.relative_to(ROOT).as_posix()}", (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Release ZIP failed its integrity check")
    digest = sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(f"{digest}  {target.name}\n", encoding="ascii")
    print(f"Created {target.name}: {target.stat().st_size:,} bytes, {len(release_files())} files")
    print(f"SHA256 {digest}")


if __name__ == "__main__":
    build()
