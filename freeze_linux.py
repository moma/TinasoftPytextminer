#!/usr/bin/python
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

__version__="1.3.0"
__url__="http://tinasoft.eu"
__longdescr__="A text-mining python module producing thematic field graphs"
__license__="GNU General Public License"
__keywords__="nlp,textmining,graph"
__author__="elias showk"
__author_email__="elishowk@nonutc.fr"
#__classifiers__="nlp textmining http"
from os.path import join
from glob import glob
import platform

from cx_Freeze import setup, Executable

# for win32, see: http://wiki.wxpython.org/cx_freeze

includes = [
  'tinasoft.data.basecsv',
  'tinasoft.data.coocmatrix',
  'tinasoft.data.gexf',
  'tinasoft.data.medline',
  'tinasoft.data.tinacsv',
  'tinasoft.data.tinasqlite',
  'tinasoft.data.whitelist',
  'jsonpickle','tenjin','simplejson'
]

excludes = ['_gtkagg', '_tkagg', 'curses', 'email', 'pywin.debugger',
            'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl',
            'Tkconstants', 'Tkinter','tinasoft.data.tinabsddb','bsddb3']

packages = ['nltk', 'numpy', 'twisted', 'twisted.web','twisted.internet','encodings','zope.interface']

setup(
        name = "tinasoft",
        version = __version__,
        description = __longdescr__,
        executables = [Executable("httpserver.py")],
        options = {
            "build_exe": {
                "includes": includes,
                "excludes": excludes,
                "packages": packages,
            }
        }
)
