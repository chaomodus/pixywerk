from .utils import response, sanitize_path
import mimetypes
mimetypes.init()
import os
import re
from jinja2 import Environment, FileSystemLoader
import time
import datetime
import sys

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
               'fstemplate':'default-fs.html',
               'title':'{path}'
}
hmatch = re.compile('^header:')

def datetimeformat(value, fmat='%Y-%m-%d %T %Z'):
    return time.strftime(fmat, time.localtime(value))

class PixyWerk(object):
    def __init__(self, config, output_port = sys.stderr):
        self.config = config
        if not (config.has_key('root') and config.has_key('template_paths') and config.has_key('name')):
            raise ValueError('need root, template_paths, and name configuration nodes.')

        tmplpaths = [os.path.join(config['root'], x) for x in config['template_paths']]
        self.template_env = Environment(loader=FileSystemLoader(tmplpaths))
        self.template_env.filters['date'] = datetimeformat
        self.output_port = output_port

    def log(self, system, message, **var):
        output = datetime.datetime.now().isoformat() + " ["+system+"] "+message.format(**var)

        self.output_port.write(output + "\n")

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

    def generate_index(self, path,metadata):
        template = self.template_env.get_template(metadata['fstemplate'])

        dcont = os.listdir(path)
        files = dict()
        for item in dcont:
            st = os.stat(os.path.join(path,item))
            mimetype='UNK'
            if os.path.isdir(os.path.join(path,item)):
                mimetype='DIR'
            else:
                mtypes = mimetypes.guess_type(os.path.join(path,item))

                if mtypes[0]:
                    mimetype = mtypes[0]
                else:
                    mimetype = 'application/octet-stream'

            try:
                res= os.path.splitext(item)
                bname='.'.join(res[0:-1])
                ext = res[-1].lower().strip()
            except:
                ext = ''
                bname = item

            if ext == '.md':
                mimetype='markdown content'
            elif ext in ('.pp', '.bb'):
                mimetype='bbcode content'
            elif ext == '.meta':
                continue
            elif ext == '.cont':
                item = bname
                mimetype='content'

            files[item] = {'type':mimetype, 'size':st.st_size, 'atime':st.st_atime, 'ctime':st.st_ctime, 'mtime':st.st_mtime,'fullpath':os.path.join(path,item),'relpath':os.path.join(metadata['path'], item)}
        if files:
            return template.render(files=files)
        else:
            return "no files"

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

    def dereference_metadata(self, metadata):
        # we'll do a format filling for subset of the metadata (just title field for now)
        metadata['title'] = metadata['title'].format(**metadata)

    def do_handle(self, path, environ):
        relpth = sanitize_path(path)
        pth = os.path.join(self.config['root'],relpth)

        if environ.has_key('HTTP_X_REAL_IP'):
            ip = environ['HTTP_X_REAL_IP']
        else:
            ip = environ['REMOTE_ADDR']

        self.log('handle','<{ip}> serving {path}', ip=ip, path=pth)
        content = ''
        templatable = False
        mimetype = ''
        enctype = ''
        code = 200

        # Load metadata tree
        metadata = self.get_metadata(relpth)
        metadata['path'] = relpth
        metadata['abspath'] = pth

        # Locate content file
        if os.path.isdir(pth):
            # search for index file
            for idxf in ('index','index.html','index.md','index.pp'):
                c, cont, mt, mimet, enct = self.do_handle(path+'/'+idxf, environ)
                if c != 404:
                    return c, cont, mt, mimet, enct
            # directory with no index - render an index
            content = self.generate_index(pth,metadata)
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
            elif ext == '.cont':
                content=file(pth, 'r').read()
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
            return 404, None, None, None, None


        # tweak metadata
        metadata['mimetype'] = mimetype
        metadata['enctype'] = enctype
        self.dereference_metadata(metadata)

        # Render file
        if templatable and content:
            template = self.template_env.get_template(metadata['template'])
            content = template.render(content=content, environ=environ, path=relpth, metadata=metadata)
            mimetype = 'text/html'

        return code, content, metadata, mimetype, enctype

    def handle(self, path, environ):
        code, content, metadata, mimetype, enctype = self.do_handle(path, environ)
        if code == 404:
            return response(code=404, message='Not found', contenttype='text/plain').done('404 Not Found')
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
