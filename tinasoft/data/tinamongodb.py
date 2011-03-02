='localhost'#!/usr/bin/python
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

from tinasoft.data import Handler
from tinasoft.pytextminer import ngram


from os.path import exists
from os.path import join
from os import makedirs

from pymongo import Connection
MONGODB_PORT = 27017

import logging
_logger = logging.getLogger('TinaAppLogger')

class Backend(Handler):
    """
    Low-Level MongoDB database backend
    """
    options = {
        'drop_tables': False
    }

    def __init__(self, path='localhost', **opts):
        """loads options, connect or create db"""
        self.loadOptions(opts)
        self.path = path
        ### connection
        self._connect(self.path)
        ### empty database if needed
        if self.drop_tables is True:
            _logger.debug("will drop all tables of db %s"%self.path)
            self._drop_tables()
        ### chacks success
        if self.is_open() is False:
            raise Exception("Unable to open a tinasqlite database")

    def is_open(self):
        return self.__open

    def _drop_tables(self):
        for coll in self.mongodb.collection_names():
            self.mongodb.drop_collection(coll)

    def _connect(self, hostname):
        """connection method, need to have self.home directory created"""
        try:
            self.mongodb = Connection.__init__(self, hostname, MONGODB_PORT)
            self.__open = True
        except Exception, connect_exc:
            _logger.error("_connect() error : %s"%connect_exc)
            raise Exception(connect_exc)

    def close(self):
        """
        Properly handles transactions explicitely (with parameter) or by default

        """
        if not self.is_open():
            return
        del self.mongodb
        self.__open = False

    def find_one(self, target, id):
        return self.mongodb[target].find_one({"_id":id})

    def find(self, target):
        return self.mongodb[target].find(timeout=False)

    def save(self, target, object):
        return self.mongodb[target].save(object)

    def update(self, target, id, update_object_fragment):
        return self.mongodb[target].update({"_id":id},update_object_fragment)

    def remove(self, target, id):
        return self.mongodb[target].remove({"_id":id})

