rProcess
========

simple post processor for rTorrent


#Usage

add
system.method.set_key=event.download.finished,my_script,"execute={python,/path/to/rprocess/rProcess.py,$d.get_hash=}"
to .rtorrent.rc

edit config.cfg to you're taste
