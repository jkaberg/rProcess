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
import logging
import traceback
import ConfigParser
from base64 import b16encode, b32decode

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs'))

from rprocess.helpers.variable import link, symlink, is_rarfile

from libs import requests
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

        media_files = []
        extracted_files = []

        # Sort files into lists depending on file extension
        for f in files:
            if not any(word in f for word in ignore_words):
                if f.endswith(media_ext):
                    media_files.append(f)

                elif f.endswith(archive_ext):
                    if f.endswith('.rar') and is_rarfile(f):  # This will ignore rar sets where all (rar) files end with .rar
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

    def process_media(self, post_proc, destination):

        if post_proc == "couchpotato":
            ssl = config.getboolean("CouchPotato", "ssl") if config.getboolean("CouchPotato", "ssl") else False
            host = config.get("CouchPotato", "host") if config.get("CouchPotato", "host") else 'localhost'
            port = config.get("CouchPotato", "port") if config.get("CouchPotato", "port") else 5050
            base_url = config.get("CouchPotato", "base_url") if config.get("CouchPotato", "base_url") else ''
            api_key = config.get("CouchPotato", "apikey")
            api_call = "/renamer.scan/?async=1&movie_folder="

            user = config.get("CouchPotato", "username") if config.get("CouchPotato", "username") else ''
            password = config.get("CouchPotato", "password") if config.get("CouchPotato", "username") else ''

        elif post_proc == "sickbeard":
            ssl = config.getboolean("Sickbeard", "ssl") if config.getboolean("Sickbeard", "ssl") else False
            host = config.get("Sickbeard", "host") if config.get("Sickbeard", "port") else 'localhost'
            port = config.get("Sickbeard", "port") if config.get("Sickbeard", "port") else 8081
            base_url = config.get("Sickbeard", "base_url") if config.get("Sickbeard", "baseURL") else ''
            api_key = config.get("Sickbeard", "apikey")
            api_call = "/home/postprocess/processEpisode?quiet=1&dir="

            user = config.get("Sickbeard", "username") if config.get("Sickbeard", "username") else ''
            password = config.get("Sickbeard", "password") if config.get("Sickbeard", "password") else ''

        else:
            return

        if not host.endswith(':'):
            host += ':'

        if not port.endswith('/'):
            port += '/'

        if base_url:
            if base_url.startswith('/'):
                base_url.replace('/', '')
            if not base_url.endswith('/'):
                base_url += '/'

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        if api_key:
            url = protocol + host + port + base_url + "api/" + api_key + api_call + destination
        else:
            url = protocol + host + port + base_url + api_call + destination

        try:
            r = requests.get(url, auth=(user, password))
            logger.debug(loggerHeader + "Postprocessing with %s :: Opening URL: %s", post_proc, url)
        except Exception, e:
            logger.error(loggerHeader + "Tried postprocessing with %s :: Unable to open URL: %s %s %s",
                         (post_proc, url, e, traceback.format_exc()))
            raise

        text = r.text
        logger.debug(loggerHeader + "Requests for PostProcessing returned :: %s" + text)


    def main(self, torrent_hash):
        output_dir = config.get("General", "outputDirectory")
        file_action = config.get("General", "fileAction")
        delete_finished = config.getboolean("General", "deleteFinished")
        append_label = config.getboolean("General", "appendLabel")
        ignore_label = (config.get("General", "ignoreLabel")).split('|') if (config.get("General", "ignoreLabel")) else ''
        client_name = config.get("Client", "client")

        couchpotato = config.getboolean("CouchPotato", "active")
        couch_label = config.get("CouchPotato", "label")
        sickbeard = config.getboolean("Sickbeard", "active")
        sick_label = config.get("Sickbeard", "label")

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

                # In some cases uTorrent will do a file lock, to circumvent (and allow post processing) we need
                # to stop the torrent while working with files associated with the torrent
                if file_action == "move" or file_action == "link":
                    client.stop_torrent(torrent)
                    logger.debug(loggerHeader + "Stopping seeding torrent with hash: %s", torrent_hash)

                # Loop through media_files and copy/link/move files
                for f in media_files:
                    file_name = os.path.split(f)[1]
                    if self.process_file(f, destination, file_action):
                        logger.info(loggerHeader + "Successfully performed %s on %s", file_action, file_name)
                    else:
                        logger.error(loggerHeader + "Failed to perform %s on %s", file_action, file_name)

                # Loop through extract_files and extract all files
                for f in extract_files:
                    file_name = os.path.split(f)[1]
                    if self.extract_file(f, destination):
                        logger.info(loggerHeader + "Successfully extracted: %s", file_name)
                    else:
                        logger.error(loggerHeader + "Failed to extract: %s", file_name)

                # If label in torrent client matches CouchPotato label set in config call CouchPotato/Sick-Beard
                # to do additional post processing (eg. renaming etc.)
                if couchpotato and any(word in torrent_info['label'] for word in couch_label):  # call CP postprocess
                    logger.debug(loggerHeader + "Calling CouchPotato to post-process: %s", torrent_info['name'])
                    self.process_media("couchpotato", destination)

                elif sickbeard and any(word in torrent_info['label'] for word in sick_label):  # call SB postprocess
                    logger.debug(loggerHeader + "Calling Sick-Beard to post-process: %s", torrent_info['name'])
                    self.process_media("sickbeard", destination)

                else:
                    logger.debug(loggerHeader + "PostProcessor call params not met.")

                # Delete the torrent (wand associated files) if its enabled in config.
                # Note that it will also delete torrent/files where file action is set to move as there wouldn't be any
                # files to seed when they've been successfully moved.
                if delete_finished or file_action == "move":
                    deleted_files = client.delete_torrent(torrent)
                    logger.info(loggerHeader + "Removing torrent with hash: %s", torrent_hash)
                    for f in deleted_files:
                        logger.info(loggerHeader + "Removed: %s", f)

                # Start the torrent again to continue seeding
                if file_action == "link":
                    # TODO: it would be best if rProcess checked to see if the post-processing completed successfully first - how?
                    client.start_torrent(torrent)
                    logger.debug(loggerHeader + "Starting seeding torrent with hash: %s", torrent_hash)

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
