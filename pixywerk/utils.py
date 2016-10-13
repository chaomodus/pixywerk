"""miscellaneous utilities used by pixywerk."""
import os
import os.path
import re

dots = re.compile('^\.+$')


class response(object):
    """A class representing a response, holding extra headers, content type and
       the stream of data."""
    def __init__(self, code=202, message='OK', contenttype='text/html'):
        self.code = code
        self.message = message
        self.headers = dict()
        self.headers['Content-type'] = contenttype

    def __str__(self):
        return "%d %s" % (self.code, self.message)

    def done(self, contents):
        """Call when response is fully constructed, in the form of return
           response.done(contents)."""
        if 'Content-Length' not in self.headers:
            if isinstance(contents, file):
                try:

                    self.headers['Content-Length'] = str(os.stat(contents).st_size)
                except:
                    pass
            else:
                # FIXME encode contents based on encoding headers!
                contents = contents.encode('UTF-8')
                self.headers['Content-Length'] = str(len(contents))
                contents = iter([contents])

        return str(self), self.headers.items(), contents


def split_path(path):
    """Split a path into its components."""
    outp = list()
    pth, tail = os.path.split(path)
    while (tail):
        outp.append(tail)
        pth, tail = os.path.split(pth)
    outp.reverse()
    return outp


def join_path(pathcomps):
    """Join a path from a list of components."""
    outp = ''
    for i in pathcomps:
        outp = os.path.join(outp, i)
    return outp


def sanitize_path(path):
    """Remove any multiple dot path components from path."""
    pthcomps = split_path(path)

    for i in range(len(pthcomps)):
        if dots.match(pthcomps[i]):
            pthcomps[i] = 'SAFE'

    return join_path(pthcomps)
