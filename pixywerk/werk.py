from .utils import response, sanitize_path
import mimetypes
mimetypes.init()
import os
import re
from jinja2 import Environment, FileSystemLoader, Template
import time
import datetime
import sys
import logging

log = logging.getLogger('pixywerk.werk')

MARKDOWN_SUPPORT=False
BBCODE_SUPPORT=False
SCSS_SUPPORT=False

try:
    import markdown
    MARKDOWN_SUPPORT=True
except: pass

try:
    import ppcode
    BBCODE_SUPPORT=True
except: pass

try:
    import scss
    SCSS_SUPPORT=True
    scssdecoder = scss.Scss()
except: pass


DEBUG=True

from . import simpleconfig

DEFAULT_PROPS={('header','Content-type'):'text/html',
               'template':'default.html',
               'fstemplate':'default-fs.html',
               'title':'{path}',
               'dereference':('title',),
}

hmatch = re.compile('^header:')

def datetimeformat(value, fmat='%Y-%m-%d %T %Z'):
    return time.strftime(fmat, time.localtime(value))

def process_md(cont):
    if MARKDOWN_SUPPORT:
        return markdown.markdown(cont)
    else:
        return cont

def process_bb(cont):
    if BBCODE_SUPPORT:
        return ppcode.decode(cont)
    else:
        return cont

def process_scss(cont):
    if SCSS_SUPPORT:
        return scssdecoder.complie(cont)
    else:
        return cont


bbcode_file_spec = {'mimeinfo':'bbcode content','mime-type':'text/html','templatable':True,'processor':process_bb}
file_types = {'.md':{'mimeinfo':'markdown content','mime-type':'text/html','templatable':True,'processor':process_md},
              '.pp':bbcode_file_spec,
              '.bb':bbcode_file_spec,
              '.scss':{'mimeinfo':'SCSS file','mime-type':'text/css','templatable':False,'processor':process_scss}}

class PixyWerk(object):
    def __init__(self, config):
        self.config = config
        if not (config.has_key('root') and config.has_key('template_paths') and config.has_key('name')):
            raise ValueError('need root, template_paths, and name configuration nodes.')

        tmplpaths = [os.path.join(config['root'], x) for x in config['template_paths']]
        self.template_env = Environment(loader=FileSystemLoader(tmplpaths))
        self.template_env.globals['getmetadata'] = self.get_metadata
        self.template_env.globals['getcontent'] = self.get_content
        self.template_env.filters['date'] = datetimeformat

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

    def get_content(self, path):
        # FIXME this should contain the actual filesystem access blob instead of do_handle.
        code, content, metadata, mimetype, enctype = self.do_handle(path)
        return content

    def generate_index(self, path,metadata):
        template = self.template_env.get_template(metadata['fstemplate'])

        dcont = os.listdir(path)
        files = dict()
        for item in dcont:
            st = os.stat(os.path.join(path,item))
            if item in self.config['pathelement_blacklist']:
                continue
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

            if file_types.has_key(ext):
                mimetype = file_types[ext]['mimeinfo']
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

    def dereference_metadata(self, metadata):
        for m in metadata['dereference']:
            # this is so meta
            metadata[m] = metadata[m].format(**metadata)

    def do_handle(self, path, environ=None):
        relpth = sanitize_path(path)
        pth = os.path.join(self.config['root'],relpth)

        try:
            if environ.has_key('HTTP_X_REAL_IP'):
                ip = environ['HTTP_X_REAL_IP']
            else:
                ip = environ['REMOTE_ADDR']
        except (KeyError, AttributeError):
            ip = 'unk'

        log.debug('handle: <{0}> entering handle for {1}'.format(ip, pth))
        content = ''
        templatable = False
        formatable = False
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
            for idxf in ('index','index.html','index.md','index.pp','index.bb'):
                c, cont, mt, mimet, enct = self.do_handle(path+'/'+idxf, environ)
                if c == 200:
                    return c, cont, mt, mimet, enct
            # directory with no index - render an index
            content = self.generate_index(pth,metadata)
            templatable = True
        elif os.access(pth+'.cont',os.F_OK):
            # cont file - magical pathname
            content = file(pth+'.cont', 'r').read().decode('utf-8')
            templatable = True
            formatable = True
        elif os.access(pth,os.F_OK):
            # normal file - load and inspect
            try:
                ext = os.path.splitext(pth)[-1].lower().strip()
            except:
                ext = ''

            if ext in file_types.keys():
                content = file_types[ext]['processor'](file(pth,'r').read().decode('utf-8'))
                templatable = file_types[ext]['templatable']
                mimetype = file_types[ext]['mime-type']
            elif ext == '.cont':
                content=file(pth, 'r').read().decode('utf-8')
                templatable = True
                formatable = True
            else:
                mtypes = mimetypes.guess_type(pth)
                if mtypes[0]:
                    mimetype = mtypes[0]
                else:
                    mimetype = 'application/octet-stream'
                if mtypes[1]:
                    enctype = mtypes[1]

                content = file(pth,'r').decode('utf-8')


        else:
            # 404
            log.info('handle: <{0}> {1} -> 404'.format(ip, pth))
            return 404, None, None, None, None


        # tweak metadata
        metadata['mimetype'] = mimetype
        metadata['enctype'] = enctype
        self.dereference_metadata(metadata)

        # Render file
        if templatable and content:
            if formatable:
                conttp = self.template_env.from_string(content,globals={'getmetadata':self.get_metadata})
                content = conttp.render(environ=environ, path=relpth, metadata=metadata)
            template = self.template_env.get_template(metadata['template'])
            content = template.render(content=content, environ=environ, path=relpth, metadata=metadata)
            mimetype = 'text/html'

        log.info('handle: <{0}> {1} -> 200'.format(ip, pth))
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
