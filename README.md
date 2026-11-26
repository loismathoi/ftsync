# ftsync

Launcher that syncs FreeTube data between machines through a synced folder, with a 3-way merge so removals propagate.

## Requirements

- Linux with Python 3.9 or newer
- FreeTube installed as a Flatpak (`io.freetubeapp.FreeTube`)
- `~/Nextcloud/FreeTube-sync`, kept identical on all machines by Nextcloud or any other sync tool

Other FreeTube install types are currently not supported.

## Installation

On every machine that should sync:

```sh
git clone https://github.com/loismathoi/ftsync
cd ftsync
./install.sh
```

`install.sh` copies FreeTube's desktop entry into `~/.local/share/applications` and points it at `ftsync.py`. The entry refers to the cloned folder, so the clone has to stay where it is.

A different shared folder is set with `REMOTE` at the top of `ftsync.py`.

## Usage

FreeTube is started from the app menu or dock as before. ftsync syncs before FreeTube opens and again after it closes. A failed sync shows a desktop notification, and FreeTube starts anyway. Starting FreeTube any other way, for example with `flatpak run`, skips the sync.

Manual sync while FreeTube is closed, and the self-check:

```sh
./ftsync.py sync
./ftsync.py test
```

### What gets synced

Profiles with their subscriptions, playlists, watch history, search history and settings.

### First sync on a machine

A fresh FreeTube install gets the shared data before FreeTube starts for the first time. A machine that already has FreeTube data merges it with the shared copy instead. On that first merge its settings win, and a video in Favorites on both machines appears twice.

The state of each machine's last sync lives in `~/.local/state/ftsync`. It lets the merge tell a removal on one machine from an addition on another, and it is never shared.

## Security

Databases of FreeTube data get saved in plain JSON to whatever folder is declared as `REMOTE`. If that folder is exposed on the network, make sure it's secured/encrypted accordingly.

## Uninstall

```sh
rm ~/.local/share/applications/io.freetubeapp.FreeTube.desktop
rm -r ~/.local/state/ftsync
```

The original FreeTube entry restores itself. FreeTube's data and the shared folder stay untouched.

## License

MIT, see [LICENSE](LICENSE).
