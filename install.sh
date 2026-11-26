#!/bin/sh
# Make the FreeTube desktop entry start FreeTube through ftsync.py.
# FTSYNC_* variables set when running this are written into the entry.
set -eu

repo=$(cd "$(dirname "$0")" && pwd)
apps=${XDG_DATA_HOME:-$HOME/.local/share}/applications

exec_line="python3 \"$repo/ftsync.py\" %u"
for var in FTSYNC_REMOTE FTSYNC_LOCAL FTSYNC_CMD; do
    eval "val=\${$var-}"
    if [ -n "$val" ]; then
        exec_line="env \"$var=$val\" $exec_line"
    fi
done

src=
for f in /var/lib/flatpak/exports/share/applications/io.freetubeapp.FreeTube.desktop \
    "$HOME/.local/share/flatpak/exports/share/applications/io.freetubeapp.FreeTube.desktop" \
    /usr/share/applications/freetube.desktop; do
    if [ -f "$f" ]; then
        src=$f
        break
    fi
done

mkdir -p "$apps"
if [ -n "$src" ]; then
    dst=$apps/$(basename "$src")
    esc=$(printf '%s' "$exec_line" | sed 's/[&|\\]/\\&/g')
    sed "s|^Exec=.*|Exec=$esc|" "$src" >"$dst"
else
    dst=$apps/ftsync-freetube.desktop
    printf '[Desktop Entry]\nType=Application\nName=FreeTube\nIcon=freetube\nExec=%s\n' \
        "$exec_line" >"$dst"
fi
echo "installed $dst"
