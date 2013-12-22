import os
import pixywerk
import simpleconfig
from utils import response
import re

default_config = {
    'root':os.getcwd(),
    'name':'pixywerk',
    'template_paths':('templates',),
    'pathelement_blacklist':('.git',),
    'wsgi_path_filters':(),
}
config = default_config

print "PIXYWERK"

if os.environ.has_key('PIXYWERK_CONFIG'):
    infile = file(os.environ['PIXYWERK_CONFIG'],'r')
    config = simpleconfig.load_config(infile, config)
    print "loaded config ",os.environ['PIXYWERK_CONFIG']

print "Config:"
for k,v in config.items():
    print k,'=',v
print "--- ready ---"

filters = ()
for f in config['wsgi_path_filters']:
    filters.append(re.compile(f))

mywerk = pixywerk.PixyWerk(config)

def print_debug(dictionary):
    outp = '<table>'
    for k,v in dictionary.items():
        outp += "<tr><td>%s</td><td>%s</td></tr>" % (k, v)
    return outp + '</table>'

def debug(env):
    cont = "<html><body>"+print_debug(env)+"</body></html>"
    resp = response()
    return resp.done(cont)

def pixywerk(environ, start_response):
    uri = environ['PATH_INFO']
    for f in filters:
        uri = f.sub('',uri)
    
    if uri[-1] == '/':
        uri = uri[:-1]
        
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

