"""Summarize a MARIDA zip archive without extracting its large raster files."""

import argparse
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


def inspect(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Archive not found: {path}")

    with ZipFile(path) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        print(f"Archive: {path}")
        print(f"Files: {len(members)}")
        print("Extensions:")
        for extension, count in Counter(Path(item.filename).suffix.lower() or "[none]" for item in members).most_common():
            print(f"  {extension}: {count}")
        print("Sample paths:")
        for item in members[:30]:
            print(f"  {item.filename}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "archive",
        nargs="?",
        type=Path,
        default=Path("backend/data/MARIDA.zip"),
        help="Path to the downloaded dataset zip",
    )
    args = parser.parse_args()
    inspect(args.archive)


if __name__ == "__main__":
    main()
