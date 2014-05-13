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
        torrent_files = []
        torrent_directory = os.path.normpath(torrent.directory)
        try:
            for f in torrent.get_files():
                if not os.path.normpath(f.path).startswith(torrent_directory):
                    file_path = os.path.join(torrent_directory, f.path.lstrip('/'))
                else:
                    file_path = f.path

                torrent_files.append(file_path)

            torrent_info = {
                'hash': torrent.info_hash,
                'name': torrent.name,
                'label': torrent.get_custom1() if torrent.get_custom1() else '',
                'folder': torrent_directory,
                'completed': torrent.complete,
                'files': torrent_files,
                }

        except Exception:
            raise

        return torrent_info if torrent_info else False

    def start_torrent(self, torrent):
        return torrent.start()

    def stop_torrent(self, torrent):
        return torrent.stop()

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
