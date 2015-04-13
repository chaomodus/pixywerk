"""Adapts PixyWerk for WSGI usage."""

import os
from . import werk
from . import simpleconfig
from .utils import response
import re
import sys
import urlparse
import logging
import logging.config
import logging.handlers

default_config = {
    'root': os.getcwd(),
    'name': 'pixywerk',
    'template_paths': ('templates',),
    'pathelement_blacklist': ('.git',),
    'wsgi_path_filters': (),
}

mywerk = None
config = None
filters = None

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False
})

log = logging.getLogger('pixywerk')
log.setLevel(logging.DEBUG)


def init(environ):
    """Sets up statics, logging, loads configuration file and initiates
       PixyWerk."""
    global config
    global mywerk
    global filters
    config = default_config

    if 'wsgi.errors' in environ:
        stderr = environ['wsgi.errors']
    else:
        stderr = sys.stderr

    lfmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh = logging.StreamHandler(stream=stderr)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(lfmt)
    log.addHandler(sh)

    if 'PIXYWERK_CONFIG' in os.environ:
        infile = file(os.environ['PIXYWERK_CONFIG'], 'r')
        config = simpleconfig.load_config(infile, config)
        log.info("init: loaded config "+os.environ['PIXYWERK_CONFIG'])
    else:
        log.error("no configuration specified! Please set PIXYWERK_CONFIG.")

    if 'workingdir' not in config:
        config['workingdir'] = config['root']
    try:
        os.chdir(config['workingdir'])
    except:
        log.error('init: error changing working directory.')

    if 'logfie' in config:
        fh = logging.handlers.RotatingFileHandler(config['logfile'],
                                                  backupCount=5)
        fh.setLevel(logging.INFO)
        fh.setFormatter(lfmt)
        log.addHandler(fh)

    filters = [re.compile(f) for f in config['wsgi_path_filters']]

    mywerk = werk.PixyWerk(config)
    log.info("init: Welcome to PixyWerk.")
    log.info('init: configuration:')
    for k, v in config.items():
        log.info('init:   {0} = {1}'.format(k, v))
    log.info('init: ready.')


def print_debug(dictionary):
    """Format a dictionary. (DEBUG PURPOSES)"""
    outp = '<table>'
    for k, v in dictionary.items():
        outp += "<tr><td>%s</td><td>%s</td></tr>" % (k, v)
    return outp + '</table>'


def debug(env):
    """Print out environment and other information about a query.
       (DEBUG PURPOSES)"""
    global mywerk
    if 'HTTP_X_REAL_IP' in env:
        ip = env['HTTP_X_REAL_IP']
    else:
        ip = env['REMOTE_ADDR']
    log.info('debug: <{0}> serving debug page.'.format(ip,))
    cont = "<html><body>"+print_debug(env)+"</body></html>"
    resp = response()
    return resp.done(cont)


def do_werk(environ, start_response):
    """This is teh callable which implements the WSGI protocol, and is
       notionally the "application" launched by the WSGI runtime."""
    # FIXME most of this can be ported for the self-hosting mode and should be
    # refactored once that is implemented.
    global config
    global mywerk

    if config is None:
        init(environ)

    try:
        raw_uri = environ['RAW_URI']
        parsed_uri = urlparse.urlparse(raw_uri)
        path = parsed_uri.path
        environ['PARSED_URI'] = parsed_uri
    except KeyError:
        path = environ['PATH_INFO']
        environ['PARSED_URI'] = None

    for f in filters:
        path = f.sub('', path)

    # if path and path[-1] == '/':
    #     path = path[:-1]

    # if not len(path):
    #     path = '/'

    relpath, pth, is_dir = mywerk.path_info(path)
    resp = '404 Not Found'
    headr = list()
    content = '404 NOT FOUND'
    if path == '/debug':
        resp, headr, content = debug(environ)
    elif is_dir and path[-1] != '/':
        resp = '301 Moved Permanantly'
        headr.append(('Location', path + '/'))
        content = ''
    else:
        resp, headr, content = mywerk.handle(path, environ)

    headr.append(('X-CMS', 'PixyWerk'))

    start_response(resp, headr)
    return content
