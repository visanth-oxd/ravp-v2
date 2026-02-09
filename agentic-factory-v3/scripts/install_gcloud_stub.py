#!/usr/bin/env python3
"""
One-time fix: install missing lib/gcloud.py for Homebrew Google Cloud SDK.
The Homebrew cask sometimes omits this file; the bin/gcloud script expects it.
Run from repo root: python scripts/install_gcloud_stub.py
You may need: sudo python scripts/install_gcloud_stub.py
"""
import os
import sys

STUB = r'''# Bootstrapper for Google Cloud SDK when lib/gcloud.py is missing (e.g. Homebrew layout).
# The real entrypoint is googlecloudsdk.gcloud_main.
import sys
import os
_lib = os.path.dirname(os.path.abspath(__file__))
if _lib not in sys.path:
    sys.path.insert(0, _lib)
from googlecloudsdk.gcloud_main import main
main()
'''

CANDIDATES = [
    "/opt/homebrew/share/google-cloud-sdk/lib/gcloud.py",
    "/usr/local/share/google-cloud-sdk/lib/gcloud.py",
]


def main():
    for path in CANDIDATES:
        lib_dir = os.path.dirname(path)
        if not os.path.isdir(lib_dir):
            continue
        if os.path.isfile(path):
            print(f"Already exists: {path}")
            return 0
        try:
            with open(path, "w") as f:
                f.write(STUB)
            print(f"Created: {path}")
            return 0
        except PermissionError:
            print(f"Permission denied. Run with sudo: sudo python {__file__}")
            return 1
    print("No SDK lib dir found. Install gcloud first: brew install --cask gcloud-cli")
    return 1


if __name__ == "__main__":
    sys.exit(main())
