#!/usr/bin/env python

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#    
#    Creator of rProcess: jkaberg, https://github.com/jkaberg
#    Based on bits and parts of rTorrent module in CouchPotatoServer

import os
import sys
import shutil
import logging
import traceback
import ConfigParser
from base64 import b16encode, b32decode

from rtorrent import RTorrent
from pyUnRAR2 import RarFile

ver = 0.001

class rProcess(object):

    def __init__(self):
        self.rt = None

    def connect(self):
        # Already connected?
        if self.rt is not None:
            return self.rt

        # Ensure url is set
        if not config.get("rTorrent", "host"):
            logger.error(loggerHeader + "Config properties are not filled in correctly, url is missing")
            return False

        if config.get("rTorrent", "username") and config.get("rTorrent", "password"):  # using username/password
            self.rt = RTorrent(
                config.get("rTorrent", "host"),
                config.get("rTorrent", "username"),
                config.get("rTorrent", "password")
            )
        else:
            self.rt = RTorrent(config.get("rTorrent", "host"))  # not using username/password

        return self.rt

    def get_torrent(self, torrent):
        media_ext = tuple((
            config.get("Miscellaneous", "media") +
            config.get("Miscellaneous", "meta") +
            config.get("Miscellaneous", "other")
        ).split('|'))
        archive_ext = tuple((config.get("Miscellaneous", "compressed")).split('|'))
        ignore_words = (config.get("Miscellaneous", "ignore")).split('|')

        try:
            media_files = []
            extracted_files = []

            for file_item in torrent.get_files():
                file_path = file_item.path.lower()

                # ignore unwanted files
                if not any(word in file_path for word in ignore_words):
                    if file_path.endswith(media_ext):
                        media_files.append(os.path.join(torrent.directory, file_path))

                    elif file_path.endswith(archive_ext):
                        extracted_files.append(os.path.join(torrent.directory, file_path))

            torrent_info = {
                'hash': torrent.info_hash,
                'name': torrent.name,
                'label': torrent.get_custom1() if torrent.get_custom1() else '',
                'folder': torrent.directory,
                'completed': torrent.complete,
                'media_files': media_files,
                'extract_files': extracted_files
            }

        except Exception, e:
            logger.error(loggerHeader + "Failed to get status from rTorrent: %s %s", e, traceback.format_exc())
            return False

        return torrent_info if torrent_info else False

    def delete_torrent(self, torrent):
        deleted = []

        for file_item in torrent.get_files():  # will only delete files, not dir/sub-dir
            file_path = os.path.join(torrent.directory, file_item.path)
            os.unlink(file_path)
            deleted.append(file_path)

        if torrent.is_multi_file() and torrent.directory.endswith(torrent.name):
            # remove empty directories bottom up
            try:
                for path, _, _ in os.walk(torrent.directory, topdown=False):
                    os.rmdir(path)
                    deleted.append(path)
            except:
                pass  # its ok, dir not empty

        torrent.erase()  # just removes the torrent, doesn't delete data

        return deleted

    def process_file(self, source_file, destination, action):
        file_name = os.path.split(source_file)[1]
        destination_file = os.path.join(destination, file_name)
        try:
            if action == "move":
                logger.debug(loggerHeader + "Moving file: %s to: %s", file_name, destination)
                shutil.move(source_file, destination_file)
                return True
            elif action == "link":
                logger.debug(loggerHeader + "Linking file: %s to: %s", file_name, destination)
                os.link(source_file, destination_file)
                return True
            elif action == "copy":
                logger.debug(loggerHeader + "Copying file: %s to: %s", file_name, destination)
                shutil.copy(source_file, destination_file)
                return True

        except Exception, e:
            logger.error(loggerHeader + "Failed to process %s: %s %s", file_name, e, traceback.format_exc())
        return False

    def extract_file(self, source_file, destination):
        try:
            rar_handle = RarFile(source_file)
            for info in rar_handle.infolist():
                if not info.isdir:
                    logger.info(loggerHeader + "Extracting file: %s to: %s", info.filename, destination)
                    rar_handle.extract(condition=[info.index], path=destination, withSubpath=False, overwrite=False)
            del rar_handle
            return True

        except Exception, e:
            logger.error(loggerHeader + "Failed to extract %s: %s %s", os.path.split(source_file)[1],
                         e, traceback.format_exc())
        return False


    def make_directories(self, destination):
        if not os.path.exists(destination):
            os.makedirs(destination)

    def main(self, torrent_hash):
        output_dir = config.get("General", "outputDirectory")
        file_action = config.get("General", "fileAction")
        delete_finished = config.getboolean("General", "deleteFinished")
        append_label = config.getboolean("General", "appendLabel")
        ignore_label = (config.get("General", "ignoreLabel")).split('|')

        if not self.connect():
            logger.error(loggerHeader + "Couldn't connect to rTorrent, exiting")
            sys.exit(-1)

        torrent = self.rt.find_torrent(torrent_hash)

        if torrent is None:
            logger.error(loggerHeader + "Couldn't find torrent with hash: %s", torrent_hash)
            sys.exit(-1)

        torrent_info = self.get_torrent(torrent)

        if torrent_info:
            if torrent_info['completed']:
                logger.info(loggerHeader + "Directory: %s", torrent_info['folder'])
                logger.info(loggerHeader + "Name: %s", torrent_info['name'])
                logger.debug(loggerHeader + "Hash: %s", torrent_info['hash'])
                if torrent_info['label']:
                    logger.info(loggerHeader + "Torrent Label: %s", torrent_info['label'])

                if any(word in torrent_info['label'] for word in ignore_label):
                    logger.error(loggerHeader + "Exiting: Found unwanted label: %s", torrent_info['label'])
                    sys.exit(-1)

                destination = os.path.join(output_dir, torrent_info['label'] if append_label else '',
                                           torrent_info['name'])

                self.make_directories(destination)

                for f in torrent_info['media_files']:  # copy/link/move files
                    process = self.process_file(f, destination, file_action)
                    file_name = os.path.split(f)[1]
                    if process:
                        logger.info(loggerHeader + "Successfully processed: %s", file_name)
                    else:
                        logger.error(loggerHeader + "Failed to process: %s", file_name)

                for f in torrent_info['extract_files']:  # extract files
                    extract = self.extract_file(f, destination)
                    file_name = os.path.split(f)[1]
                    if extract:
                        logger.info(loggerHeader + "Successfully extracted: %s", file_name)
                    else:
                        logger.error(loggerHeader + "Failed to extract: %s", file_name)

                if delete_finished:
                    deleted_files = self.delete_torrent(torrent)
                    logger.info(loggerHeader + "Removing torrent with hash: %s", torrent_hash)
                    for f in deleted_files:
                        logger.info(loggerHeader + "Removed: %s", f)

            else:
                logger.error(loggerHeader + "Torrent with hash: %s hasn't completed downloading", torrent_hash)
                sys.exit(-1)

        else:
            logger.error(loggerHeader + "Unknown error :(")
            sys.exit(-1)


