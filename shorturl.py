#! /usr/bin/env python2.2

import asyncore
import asynchat
import socket
import sys
import time

__version__ = '1.0'

DEFAULT_ERROR_MESSAGE = """\
<head>
<title>Error response</title>
</head>
<body>
<h1>Error response</h1>
<p>Error code %(code)d.
<p>Message: %(message)s.
<p>Error code explanation: %(code)s = %(explain)s.
</body>
"""

URLS = []

class URLServer(asyncore.dispatcher):
    def __init__(self, bind, connFactory):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(bind)
        self.listen(4)
        self.connFactory = connFactory

    def handle_accept(self):
        conn, addr = self.accept()
        self.connFactory(conn)


class HTTPHandler(asynchat.async_chat):
    def __init__(self, conn):
        asynchat.async_chat.__init__(self, conn=conn)
        self.client_address = self.getpeername()
        self.set_terminator('\r\n\r\n')
        self.data = ''

    def collect_incoming_data(self, data):
        self.data += data

    def found_terminator(self):
        try:
            self.headers = self.data.split('\r\n')
            self.requestline = self.headers[0]
            self.command, self.path, self.request_version = self.requestline.split()
        except:
            self.send_error(500)
            raise

        try:
            func = getattr(self, "do_" + self.command)
        except AttributeError:
            self.send_error(501, "Unsupported method (%s)" % `self.command`)
            return

        try:
            func()
        except:
            self.send_error(500)
            raise

        self.close()


    # The Python system version, truncated to its first component.
    sys_version = "Python/" + sys.version.split()[0]

    # The server software version.  You may want to override this.
    # The format is multiple whitespace-separated strings,
    # where each string is of the form name[/version].
    server_version = "AsyncoreBaseHTTP/" + __version__

    # The version of the HTTP protocol we support.
    # Don't override unless you know what you're doing (hint: incoming
    # requests are required to have exactly this version string).
    protocol_version = "HTTP/1.0"

    # Table mapping response codes to messages; entries have the
    # form {code: (shortmessage, longmessage)}.
    # See http://www.w3.org/hypertext/WWW/Protocols/HTTP/HTRESP.html
    responses = {
        200: ('OK', 'Request fulfilled, document follows'),
        201: ('Created', 'Document created, URL follows'),
        202: ('Accepted',
              'Request accepted, processing continues off-line'),
        203: ('Partial information', 'Request fulfilled from cache'),
        204: ('No response', 'Request fulfilled, nothing follows'),

        301: ('Moved', 'Object moved permanently -- see URI list'),
        302: ('Found', 'Object moved temporarily -- see URI list'),
        303: ('Method', 'Object moved -- see Method and URL list'),
        304: ('Not modified',
              'Document has not changed singe given time'),

        400: ('Bad request',
              'Bad request syntax or unsupported method'),
        401: ('Unauthorized',
              'No permission -- see authorization schemes'),
        402: ('Payment required',
              'No payment -- see charging schemes'),
        403: ('Forbidden',
              'Request forbidden -- authorization will not help'),
        404: ('Not found', 'Nothing matches the given URI'),

        500: ('Internal error', 'Server got itself in trouble'),
        501: ('Not implemented',
              'Server does not support this operation'),
        502: ('Service temporarily overloaded',
              'The server cannot process the request due to a high load'),
        503: ('Gateway timeout',
              'The gateway server did not receive a timely response'),

        }

    error_message_format = DEFAULT_ERROR_MESSAGE

    def send_error(self, code, message=None):
        """Send and log an error reply.

        Arguments are the error code, and a detailed message.
        The detailed message defaults to the short entry matching the
        response code.

        This sends an error response (so it must be called before any
        output has been generated), logs the error, and finally sends
        a piece of HTML explaining the error to the user.

        """

        try:
            short, long = self.responses[code]
        except KeyError:
            short, long = '???', '???'
        if not message:
            message = short
        explain = long
        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.send(self.error_message_format %
                  {'code': code,
                   'message': message,
                   'explain': explain})

    def send_response(self, code, message=None):
        """Send the response header and log the response code.

        Also send two standard headers with the server software
        version and the current date.

        """
        self.log_request(code)
        if message is None:
            if self.responses.has_key(code):
                message = self.responses[code][0]
            else:
                message = ''
        if self.request_version != 'HTTP/0.9':
            self.send("%s %s %s\r\n" %
                      (self.protocol_version, str(code), message))
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())

    def send_header(self, keyword, value):
        """Send a MIME header."""
        if self.request_version != 'HTTP/0.9':
            self.send("%s: %s\r\n" % (keyword, value))

    def end_headers(self):
        """Send the blank line ending the MIME headers."""
        if self.request_version != 'HTTP/0.9':
            self.send("\r\n")

    def log_request(self, code='-', size='-'):
        """Log an accepted request.

        This is called by send_reponse().

        """

        self.log_message('"%s" %s %s',
                         self.requestline, str(code), str(size))

    def log_error(self, *args):
        """Log an error.

        This is called when a request cannot be fulfilled.  By
        default it passes the message on to log_message().

        Arguments are the same as for log_message().

        XXX This should go to the separate error log.

        """

        apply(self.log_message, args)

    def log_message(self, format, *args):
        """Log an arbitrary message.

        This is used by all other logging functions.  Override
        it if you have specific logging wishes.

        The first argument, FORMAT, is a format string for the
        message to be logged.  If the format string contains
        any % escapes requiring parameters, they should be
        specified as subsequent arguments (it's just like
        printf!).

        The client host and current date/time are prefixed to
        every message.

        """

        return
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def version_string(self):
        """Return the server software version string."""
        return self.server_version + ' ' + self.sys_version

    def date_time_string(self):
        """Return the current date and time formatted for a message header."""
        now = time.time()
        year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
        s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
                self.weekdayname[wd],
                day, self.monthname[month], year,
                hh, mm, ss)
        return s

    def log_date_time_string(self):
        """Return the current time formatted for logging."""
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
                day, self.monthname[month], year, hh, mm, ss)
        return s

    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def address_string(self):
        """Return the client address formatted for logging.

        This version looks up the full hostname using gethostbyaddr(),
        and tries to find a name that contains at least one dot.

        """

        host, port = self.client_address
        return socket.getfqdn(host)


class URLHandler(HTTPHandler):
    def do_GET(self):
        global URLS

        if self.path == '/':
            self.list_urls()
            return
        elif self.path == '/newest':
            url = URLS[-1]
        else:
            try:
                idx = int(self.path[1:])
                url = URLS[idx]
            except (ValueError, IndexError):
                self.send_error(404)
                return

        self.send_response(301)
        self.send_header('Location', url)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.send('<a href="%s">%s</a>' % (url, url))

    def log_message(self, format, *args):
        # Don't do anything, so we can run in the background.
        pass

    def list_urls(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.send('<title>URLs</title><h1>URLs</h1><ol>\n')
        for i in range(len(URLS), 0, -1):
            url = URLS[i - 1]
            self.send('<li><a href="%s">%s</a></li>\n' % (url, url))
        self.send('</ol>\n')

def add(url):
    URLS.append(url)
    return len(URLS) - 1

def unpackHost(str):
    host, port = str.split(':')
    port = int(port)
    return (host, port)

def start(bindaddr):
    return URLServer(bindaddr, URLHandler)

def main():
    import sys

    (bind,) = sys.argv[1:]
    bindaddr = unpackHost(bind)
    m = start(bindaddr)
    asyncore.loop()

if __name__ == '__main__':
    main()
