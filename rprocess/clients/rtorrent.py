import os

from libs.rtorrent import RTorrent

class TorrentClient(object):
    def __init__(self):
        self.conn = None

    def connect(self, host, username, password):
        if self.conn is not None:
            return self.conn

        if not host:
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

    def find_torrent(self, hash):
        return self.conn.find_torrent(hash)

    def get_torrent (self, torrent):
        files = []
        try:
            for f in torrent.get_files():
                files.append(os.path.normpath(os.path.join(torrent.directory, f.path.lower())))

            torrent_info = {
                'hash': torrent.info_hash,
                'name': torrent.name,
                'label': torrent.get_custom1() if torrent.get_custom1() else '',
                'folder': torrent.directory,
                'completed': torrent.complete,
                'files': files,
                }

        except Exception:
            raise

        return torrent_info if torrent_info else False

    def delete_torrent(self, torrent):
        deleted = []
        try:
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
        except Exception:
            raise

        torrent.erase()

        return deleted
