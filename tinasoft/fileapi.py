# -*- coding: utf-8 -*-
#  Copyright (C) 2009-2011 CREA Lab, CNRS/Ecole Polytechnique UMR 7656 (Fr)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__="elishowk@nonutc.fr"

from os.path import exists
from os.path import join
from os.path import abspath
from os.path import isfile
from os.path import split

from os import makedirs
from os import listdir
from shutil import rmtree

from datetime import datetime

import zlib

class PytextminerFileApi(object):
    """
    Handles all the application file on a local filesystem
    """
    # type and name of the main database
    STORAGE_DSN = "tinasqlite://tinasoft.sqlite"

    def _init_user_directory(self):
        userpath = join( self.config['general']['basedirectory'], self.config['general']['user'] )
        if not exists(userpath):
            makedirs(userpath)
        return userpath

    def _init_source_file_directory(self):
        sourcepath = join(
            self.config['general']['basedirectory'],
            self.config['general']['source_file_directory']
        )
        if not exists(sourcepath):
            makedirs(sourcepath)
        return sourcepath

    def _init_db_directory(self):
        if not exists(join(
                self.config['general']['basedirectory'],
                self.config['general']['dbenv']
            )
            ):
            makedirs(join(
                self.config['general']['basedirectory'],
                self.config['general']['dbenv']
                )
            )

    def _get_user_filepath(self, dataset, filetype, label):
        """
        returns a new relative file path into the user directory
        given a dataset, its type and a label
        """
        path = join( self.user, dataset, filetype )
        now = "".join(str(datetime.now())[:10].split("-"))
        # standard separator in filenames
        filename = now + "-" + label
        finalpath = join( path, label )
        if not exists(path):
            makedirs(path)
            return finalpath
        return finalpath

    def _get_filepath_id(self, path):
        """
        returns the file identifier given a path
        """
        if path is None:
            return None
        if not isfile( path ):
            return None
        (head, tail) = split(path)
        if tail == "":
            return None
        filename_components = tail.split("-")
        if len(filename_components) == 1:
            return None
        return filename_components[0]

    def walk_user_path(self, dataset, filetype):
        """
        Part of the File API
        returns the list of files in the user directory tree
        """
        path = join( self.user, dataset, filetype )
        if not exists( path ):
            return []
        return [
            abspath(join( path, file ))
            for file in listdir( path )
            if not file.startswith("~") and not file.startswith(".")
        ]

    def walk_datasets(self):
        """
        Part of the File API
        returns the list of existing databases
        """
        dataset_list = []
        path = join( self.config['general']['basedirectory'], self.config['general']['dbenv'] )
        validation_filename = self.STORAGE_DSN.split("://")[1]
        if not exists( path ):
            return dataset_list
        for file in listdir( path ):
            if exists(join(path, file, validation_filename)):
                dataset_list += [file]
        return dataset_list

    def delete_dataset(self, dataset_id):
        """
        Part of the File API
        remove a dataset db directory and suer directory
        """
        # may be ? win32api.SetFileAttributes(path, win32con.FILE_ATTRIBUTE_NORMAL)
        del self.opened_storage[dataset_id]
        rmtree(join( self.config['general']['basedirectory'], self.config['general']['dbenv'], dataset_id ), True, lambda: True)
        rmtree(join( self.user, dataset_id ), True, lambda: True)
        return dataset_id

    def walk_source_files(self):
        """
        Part of the File API
        returns the list of files in "sources" directory
        """
        path = join(
            self.config['general']['basedirectory'],
            self.config['general']['source_file_directory']
        )
        if not exists( path ):
            return []
        return listdir( path )

    def _get_sourcefile_path(self, filename):
        """
        Private method returning a source file path given its name
        """
        path = join(
            self.config['general']['basedirectory'],
            self.config['general']['source_file_directory'],
            filename
        )
        if not exists( path ):
            raise IOError("file named %s was not found in %s"%(
                filename,
                join(
                    self.config['general']['basedirectory'],
                    self.config['general']['source_file_directory'])
                )
            )
            return None
        return path

    def write_user_file(self, dataset, path, content):
        """ write user file """
        # path = a/b/c/aa.bb.cc
        fullname = path.split("/")[-1] # fullname = aa.bb.cc
        ext = fullname.split(".")[-1] # ext = cc
        userpath = self._get_user_filepath(dataset, ext, name)
        try:
            content = zlib.decompress(content)
        except:
            # okay, we suppose it was not compressed
            pass
        try:
            f = codecs.open(userpath,"w+b",errors='replace',encoding='utf-8')
        except:
            raise IOError("Error when writing user file to "+path+": "+e)
        try:
            f.write(content)
        except Exception, e:
            raise IOError("Error when writing user file content to "+path+": "+e)
        finally:
            f.close()
        return userpath
