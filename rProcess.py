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
import re
import sys
import shutil
import logging
import traceback
import ConfigParser
from base64 import b16encode, b32decode

from libs.unrar2 import RarFile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs'))

ver = 0.1

class rProcess(object):

    def __init__(self):
        client = config.get("Client", "client")
        if client == 'rtorrent':
            import rprocess.clients.client
        elif client == 'utorrent':
            import rprocess.clients.utorrent
#        else:

#        try:
#            __import__('clients.' + config.get("Client", "client"))
#        except Exception, e:
#            logger.error(loggerHeader + "No client to work with: %s %s ", e, traceback.format_exc())
#            sys.exit(-1)


    def filter_files(self, files):
        media_ext = tuple((
            config.get("Miscellaneous", "media") +
            config.get("Miscellaneous", "meta") +
            config.get("Miscellaneous", "other")).split('|'))
        archive_ext = tuple((config.get("Miscellaneous", "compressed")).split('|'))
        ignore_words = (config.get("Miscellaneous", "ignore")).split('|')
        rar_search = '(?P<file>^(?P<base>(?:(?!\.part\d+\.rar$).)*)\.(?:(?:part0*1\.)?rar)$)'

        media_files = []
        extracted_files = []

        for f in files:
            # ignore unwanted files
            if not any(word in f for word in ignore_words):
                if f.endswith(media_ext):
                    media_files.append(f)

                elif f.endswith(archive_ext):
                    if 'part' in f:
                        if re.search(rar_search, f):
                            extracted_files.append(f)
                    else:
                        extracted_files.append(f)

        return media_files, extracted_files


    def process_file(self, source_file, destination, action):
        file_name = os.path.split(source_file)[1]
        destination_file = os.path.join(destination, file_name)
        if not os.path.isfile(destination_file):
            try:
                if action == "move":
                    logger.debug(loggerHeader + "Moving file: %s to: %s", file_name, destination)
                    shutil.move(source_file, destination_file)
                elif action == "link":
                    logger.debug(loggerHeader + "Linking file: %s to: %s", file_name, destination)
                    os.link(source_file, destination_file)
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
            try:
                os.makedirs(destination)
                logger.info(loggerHeader + "Creating directory: %s" % destination)

            except OSError as e:
                if e.errno != errno.EEXIST:
                    logger.error(loggerHeader + "Failed to create directory: %s %s %s", destination,
                                 e, traceback.format_exc())
                    raise
                pass

    def main(self, torrent_hash):
        output_dir = config.get("General", "outputDirectory")
        file_action = config.get("General", "fileAction")
        delete_finished = config.getboolean("General", "deleteFinished")
        append_label = config.getboolean("General", "appendLabel")
        ignore_label = (config.get("General", "ignoreLabel")).split('|')

        if not torrent.connect(config.get("Client", "host"),
                               config.get("Client", "username"),
                               config.get("Client", "password")):
            logger.error(loggerHeader + "Couldn't connect to %s, exiting", config.get("Client", "client"))
            sys.exit(-1)

        t = torrent.find_torrent(torrent_hash)

        if t is None:
            logger.error(loggerHeader + "Couldn't find torrent with hash: %s", torrent_hash)
            sys.exit(-1)

        t_info = torrent.get_torrent(t)

        if t_info:
            if t_info['completed']:
                logger.info(loggerHeader + "Directory: %s", t_info['folder'])
                logger.info(loggerHeader + "Name: %s", t_info['name'])
                logger.debug(loggerHeader + "Hash: %s", t_info['hash'])
                if t_info['label']:
                    logger.info(loggerHeader + "Torrent Label: %s", t_info['label'])

                if any(word in t_info['label'] for word in ignore_label):
                    logger.error(loggerHeader + "Exiting: Found unwanted label: %s", t_info['label'])
                    sys.exit(-1)

                destination = os.path.join(output_dir, t_info['label'] if append_label else '',
                                           t_info['name'])

                self.make_directories(destination)

                media_files, extract_files = self.filter_files(t_info['files'])

                for f in media_files:  # copy/link/move files
                    process = self.process_file(f, destination, file_action)
                    file_name = os.path.split(f)[1]
                    if process:
                        logger.info(loggerHeader + "Successfully processed: %s", file_name)
                    else:
                        logger.error(loggerHeader + "Failed to process: %s", file_name)

                for f in extract_files:  # extract files
                    extract = self.extract_file(f, destination)
                    file_name = os.path.split(f)[1]
                    if extract:
                        logger.info(loggerHeader + "Successfully extracted: %s", file_name)
                    else:
                        logger.error(loggerHeader + "Failed to extract: %s", file_name)

                if delete_finished:
                    deleted_files = torrent.delete_torrent(t)
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
        logger.error(loggerHeader + "Torrent hash is missing, or an invalid hash value has been passed")
    else:
        rp = rProcess()
        rp.main(torrent_hash)
