# -*- coding: utf-8 -*-
#
# pkpgcounter: a generic Page Description Language parser
#
# (c) 2003-2009 Jerome Alet <alet@librelogiciel.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id$
#

"""This module defines the base class for all Page Description Language parsers."""

import sys
import os
import logging

KILOBYTE = 1024
MEGABYTE = 1024 * KILOBYTE
FIRSTBLOCKSIZE = 16 * KILOBYTE
LASTBLOCKSIZE = int(KILOBYTE / 4)

LOG = logging.getLogger("pkpgcounter.pdlparser")

class PDLParserError(Exception):
    """An exception for PDLParser related stuff."""
    def __init__(self, message = ""):
        self.message = message
        Exception.__init__(self, message)
    def __repr__(self):
        return self.message
    __str__ = __repr__

class PDLParser:
    """Generic PDL parser."""
    totiffcommands = None       # Default command to convert to TIFF
    required = []               # Default list of required commands
    openmode = "rb"             # Default file opening mode
    encoding = "utf-8"         # Default encoding opening files
    format = "Unknown"          # Default file format
    def __init__(self, parent, filename, xxx_todo_changeme):
        """Initialize the generic parser."""
        (firstblock, lastblock) = xxx_todo_changeme
        self.parent = parent
        # We need some copies for later inclusion of parsers which
        # would modify the parent's values
        self.filename = filename[:]
        self.firstblock = firstblock[:]
        self.lastblock = lastblock[:]
        self.infile = None
        if not self.isValid():
            raise PDLParserError("Invalid file format !")
        else:
            self.logdebug("Input file is in the '%s' file format." % self.format)

        # Note: individual modules are overriding openmode.  The rU below comes from the pdf.py
        if self.openmode == 'rU':
            self.infile = open(self.filename, self.openmode, encoding=self.encoding, errors='ignore')
        else:
            self.infile = open(self.filename, self.openmode)

    def __del__(self):
        """Ensures the input file gets closed."""
        if self.infile:
            self.infile.close()

    def findExecutable(self, command):
        """Finds an executable in the PATH and returns True if found else False."""
        for cmd in [p.strip() for p in command.split("|")]: # | can separate alternatives for similar commands (e.g. a2ps|enscript)
            for path in os.environ.get("PATH", "").split(":"):
                fullname = os.path.abspath(os.path.join(os.path.expanduser(path), cmd))
                if os.path.isfile(fullname) and os.access(fullname, os.X_OK):
                    return True
        return False

    def isMissing(self, commands):
        """Returns True if some required commands are missing, else False."""
        howmanythere = 0
        for command in commands:
            if not self.findExecutable(command):
                sys.stderr.write("ERROR: %(command)s is missing or not executable. You MUST install it for pkpgcounter to be able to do what you want.\n" % locals())
                sys.stderr.flush()
            else:
                howmanythere += 1
        if howmanythere == len(commands):
            return False
        else:
            return True

    def logdebug(self, message):
        """Logs a debug message if needed."""
        LOG.debug(message)

    def isValid(self):
        """Returns True if data is in the expected format, else False."""
        raise RuntimeError("Not implemented !")

    def getJobSize(self):
        """Counts pages in a document."""
        raise RuntimeError("Not implemented !")

