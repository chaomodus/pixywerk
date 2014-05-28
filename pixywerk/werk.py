from .utils import response, sanitize_path
import mimetypes
mimetypes.init()
import os
import re
from jinja2 import Environment, FileSystemLoader

MARKDOWN_SUPPORT=False
BBCODE_SUPPORT=False

try:
    import markdown
    MARKDOWN_SUPPORT=True
except: pass

try:
    import ppcode
    BBCODE_SUPPORT=True
except: pass

from . import simpleconfig

DEFAULT_PROPS={('header','Content-type'):'text/html',
               'template':'default.html',
               'title':'%{path}'
}
hmatch = re.compile('^header:')

class PixyWerk(object):
    def __init__(self, config):
        self.config = config
        if not (config.has_key('root') and config.has_key('template_paths') and config.has_key('name')):
            raise ValueError('need root, template_paths, and name configuration nodes.')

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

    def get_metadata(self, relpath):
        # FIXME this would be trivial to cache
        meta = dict(DEFAULT_PROPS)

        pthcomps = os.path.split(relpath)
        curpath = self.config['root']
        for p in pthcomps:
            metafn = os.path.join(curpath, '.meta')
            if os.access(metafn,os.F_OK):
                meta = simpleconfig.load_config(file(metafn, 'r'), meta)
            curpath=os.path.join(curpath, p)

        if os.path.isdir(curpath):
            metafn = os.path.join(curpath, '.meta')
        else:
            metafn = curpath+'.meta'

        if os.access(metafn,os.F_OK):
            meta = simpleconfig.load_config(file(metafn,'r'), meta)

        return meta

    def generate_index(self, path):
        return ""

    def process_md(self, cont):
        if MARKDOWN_SUPPORT:
            return markdown.markdown(cont)
        else:
            return cont

    def process_bb(self, cont):
        if BBCODE_SUPPORT:
            return ppcode.decode(cont)
        else:
            return cont

    def handle(self, path, environ):
        relpth = sanitize_path(path)
        pth = os.path.join(self.config['root'],relpth)

        print "handling ",pth
        content = ''
        templatable = False
        mimetype = ''
        enctype = ''
        # Locate content file
        if os.path.isdir(pth):
            # directory - render an index
            content = self.generate_index(pth)
            templatable = True
        elif os.access(pth+'.cont',os.F_OK):
            # cont file - magical pathname
            content = file(pth+'.cont', 'r').read()
            templatable = True
        elif os.access(pth,os.F_OK):
            # normal file - load and inspect
            try:
                ext = os.path.splitext(pth)[-1].lower().strip()
            except:
                ext = ''

            if ext == '.md':
                content=self.process_md(file(pth,'r').read())
                templatable = True
            elif ext in ('.pp', '.bb'):
                content=self.processs_bb(file(pth, 'r').read())
                templatable = True
            else:
                mtypes = mimetypes.guess_type(pth)
                if mtypes[0]:
                    mimetype = mtypes[0]
                else:
                    mimetype = 'application/octet-stream'
                if mtypes[1]:
                    enctype = mtypes[1]

                content = file(pth,'r')


        else:
            # 404
            return response(code=404, message='Not found', contenttype='text/plain').done('404 Not Found')

        # Load metadata tree
        metadata = self.get_metadata(relpth)

        # Render file
        if templatable and content:
            template = self.template_env.get_template(metadata['template'])
            content = template.render(content=content, environ=environ, path=relpth, metadata=metadata)
            mimetype = 'text/html'

        resp = response()
        for i in metadata.keys():
            if len(i) == 2 and i[0] == 'header':
                resp.headers[i[1]] = metadata[i]

        if mimetype:
            resp.headers['Content-type'] = mimetype
        if enctype:
            resp.headers['Content-encoding'] = enctype


        # Send contents
        return resp.done(content)
