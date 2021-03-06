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
#  along with this program.  If not, see <http://www.gnu.org/licenses/gpl.html>.


from tinasoft.data import Exporter as BaseExporter
from tinasoft.data import Importer as BaseImporter

import codecs
import csv
class ExcelComma (csv.excel):
    def __init__(self):
        csv.excel.__init(self)
        self.delimiter = ","   
csv.register_dialect("excel-comma",ExcelComma)
csv.register_dialect("auto",ExcelComma)
class ExcelSemicolon (csv.excel):
    def __init__(self):
        csv.excel.__init(self)
        self.delimiter = ","   
csv.register_dialect("excel-semicolon",ExcelSemicolon)


import logging
_logger = logging.getLogger('TinaAppLogger')

class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF_8
    """
    def __init__(self, f):
        self.decodedreader = f
        self.utf8encoder = codecs.getencoder("utf_8")

    def __iter__(self):
        return self

    def next(self):
        """
        Encodes next line to utf_8
        """
        encodedline = self.utf8encoder( self.decodedreader.next(), 'ignore' )
        return encodedline[0]


class Importer(BaseImporter):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    options = {
        'dialect_read': 'auto', # 'excel'
        'encoding': 'utf_8'
    }

    def __init__(self, path, **kwargs):
        BaseImporter.__init__(self, path, **kwargs)
        # gets columns names
        f1 = self.open( path )
        if f1 is None:
            return
        
        dialect = self.dialect_read
        if dialect == "auto":
            if dialect in csv.list_dialects():
                # auto is really auto! we recompute it each time..
                csv.unregister_dialect("auto")
                print "cleaning auto dialect"
            if dialect not in csv.list_dialects():
                csv.register_dialect("auto",csv.Sniffer().sniff(open(path,"rb").read(10000)))
                print "registered auto dialect"

            # failure to detect using auto?
            if dialect not in csv.list_dialects():
                dialect = self.dialect_read = "excel"

        try:
            print "tried delimiter: %s"% csv.get_dialect(dialect).delimiter
        except:
            print "had to use: ,"
        #print "dialect: %s"%dialect
        
        tmp = csv.reader(f1, dialect=dialect)

        #tmp = csv.reader( f1, dialect=kwargs['dialect'], quoting=csv.QUOTE_NONNUMERIC )
        self.fieldnames = tmp.next()
        del f1, tmp

        recodedcsvfile = UTF8Recoder(self.open(path))
        self.reader = csv.DictReader(
            recodedcsvfile,
            fieldnames=self.fieldnames,
            dialect=dialect,
            restkey="unknown",
            restval=""
        )
        
        # only reads the first line
        for line in self:
            break
        
    def _utf8_to_unicode(self, row):
        """
        Static utf_8 to unicode decoder
        Dedicated to decode csv.DictReader lines output
        """
        unicoderow = {}
        for k,s in row.iteritems():
            try:
                if isinstance(s, str):
                    unicoderow[k] = unicode(s, encoding="utf_8", errors='ignore')
                else:
                    unicoderow[k] = s
            except Exception, ex:
                _logger.error("basecsv._row_to_unicode(), line %d, reason : %s"%(self.reader.line_num, ex))  
        return unicoderow
        
    def next(self):
        try:
            row = self.reader.next()
        except StopIteration, si:
            raise StopIteration(si)
        except Exception, ex:
            _logger.error("basecsv.next() error, line %d, reason : %s"%(self.reader.line_num, ex))
            return None
        else:
            return self._utf8_to_unicode(row)

    def __iter__(self):
        return self


class Exporter(BaseExporter):
    """
    home-made exporter class for a csv file
    """
    # defaults
    options = {
        'encoding': 'utf_8',
        'dialect_write': 'auto'
    }

    def __init__( self, filepath, **kwargs ):
        self.loadOptions(kwargs)
        self.filepath = filepath
        self.file = codecs.open( self.filepath, "w+", encoding=self.encoding, errors='replace' )

    def __del__(self):
        self.file.close()


    # TODO put all this slow delimiter code in the constructor to accelerate
    def writeRow( self, row ):
        """
        writes a csv row to the file handler
        """



        line=[]
        dialect = self.dialect_write
        delimiter = ","
        quotechar = '"'
        iquotechar = "'"
        if dialect in csv.list_dialects():
            dial = csv.get_dialect(dialect)

            try:
                delimiter = dial.delimiter
            except:
                print "couldn't load delimiter from dialect %s" % dialect
                print "so we will be using %s" % delimiter

            try:
                quotechar = dial.quotechar
            except:
                print "couldn't load quotechar from dialect %s" % dialect
                print "so we will be using %s" % quotechar

        if quotechar == "'": iquotechar = '"'
        if quotechar == '"': iquotechar = "'"

        print "will use delimiter %s to write to CSV" % delimiter
            
        try:
            for cell in row:
                if isinstance(cell, str) is True or isinstance(cell, unicode) is True:
                    # there should not be " in cells !!
                    print "\ncell: %s"%cell
                    print "fixed cell: %s"% "".join([quotechar,cell.replace(quotechar,iquotechar),quotechar])
                    line += ["".join([quotechar,cell.replace(quotechar,iquotechar),quotechar])]
                    
                elif isinstance(cell, float) is True:
                    #line += ["".join([self.quotechar,"%.2f"%round(cell,2),self.quotechar])]
                    # AVOID OPENOFFICE FLOAT TO DATE AUTO CONVERSION !!!!
                    line += ["%.2f"%round(cell,2)]
                else:
                    line += [str(cell)]

            self.file.write( delimiter.join(line) + "\n" )
        except Exception, ex:
            _logger.error("error basecsv.Exporter : %s"%ex)

    def writeFile( self, columns, rows ):
        """
        Iterates over a list of rows and calls
        """
        self.writeRow( columns )
        for row in rows:
            self.writeRow( row )
