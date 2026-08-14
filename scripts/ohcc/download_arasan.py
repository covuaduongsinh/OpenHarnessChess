"""Place or verify Arasan binary (MIT). Does not download GPL engines."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR_BIN = ROOT / "vendor" / "arasan" / "bin"
NOTICE = ROOT / "vendor" / "arasan" / "NOTICE.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install a local Arasan UCI binary into vendor/arasan/bin (MIT only)."
    )
    parser.add_argument(
        "--from",
        dest="source",
        type=Path,
        help="Path to an existing Arasan binary to copy into vendor/arasan/bin/",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check whether a binary is resolvable",
    )
    args = parser.parse_args(argv)

    VENDOR_BIN.mkdir(parents=True, exist_ok=True)
    target_name = "arasan.exe" if sys.platform.startswith("win") else "arasan"
    target = VENDOR_BIN / target_name

    if args.source:
        src = args.source.expanduser().resolve()
        if not src.is_file():
            print(f"Source not found: {src}", file=sys.stderr)
            return 1
        shutil.copy2(src, target)
        print(f"Copied {src} -> {target}")
        print(f"Ensure MIT license text is present at {NOTICE.parent / 'LICENSE'}")
        print(f"Set ARASAN_PATH={target}")
        return 0

    # Resolve check
    candidates = [
        Path(os.environ["ARASAN_PATH"]) if os.environ.get("ARASAN_PATH") else None,
        target,
        VENDOR_BIN / "arasan",
        VENDOR_BIN / "arasan.exe",
    ]
    found = next((p for p in candidates if p and p.is_file()), None)
    if found:
        print(f"Arasan binary OK: {found}")
        return 0

    print("Arasan binary not found.", file=sys.stderr)
    print("Build/download Arasan (MIT) from upstream, then:", file=sys.stderr)
    print(f"  python scripts/ohcc/download_arasan.py --from /path/to/arasan", file=sys.stderr)
    print(f"See {NOTICE}", file=sys.stderr)
    return 1 if args.check or True else 1


if __name__ == "__main__":
    raise SystemExit(main())
