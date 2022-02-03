import sys
import os
import tempfile
import logging
import warnings

#import pdlparser, postscript, pdf, pcl345, pclxl, hbp, \
#       pil, mscrap, cfax, lidil, escp2, dvi, tiff, ooo, zjstream, \
#       pnmascii, bj, qpdl, spl1, escpages03, plain

import pdlparser, postscript, pdf, pcl345, pclxl, plain

LOG = logging.getLogger("pkpgcounter.analyzer")

class AnalyzerOptions:
    """A class for use as the options parameter to PDLAnalyzer's constructor."""
    def __init__(self, debug=None,
                       colorspace=None,
                       resolution=None):
        """Sets initial attributes."""
        self.debug = debug
        self.colorspace = colorspace
        self.resolution = resolution


class PDLAnalyzer:
    """Class for PDL autodetection."""
    def __init__(self, filename, options=AnalyzerOptions()):
        """Initializes the PDL analyzer.

           filename is the name of the file or '-' for stdin.
           filename can also be a file-like object which
           supports read() and seek().
        """
        self.options = options
        self.filename = filename
        self.workfile = None

        self._parser = None

    def getJobSize(self):
        """Returns the job's size."""
        size = 0
        self.openFile()
        try:
            try:
                size = self.pdlhandler.getJobSize()
            except pdlparser.PDLParserError as msg:
                raise pdlparser.PDLParserError("Unsupported file format for %s (%s)" % (self.filename, msg))
        finally:
            self.closeFile()
        return size

    def openFile(self):
        """Opens the job's data stream for reading."""
        if hasattr(self.filename, "read") and hasattr(self.filename, "seek"):
            # filename is in fact a file-like object
            infile = self.filename
        elif self.filename == "-":
            # we must read from stdin
            infile = sys.stdin
        else:
            # normal file
            self.workfile = open(self.filename, "rb")
            return

        # Use a temporary file, always seekable contrary to standard input.
        self.workfile = tempfile.NamedTemporaryFile(mode="w+b",
                                                    prefix="pkpgcounter_",
                                                    suffix=".prn",
                                                    dir=tempfile.gettempdir())
        self.filename = self.workfile.name
        while True:
            data = infile.read(pdlparser.MEGABYTE)
            if not data:
                break
            self.workfile.write(data)
        self.workfile.flush()
        self.workfile.seek(0)

    def closeFile(self):
        """Closes the job's data stream if we have to."""
        self.workfile.close()

    def readFirstAndLastBlocks(self, inputfile):
        """Reads the first and last blocks of data."""
        # Now read first and last block of the input file
        # to be able to detect the real file format and the parser to use.
        firstblock = inputfile.read(pdlparser.FIRSTBLOCKSIZE)
        try:
            inputfile.seek(-pdlparser.LASTBLOCKSIZE, 2)
            lastblock = inputfile.read(pdlparser.LASTBLOCKSIZE)
        except IOError:
            lastblock = ""
        return (firstblock, lastblock)


    @property
    def pdlhandler(self):
        if not self._parser:
            self._detectPDLHandler()
        return self._parser

    def detectPDLHandler(self):
        warnings.warn("deprecated - use property self.pdlhandler", DeprecationWarning)
        return self.pdlhandler

    def _detectPDLHandler(self):
        """Tries to autodetect the document format.

           Returns the correct PDL handler class or None if format is unknown
        """

        if self._parser:
            return

        if not os.stat(self.filename).st_size:
            raise pdlparser.PDLParserError("input file %s is empty !" % str(self.filename))
        (firstblock, lastblock) = self.readFirstAndLastBlocks(self.workfile)
        # IMPORTANT: the order is important below. FIXME.
#        for module in (postscript, \
#                       pclxl, \
#                       pdf, \
#                       qpdl, \
#                       spl1, \
#                       dvi, \
#                       tiff, \
#                       cfax, \
#                       zjstream, \
#                       ooo, \
#                       hbp, \
#                       lidil, \
#                       pcl345, \
#                       escp2, \
#                       escpages03, \
#                       bj, \
#                       pnmascii, \
#                       pil, \
#                       mscrap, \
#                       plain):     # IMPORTANT: don't move this one up !
        for module in (postscript, \
                       pclxl, \
                       pdf, \
                       pcl345, \
                       plain):     # IMPORTANT: don't move this one up !

            try:
                self._parser = module.Parser(self, self.filename,
                                           (firstblock, lastblock))
                LOG.debug("Parser = %s" % module.__name__)
                break
            except pdlparser.PDLParserError:
                pass # try next parser

        if not self._parser:
            raise pdlparser.PDLParserError("Analysis of first data block failed.")

def main():
    """Entry point for PDL Analyzer."""
    import optparse
    from copy import copy

    def check_cichoice(option, opt, value):
        """To add a CaseIgnore Choice option type."""
        valower = value.lower()
        if valower in [v.lower() for v in option.cichoices]:
            return valower
        else:
            choices = ", ".join([repr(o) for o in option.cichoices])
            raise optparse.OptionValueError(
                "option %s: invalid choice: %r (choose from %s)"
                % (opt, value, choices))

    class MyOption(optparse.Option):
        """New Option class, with CaseIgnore Choice type."""
        TYPES = optparse.Option.TYPES + ("cichoice",)
        ATTRS = optparse.Option.ATTRS + ["cichoices"]
        TYPE_CHECKER = copy(optparse.Option.TYPE_CHECKER)
        TYPE_CHECKER["cichoice"] = check_cichoice

    parser = optparse.OptionParser(option_class=MyOption,
                                   usage="python analyzer.py [options] file1 [file2 ...]")

    (options, arguments) = parser.parse_args()
    
    if (not arguments) or ((not sys.stdin.isatty()) and ("-" not in arguments)):
        arguments.append("-")
    totalsize = 0
    lines = []
    try:
        for arg in arguments:
            try:
                parser = PDLAnalyzer(arg, options)
                totalsize += parser.getJobSize()
            except (IOError, pdlparser.PDLParserError) as msg:
                sys.stderr.write("ERROR: %s\n" % msg)
                sys.stderr.flush()
    except KeyboardInterrupt:
        sys.stderr.write("WARN: Aborted at user's request.\n")
        sys.stderr.flush()
    sys.stdout.write("%i\n" % totalsize)


if __name__ == "__main__":
    main()
