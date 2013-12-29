import os
try:
    import json
except ImportError:
    import simplejson as json

from libs.utorrent.client import UTorrentClient

# Only compatible with uTorrent 3.0+

class TorrentClient(object):
    def __init__(self):
        self.conn = None

    def connect(self, host, username, password):
        if self.conn is not None:
            return self.conn

        if not host:
            return False

        if username and password:
            self.conn = UTorrentClient(
                host,
                username,
                password
            )
        else:
            self.conn = UTorrentClient(host)

        return self.conn

    def find_torrent(self, hash):
        try:
            _, torrent_list = self.conn.list()

            for t in torrent_list['torrents']:
                if t[0] == hash:
                    torrent = t

        except Exception:
            raise

        return torrent if torrent else False

    def get_torrent(self, torrent):
        torrent_files = []
        try:
            if torrent[4] == 1000:
                completed = True
            else:
                completed = False

            _, data = self.conn.getfiles(torrent[0])
            _, files = data['files']

            for f in files:
                torrent_files.append(os.path.join(torrent[26], f[0]))

            torrent_info = {
                'hash': torrent[0],
                'name': torrent[2],
                'label': torrent[11] if torrent[11] else '',
                'folder': torrent[26],
                'completed': completed,
                'files': torrent_files,
            }
        except Exception:
            raise

        return torrent_info

    def delete_torrent(self, torrent):
        deleted = []
        try:
            _, data = self.conn.getfiles(torrent[0])
            _, files = data['files']

            for f in files:
                deleted.append(os.path.join(torrent[26], f[0]))

            self.conn.removedata(torrent[0])

        except Exception:
            raise

        return deleted
