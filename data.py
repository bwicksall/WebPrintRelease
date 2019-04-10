import cups
import json
import subprocess
import os
import config
from cache import cache

def getPageCount( file, job_id ):
    """Count the pages in a file"""
    
    # Use str(job_id) as the key cause file changes every time
    cached = cache.get( str( job_id ) )
    if cached:
        return int( cached )
    
    # Use pkpgcounter to get page count
    args = ( "pkpgcounter", file )
    
    try:
        popen = subprocess.Popen( args, stdout=subprocess.PIPE )
        popen.wait()
        pageCount = popen.stdout.read()
        result = pageCount.strip()
    except:
        result = '0'
    
    # Set the cache and return the result.  1 Hour timeout
    cache.set( str( job_id ), result, timeout=3600 )
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
        raise Exception( 'Error: ' + e.message )
        return
    except cups.IPPError as ( status, description ):
        raise Exception( 'Error: ' + description )
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

            # How many copies?
            copies = v.get( 'copies', 1 )

            # Get a documents page count
            pages = getPageCount( document['file'], v['job-id'] )

            # copies * page-count
            v['page-count'] = copies * pages

            # Cleanup the temp document file
            os.remove( document['file'] )

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
        raise Exception( 'Error: ' + e.message )
        return
    except cups.IPPError as ( status, description ):
        raise Exception( 'Error: ' + description )
        return

    try:
        # Get a copy of the actual document being printed
        document = conn.getDocument( job['job-printer-uri'], job['job-id'], 1 )
    except:
        # No way to get page-count
        job['page-count'] = 0
    else:
        # Get a documents page count
        job['page-count'] = getPageCount( document['file'], job['job-id'] )

        # Cleanup the temp document file
        os.remove( document['file'] )

    return job

def getPrinterList():

    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
    except RuntimeError as e:
        raise Exception( 'Error: ' + e.message )
        return
    except cups.IPPError as ( status, description ):
        raise Exception( 'Error: ' + description )
        return

    printerlist = []
    for k, v in printers.items():
        printer = getPrinterAttrs( k )

        printerlist.append( printer )

    return printerlist

def getPrinterAttrs( name ):

    try:
        conn = cups.Connection()
        printerAttrs = conn.getPrinterAttributes( name )
    except RuntimeError as e:
        raise Exception( 'Error: ' + e.message )
        return
    except cups.IPPError as ( status, description ):
        raise Exception( 'Error: ' + description )
        return

    return printerAttrs

def releaseJob( job_id ):

    try:
        conn = cups.Connection()
        # Release the job
        jobs = conn.setJobHoldUntil( job_id, 'no-hold' )
    except RuntimeError as e:
        raise Exception( 'Error: ' + e.message )
        return
    except cups.IPPError as ( status, description ):
        raise Exception( 'Error: ' + description )
        return

    return

def cancelJob( job_id ):

    try:
        conn = cups.Connection()
        # Cancel the job.  False just cancels.  True cancels and purges the job from history.
        jobs = conn.cancelJob( job_id, False )
    except RuntimeError as e:
        raise Exception( 'Error: ' + e.message )
        return
    except cups.IPPError as ( status, description ):
        raise Exception( 'Error: ' + description )
        return

    return
