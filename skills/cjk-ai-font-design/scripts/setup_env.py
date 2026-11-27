"""One-command environment check and optional auto-install for cjk-ai-font-design."""
import argparse
import importlib
import subprocess
import sys

REQUIRED = [
    ("fontTools", "fonttools"),
    ("brotli", "brotli"),
    ("vtracer", "vtracer"),
    ("PIL", "pillow"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
]


def check_missing():
    missing = []
    for mod, pkg in REQUIRED:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def main():
    ap = argparse.ArgumentParser(description="Check or auto-install Python dependencies for cjk-ai-font-design.")
    ap.add_argument("--install", action="store_true", help="Automatically pip-install missing packages.")
    args = ap.parse_args()

    missing = check_missing()
    if not missing:
        print("OK: all dependencies installed (fonttools, brotli, vtracer, pillow, numpy, scipy).")
        return

    print("Missing packages:", ", ".join(missing))
    if not args.install:
        print("Run with --install to install automatically:")
        print(f"  {sys.executable} {__file__} --install")
        sys.exit(1)

    cmd = [sys.executable, "-m", "pip", "install", *missing]
    print("Installing:", " ".join(cmd))
    subprocess.check_call(cmd)
    still = check_missing()
    if still:
        print("ERROR: still missing after install:", ", ".join(still))
        sys.exit(1)
    print("OK: all dependencies installed and verified.")


if __name__ == "__main__":
    main()
