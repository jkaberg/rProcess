#    !/usr/bin/env python

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
#    ThePieMan did things! https://github.com/ThePieMan

import os
import sys
import re
import shutil
import time
import logging
import traceback
import ConfigParser
from base64 import b16encode, b32decode

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs'))

from libs import requests
from rprocess.helpers.variable import link, symlink
from libs.unrar2 import RarFile

ver = 0.3


class rProcess(object):
    def __init__(self):
        pass

    def filter_files(self, files):
        media_ext = tuple((
            config.get("Miscellaneous", "media") +
            config.get("Miscellaneous", "meta") +
            config.get("Miscellaneous", "other")).split('|'))
        archive_ext = tuple((config.get("Miscellaneous",
                            "compressed")).split('|'))
        ignore_words = (config.get("Miscellaneous", "ignore")).split('|')

        # TODO: get first archive from rar header instead
        rar_search = '(?P<file>^(?P<base>(?:(?!\.part\d+\.rar$).)*)\.(?:(?:part0*1\.)?rar)$)'

        media_files = []
        extracted_files = []

        for f in files:
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
                    link(source_file, destination_file)
                elif action == "symlink":
                    logger.debug(loggerHeader + "Sym-linking file: %s to: %s", file_name, destination)
                    symlink(source_file, destination_file)
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
            for rar_file in rar_handle.infolist():
                sub_path = os.path.join(destination, rar_file.filename)
                if rar_file.isdir and not os.path.exists(sub_path):
                    os.makedirs(sub_path)
                else:
                    rar_handle.extract(condition=[rar_file.index], path=destination, withSubpath=True, overwrite=False)
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

    def process_media(self, media_processor, destination):
        if media_processor == "couchpotato":
            try:
                baseURL = config.get("Couchpotato", "baseURL")
                if not baseURL == '':
                    logger.debug(loggerHeader + "process_media :: URL base: %s", baseURL)
            except ConfigParser.NoOptionError:
                baseURL = ''

            if config.getboolean("Couchpotato", "ssl"):
                protocol = "https://"
            else:
                protocol = "http://"
            url = protocol + config.get("Couchpotato", "host") + ":" + config.get("Couchpotato", "port") + "/" + baseURL + "api/" + config.get("Couchpotato", "apikey") + "/renamer.scan/?async=1&movie_folder=" + destination
            user = config.get("Couchpotato", "username")
            password = config.get("Couchpotato", "password")

        elif media_processor == "sickbeard":
            try:
                baseURL = config.get("Sickbeard", "baseURL")
                if not baseURL == '':
                    logger.debug(loggerHeader + "process_media :: URL base: %s ", baseURL)
            except ConfigParser.NoOptionError:
                baseURL = ''

            if config.getboolean("Sickbeard", "ssl"):
                protocol = "https://"
            else:
                protocol = "http://"
            url = protocol + config.get("Sickbeard", "host") + ":" + config.get("Sickbeard", "port") + "/" + baseURL + "home/postprocess/processEpisode?quiet=1&dir=" + destination
            user = config.get("Sickbeard", "username")
            password = config.get("Sickbeard", "password")
        else:
            return

        try:
            r = requests.get(url, auth=(user, password))
            logger.debug(loggerHeader + "Postprocessing with %s :: Opening URL: %s", media_processor, url)
        except Exception, e:
            logger.error(loggerHeader + "Tried postprocessing with %s :: Unable to open URL: %s %s %s", (media_processor, url, e, traceback.format_exc()))
            raise

        text = r.text
        logger.debug(loggerHeader + "Requests for PostProcessing returned :: %s" + text)

        # This is a ugly solution, we need a better one!!
        timeout = time.time() + 60 * 2  # 2 min time out
        while os.path.exists(destination):
            if time.time() > timeout:
                logger.debug(
                    loggerHeader + "process_media :: The destination directory hasn't been deleted after 2 minutes, something is wrong")
                break
            time.sleep(2)

    def main(self, torrent_hash):
        output_dir = config.get("General", "outputDirectory")
        file_action = config.get("General", "fileAction")
        delete_finished = config.getboolean("General", "deleteFinished")
        append_label = config.getboolean("General", "appendLabel")
        ignore_label = (config.get("General", "ignoreLabel")).split('|')
        client_name = config.get("Client", "client")
        cp_active = config.getboolean("CouchPotato", "active")
        sb_active = config.getboolean("Sickbeard", "active")
        cp_label = config.get("CouchPotato", "CPLabel")
        sb_label = config.get("Sickbeard", "SBLabel")

        # TODO: fix this.. ugly!
        if client_name == 'rtorrent':
            import rprocess.clients.rtorrent as TorClient
        elif client_name == 'utorrent':
            import rprocess.clients.utorrent as TorClient

        client = TorClient.TorrentClient()

        if not client.connect(config.get("Client", "host"),
                              config.get("Client", "username"),
                              config.get("Client", "password")):
            logger.error(loggerHeader + "Couldn't connect to %s, exiting", config.get("Client", "client"))
            sys.exit(-1)

        torrent = client.find_torrent(torrent_hash)

        if torrent is None:
            logger.error(loggerHeader + "Couldn't find torrent with hash: %s", torrent_hash)
            sys.exit(-1)

        torrent_info = client.get_torrent(torrent)

        if torrent_info:
            if torrent_info['completed']:
                logger.info(loggerHeader + "Client: %s", client_name)
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

                media_files, extract_files = self.filter_files(torrent_info['files'])

                if (file_action == "move" or file_action == "link") and not extract_files:  # This stopping action needs to be told to exclude when it is an archive file
                    client.stop_torrent(torrent_hash)
                    logger.debug(loggerHeader + "Stopping seeding torrent with hash: %s", torrent_hash)

                for f in media_files:  # copy/link/move files
                    file_name = os.path.split(f)[1]
                    if self.process_file(f, destination, file_action):
                        logger.info(loggerHeader + "Successfully performed %s on %s", file_action, file_name)
                    else:
                        logger.error(loggerHeader + "Failed to perform %s on %s", file_action, file_name)

                for f in extract_files:  # extract files
                    file_name = os.path.split(f)[1]
                    if self.extract_file(f, destination):
                        logger.info(loggerHeader + "Successfully extracted: %s", file_name)
                    else:
                        logger.error(loggerHeader + "Failed to extract: %s", file_name)

                if cp_active and any(word in torrent_info['label'] for word in cp_label):  # call CP postprocess
                    logger.debug(loggerHeader + "Couchpotato PostProcessing variables met.")
                    self.process_media("couchpotato", destination)

                elif sb_active and any(word in torrent_info['label'] for word in sb_label):  # call SB postprocess
                    logger.debug(loggerHeader + "Sickbeard PostProcessing variables met.")
                    self.process_media("sickbeard", destination)

                else:
                    logger.debug(loggerHeader + "PostProcessor call params not met.")

