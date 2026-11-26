#!/usr/bin/env python3
"""Sync FreeTube data between machines through a shared folder.

Usage: ftsync.py [URL]   sync, run FreeTube, sync again
       ftsync.py sync    sync only (FreeTube must be closed)
       ftsync.py test    run the self-check

Each sync is a 3-way merge of the local FreeTube data, the shared copy in
remote (a folder that Nextcloud or similar keeps in sync), and the
state of the last sync on this machine (the base). The base tells an
addition on one side from a removal on the other. A machine without a base
adopts the shared copy as it is.

Optional config in $XDG_CONFIG_HOME/ftsync/config.toml, keys:
  local = "~/.config/FreeTube"         FreeTube data, default detected
  remote = "~/Nextcloud/FreeTube-sync" shared folder, this is the default
  cmd = ["freetube"]                   start command, default detected
"""
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

APP = 'io.freetubeapp.FreeTube'
FLATPAK = Path.home() / '.var/app' / APP / 'config/FreeTube'
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'ftsync/config.toml'
BASE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'ftsync'
LOCAL_ONLY = {'bounds'}  # settings that stay per machine


def config(path):
    """Return (local, remote, cmd); cmd None means the Flatpak."""
    c = tomllib.loads(path.read_text()) if path.exists() else {}
    if unknown := set(c) - {'local', 'remote', 'cmd'}:
        raise SystemExit(f'{path}: unknown keys {sorted(unknown)}')
    if 'local' in c:
        local = Path(c['local']).expanduser()
    else:
        native = Path.home() / '.config/FreeTube'
        local = native if native.is_dir() and not FLATPAK.is_dir() else FLATPAK
    remote = Path(c.get('remote', '~/Nextcloud/FreeTube-sync')).expanduser()
    cmd = c.get('cmd', None if local == FLATPAK else ['freetube'])
    return local, remote, cmd and [os.path.expanduser(a) for a in cmd]


LOCAL, REMOTE, CMD = config(CONFIG)


def merge3(b, l, r, conflict):
    """Merge dicts keyed by id. An edit beats a deletion."""
    out = {}
    for k in list(l) + [k for k in r if k not in l]:
        B, L, R = b.get(k), l.get(k), r.get(k)
        if L == R or R == B:
            v = L
        elif L == B:
            v = R
        elif L is None or R is None:
            v = L or R
        else:
            v = conflict(B, L, R)
        if v is not None:
            out[k] = v
    return out


def newer(field):
    return lambda _B, L, R: R if (R.get(field) or 0) > (L.get(field) or 0) else L


def nested(field, key):
    """Merge a doc whose `field` is a list of items identified by `key`."""
    def conflict(B, L, R):
        idx = lambda d: {i[key]: i for i in (d or {}).get(field, [])}
        doc = dict(newer('lastUpdatedAt')(B, L, R))
        doc[field] = list(merge3(idx(B), idx(L), idx(R), lambda _b, l, _r: l).values())
        return doc
    return conflict


# file: (document key, conflict resolver)
COLLECTIONS = {
    'profiles.db': ('_id', nested('subscriptions', 'id')),
    'playlists.db': ('_id', nested('videos', 'playlistItemId')),
    'history.db': ('videoId', newer('timeWatched')),
    'search-history.db': ('_id', newer('lastUpdatedAt')),
    'settings.db': ('_id', lambda _B, L, _R: L),
}


def load(path, key):
    """Read a NeDB file: one JSON doc per line, later lines win."""
    docs = {}
    if not path.exists():
        return docs
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if '$$indexCreated' in o:
            continue
        if o.get('$$deleted'):
            docs = {k: v for k, v in docs.items() if v['_id'] != o['_id']}
            continue
        docs[o[key]] = o
    return docs


def dump(path, docs):
    text = ''.join(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n'
                   for o in docs.values())
    if path.exists() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text)
    tmp.replace(path)


def sync():
    if not LOCAL.is_dir():
        raise SystemExit(f'no FreeTube data in {LOCAL}, start FreeTube once first')
    for name, (key, conflict) in COLLECTIONS.items():
        l = load(LOCAL / name, key)
        r = load(REMOTE / name, key)
        if not (BASE / name).exists() and (REMOTE / name).exists():
            b = l = r  # new machine: adopt the shared copy
        else:
            b = load(BASE / name, key)
        # Nextcloud conflict copies hold changes another machine uploaded.
        copies = sorted(REMOTE.glob(f'{name[:-3]} (conflicted copy*).db'))
        keep = {k: v for k, v in load(LOCAL / name, key).items() if k in LOCAL_ONLY}
        l, r, b = ({k: v for k, v in d.items() if k not in LOCAL_ONLY} for d in (l, r, b))
        m = merge3(b, l, r, conflict)
        for c in copies:
            m = merge3(b, m, load(c, key), conflict)
        dump(REMOTE / name, m)
        dump(BASE / name, m)
        dump(LOCAL / name, m | keep)
        for c in copies:
            c.unlink()


def running():
    # Electron keeps this symlink in the data folder while FreeTube runs.
    return os.path.lexists(LOCAL / 'SingletonLock')


def launch(args):
    if CMD:
        subprocess.run([*CMD, *args], check=False)
    else:
        subprocess.run(['flatpak', 'run', '--command=/app/bin/run.sh',
                        '--file-forwarding', APP, '@@u', *args, '@@'],
                       check=False)


def notify(msg):
    print(msg, file=sys.stderr)
    try:
        subprocess.run(['notify-send', 'FreeTube sync failed', msg], check=False)
    except FileNotFoundError:
        pass


def safe_sync():
    try:
        sync()
    except Exception as e:  # noqa: BLE001  a failed sync must not block FreeTube
        notify(repr(e))


def test():
    s = lambda *ids: {'_id': 'allChannels', 'lastUpdatedAt': 0,
                      'subscriptions': [{'id': i} for i in ids]}
    f = COLLECTIONS['profiles.db'][1]
    m = merge3({'p': s('a', 'b')}, {'p': s('a', 'c')}, {'p': s('b', 'd')}, f)
    assert [x['id'] for x in m['p']['subscriptions']] == ['c', 'd'], m
    # removal on one side propagates, untouched side adopts it
    assert merge3({'x': 1, 'y': 2}, {'x': 1}, {'x': 1, 'y': 2}, None) == {'x': 1}
    # edit beats deletion
    assert merge3({'x': 1}, {}, {'x': 2}, None) == {'x': 2}
    h = COLLECTIONS['history.db'][1]
    assert merge3({}, {'v': {'timeWatched': 1}}, {'v': {'timeWatched': 2}}, h)['v']['timeWatched'] == 2
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'config.toml'
        t.write_text('remote = "~/x"\ncmd = ["~/a b", "-v"]\n')
        assert config(t)[1:] == (Path.home() / 'x', [str(Path.home() / 'a b'), '-v']), config(t)
        t.write_text('remot = "~/x"\n')
        try:
            config(t)
            raise AssertionError('typo key accepted')
        except SystemExit:
            pass
    print('ok')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['test']:
        test()
    elif args == ['sync']:
        if running():
            raise SystemExit('close FreeTube first')
        sync()
    else:
        was_running = running()
        if not was_running:
            safe_sync()
        launch(args)
        if not was_running and not running():
            safe_sync()
