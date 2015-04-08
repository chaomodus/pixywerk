"""Core PixyWerk functionality."""

from .utils import response, sanitize_path
import mimetypes
mimetypes.init()
import os
import re
from jinja2 import Environment, FileSystemLoader
import time
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
    """Format date/time for jinja."""
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
        return scssdecoder.compile(cont)
    else:
        return cont


bbcode_file_spec = {'mimeinfo':'bbcode content','mime-type':'text/html','templatable':True,'processor':process_bb}
file_types = {'.md':{'mimeinfo':'markdown content','mime-type':'text/html','templatable':True,'processor':process_md},
              '.pp':bbcode_file_spec,
              '.bb':bbcode_file_spec,
              '.scss':{'mimeinfo':'SCSS file','mime-type':'text/css','templatable':False,'processor':process_scss}}

class PixyWerk(object):
    """A full CMS system based on mapping a portion of the filesystem to web, with templates, automatic format handling and per-file heirarchical metadata."""
    def __init__(self, config):
        self.config = config
        if not (config.has_key('root') and config.has_key('template_paths') and config.has_key('name')):
            raise ValueError('need root, template_paths, and name configuration nodes.')

        tmplpaths = [os.path.join(config['root'], x) for x in config['template_paths']]
        self.template_env = Environment(loader=FileSystemLoader(tmplpaths))
        # some convenience functions for making dynamic content
        self.template_env.globals['getmetadata'] = self.get_metadata
        self.template_env.globals['getcontent'] = self.get_content
        self.template_env.globals['getlist'] = self.get_list
        # a useful filter for formatting dates
        self.template_env.filters['date'] = datetimeformat

    def get_metadata(self, relpath):
        """Return the metadata (dict) for a path relative to the root path."""
        # FIXME this would be trivial to cache
        meta = dict(DEFAULT_PROPS)
        pthcomps = os.path.split(relpath)
        curpath = self.config['root']
        for p in pthcomps:
            metafn = os.path.join(curpath, '.meta')
            if os.access(metafn,os.F_OK):
                meta = simpleconfig.load_config(file(metafn, 'r'), meta)
            curpath=os.path.join(curpath, p)
        extspl = os.path.splitext(curpath)
        if len(extspl) > 1 and extspl[1] == '.cont':
            metafn = os.path.join(extspl[0] + '.meta')
        elif os.path.isdir(curpath):
            metafn = os.path.join(curpath, '.meta')
        else:
            metafn = curpath+'.meta'
        if os.access(metafn,os.F_OK):
            meta = simpleconfig.load_config(file(metafn,'r'), meta)
        return meta

    def get_list(self, relpath):
        """Return a list of files within a relative path, with some minor metadata."""
        items = list(os.listdir(os.path.join(self.config['root'],relpath)))
        list.sort(lambda x, y: cmp(x, y))
        output = list()
        for item in items:
            output.append((item, os.path.isdir(item)))
        return output

    def get_content(self, path):
        """Return the rendered content for an absolute path."""
        # FIXME this should contain the actual filesystem access blob instead of do_handle.
        code, content, metadata, mimetype, enctype = self.do_handle(path, template_override=True)
        if isinstance(content, file):
            content = content.read().decode('utf-8')
        return content

    def generate_index(self, path,metadata):
        """Use the template contained in fstemplate to generate a content blob representing a filesystem index."""
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
        """Stub. Derefernces metadata refrenced in the derefernce config option with other metadata values."""
        for m in metadata['dereference']:
            # this is so meta
            metadata[m] = metadata[m].format(**metadata)

    def path_info(self, path):
        relpth = sanitize_path(path)
        pth = os.path.join(self.config['root'],relpth)
        is_dir = os.path.isdir(pth)
        return relpth, pth, is_dir

    def do_handle(self, path, environ=None, template_override=False):
        """Guts of single access handling. Here be dragons."""
        relpth, pth, is_dir = self.path_info(path)

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

        # handle redirects from the metadata file
        if metadata.has_key('redirect'):
            code = metadata['redirect'][0]
            location = metadata['redirect'][1]
            log.info('handle: <{0}> {1} -> {2} => {3}'.format(ip, pth, code, location))
            return code, 'Moved', {('header','Location'):location, 'message':'Mowed'}, None, None
        # Locate content file
        elif is_dir:
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

                content = file(pth,'r')
        else:
            # 404
            log.info('handle: <{0}> {1} -> 404'.format(ip, pth))
            return 404, None, None, None, None


        # tweak metadata
        metadata['mimetype'] = mimetype
        metadata['enctype'] = enctype
        self.dereference_metadata(metadata)

        # Render file
        if templatable and content and not template_override:
            if formatable:
                conttp = self.template_env.from_string(content,globals={'getmetadata':self.get_metadata})
                content = conttp.render(environ=environ, path=relpth, metadata=metadata)
            template = self.template_env.get_template(metadata['template'])
            content = template.render(content=content, environ=environ, path=relpth, metadata=metadata)
            mimetype = 'text/html'

        log.info('handle: <{0}> {1} -> 200'.format(ip, pth))
        return code, content, metadata, mimetype, enctype

    def handle(self, path, environ):
        """Handle one access, wrapping results in a response object."""
        code, content, metadata, mimetype, enctype = self.do_handle(path, environ)
        if code == 404:
            return response(code=404, message='Not found', contenttype='text/plain').done('404 Not Found')
        resp = response(code=code)
        for i in metadata.keys():
            if len(i) == 2 and i[0] == 'header':
                resp.headers[i[1]] = metadata[i]
        if metadata.has_key('message'):
            resp.message = metadata['message']
        if mimetype:
            resp.headers['Content-type'] = mimetype
        if enctype:
            resp.headers['Content-encoding'] = enctype


        # Send contents
        return resp.done(content)
