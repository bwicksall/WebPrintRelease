import cups
import json
import subprocess
import os
import config
from pypdf import PdfReader
from db import getDbPageCount, putDbPageCount, getDbJobLocation, putDbJobLocation
import sys
sys.path.insert(0,"./PageCounter")
from PageCounter import detectPageCount

def detectPageCountInternal( file ):
    """Count the pages in a file"""

    # Assuming PDF for now

    try:
        # creating a pdf file object
        pdfFileObj = open( file , 'rb' )

        # creating a pdf reader object
        Reader = PdfReader( pdfFileObj )

        # Get page count
        result = len( Reader.pages )
    except:
        result ='0'

    return result

def getPageCount( file, job_id ):
    """Get either stored or newly detected page count"""

    # Check DB
    dbCount = getDbPageCount( job_id )

    if dbCount:
        # Found in the DB
        result = dbCount
    elif file:
        # See if we can detect page count internally
        result = detectPageCountInternal( file )

        if not result:
            # Try with PageCounter
            result = detectPageCount( file )

        if result != '0':
            putDbPageCount( job_id, result )
    else:
        # Can't find page count anywhere
        result = '0'

    return int( result )

def getJobLocation( job_id, job_printer_uri ):
    """Get the printer location for a job"""

    # Check DB for location
    dbLocation = getDbJobLocation( job_id )

    if dbLocation:
        # Found in the DB
        result = dbLocation
    else:
        offset = job_printer_uri.rfind( '/' )
        printerName = job_printer_uri[offset + 1:]

        PrinterAttrs = getPrinterAttrs( printerName )
        Location = PrinterAttrs.get('printer-location', 'Unknown')
        putDbJobLocation( job_id, Location )

        result = Location

    return result

def calcPrintedPages( page_count, copies, sheets_completed, job_state ):

    # Job not completed so no pages printed
    if job_state != 9:
        return 0

    # Use page_count if available.  Otherwise use sheets completed for legacy support
    if page_count > 0:
        result = page_count * copies
    else:
        result = sheets_completed

    return int( result )

def getPrintJobs( which_jobs_in='not-completed', sort='job-originating-user-name', sort_order='asc' ):
    
    # Show all active jobs but limit completed.  Set limit in config.py
    if which_jobs_in=='not-completed':
        result_limit = -1
    else:
        try:
            result_limit = config.COMPLETED_LIMIT
        except:
            # use a safe default
            result_limit = 100

    try:
        conn = cups.Connection()

        # Just retrieve these attributes.  'All' was sometimes returning partial reselt sets.
        r = ["job-id",
             "job-name",
             "job-state",
             "job-printer-uri",
             "job-originating-user-name",
             "job-k-octets",
             "time-at-creation",
             "job-media-sheets-completed",
             "time-at-completed",
             "Duplex",
             "copies"
            ]

        # Get all jobs
        jobs = conn.getJobs( which_jobs=which_jobs_in,
                             my_jobs=False,
                             limit=result_limit,
                             first_job_id=-1,
                             requested_attributes=r )
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    # Merge job-id into the dictionary and create a new list of dicts
    # with some added information.
    joblist = []
    for k, v in jobs.items():
        v['job-id'] = k

        # Document not available for completed jobs
        if which_jobs_in=='not-completed':
            # Get a copy of the actual document being printed
            document = conn.getDocument( v['job-printer-uri'], v['job-id'], 1 )

            # Get a documents page count
            v['page-count'] = getPageCount( document['file'], v['job-id'] )

            # Cleanup the temp document file
            os.remove( document['file'] )
        else:
            # No file so try db for page count
            v['page-count'] = getPageCount( None, v['job-id'] )

        v['printed-pages'] = calcPrintedPages( v.get('page-count', 0), v.get('copies', 1), v.get('job-media-sheets-completed', 0), v.get('job-state', 0) )

        v['job-printer-location'] = getJobLocation( v['job-id'], v.get('job-printer-uri', 'Unknown'))

        joblist.append(v)

    if sort_order == 'asc':
        # Sort the list by username, job-id ascending.  -k['job-id'] would be decending.
        joblist.sort(key = lambda k: k[sort] )
    else:
        # Sort Desc
        joblist.sort(key = lambda k: k[sort], reverse=True )

    return joblist

def getPrintJob( job_id ):

    try:
        conn = cups.Connection()

        # Just retrieve these attributes.  'All' was sometimes returning partial reselt sets.
        r = ["job-id",
             "job-name",
             "job-originating-user-name",
             "job-originating-host-name",
             "job-state",
             "job-state-reasons",
             "page-count",
             "job-media-sheets-completed",
             "Duplex",
             "number-of-documents",
             "job-k-octets",
             "job-k-octets-processed",
             "job-uri",
             "job-hold-until",
             "job-priority",
             "time-at-creation",
             "time-at-processing",
             "time-at-completed",
             "PageSize",
             "job-printer-uri",
             "job-printer-up-time",
             "document-format",
             "document-format-detected",
             "document-format-supplied",
             "copies"
            ]

        # Get a job
        job = conn.getJobAttributes( job_id=job_id, requested_attributes=r )
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    try:
        # Get a copy of the actual document being printed
        document = conn.getDocument( job['job-printer-uri'], job['job-id'], 1 )
    except:
        # No file so check database for page count
        job['page-count'] = getPageCount( None, job['job-id'] )
    else:
        # Get a documents page count
        job['page-count'] = getPageCount( document['file'], job['job-id'] )

        # Cleanup the temp document file
        os.remove( document['file'] )

    job['printed-pages'] = calcPrintedPages( job.get('page-count', 0), job.get('copies', 1), job.get('job-media-sheets-completed', 0), job.get('job-state', 0) )
    
    job['job-printer-location'] = getJobLocation( job_id, job.get('job-printer-uri', 'Unknown'))

    return job

def getPrinterList():

    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    printerlist = []
    for k, v in printers.items():
        printer = getPrinterAttrs( k )

        printerlist.append( printer )

    return printerlist

def getLocations():

    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    locations = []
    for k, v in printers.items():
        printer = getPrinterAttrs( k )

        locations.append( printer.get('printer-location', 'Unknown') )

    locations = list(set(locations)) 
    locations.sort()

    return locations

def getPrinterAttrs( name ):

    try:
        conn = cups.Connection()
        printerAttrs = conn.getPrinterAttributes( name )
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    return printerAttrs

def releaseJob( job_id ):

    try:
        conn = cups.Connection()
        # Release the job
        jobs = conn.setJobHoldUntil( job_id, 'no-hold' )
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    return

def cancelJob( job_id ):

    try:
        conn = cups.Connection()
        # Cancel the job.  False just cancels.  True cancels and purges the job from history.
        jobs = conn.cancelJob( job_id, False )
    except RuntimeError as e:
        raise Exception( 'Error: ' + repr(e) )
        return
    except cups.IPPError as e:
        raise Exception( 'Error: ' + e.description )
        return

    return
