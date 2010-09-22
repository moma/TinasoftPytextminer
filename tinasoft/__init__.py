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

__all__ = ["pytextminer","data"]

# python utility modules
import sys
import os
from os.path import exists
from os.path import join
from os.path import abspath
from os import makedirs

import yaml
from datetime import datetime

import locale
import logging
import logging.handlers

# tinasoft core modules
from tinasoft.data import Engine
from tinasoft.data import Reader
from tinasoft.data import Writer
from tinasoft.data import whitelist as whitelistdata
from tinasoft.pytextminer import corpora
from tinasoft.pytextminer import extractor
from tinasoft.pytextminer import whitelist
from tinasoft.pytextminer import stopwords
from tinasoft.pytextminer import indexer
from tinasoft.pytextminer import adjacency
from tinasoft.pytextminer import stemmer


LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

# fixes the type and name of database
STORAGE_DSN = "tinasqlite://tinasoft.sqlite"

class TinaApp(object):
    """
    Main application class
    should be used in conjunction with ThreadPool()
    see below the standard return codes
    """

    STATUS_RUNNING = 0
    STATUS_ERROR = 666
    STATUS_OK = 1

    @staticmethod
    def notify( subject, msg, data ):
        """
        This method should be overwritten by a context-dependent notifier
        """
        pass

    def __init__(
            self,
            configFilePath,
            loc=None,
            loglevel=logging.DEBUG
        ):
        """
        Init config, logger, locale, storage
        """
        object.__init__(self)
        self.last_dataset_id = None
        self.storage = None
        # import config yaml to self.config
        try:
            self.config = yaml.safe_load( file( configFilePath, 'rU' ) )
        except yaml.YAMLError, exc:
            print exc
            print "bad config yaml path passed to TinaApp"
            print configFilePath
            return self.STATUS_ERROR
        # creates applications directories
        self.user = join( self.config['general']['basedirectory'], self.config['general']['user'] )
        if not exists(self.user):
            makedirs(self.user)

        self.source_file_directory = join( self.config['general']['basedirectory'], self.config['general']['source_file_directory'] )
        if not exists(self.source_file_directory):
            makedirs(self.source_file_directory)

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
        #if not exists(join( self.config['general']['basedirectory'], self.config['general']['index'] )):
            #makedirs(join( self.config['general']['basedirectory'], self.config['general']['index'] ))
        if not exists(join(
                self.config['general']['basedirectory'],
                self.config['general']['log']
            )
            ):
            makedirs(join(
                self.config['general']['basedirectory'],
                self.config['general']['log']
                )
            )

        # Set up a specific logger with our desired output level
        self.LOG_FILENAME = join(
            self.config['general']['basedirectory'],
            self.config['general']['log'],
            'tinasoft.log'
        )
        # set default level to DEBUG
        if 'loglevel' in self.config['general']:
            loglevel = LEVELS[self.config['general']['loglevel']]
        # logger configuration
        self.logger = logging.getLogger('TinaAppLogger')
        self.logger.setLevel(loglevel)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            '%Y-%m-%d %H:%M:%S'
        )
        rotatingFileHandler = logging.handlers.RotatingFileHandler(
            filename = self.LOG_FILENAME,
            maxBytes = 1024000,
            backupCount = 3
        )
        rotatingFileHandler.setFormatter(formatter)
        self.logger.addHandler(rotatingFileHandler)
        # tries support of the locale by the host system
        try:
            if loc is None:
                self.locale = self.config['general']['locale']
            else:
                self.locale = loc
            locale.setlocale(locale.LC_ALL, self.locale)
        except:
            self.locale = ''
            self.logger.warning(
                "configured locale was not found, switching to default ='%s'"%self.locale
            )
            locale.setlocale(locale.LC_ALL, self.locale)

        self.logger.debug("TinaApp started")

    def __del__(self):
        """resumes the storage transactions when destroying this object"""
        if self.storage is not None:
            del self.storage

    def set_storage( self, dataset_id, create=True, **options ):
        """
        unique DB connection handler
        one separate database per dataset=corpora
        always check self.storage is not None before using it
        """
        if self.last_dataset_id is not None and self.last_dataset_id == dataset_id:
            # connection already opened
            return TinaApp.STATUS_OK
        if self.storage is not None:
            self.logger.debug("safely closing last storage connection")
            del self.storage
        try:
            storagedir = join(
                self.config['general']['basedirectory'],
                self.config['general']['dbenv'],
                dataset_id
            )
            if not exists( storagedir ) and create is False:
                raise Exception("dataset %s does not exists, won't create it"%dataset_id)
                return TinaApp.STATUS_OK
                #else:
                #    makedirs( storagedir )
            else:
                # overwrite db home dir
                options['home'] = storagedir
                self.logger.debug(
                    "new connection to a storage for data set %s at %s"%(dataset_id, storagedir)
                )
                self.storage = Engine(STORAGE_DSN, **options)
                self.last_dataset_id = dataset_id
                return TinaApp.STATUS_OK
        except Exception, exception:
            self.logger.error( exception )
            self.storage = self.last_dataset_id = None
            return TinaApp.STATUS_ERROR

    def extract_file(self,
            path,
            dataset,
            whitelistlabel=None,
            outpath=None,
            format='tinacsv',
            overwrite=False,
            minoccs=1,
            userstopwords=None
        ):
        """
        tinasoft source extraction controler
        send a corpora and a storage handler to an Extractor() instance
        """
        path = self._get_sourcefile_path(path)
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        # prepares extraction export path
        if outpath is None:
            if whitelistlabel is None:
                whitelistlabel=dataset
            outpath = self._get_user_filepath(
                dataset,
                'whitelist',
                "%s-extract_dataset.csv"%whitelistlabel
            )
        corporaObj = corpora.Corpora(dataset)
        # instanciate extractor class
        stopwds = stopwords.StopWords(
            "file://%s"%join(self.config['general']['basedirectory'],
            self.config['general']['shared'],
            self.config['general']['stopwords'])
        )

        userstopwords = self.import_userstopwords( userstopwords )
        extract = extractor.Extractor(
            self.storage,
            self.config['datasets'],
            corporaObj,
            stopwds,
            userstopwords,
            stemmer=stemmer.Nltk()
        )
        outpath= extract.extract_file( path, format, outpath, whitelistlabel, minoccs )
        if outpath is not False:
            return abspath(outpath)
        else:
            return self.STATUS_ERROR

    def index_file(self,
            path,
            dataset,
            whitelistpath,
            format='tinacsv',
            overwrite=False,
        ):
        """
        Like import_file but limited to a given whitelist
        """
        path = self._get_sourcefile_path(path)
        corporaObj = corpora.Corpora(dataset)
        whitelist = self.import_whitelist(whitelistpath)
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        # instanciate stopwords and extractor class
        stopwds = stopwords.StopWords(
            "file://%s"%join(self.config['general']['basedirectory'],
            self.config['general']['shared'],
            self.config['general']['stopwords'])
        )
        #stemmer = self._import_module( self.config['datasets']['stemmer'] )
        extract = extractor.Extractor(
            self.storage,
            self.config['datasets'],
            corporaObj,
            stopwds,
            stemmer=stemmer.Nltk()
        )
        if extract.index_file(
            path,
            format,
            whitelist,
            overwrite
        ) is True:
            return extract.duplicate
        else:
            return self.STATUS_ERROR

    def index_archive(self,
            path,
            dataset,
            periods,
            whitelistpath,
            format,
            outpath=None,
            minCooc=1
        ):
        """
        Index a whitelist against an archive of articles,
        updates cooccurrences into storage,
        optionally exporting cooccurrence matrix
        """
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        # path is an archive directory
        path = self._get_sourcefile_path(path)
        corporaObj = corpora.Corpora(dataset)
        whitelist = self.import_whitelist(whitelistpath)
        # prepares extraction export path
        if outpath is not None:
            outpath = self._get_user_filepath(
                dataset,
                'cooccurrences',
                "%s_%s-index_archive.csv"%("+".join(periods),whitelist['label'])
            )
            exporter = Writer("coocmatrix://"+outpath)
        else:
            exporter = None
        archive = Reader( format + "://" + path )
        archive_walker = archive.walkArchive(periods)
        try:
            period_gen, period = archive_walker.next()
            sc = indexer.ArchiveCounter(self.storage)
            if not sc.walkCorpus(whitelist, period_gen, period, exporter, minCooc):
                return self.STATUS_ERROR
            elif not sc.writeMatrix(period, True, minCooc):
                return self.STATUS_ERROR
        except StopIteration, si:
            return self.STATUS_OK

    def generate_graph(self,
            dataset,
            periods,
            whitelistpath,
            outpath=None,
            ngramgraphconfig=None,
            documentgraphconfig=None
        ):
        """
        Generates the proximity numpy matrix from indexed NGrams/Document/Corpus
        given a list of periods and a whitelist
        Then export the corresponding graph

        @return relative path to the gexf file
        """
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        coocmatrix = docmatrix = None
        # for each period, processes cooc and doc intersection
        for period in periods:
            try:
                ngramAdj = adjacency.NgramAdjacency( self.config, self.storage, period, ngramgraphconfig )
                docAdj = adjacency.DocAdjacency( self.config, self.storage, period, documentgraphconfig )
                # to aggregate matrix of multiple periods
                if coocmatrix:
                    ngramAdj.matrix = coocmatrix
                if docmatrix:
                    docAdj.matrix = docmatrix
            except Warning, warner:
                self.logger.warning( warner )
                continue
            coocmatrix = ngramAdj.walkDocuments()
            docmatrix = docAdj.walkDocuments()

        # prepares gexf out path
        params_string = "%s_%s"%(self._get_filepath_id(whitelistpath),"+".join(periods))
        # outpath is an optional label
        if outpath is None:
            outpath = self._get_user_filepath(dataset, 'gexf', params_string)
        else:
            outpath = self._get_user_filepath(dataset, 'gexf', params_string + "_%s"%outpath)

        # import whitelist
        whitelist = self.import_whitelist(whitelistpath)
        # call the GEXF exporter
        GEXFWriter = Writer('gexf://', **self.config['datamining'])
        # adds meta to the futur gexf file
        graphmeta = {
            'parameters': {
                'periods' : "+".join(periods),
                'whitelist': self._get_filepath_id(whitelistpath),
                'location': outpath,
                'dataset': dataset,
                'layout/algorithm': 'tinaforce',
                'rendering/edge/shape': 'curve',
                'data/source': 'browser'
            }
        }
        return GEXFWriter.ngramDocGraph(
            coocmatrix,
            docmatrix,
            outpath + ".gexf",
            db = self.storage,
            periods = periods,
            whitelist = whitelist,
            meta = graphmeta,
            ngramgraphconfig = ngramgraphconfig,
            documentgraphconfig = documentgraphconfig
        )

    def export_cooc(self,
            dataset,
            periods,
            whitelistpath=None,
            outpath=None
        ):
        """
        OBSOLETE
        returns a text file outpath containing the db cooc
        for a list of periods ans an ngrams whitelist
        """
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        if outpath is None:
            outpath = self._get_user_filepath(
                dataset,
                'cooccurrences',
                "%s-export_cooc.txt"%"+".join(periods)
            )
        whitelist = None
        if whitelistpath is not None:
            whitelist = self.import_whitelist(whitelistpath)
        exporter = Writer('coocmatrix://'+outpath)
        return exporter.export_cooc( self.storage, periods, whitelist )


    def import_whitelist(
            self,
            whitelistpath,
            userstopwords=None,
            **kwargs
        ):
        """
        import one or a list of whitelits files
        returns a whitelist object to be used as input of other methods
        """
        whitelist_id = self._get_filepath_id(whitelistpath)
        if whitelist_id is not None:
            # whitelist_path EXIST
            self.logger.debug("loading whitelist from %s (%s)"%(whitelistpath, whitelist_id))
            wlimport = Reader('whitelist://'+whitelistpath, **kwargs)
            wlimport.whitelist = whitelist.Whitelist( whitelist_id, whitelist_id )
            new_wl = wlimport.parse_file()
        else:
            # whitelist_id is a whitelist label into storage
            self.logger.debug("loading whitelist %s from storage"%whitelist_id)
            new_wl = whitelist.Whitelist( whitelist_id, whitelist_id )
            new_wl = whitelistdata.load_from_storage(new_wl, dataset, periods, userstopwords)
        # TODO stores the whitelist ?
        return new_wl

    def import_userstopwords(
            self,
            path=None
        ):
        """
        imports a user defined stopword file (one ngram per line)
        returns a list of one StopWordFilter class instance
        to be used as input of other methods
        """
        if path is None:
            path = join(
                self.config['general']['basedirectory'],
                self.config['general']['userstopwords']
            )
        return [stopwords.StopWordFilter( "file://%s" % path )]

    def _get_user_filepath(self, dataset, filetype, filename):
        """returns a filename from the user directory"""
        path = join( self.user, dataset, filetype )
        now = "".join(str(datetime.now())[:10].split("-"))
        # standard separator in filenames
        filename = now + "-" + filename
        finalpath = join( path, filename )
        if not exists(path):
            makedirs(path)
            return finalpath
        return finalpath

    def _get_filepath_id(self, path):
        """returns the file identifier from a path"""
        if path is None:
            return None
        if not os.path.isfile( path ):
            return None
        (head, tail) = os.path.split(path)
        if tail == "":
            return None
        filename_components = tail.split("-")
        if len(filename_components) == 1:
            return None
        return filename_components[1]

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
            for file in os.listdir( path )
            if not file.startswith("~") and not file.startswith(".")
        ]

    def walk_datasets(self):
        """
        Part of the File API
        returns the list of existing databases
        """
        dataset_list = []
        path = join( self.config['general']['basedirectory'], self.config['general']['dbenv'] )
        validation_filename = STORAGE_DSN.split("://")[1]
        if not exists( path ):
            return dataset_list
        for file in os.listdir( path ):
            if exists(join(path, file, validation_filename)):
                dataset_list += [file]
        return dataset_list

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
        return os.listdir( path )

    def _get_sourcefile_path(self, filename):
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

    def _import_module(self, name):
        """returns a imported module given its string name"""
        try:
            module =  __import__(name)
            return sys.modules[name]
        except ImportError, exc:
            raise Exception("couldn't load module %s: %s"%(name,exc))

    def import_file(self,
            path,
            dataset,
            format='tinacsv',
            overwrite=False,
        ):
        """
        OBSOLETE
        tinasoft common csv file import controler
        """
        path = self._get_sourcefile_path(path)
        corporaObj = corpora.Corpora(dataset)
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        # instanciate stopwords and extractor class
        stopwds = stopwords.StopWords(
            "file://%s"%join(self.config['general']['basedirectory'],
            self.config['general']['shared'],
            self.config['general']['stopwords'])
        )
        stemmer = self._import_module( self.config['datasets']['stemmer'])
        extract = extractor.Extractor(
            self.storage,
            self.config['datasets'],
            corporaObj,
            stopwds,
            stemmer=stemmer.Nltk()
        )
        if extract.import_file(
            path,
            format,
            overwrite
        ) is True:
            return extract.duplicate
        else:
            return self.STATUS_ERROR


    def export_whitelist( self,
            periods,
            dataset,
            whitelistlabel,
            outpath=None,
            whitelistpath=None,
            userstopwords=None,
            minoccs=1,
            **kwargs
        ):
        """
        OBSOLETE
        Public access to tinasoft.data.ngram.export_whitelist()
        """
        # creating default outpath
        if outpath is None:
            outpath = self._get_user_filepath(
                dataset,
                'whitelist',
                "%s-export_whitelist.csv"%whitelistlabel
            )
        if self.set_storage( dataset ) == self.STATUS_ERROR:
            return self.STATUS_ERROR
        userstopwords = self.import_userstopwords(userstopwords)
        whitelist = self.import_whitelist(whitelistpath, userstopwords)
        exporter = Writer('whitelist://'+outpath, **kwargs)
        return abspath(exporter.export_whitelist(
            self.storage,
            periods,
            whitelistlabel,
            userstopwords,
            whitelist,
            minoccs
        ))
