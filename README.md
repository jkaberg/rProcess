rProcess
========

post processor for torrent clients

##Options
- Link/symlink/copy/move or extract content to destination
- Ignore torrents with x label
- Append label to destination path
- Delete torrrent from client (with files) once rProcess is done

##Supported clients
- rTorrent
- uTorrent

##Requirements
- Python 2.6+
- rTorrent 0.9.2/libTorrent 1.13.2
- uTorrent 3.0+

##Usage
###rTorrent
Add (note the path's **/path/to/rprocess/rProcess.py** bellow)

```
system.method.set_key=event.download.finished,my_script,"execute={python,/path/to/rprocess/rProcess.py,$d.get_hash=}"
```

to the bottom of (usally in home/$user/) **.rtorrent.rc** and then edit config.cfg to you're taste

###uTorrent
- Enable and setup WebUI in uTorrent (set username, password and port)
- In "Run Program" set it to (note the path's **C:\Python27\pythonw.exe C:\path\to\rProcess.py** below)

```
C:\Python27\pythonw.exe C:\path\to\rProcess.py "%I"
```
