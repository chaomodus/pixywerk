import os
from . import werk
from . import simpleconfig
from . import log
from .utils import response
import re
import sys
import os
import urlparse

default_config = {
    'root':os.getcwd(),
    'name':'pixywerk',
    'template_paths':('templates',),
    'pathelement_blacklist':('.git',),
    'wsgi_path_filters':(),
}

mywerk = None
config = None
filters = None
logger = None

def init(environ):
    global config
    global mywerk
    global filters
    global logger
    config = default_config

    if environ.has_key('wsgi.errors'):
        log_ports = [environ['wsgi.errors'],]
    else:
        log_ports = [sys.stderr,]

    if os.environ.has_key('PIXYWERK_CONFIG'):
        infile = file(os.environ['PIXYWERK_CONFIG'],'r')
        config = simpleconfig.load_config(infile, config)
        print "loaded config ",os.environ['PIXYWERK_CONFIG']

    if not config.has_key('workingdir'):
        config['workingdir'] = config['root']
    try:
        os.chdir(config['workingdir'])
    except:
        print "error changing working directory."

    if config.has_key('logfile'):
        log_ports.append(config['logfile'])

    logger = log.Logger(*log_ports)

    filters = []
    for f in config['wsgi_path_filters']:
        filters.append(re.compile(f))

    mywerk = werk.PixyWerk(config, logger)
    logger(None, 'WSGI','PIXYWERK startup')
    logger(None, 'WSGI','configuration:')
    for k,v in config.items():
        logger(None,'WSGI','{key} = {value}', key=k, value=v)
    logger(None,'WSGI','ready')



def print_debug(dictionary):
    outp = '<table>'
    for k,v in dictionary.items():
        outp += "<tr><td>%s</td><td>%s</td></tr>" % (k, v)
    return outp + '</table>'

def debug(env):
    global mywerk
    global logger
    if env.has_key('HTTP_X_REAL_IP'):
        ip = env['HTTP_X_REAL_IP']
    else:
        ip = env['REMOTE_ADDR']
    logger(None,'debug','<{ip}> SERVING DEBUG PAGE', ip=ip)
    cont = "<html><body>"+print_debug(env)+"</body></html>"
    resp = response()
    return resp.done(cont)

def do_werk(environ, start_response):
    global config
    global mywerk

    if config is None:
        init(environ)
    raw_uri = environ['RAW_URI']
    parsed_uri = urlparse.urlparse(raw_uri)
    path = parsed_uri.path
    environ['PARSED_URI'] = parsed_uri

    for f in filters:
        path = f.sub('',path)

    if path and path[-1] == '/':
        path = path[:-1]

    if not len(path):
        path = '/'

    resp = '404 Not Found'
    headr = dict()
    content = '404 NOT FOUND'
    if path == '/debug':
        resp, headr, content = debug(environ)
    else:
        resp, headr, content = mywerk.handle(path, environ)

    headr.append(('X-CMS','PixyWerk'))

    start_response(resp, headr)
    return content
