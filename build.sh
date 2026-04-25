#!/bin/bash
# Rebuild the native Swift settings dialogs in the macOS .app bundles.
# Requires Xcode Command Line Tools (`xcode-select --install`) for `swiftc`.
#
# Usage:
#   ./build.sh           # rebuild all three GUIs
#   ./build.sh md2pdf    # rebuild md2pdf only (also: doc2md, validator)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-all}"

if ! command -v swiftc >/dev/null 2>&1; then
    echo "error: swiftc not found." >&2
    echo "       Install the Xcode Command Line Tools:" >&2
    echo "       xcode-select --install" >&2
    exit 1
fi

build_md2pdf() {
    echo "==> md2pdf settings_gui"
    cd "$REPO_ROOT/md2pdf.app/Contents/Resources"
    swiftc -O settings_gui.swift -o settings_gui
    cp settings_gui ../MacOS/settings_gui
    echo "    built: md2pdf.app/Contents/{Resources,MacOS}/settings_gui"
}

build_doc2md() {
    echo "==> doc2md settings_gui"
    cd "$REPO_ROOT/doc2md.app/Contents/Resources"
    swiftc -O settings_gui.swift -o settings_gui
    echo "    built: doc2md.app/Contents/Resources/settings_gui"
}

build_validator() {
    echo "==> md2pdf-validator validator_gui"
    cd "$REPO_ROOT/md2pdf-validator.app/Contents/Resources"
    swiftc -O validator_gui.swift -o validator_gui
    cp validator_gui ../MacOS/validator_gui
    echo "    built: md2pdf-validator.app/Contents/{Resources,MacOS}/validator_gui"
}

case "$TARGET" in
    all)
        build_md2pdf
        build_doc2md
        build_validator
        ;;
    md2pdf)    build_md2pdf ;;
    doc2md)    build_doc2md ;;
    validator) build_validator ;;
    *)
        echo "usage: $0 [all|md2pdf|doc2md|validator]" >&2
        exit 2
        ;;
esac

echo "done."
