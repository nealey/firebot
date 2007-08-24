#! /usr/bin/env python

"""An asyncore process object.

You'd use it with popen.  See the code at the bottom of
this file for an example.
"""

import asyncore
import fcntl
import os


class process_wrapper:
    """A wrapper to make a process look like a socket.

asyncore wants things to look like sockets.  So we fake it.
"""

    def __init__(self, inf):
        self.inf = inf
        self.fd = inf.fileno()

    def recv(self, size):
        return self.inf.read(size)

    def send(self, data):
        return

    def close(self):
        return self.inf.close()

    def fileno(self):
        return self.fd

class process_dispatcher(asyncore.dispatcher):

    def __init__(self, inf=None):
        asyncore.dispatcher.__init__(self)
        self.connected = 1
        if inf:
            flags = fcntl.fcntl(inf.fileno(), fcntl.F_GETFL, 0)
            flags = flags | os.O_NONBLOCK
            fcntl.fcntl(inf.fileno(), fcntl.F_SETFL, flags)
            self.set_file(inf)

    def set_file(self, inf):
        self.socket = process_wrapper(inf)
        self._fileno = self.socket.fileno()
        self.add_channel()

    def writable(self):
        # It's a one-way socket
        return False

if __name__ == '__main__':
    class foo(process_dispatcher):
        def handle_read(self):
            r = self.recv(1024)
            if r:
                print '[' + r + ']'

        def handle_close(self):
            print "returned", self.close()

    f = os.popen('ls', 'r')
    p = foo(f)
    asyncore.loop()

