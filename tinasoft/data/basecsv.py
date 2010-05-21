# -*- coding: utf-8 -*-
from tinasoft.data import Handler

import codecs
import csv
#from datetime import datetime
import logging
_logger = logging.getLogger('TinaAppLogger')

#class Handler(Handler):


class Exporter (Handler):
    """exporter class for csv file"""
    def __init__(self,
            filepath,
            delimiter = ',',
            quotechar = '"',
            #dialect = 'excel',
            **kwargs
        ):
        self.filepath = filepath
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.dialect = dialect
        self.loadOptions(kwargs)
        self.file = codecs.open(self.filepath, "w+", encoding=self.encoding, errors='replace' )

    def writeRow( self, row ):
        #row=map(str, row)
        self.file.write( self.delimiter.join( \
            ["".join([self.quotechar,cell,self.quotechar]) \
            for cell in row] ) + "\n" )

    def writeFile( self, columns, rows ):
        self.writeRow( columns )
        for row in rows:
            self.writeRow( row )


class Importer (Handler):
    """importer class for csv file"""
    def __init__(self,
            filepath,
            delimiter=',',
            quotechar='"',
            **kwargs
        ):
        #_logger.debug("start of basecsv.Importer.__init__ " + filepath )
        try:
            self.filepath = filepath
            self.loadOptions( kwargs )
            # CSV format
            self.delimiter = delimiter
            self.quotechar = quotechar
            # gets columns names
            f1 = self.open( filepath )
            tmp = csv.reader(
                f1,
                delimiter=self.delimiter,
                quotechar=self.quotechar
            )
            self.fieldNames = tmp.next()
            del f1
            # open the file in a Dict mode
            f2 = self.open( filepath )
            self.csv = csv.DictReader(
                    f2,
                    self.fieldNames,
                    delimiter=self.delimiter,
                    quotechar=self.quotechar)
            self.csv.next()
            del f2
            self.docDict = {}
            self.corpusDict = {}
        except Exception, e:
            _logger.error(e)

    def open( self, filepath ):
        return codecs.open( filepath,'rU', errors='replace' )
