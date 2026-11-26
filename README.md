# ftsync

Launcher that syncs FreeTube data between machines through any synced folder (Nextcloud, Syncthing, Dropbox), with a 3-way merge so removals propagate.

## Repository

- [ftsync.py](ftsync.py): sync, then run FreeTube, then sync again. `ftsync.py sync` syncs only, `ftsync.py test` runs the self-check.
- [install.sh](install.sh): points the FreeTube desktop entry at `ftsync.py`.

## System

- Needs: Linux, Python 3, FreeTube, a folder that some tool keeps in sync between machines.
- Installing: clone to a fixed path, run `./install.sh`. Moving the repo afterwards breaks the desktop entry.
- Config: `~/.config/ftsync/config.toml`, optional, keys below. Unknown keys stop the sync.
- `remote`: the synced folder, default `~/Nextcloud/FreeTube-sync`.
- `local`: FreeTube data, default Flatpak `~/.var/app/io.freetubeapp.FreeTube/config/FreeTube` if present, else `~/.config/FreeTube` (deb, rpm, AUR, AppImage).
- `cmd`: list that starts FreeTube, default the Flatpak, or `["freetube"]` with a non-Flatpak `local`. AppImage: e.g. `["~/Apps/FreeTube.AppImage"]`.
- Example, AUR install with Syncthing: `remote = "~/Sync/freetube"`, `local` and `cmd` detected.
- Synced: profiles, playlists, history, search history, settings except window bounds.
- Not synced: subscription cache.
- Base: `~/.local/state/ftsync`. A machine without one adopts the shared copy and drops its local data.
- Starting FreeTube any other way than the desktop entry skips the sync.

## Status

- Done: merge logic, tested in simulation.
- TODO: first real use on desktop and laptop.
- Not tested: non-Flatpak installs, Snap.

## License

MIT, see [LICENSE](LICENSE).
