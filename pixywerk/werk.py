from .utils import response, sanitize_path
import mimetypes
mimetypes.init()
import os
import re
from jinja2 import Environment, FileSystemLoader

from . import simpleconfig

DEFAULT_PROPS={('header','Content-type'):'text/html',
               'handler':'template',
               'template':'default.html',
}
hmatch = re.compile('^header:')

class PixyWerk(object):
    def __init__(self, config):
        self.config = config
        if not (config.has_key('root') and config.has_key('template_paths') and config.has_key('name')):
            raise ValueError('need root, template_paths, name configuration nodes.')

        self.handlers = {'template':self.handle_template}
        tmplpaths = [os.path.join(config['root'], x) for x in config['template_paths']]
        self.template_env = Environment(loader=FileSystemLoader(tmplpaths))

    def handle_template(self, path, environ, metadata, contentfn):
        template = self.template_env.get_template(metadata['template'])
        content = ''
        if os.access(contentfn, os.F_OK):
            # default - html fragment
            content = file(contentfn, 'r').read()
        else:
            if os.access(contentfn+'.md', os.F_OK):
                # support markdown
                pass
            elif os.access(contentfn+'.rst', os.F_OK):
                # support restructuredtext
                pass
            elif os.access(contentfn+'.bb', os.F_OK):
                # support bbcode
                pass
        rendered = template.render(content=content, environ=environ, path=path, metadata=metadata)

        # this should probably be shared between all of the handlers.
        headers = dict()
        for i in metadata.keys():
            if len(i) == 2 and i[0] == 'header':
                headers[i[1]] = metadata[i]
        resp = response()
        resp.headers = headers

        return response().done(rendered)

    def handle(self, path, environ):
        pth = os.path.join(self.config['root'],sanitize_path(path))
        print "handling ",pth

        propfile = None
        contfn = None
        if os.path.isdir(pth):
            if os.access(os.path.join(pth, 'index.props'), os.F_OK):
                # does XXXXX/index.props file exist for path?
                propfile = file(os.path.join(pth, 'index.props'), 'r')
                contfn = os.path.join(pth, 'index.cont')
            elif os.access(os.path.join(pth, '.props'), os.F_OK):
                propfile = file(os.path.join(pth, '.props'), 'r')
                contfn = os.path.join(pth, '.cont')
        else:
            # does XXXXX.props exist for the path?
            if os.access(pth + '.props', os.F_OK):
                propfile = file(pth+'.props', 'r')
                contfn = pth+'.cont'

        if propfile:
            props = simpleconfig.load_config(propfile,DEFAULT_PROPS)
            # look up handler
            if props.has_key('handler') and self.handlers.has_key(props['handler']):
                #FIXME let's help the handlers a bit to reduce the duplicate code for packaging the response.
                return self.handlers[props['handler']](pth, environ, props, contfn)
            else:
                # fixme, error code page config options
                return response(code=503, message='Page error.', contenttype='text/plain').done('503 page error.')

        elif os.access(pth, os.F_OK):
            # does the literal file exist?
            mtypes = mimetypes.guess_type(pth)
            ctype = ''
            if mtypes[0]:
                ctype = mtypes[0]
            else:
                ctype='application/octet-stream'

            r = response(contenttype=ctype)
            if mtypes[1]:
                r.headers['Content-encoding'] = mtypes[1]

            return r.done(file(pth,'r'))

        # IF NO = 404
        # fixme, error code page config options
        return response(code=404, message='Not found', contenttype='text/plain').done('404 Not Found')
