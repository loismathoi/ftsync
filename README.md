# ftsync

Launcher that syncs FreeTube data between machines through any synced folder (Nextcloud, Syncthing, Dropbox), with a 3-way merge so removals propagate.

## Repository

- [ftsync.py](ftsync.py): sync, then run FreeTube, then sync again. `ftsync.py sync` syncs only, `ftsync.py test` runs the self-check.
- [install.sh](install.sh): points the FreeTube desktop entry at `ftsync.py`, with any `FTSYNC_*` variables set at install time baked in.

## System

- Needs: Linux, Python 3, FreeTube, a folder that some tool keeps in sync between machines.
- Installing: clone to a fixed path, run `./install.sh` with the variables below. Moving the repo afterwards breaks the desktop entry.
- `FTSYNC_REMOTE`: the synced folder, default `~/Nextcloud/FreeTube-sync`.
- `FTSYNC_LOCAL`: FreeTube data, default Flatpak `~/.var/app/io.freetubeapp.FreeTube/config/FreeTube`. Other installs (deb, rpm, AUR, AppImage): `~/.config/FreeTube`.
- `FTSYNC_CMD`: command that starts FreeTube, default the Flatpak. Other installs: e.g. `freetube` or the AppImage path.
- Example, AUR install: `FTSYNC_REMOTE=~/Sync/freetube FTSYNC_LOCAL=~/.config/FreeTube FTSYNC_CMD=freetube ./install.sh`
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
