#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__="Elias Showk"
__date__ ="$Apr, 12 2010$"

# core modules
import unittest
import os


from tinasoft.data import Reader
from tinasoft.pytextminer import corpora
import pickle
import os


class MedlineTestCase(unittest.TestCase):
    def setUp(self):
        self.corpora = corpora.Corpora('medline corpora')
        self.file = 'source_files/pubmed_cancer_tina_toydb.txt'

    def testImporter(self):
        count=0
        opts = { 'period_size': 8 }
        reader = Reader( "medline://"+self.file, **opts )
        fileGenerator = reader.parseFile()
        try:
            while 1:
                count += 1
                fileGenerator.next()
        except StopIteration, si:
            print "finished test"
            print "found %d documents"%count
            print "found the following corpus : ", reader.corpusDict
            return
        except Exception,e:
            self.fail(e)

if __name__ == '__main__':
    unittest.main()
