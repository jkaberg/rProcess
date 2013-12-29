import os
import sys
import traceback
print sys.path

from rtorrent import RTorrent

class rTorrent(object):
    def __init__(self):
        self.conn = None

    def connect(self, host, username, password):
        if self.conn is not None:
            return self.conn

        if not host:
            raise "Config properties are not filled in correctly, url is missing"
            return False

        if username and password:
            self.conn = RTorrent(
                host,
                username,
                password
            )
        else:
            self.conn = RTorrent(host)

        return self.conn

    def get_torrent(self, torrent):
        files = []
        try:
            for f in torrent.get_files():
                files.append(f.path.lower())

            torrent_info = {
                'hash': torrent.info_hash,
                'name': torrent.name,
                'label': torrent.get_custom1() if torrent.get_custom1() else '',
                'folder': torrent.directory,
                'completed': torrent.complete,
                'files': files,
                }

        except Exception, e:
            raise "Failed to get status from rTorrent: %s %s", e, traceback.format_exc()
            return False

        return torrent_info if torrent_info else False

    def delete_torrent(self, torrent):
        deleted = []

        for file_item in torrent.get_files():
            file_path = os.path.join(torrent.directory, file_item.path)
            os.unlink(file_path)
            deleted.append(file_item.path)

        if torrent.is_multi_file() and torrent.directory.endswith(torrent.name):
            try:
                for path, _, _ in os.walk(torrent.directory, topdown=False):
                    os.rmdir(path)
                    deleted.append(path)
            except:
                pass

        torrent.erase()

        return deleted

class torrent(object):
    def __init__(self):
        pass

    def connect(self, host, username, password):
        return rTorrent.connect(host, username, password)

    def get_torrent (self, t):
        return rTorrent.get_torrent(t)

    def delete_torrent(self, t):
        return rTorrent.delete_torrent(t)
