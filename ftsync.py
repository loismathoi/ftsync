#!/usr/bin/env python3
"""Sync FreeTube data between machines through a shared folder.

Usage: ftsync.py [URL]   sync, run FreeTube, sync again
       ftsync.py sync    sync only (FreeTube must be closed)
       ftsync.py test    run the self-check

Each sync is a 3-way merge of the local FreeTube data, the shared copy in
~/Nextcloud/FreeTube-sync (the remote), and the state of the last sync on
this machine (the base). The base tells an addition on one side from a
removal on the other. Without a base, both sides count as additions and
merge. A missing local file adopts the shared copy, which seeds a fresh
install before FreeTube's first start.

Only the Flatpak install is supported.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

APP = 'io.freetubeapp.FreeTube'
LOCAL = Path.home() / '.var/app' / APP / 'config/FreeTube'
REMOTE = Path.home() / 'Nextcloud/FreeTube-sync'
# An empty XDG variable counts as unset, as the XDG spec says.
BASE = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'ftsync'
# settings that stay per machine
LOCAL_ONLY = {
    'bounds',  # window properties
}


def notify(msg):
    print(msg, file=sys.stderr)
    try:
        subprocess.run(['notify-send', 'FreeTube sync failed', msg], check=False)
    except FileNotFoundError:
        pass


def merge3(base, local, remote, conflict):
    """3-way merge of dicts id -> doc; a missing doc is None. First match wins:

    - local == remote, or remote == base: take local
    - local == base: take remote
    - one side None: edit overrules deletion, take the other
    - else: conflict(base, local, remote)

    A None result drops the id. Empty base: both sides are kept.
    """
    merged = {}
    for id in list(local) + [i for i in remote if i not in local]:
        in_base = base.get(id)
        in_local = local.get(id)
        in_remote = remote.get(id)
        if in_local == in_remote or in_remote == in_base:
            doc = in_local
        elif in_local == in_base:
            doc = in_remote
        elif in_local is None or in_remote is None:
            doc = in_local or in_remote
        else:
            doc = conflict(in_base, in_local, in_remote)
        if doc is not None:
            merged[id] = doc
    return merged


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
    for line in path.read_text(encoding='utf-8').splitlines():
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
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '~')  # Nextcloud ignores *~ by default
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def sync():
    for name, (key, conflict) in COLLECTIONS.items():
        local_file, remote_file, base_file = LOCAL / name, REMOTE / name, BASE / name
        if not local_file.exists() and not remote_file.exists():
            continue  # nothing on either side, do not create empty files
        local = load(local_file, key)
        remote = load(remote_file, key)
        if not local_file.exists():
            base = local = remote  # fresh install or lost file: adopt the shared copy
        else:
            base = load(base_file, key)  # no base yet: empty, so both sides merge
        # A Nextcloud conflict copy holds this machine's upload that lost a race.
        copies = sorted(REMOTE.glob(f'{name[:-3]} (conflicted copy*).db'))
        keep = {k: v for k, v in load(local_file, key).items() if k in LOCAL_ONLY}
        local, remote, base = ({k: v for k, v in d.items() if k not in LOCAL_ONLY}
                               for d in (local, remote, base))
        merged = merge3(base, local, remote, conflict)
        for copy in copies:
            merged = merge3(base, merged, load(copy, key), conflict)
        # Base last: a sync cut short anywhere before it merges again correctly.
        dump(local_file, merged | keep)
        dump(remote_file, merged)
        for copy in copies:
            copy.unlink()
        dump(base_file, merged)


def running():
    # Electron's SingletonLock outlives a crash, flatpak ps lags behind a close.
    if not os.path.lexists(LOCAL / 'SingletonLock'):
        return False
    ps = subprocess.run(['flatpak', 'ps', '--columns=application'],
                        capture_output=True, text=True, check=True)
    return APP in ps.stdout.split()


def launch(args):
    subprocess.run(['flatpak', 'run', '--file-forwarding', APP, '@@u', *args, '@@'],
                   check=False)


def safe_sync():
    try:
        sync()
    except Exception as e:  # noqa: BLE001  a failed sync must not block FreeTube
        notify(repr(e))


def test():
    global REMOTE
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

    # Machines a, b, c share one remote folder.
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        REMOTE = d / 'remote'

        def on(machine):
            global LOCAL, BASE
            LOCAL, BASE = d / machine, d / f'{machine}-base'
            sync()

        v = lambda i: {'_id': f'{i}-id', 'videoId': i, 'timeWatched': 1}
        ids = lambda p: sorted(load(p, 'videoId'))
        # first machine, FreeTube never started, empty remote: nothing written
        on('c')
        assert not (d / 'c').exists() and not REMOTE.exists()
        dump(d / 'a/history.db', {'v1': v('v1'), 'v2': v('v2')})
        dump(d / 'a/settings.db', {'bounds': {'_id': 'bounds', 'value': 'a'},
                                   'theme': {'_id': 'theme', 'value': 'dark'}})
        on('a')
        assert ids(REMOTE / 'history.db') == ['v1', 'v2']
        assert sorted(load(REMOTE / 'settings.db', '_id')) == ['theme']
        # fresh install: missing data folder is seeded from the remote
        on('b')
        assert ids(d / 'b/history.db') == ['v1', 'v2']
        # removal on b reaches a, a keeps its own bounds
        dump(d / 'b/history.db', {'v2': v('v2')})
        on('b')
        on('a')
        assert ids(d / 'a/history.db') == ['v2']
        assert load(d / 'a/settings.db', '_id')['bounds']['value'] == 'a'
        # a lost local file is restored, not deleted everywhere
        (d / 'a/history.db').unlink()
        on('a')
        assert ids(REMOTE / 'history.db') == ids(d / 'a/history.db') == ['v2']
        # machine with its own data but no base merges, drops nothing
        dump(d / 'e/history.db', {'v3': v('v3')})
        on('e')
        assert ids(REMOTE / 'history.db') == ids(d / 'e/history.db') == ['v2', 'v3']
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
        # Already running: launch only hands args to the open window.
        if running():
            launch(args)
        else:
            safe_sync()
            launch(args)  # returns when FreeTube exits
            safe_sync()
