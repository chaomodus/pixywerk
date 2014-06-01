import os
from . import werk
from . import simpleconfig
from .utils import response
import re
import sys

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

def init(environ):
    global config
    global mywerk
    global filters
    config = default_config

    if environ.has_key('wsgi.errors'):
        output_port = environ['wsgi.errors']
    else:
        output_port = sys.stderr

    if os.environ.has_key('PIXYWERK_CONFIG'):
        infile = file(os.environ['PIXYWERK_CONFIG'],'r')
        config = simpleconfig.load_config(infile, config)
        print "loaded config ",os.environ['PIXYWERK_CONFIG']

    filters = []
    for f in config['wsgi_path_filters']:
        filters.append(re.compile(f))

    mywerk = werk.PixyWerk(config, output_port)
    mywerk.log('WSGI','PIXYWERK startup')
    mywerk.log('WSGI','configuration:')
    for k,v in config.items():
        mywerk.log('WSGI','{key} = {value}', key=k, value=v)
    mywerk.log('WSGI','ready')



def print_debug(dictionary):
    outp = '<table>'
    for k,v in dictionary.items():
        outp += "<tr><td>%s</td><td>%s</td></tr>" % (k, v)
    return outp + '</table>'

def debug(env):
    global mywerk
    if env.has_key('HTTP_X_REAL_IP'):
        ip = env['HTTP_X_REAL_IP']
    else:
        ip = env['REMOTE_ADDR']
    mywerk.log('debug','<{ip}> SERVING DEBUG PAGE', ip=ip)
    cont = "<html><body>"+print_debug(env)+"</body></html>"
    resp = response()
    return resp.done(cont)

def do_werk(environ, start_response):
    global config
    global mywerk

    if config is None:
        init(environ)
    uri = environ['PATH_INFO']
    for f in filters:
        uri = f.sub('',uri)

    if uri and uri[-1] == '/':
        uri = uri[:-1]

    if not len(uri):
        uri = '/'

    resp = '404 Not Found'
    headr = dict()
    content = '404 NOT FOUND'
    if uri == '/debug':
        resp, headr, content = debug(environ)
    else:
        resp, headr, content = mywerk.handle(uri, environ)

    headr.append(('X-CMS','PixyWerk'))

    start_response(resp, headr)
    return content
