import os

from libs.transmission import TransmissionRPC

class TorrentClient(object):
    def __init__(self):
        self.conn = None

    def connect(self, host, username, password):

        host_addr = host.split(':')[1].replace('/', '')
        host_port = host.split(':')[2].split('/')[0]
        host_path = host.split(host_port)[1]

        if self.conn is not None:
            return self.conn

        if not host:
            return False

        if username and password:
            self.conn = TransmissionRPC(
                host = host_addr,
                port = host_port,
                rpc_url = host_path,
                username = username,
                password = password,
            )
        else:
            self.conn = TransmissionRPC(
                host = host_addr,
                port = host_port,
                rpc_url = host_path,
            )

        return self.conn

    def find_torrent(self, hash):

        params = {
            'fields': ['id', 'name', 'hashString', 'percentDone', 'status', 'downloadDir', 'files']
        }

        self.conn.get_session()
        queue = self.conn.get_alltorrents(params)
        if not (queue and queue.get('torrents')):
            raise 'Nothing in queue or error'

        for torrent in queue['torrents']:
            if torrent['hashString'] in hash:
                return torrent

        return False

    def get_torrent (self, torrent):
        torrent_files = []
        torrent_completed = False
        torrent_directory = os.path.normpath(torrent['downloadDir'])
        try:
            for f in torrent['files']:
                if not os.path.normpath(f.path).startswith(torrent_directory):
                    file_path = os.path.join(torrent_directory, f['name'].lstrip('/'))
                else:
                    file_path = f['name']

                torrent_files.append(file_path)

            if torrent['status'] == 0 and torrent['percentDone'] == 1:
                torrent_completed = True  # torrent download complete

            torrent_info = {
                'hash': torrent['hashString'],
                'name': torrent['name'],
                'label': 'transmission_has_no_labels',  # temporary workaround
                'folder': torrent['downloadDir'],
                'completed': torrent_completed,
                'files': torrent_files,
                }

        except Exception:
            raise

        return torrent_info if torrent_info else False

    def delete_torrent(self, torrent):
        deleted = []
        try:
            for f in torrent['files']:
                deleted.append(os.path.normpath(os.path.join(torrent['downloadDir'], f['name'])))

            self.conn.remove_torrent(torrent['id'], True)

        except Exception:
            raise

        return deleted