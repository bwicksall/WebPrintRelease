from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, send_from_directory
from data import getPrintJobs, getPrintJob, releaseJob, cancelJob, getPrinterList
#from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from functools import wraps
from datetime import datetime, timedelta, date
from cache import cache
import os
import config
import getpass

app = Flask(__name__)
tempfolder = '/tmp/webprint_' + getpass.getuser()
cache.init_app(app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': tempfolder})
app.secret_key=config.SECRET_KEY

def is_number( s ):
    try:
        float( s )
        return True
    except:
        return False

@app.template_filter()
def datetimefilter( value, format='%Y/%m/%d %I:%M %p' ):
    if is_number( value ):
        ts = int( value )

        return datetime.fromtimestamp(ts).strftime( format )
    else:
        return value

app.jinja_env.filters['datetimefilter'] = datetimefilter

@app.template_filter()
def jobstate( value ):
    states = {  3:'Pending',
                4:'Held', 
                5:'Printing',
                6:'Stopped',
                7:'Canceled',
                8:'Aborted: Error',
                9:'Completed'
             }
    
    return states.get( value, 'Unknown' )

app.jinja_env.filters['jobstate'] = jobstate

@app.template_filter()
def printerstate( value ):
    states = {  3:'Idle',
                4:'Processing',
                5:'Stopped'
             }

    return states.get(value, 'Unknown')

app.jinja_env.filters['printerstate'] = printerstate

@app.template_filter()
def queuefromuri(value):
    offset = value.rfind( '/' )
    name = value[offset + 1:]

    return name

app.jinja_env.filters['queuefromuri'] = queuefromuri

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route( '/favicon.ico' )
def favicon():
    return send_from_directory( os.path.join( app.root_path, 'static' ),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon' )

@app.route( '/' )
def index():
    return render_template( 'home.html' )

@app.route( '/about' )
def about():
    return render_template( 'about.html' )

@app.route( '/jobs' )
@is_logged_in
def jobs():

    # Get advanced session values
    advanced = session.get( 'advanced', 0 )
    advanced_start = session.get( 'advanced_start', datetime.now() )

    # Keep track of sort order
    sort = request.args.get('sort', 'job-originating-user-name')
    sort_order = request.args.get('order', 'asc')

    # Used to toggle sort order in template
    if sort_order == 'asc':
        sort_order_next = 'desc'
    else:
        sort_order_next = 'asc'

    # Check how long you have been in advanced mode.  Toggle off if greater than 5 minutes.
    time_now = datetime.now()
    if time_now - advanced_start > timedelta( minutes=5 ):
        advanced = 0
        session['advanced'] = 0

    # Used in the template to update advanced button text
    if advanced == 0:
        next_mode = 'on'
    else:
        next_mode = 'off'

    # Go ahead and get the print jobs
    try:
        Jobs = getPrintJobs( 'not-completed', sort, sort_order )
    except Exception as e:
        return render_template( 'jobs.html', error = e.message )
    
    if Jobs:
        return render_template( 'jobs.html', jobs = Jobs, advanced = advanced, next_mode = next_mode, sort = sort, sort_order = sort_order, sort_order_next = sort_order_next )
    else:
        msg = 'No Print Jobs in Queue'
        return render_template( 'jobs.html', msg = msg, advanced = advanced, next_mode = next_mode )

@app.route( '/jobscompleted' )
@is_logged_in
def jobscompleted():

    # Keep track of sort order
    sort = request.args.get('sort', 'time-at-completed')
    sort_order = request.args.get('order', 'desc')

    # Used to toggle sort order in template
    if sort_order == 'asc':
        sort_order_next = 'desc'
    else:
        sort_order_next = 'asc'

    try:
        Jobs = getPrintJobs( 'completed', sort, sort_order )
    except Exception as e:
        return render_template( 'jobscompleted.html', error = e.message )

    if Jobs:
        filters = request.args.get('filters', 'none')
        daterange = request.args.get('daterange')

        if daterange == None:
            # No date range provided so lets build one that spans 30 days
            startdate = datetime.now() - timedelta(days=30)
            enddate = datetime.now() + timedelta(days=1)
            daterange = startdate.strftime('%m/%d/%Y') + ' - ' + datetime.now().strftime('%m/%d/%Y')
        else:
            # We have a date range so lets parse it
            str_startdate,str_enddate = daterange.split(' - ')

            startdate = datetime.strptime(str_startdate, '%m/%d/%Y')
            enddate = datetime.strptime(str_enddate, '%m/%d/%Y') + timedelta(days=1)

        if filters == 'none':
            # No filters so we will just limit on date range
            filtered_jobs = list( filter( lambda d: startdate < datetime.fromtimestamp( d['time-at-completed'] ) < enddate, Jobs ) )
            return render_template( 'jobscompleted.html', jobs = filtered_jobs, filters = filters, daterange = daterange, sort = sort, sort_order = sort_order, sort_order_next = sort_order_next )
        else:
            # We have filters so filter and limit on date range
            StateList = [9] # == completed
            filtered_jobs = list( filter( lambda d: ( d['job-state'] in StateList ) and ( startdate < datetime.fromtimestamp( d['time-at-completed'] ) < enddate ), Jobs ) )
            return render_template( 'jobscompleted.html', jobs = filtered_jobs, filters = filters, daterange = daterange, sort = sort, sort_order = sort_order, sort_order_next = sort_order_next )
    else:
        msg = 'No Print Jobs History'
        return render_template( 'jobscompleted.html', msg = msg )

@app.route( '/jobs/<int:id>' )
@is_logged_in
def job( id ):

    try:
        Job = getPrintJob( id )
    except Exception as e:
        return render_template( 'job.html', error = e.message )
    else:
        return render_template( 'job.html', job=Job )

@app.route( '/release_job/<int:id>', methods=['POST'] )
@is_logged_in
def release_job( id ):

    try:
        releaseJob( id )
    except Exception as e:
        flash( e.message, 'danger' )
    else:
        flash( 'Job ' + str(id) + ' Released', 'success' )

    # Get sort order to pass to the destination page
    sort = request.form.get('sort', None)
    sort_order = request.form.get('sort_order', None)

    # Build sort order string
    if sort == None:
        sort_str = ''
    else:
        sort_str = '?sort=' + sort + '&order=' + sort_order

    return redirect( url_for( 'jobs' )  + sort_str )

@app.route( '/cancel_job/<int:id>', methods=['POST'] )
@is_logged_in
def cancel_job( id ):

    try:
        cancelJob( id )
    except Exception as e:
        flash( e.message, 'danger' )
    else:
        flash( 'Job ' + str(id) + ' Cancelled', 'success' )

    # Get sort order to pass to the destination page
    sort = request.form.get('sort', None)
    sort_order = request.form.get('sort_order', None)

    # Build sort order string
    if sort == None:
        sort_str = ''
    else:
        sort_str = '?sort=' + sort + '&order=' + sort_order

    return redirect( url_for( 'jobs' )  + sort_str )

@app.route( '/set_advanced', methods=['POST'] )
@is_logged_in
def set_advanced():

    # Get current advaned state
    advanced = session.get('advanced', 0)

    # Get sort order to pass to the destination page
    sort = request.form.get('sort', None)
    sort_order = request.form.get('sort_order', None)

    # Build sort order string
    if sort == None:
        sort_str = ''
    else:
        sort_str = '?sort=' + sort + '&order=' + sort_order

    # Are we toggling on or off?
    if advanced == 0:
        session['advanced'] = 1
        session['advanced_start'] = datetime.now()
    else:
        session['advanced'] = 0

    return redirect( url_for( 'jobs' ) + sort_str )

@app.route( '/printers' )
@is_logged_in
def printers():
    
    try:
        Printers = getPrinterList()
    except Exception as e:
        return render_template( 'printers.html', error = e.message )
    
    if Printers:
        return render_template( 'printers.html', printers = Printers )
    else:
        msg = 'No Prints Configured'
        return render_template( 'printers.html', msg = msg )

@app.route( '/login', methods=['GET','POST'] )
def login():
    
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']
        
        if username == config.USERNAME:
            if password_candidate == config.PASSWORD:
                session['logged_in'] = True
                session['username'] = username
                
                flash('You are now logged in', 'success')
                return redirect(url_for('jobs'))
            else:
                error = 'You have entered an invalid username or password'
                return render_template('login.html', error=error)
        else:
            error = 'You have entered an invalid username or password'
            return render_template('login.html', error=error)
        
    return render_template('login.html')

@app.route('/logout')
@is_logged_in
def logout():
    
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host=config.HOST, port=int(config.PORT), debug=config.DEBUG)