class Engine(Backend):
    """
    High level database Engine of Tinasoft's MongoDB interface
    """
    # max-size to automatically flush insert queues
    MAX_INSERT_QUEUE = 500
    # caches current insert queues data
    ngramqueue = []
    ngramqueueindex = []
    graphpreprocessqueue = {}
    # used for an indexation session
    ngramindex = []

    options = {
        'drop_tables': False,
        'tables' : [
            'Corpora',
            'Corpus',
            'Document',
            'NGram',
            'Whitelist',
            'GraphPreprocessNGram'
        ],
    }

    def __del__(self):
        """safely closes db"""
        self.close()

    def load(self, id, target, raw=False):
        return self.find_one(target, id)

    def loadMany(self, target, raw=False):
        """
        returns a iterator of tuples (id, pickled_obj)
        """
        return self.find(target, id)

    def loadCorpora(self, id, raw=False ):
        return self.load(id, 'Corpora', raw)

    def loadCorpus(self, id, raw=False ):
        return self.load(id, 'Corpus', raw)

    def loadDocument(self, id, raw=False ):
        return self.load(id, 'Document', raw)

    def loadNGram(self, id, raw=False ):
        return self.load(id, 'NGram', raw)

    def loadGraphPreprocess(self, id, category, raw=False ):
        return self.load(id, 'GraphPreprocess'+category, raw)

    def loadWhitelist(self, id, raw=False):
        return self.load(id, 'Whitelist', raw)

    def insert(self, obj, target, id=None):
        """insert one object given its type"""
        return self.save(target, obj)

    def insertCorpora(self, obj, id=None ):
        return self.insert( obj, 'Corpora', id )

    def insertCorpus(self, obj, id=None ):
        return self.insert( obj, 'Corpus', id )

    def insertDocument(self, obj, id=None ):
        return self.insert( obj, 'Document', id )

    def insertNGram(self, obj, id=None ):
        return self.insert( obj, 'NGram', id )

    def insertGraphPreprocess(self, obj, id, type ):
        """
        @id "corpus_id::node_id"
        @obj graph row dict
        """
        return self.insert( obj, 'GraphPreprocess'+type, id )

    def insertWhitelist(self, obj, id ):
        return self.insert( obj, 'Whitelist', id )

    def insertCluster(self, obj, id ):
        return self.insert( obj, 'Cluster', id )

    def _neighboursUpdate(self, obj, target):
        """
        updates EXISTING neighbours symmetric edges and removes zero weighted edges
        """
        for category in obj['edges'].keys():
            if category == target: continue
            for neighbourid in obj['edges'][category].keys():
                neighbourobj = self.load(neighbourid, category)
                if neighbourobj is not None:
                    if obj['edges'][category][neighbourid] <= 0:
                        del obj['edges'][category][neighbourid]
                        if obj['id'] in neighbourobj['edges'][target]:
                            del neighbourobj['edges'][target][obj['id']]
                    else:
                        neighbourobj['edges'][target][obj['id']] = obj['edges'][category][neighbourid]
                    self.insert(neighbourobj, category)
                else:
                    _logger.warning("missing neighbour %s for node %s"%(neighbourid,obj.id))

    def update_node( self, obj, target, redondantupdate=False ):
        """updates an object and its edges"""
        stored = self.load( obj['id'], target )
        if stored is not None:
            stored.updateObject(obj)
            obj = stored
        if redondantupdate is True:
            self._neighboursUpdate(obj, target)
        # sends a storage object in case it's a Document otherwise it's not used
        obj._cleanEdges(storage=self)
        self.insert( obj, target )

    def updateWhitelist(self, obj, redondantupdate=False):
        """updates a Whitelist and associations"""
        self.update_node(obj, 'Whitelist', redondantupdate)

    def updateCorpora(self, obj, redondantupdate=False):
        """updates a Corpora and associations"""
        self.update_node(obj, 'Corpora', redondantupdate)

    def updateCorpus( self, obj, redondantupdate=False):
        """updates a Corpus and associations"""
        self.update_node(obj, 'Corpus', redondantupdate)

    def updateDocument( self, obj, redondantupdate=False ):
        """updates a Document and associations"""
        self.update_node(obj, 'Document', redondantupdate)

    def updateNGram( self, obj, redondantupdate=False ):
        """updates a ngram and associations"""
        self.update_node(obj, 'NGram', redondantupdate)

    def updateGraphPreprocess(self, period, category, id, row):
        """
        updates a graph preprocess row
        transaction queue grouping by self.MAX_INSERT_QUEUE
        """
        for neighbourid, value in row.iteritems():
            self.
        if category not in self.graphpreprocessqueue:
            self.graphpreprocessqueue[category] = []
        self.graphpreprocessqueue[category] += [(period+"::"+id, row)]
        queuesize = len( self.graphpreprocessqueue[category] )
        if queuesize > self.MAX_INSERT_QUEUE:
            self.flushGraphPreprocessQueue()
            return 0
        else:
            return queuesize

    def select( self, tabname, key=None, raw=False ):
        """
        Yields raw or unpickled tuples (key, obj)
        from a table filtered with a range of key prefix
        """
        if key is not None:
            startkey = re.compile("^%s.*"%key)
            cursor = self.mongodb[target].find({"_id":{"$regex":startkey}},timeout=False)
        else:
            cursor = self.find(tabname)
        for record in cursor:
             if raw is True:
                yield record
            else:
                yield (record["_id"], record)

    def delete(self, id, target, redondantupdate=False):
        """
        deletes a object given its type and id
        """
        if redondantupdate is True:
            obj = self.load(id, target)
            if obj is None: return
            for cat in obj.edges.keys():
                for neighbour_id in obj.edges[cat].keys():
                    neighbour_obj = self.load(neighbour_id, cat)
                    if neighbour_obj is None: continue
                    if id in neighbour_obj.edges[target]:
                        del neighbour_obj.edges[target][id]
                    self.insert(neighbour_obj, cat)
        self.remove(target, id)

    def deleteNGramForm(self, form, ngid, is_keyword):
        """
        removes a NGram's form if every Documents it's linked to
        """
        # updates the NGram first
        ng = self.loadNGram(ngid)
        if form in ng['edges']['label']:
            del ng['edges']['label'][form]
        if form in ng['edges']['postag']:
            del ng['edges']['postag'][form]
        self.insertNGram(ng)

        doc_count = 0
        for doc_id in ng['edges']['Document'].keys():
            doc = self.loadDocument(doc_id)
            doc.deleteNGramForm(form, ngid, is_keyword)
            doc._cleanEdges(self)
            self.insertDocument(doc)
            # propagates decremented edges to its neighbours
            self._neighboursUpdate(doc, 'Document')
            doc_count += 1
            yield None
        yield [form, doc_count]
        return

    def addNGramForm(self, form, target_doc_id, is_keyword):
        """
        adds a NGram as a form to all the dataset's Documents
        """
        new_ngram = ngram.NGram(form.split(" "), label=form)
        stored_ngram = self.loadNGram(new_ngram.id)

        if stored_ngram is not None:
            _logger.debug("%s exists in database"%new_ngram.label)
            stored_ngram.addForm(form.split(" "), ["None"])
            # only updates form attributes
            new_ngram = stored_ngram

        # updated NGram
        self.insertNGram(new_ngram)
        # first and only dataset
        dataset_gen = self.loadMany("Corpora")
        (dataset_id, dataset) = dataset_gen.next()
        doc_count = 0

        # walks through all documents
        for corp_id in dataset['edges']['Corpus'].keys():
            corpus_obj = self.loadCorpus(corp_id)
            for docid in corpus_obj['edges']['Document'].keys():
                total_occs = 0
                doc = self.loadDocument(docid)
                if docid != target_doc_id:
                    total_occs += doc.addNGramForm(form, new_ngram.id, self, False)
                else:
                    total_occs += doc.addNGramForm(form, new_ngram.id, self, is_keyword)
                self.insertDocument(doc)
                if total_occs > 0:
                    doc_count += 1
                    _logger.debug("adding %d times %s in document %s"%(total_occs, form, docid))
                yield None

        yield [form, doc_count]
        return
