#!/bin/sh
# Point the FreeTube desktop entry at ftsync.py.
set -eu

repo=$(cd "$(dirname "$0")" && pwd)
apps=${XDG_DATA_HOME:-$HOME/.local/share}/applications # needs fix for non GNOME?
cmd="python3 \"$repo/ftsync.py\" %u"
flatpak=share/applications/io.freetubeapp.FreeTube.desktop

# needs further install locations, Windows?
# First entry found wins: system Flatpak, user Flatpak.
src=
for f in "/var/lib/flatpak/exports/$flatpak" \
    "$HOME/.local/share/flatpak/exports/$flatpak"; do
    if [ -f "$f" ]; then
        src=$f
        break
    fi
done
if [ -z "$src" ]; then
    echo "no FreeTube Flatpak found, install io.freetubeapp.FreeTube first" >&2
    exit 1
fi

mkdir -p -v "$apps"
dst=$apps/$(basename "$src")
# Escape & | \ in path
esc=$(printf '%s' "$cmd" | sed 's/[&|\\]/\\&/g')
sed "s|^Exec=.*|Exec=$esc|" "$src" >"$dst"
echo "installed $dst"