#   Delete needs to occur ONLY when the file action is move, and exclude when the files are archive
                if file_action == "move" and not extract_files:
                    deleted_files = client.delete_torrent(torrent)
                    logger.info(loggerHeader + "Removing torrent with hash: %s", torrent_hash)
                    for f in deleted_files:
                        logger.info(loggerHeader + "Removed: %s", f)

#   Start needs to occur ONLY when the file action is link, and exclude when the files are archive
                elif file_action == "link" and not extract_files:
                # it would be best if rProcess checked to see if the post-processing completed successfully first - how?
                    client.start_torrent(torrent_hash)
                    logger.debug(loggerHeader + "Starting seeding torrent with hash: %s", torrent_hash)

                if delete_finished and file_action != "move":
                    deleted_files = client.delete_torrent(torrent)
                    logger.info(loggerHeader + "Removing torrent with hash: %s", torrent_hash)
                    for f in deleted_files:
                        logger.info(loggerHeader + "Removed: %s", f)

                logger.info(loggerHeader + "We're all done here!")

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
    logger.debug(loggerHeader + "Working on torrent: " + torrent_hash)

    if len(torrent_hash) == 32:
        torrent_hash = b16encode(b32decode(torrent_hash))

    if not len(torrent_hash) == 40:
        logger.error(loggerHeader + "Torrent hash is missing, or an invalid hash value has been passed")
    else:
        rp = rProcess()
        rp.main(torrent_hash)
