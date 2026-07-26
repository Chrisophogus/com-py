import argparse
import ast
import json
import pickletools
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
EXCLUDED_DIRECTORIES = {".git", ".venv", "__pycache__"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
VIDEO_SUFFIXES = {".mkv", ".mp4"}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".txt", ".gitattributes", ".gitignore", ".example"}
FORBIDDEN_TRACKED_NAMES = {".DS_Store", ".env"}


def parse_args():
    parser = argparse.ArgumentParser(description="Validate repository source and artefacts.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check ignored local files as well as tracked files.",
    )
    return parser.parse_args()


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def local_files():
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(ROOT).parts)
    )


def validate_python(path):
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))


def validate_json(path):
    with path.open("r", encoding="utf-8") as file:
        json.load(file)


def validate_jsonl(path):
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if line.strip():
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"line {line_number}: {exc}") from exc


def validate_image(path):
    with Image.open(path) as image:
        image.verify()


def validate_video(path):
    subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )


def validate_pickle(path):
    with path.open("rb") as file:
        for _ in pickletools.genops(file.read()):
            pass


def validate_file(path):
    suffix = path.suffix.lower()
    if suffix == ".py":
        validate_python(path)
        return "python"
    if suffix == ".json":
        validate_json(path)
        return "json"
    if suffix == ".jsonl":
        validate_jsonl(path)
        return "jsonl"
    if suffix in IMAGE_SUFFIXES:
        validate_image(path)
        return "image"
    if suffix in VIDEO_SUFFIXES:
        validate_video(path)
        return "video"
    if suffix == ".pkl":
        validate_pickle(path)
        return "pickle"
    if suffix == ".toml":
        with path.open("rb") as file:
            tomllib.load(file)
        return "toml"
    if suffix in TEXT_SUFFIXES or path.name in {".gitignore", ".gitattributes", ".env", ".env.example"}:
        path.read_text(encoding="utf-8")
        return "text"
    with path.open("rb") as file:
        file.read(1)
    return "other"


def validate_git():
    result = subprocess.run(
        ["git", "fsck", "--full"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "git fsck failed")


def validate_environment():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stdout + result.stderr).strip()
        raise RuntimeError(detail or "pip check failed")


def main():
    args = parse_args()
    files = local_files() if args.all else tracked_files()
    errors = []
    counts = Counter()

    for path in files:
        relative = path.relative_to(ROOT)
        if not args.all and (
            path.name in FORBIDDEN_TRACKED_NAMES
            or path.suffix.lower() in {".pyc", ".pyo"}
            or relative.parts[0] in {".codex", ".venv"}
        ):
            errors.append(f"{relative}: local/generated file must not be tracked")
            continue
        try:
            counts[validate_file(path)] += 1
        except Exception as exc:
            errors.append(f"{relative}: {exc}")

    for name, check in (("Git", validate_git), ("environment", validate_environment)):
        try:
            check()
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    scope = "local" if args.all else "repository"
    summary = ", ".join(f"{category}={count}" for category, count in sorted(counts.items()))
    print(f"Checked {len(files)} {scope} files ({summary}).")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Repository checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
