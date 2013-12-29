class uTorrent(object):
    def __init__(self):
        pass

class torrent(object):
    def __init__(self):
        pass

    def connect(self, host, username, password):
        return uTorrent.connect(host, username, password)

    def get_torrent (self, t):
        return uTorrent.get_torrent(t)

    def delete_torrent(self, t):
        return uTorrent.delete_torrent(t)