if __name__ == "__main__":

    config = ConfigParser.ConfigParser()
    configFilename = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "config.cfg"))
    config.read(configFilename)

    logfile = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "rProcess.log"))
    loggerHeader = "rProcess :: "
    loggerFormat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S')
    logger = logging.getLogger('rProcess')

    loggerStd = logging.StreamHandler()
    loggerStd.setFormatter(loggerFormat)

    loggerHdlr = logging.FileHandler(logfile)
    loggerHdlr.setFormatter(loggerFormat)
    loggerHdlr.setLevel(logging.INFO)

    if config.getboolean("General", "debug"):
        logger.setLevel(logging.DEBUG)
        loggerHdlr.setLevel(logging.DEBUG)
        loggerStd.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        loggerHdlr.setLevel(logging.INFO)
        loggerStd.setLevel(logging.INFO)

    logger.addHandler(loggerStd)
    logger.addHandler(loggerHdlr)

    logger.info(loggerHeader + "rProcess: %s", ver)

    if not os.path.isfile(configFilename):
        logger.error(loggerHeader + "Config file not found: " + configFilename)
        raise
    else:
        logger.info(loggerHeader + "Config loaded: " + configFilename)

    # usage: rProcess.py <torrent hash>
    torrent_hash = sys.argv[1]  # Hash of the torrent

    if len(torrent_hash) == 32:
        torrent_hash = b16encode(b32decode(torrent_hash))

    if not len(torrent_hash) == 40:
        logger.error(loggerHeader + "Torrent torrent_hash is missing, or an invalid torrent_hash value has been passed")
    else:
        rp = rProcess()
        rp.main(torrent_hash)