#!/usr/bin/env python3
"""批量替换项目中的"异象"为"异象"。"""

from pathlib import Path

ROOT = Path("c:/Users/34773/Desktop/tards开发库")

# File extensions to process
EXTENSIONS = {".py", ".md", ".html", ".txt"}

# Directories to skip
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
}

def should_process(path: Path) -> bool:
    """Check if file should be processed."""
    # Skip hidden dirs and special dirs
    for part in path.parts:
        if part.startswith(".") and part not in {".agents"}:
            if part in {".git", ".venv"}:
                return False
    for skip in SKIP_DIRS:
        if skip in path.parts:
            return False
    return path.suffix.lower() in EXTENSIONS

def replace_in_file(path: Path) -> int:
    """Replace '异象' with '异象' in a file. Return count of replacements."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return 0

    if "异象" not in content:
        return 0

    new_content = content.replace("异象", "异象")
    count = content.count("异象")

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return count

def main():
    total_files = 0
    total_replacements = 0
    processed = []

    for path in ROOT.rglob("*"):
        if path.is_file() and should_process(path):
            count = replace_in_file(path)
            if count > 0:
                total_files += 1
                total_replacements += count
                processed.append((str(path.relative_to(ROOT)), count))

    print(f"Processed {total_files} files, {total_replacements} replacements")
    print("\nTop files by replacement count:")
    for rel_path, count in sorted(processed, key=lambda x: -x[1])[:20]:
        print(f"  {count:4d}  {rel_path}")

if __name__ == "__main__":
    main()
