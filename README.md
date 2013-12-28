rProcess
========

simple post processor for rTorrent

###Options

- Link/copy/move or extract content to destination, set in config.cfg
- Append label to destination path

###Usage

Add (note the **/path/to/rprocess/rProcess.py** bellow)

```
system.method.set_key=event.download.finished,my_script,"execute={python,/path/to/rprocess/rProcess.py,$d.get_hash=}"
```

to the bottom of (usaly in home/$user/) **.rtorrent.rc** and then edit config.cfg to you're taste
