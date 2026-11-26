# ftsync

Launcher that syncs FreeTube data between machines through a synced folder, with a 3-way merge so removals propagate.

## Repository

- [ftsync.py](ftsync.py): sync, then run FreeTube, then sync again. `ftsync.py sync` syncs only, `ftsync.py test` runs the self-check.
- [install.sh](install.sh): points the FreeTube desktop entry at `ftsync.py`.

## Installation

- Requirements: Linux, Python 3.9+, the FreeTube Flatpak (`io.freetubeapp.FreeTube`), `~/Nextcloud/FreeTube-sync` kept in sync between machines by Nextcloud or any other tool.
- Other shared folder: change `REMOTE` in `ftsync.py`.
- Install on every machine: `git clone https://github.com/loismathoi/ftsync && ftsync/install.sh`. The desktop entry points into the clone, so keep it in place.
- Uninstall: `rm -r ~/.local/share/applications/io.freetubeapp.FreeTube.desktop ~/.local/state/ftsync`, the original FreeTube entry takes over again.

## Usage

- Start FreeTube from the menu or dock as usual. Starting it any other way skips the sync.
- Synced: profiles, playlists, history, search history, settings except window bounds.
- Not synced: subscription cache.
- A fresh install gets the shared copy before FreeTube's first start.
- First sync of a machine that already has FreeTube data: both sides merge, its settings win, a video in Favorites on both machines appears twice.
- Sync state: `~/.local/state/ftsync`, one per machine, never shared.
- Not supported: non-Flatpak installs.

## License

MIT, see [LICENSE](LICENSE).
