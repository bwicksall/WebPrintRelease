import sqlite3

def initDB():
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    # Check to see if tables exist and act accordingly
    c.execute( "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'" )

    if c.fetchone() == None:
        # Tables don't exist so create
        c.execute( "CREATE TABLE jobs (id integer, pages integer)" )
        
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

def putDbPageCount( job_id, pages ):
    conn = sqlite3.connect( 'wpr.db' )

    c = conn.cursor()

    c.execute( 'INSERT INTO jobs VALUES (?,?)', ( job_id, pages ) )

    conn.commit()
    conn.close()

    return
    
