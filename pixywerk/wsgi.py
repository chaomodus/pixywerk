"""Adapts PixyWerk for WSGI usage."""

import os
from . import werk
from . import config
from . import version
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
    'banner':False,
    'debugpage':False,
}

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False
})

log = logging.getLogger('pixywerk')
log.setLevel(logging.DEBUG)

class PixyWSGI(object):
    def __init__(self, configdict={}):
        self.config = default_config
        self.werk = None
        self.filters = []

        lfmt = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh = logging.StreamHandler(stream=sys.stderr)
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(lfmt)
        log.addHandler(sh)

        if 'PIXYWERK_CONFIG' in os.environ:
            with file(os.environ['PIXYWERK_CONFIG'], 'r') as infile:
                self.config = config.load_config_file(infile, self.config)
                log.info("init: loaded config "+os.environ['PIXYWERK_CONFIG'])
        else:
            log.error("no configuration specified! Please set PIXYWERK_CONFIG.")

        if 'workingdir' not in self.config:
            self.config['workingdir'] = self.config['root']
        try:
            os.chdir(self.config['workingdir'])
        except:
            log.error('init: error changing working directory.')

        logcount = 5
        if 'log_count' in self.config:
            try:
                logcount = int(self.config['log_count'])
            except:
                pass

        logsize = 104857600 # 100 mebibytes
        if 'log_maxsize' in self.config:
            try:
                logsize = int(self.config['log_maxsize'])
            except:
                pass

        if 'logfie' in self.config:
            fh = logging.handlers.RotatingFileHandler(self.config['logfile'],
                                                      backupCount=logcount,
                                                      maxBytes=logsize)
            fh.setLevel(logging.INFO)
            fh.setFormatter(lfmt)
            log.addHandler(fh)

        self.werk = werk.PixyWerk(self.config)
        log.info("init: Welcome to PixyWerk.")
        log.info('init: configuration:')
        for k, v in self.config.items():
            log.info('init:   {0} = {1}'.format(k, v))
        log.info('init: ready.')


    def print_debug(self, dictionary):
        """Format a dictionary. (DEBUG PURPOSES)"""
        outp = '<table>'
        for k, v in dictionary.items():
            outp += "<tr><td>{key}</td><td>{value}</td></tr>".format(key=k, value=v)
        return outp + '</table>'


    def debug(self, env):
        """Print out environment and other information about a query.
        (DEBUG PURPOSES)"""

        if 'HTTP_X_REAL_IP' in env:
            ip = env['HTTP_X_REAL_IP']
        else:
            ip = env['REMOTE_ADDR']
        log.info('debug: <{0}> serving debug page.'.format(ip,))
        cont = "<html><body>"+print_debug(env)+"</body></html>"
        resp = response()
        return resp.done(cont)


    def __call__(self, environ, start_response):
        """This is teh callable which implements the WSGI protocol, and is
        notionally the "application" launched by the WSGI runtime."""

        try:
            raw_uri = environ['RAW_URI']
            parsed_uri = urlparse.urlparse(raw_uri)
            path = parsed_uri.path
            environ['PARSED_URI'] = parsed_uri
        except KeyError:
            path = environ['PATH_INFO']
            environ['PARSED_URI'] = None

        for f in self.filters:
            path = f.sub('', path)

        relpath, pth, is_dir = self.werk.path_info(path)
        resp = '404 Not Found'
        headr = list()
        content = '404 NOT FOUND'
        if self.config['debugpage'] and path == '/debug':
            resp, headr, content = debug(environ)
        elif is_dir and path[-1] != '/':
            resp = '301 Moved Permanantly'
            headr.append(('Location', path + '/'))
            content = ''
        else:
            resp, headr, content = self.werk.handle(path, environ)

        if self.config['banner']:
            headr.append(('X-CMS', 'PixyWerk {version}'.format(version=version.version)))
        headr = [(x,str(y)) for x, y in headr]
        start_response(resp, headr)
        return content
