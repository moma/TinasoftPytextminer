# -*- coding: utf-8 -*-
# PyTextMiner Target class
import string
import locale as localization
from .. import NGram

class Target():
    """Target containing ngrams"""

    def __init__(self,
        rawTarget,
        tokens=None,
        type=None,
        ngrams=None,
        minSize=3,
        maxSize=3,
        locale='fr_FR.UTF-8',
        forbiddenChars=u"[^a-zA-Z\'\"\-\s\@\.\,\/\?\!\%\&ÂÆÇÈÉÊÎÛÙàâæçèéêîĨôÔùûü]",
        separator= u"[\s]+",
        emptyString = " ",
        sanitizedTarget=None
        ):

        """Text Target constructor"""
        self.rawTarget = rawTarget
        if tokens is None:
            tokens = []
        self.tokens = tokens
        self.type = type
        if ngrams is None:
            ngrams={}
        self.ngrams = ngrams
        self.minSize = minSize
        self.maxSize = maxSize
        self.locale = locale
        self.forbiddenChars = forbiddenChars
        self.separator = separator
        self.emptyString = emptyString
        self.sanitizedTarget = sanitizedTarget
        #try:
        localization.setlocale(localization.LC_ALL, self.locale)

    def __str__(self):
        return self.rawTarget.encode('utf-8')
    def __repr__(self):
        return self.rawTarget.encode('utf-8')

    def processCooc
