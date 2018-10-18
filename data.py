import cups
import json
import subprocess
import os
from cache import cache

def getPageCount( file, job_id ):
    "Count the pages in a file"
    
    # Use str(job_id) as the key cause file changes every time
    cached = cache.get(str(job_id))
    if cached:
        return cached
    
    # Use pkpgcounter to get page count
    args = ("pkpgcounter", file)
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    pageCount = popen.stdout.read()
    result = pageCount.strip()
    
    # Set the cache and return the result.  1 Hour timeout
    cache.set(str(job_id), result, timeout=3600)
    return result

def getPrintJobs(which_jobs_in='not-completed'):
    
    # Show all active jobs but limit completed to 50
    if which_jobs_in=='not-completed':
        result_limit = -1
    else:
        result_limit = 50
        
    # Setup the connection
    conn = cups.Connection()

    # Get all jobs
    jobs = conn.getJobs(which_jobs=which_jobs_in,
                       my_jobs=False,
                       limit=result_limit,
                       first_job_id=-1,
                       requested_attributes=['all'])

    # Merge job-id into the dictionary and create a new list of dicts
    # with some added information.
    joblist = []
    for k, v in jobs.items():
        v['job-id'] = k

        # Document not available for completed jobs
        if which_jobs_in=='not-completed':
            # Get a copy of the actual document being printed
            document = conn.getDocument(v['job-printer-uri'], v['job-id'], 1)

            # Get a documents page count
            v['page-count'] = getPageCount(document['file'], v['job-id'])

            # Cleanup the temp document file
            os.remove(document['file'])

        joblist.append(v)

    if which_jobs_in=='not-completed':
        # Sort the list by username, job-id ascending.  -k['job-id'] would be decending.
        joblist.sort(key = lambda k: (k['job-originating-user-name'], k['job-id']) ) 
    else:
        # Sort the list by time-at-completed decending.
        joblist.sort(key = lambda k: -k['time-at-completed'] )

    return joblist

def getPrintJob(job_id):
    
    conn = cups.Connection()

    # Get a job
    job = conn.getJobAttributes(job_id=job_id,
                                requested_attributes=['all'])

    try:
        # Get a copy of the actual document being printed
        document = conn.getDocument(job['job-printer-uri'], job['job-id'], 1)
        
    except:
        # No way to get page-count
        job['page-count'] = 0

    else:
        # Get a documents page count
        job['page-count'] = getPageCount(document['file'], job['job-id'])

        # Cleanup the temp document file
        os.remove(document['file'])

    return job

def getPrinterList():
    
    conn = cups.Connection()
    
    printers = conn.getPrinters()
    
    printerlist = []
    for k, v in printers.items():
        v['printer-id'] = k

        printerlist.append(v)
    
    return printerlist

def releaseJob(job_id):
    
    conn = cups.Connection()

    # Release the job
    jobs = conn.setJobHoldUntil(job_id, 'no-hold')
    
    return
                                
                                
