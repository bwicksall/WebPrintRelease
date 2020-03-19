import sqlite3

def initDB():
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    # Check to see if jobs table exists and act accordingly
    c.execute( "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'" )

    if c.fetchone() == None:
        # Table doesn't exist so create
        c.execute( "CREATE TABLE jobs (id integer, pages integer)" )

        conn.commit()

    # Check to see if ver table exists and act accordingly
    c.execute( "SELECT name FROM sqlite_master WHERE type='table' AND name='ver'" )

    if c.fetchone() == None:
        # Table doesn't exist so create
        c.execute( "CREATE TABLE ver (version integer)" )

        c.execute( 'INSERT INTO ver VALUES (1)' )

        conn.commit()

    # Version 2 Updates
    c.execute( "SELECT version FROM ver" )
    row = c.fetchone()
    if row[0] == 1:
        c.execute( "ALTER TABLE jobs ADD location VARCHAR" )

        c.execute( 'UPDATE ver SET version = 2' )

        conn.commit()

    conn.close()

def getDbPageCount( job_id ):
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    c.execute( "SELECT pages FROM jobs WHERE id=?", (job_id,) )

    row = c.fetchone()

    conn.close()

    if row == None:
        result = None
    else:
        result = row[0]

    return result

def getDbJobLocation( job_id ):
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    c.execute( "SELECT location FROM jobs WHERE id=?", (job_id,) )

    row = c.fetchone()

    conn.close()

    if row == None:
        result = None
    else:
        result = row[0]

    return result

def putDbPageCount( job_id, pages ):
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    c.execute( 'INSERT INTO jobs (id, pages) VALUES (?,?)', ( job_id, pages ) )

    conn.commit()
    conn.close()

    return

def putDbJobLocation( job_id, location ):
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    c.execute( 'UPDATE jobs SET location = ? WHERE id = ?', ( location, job_id ) )

    conn.commit()
    conn.close()

    return
    
