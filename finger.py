#! /usr/bin/env python

import asynchat
import socket

class Finger(asynchat.async_chat):
    def __init__(self, host, query, callback):
        asynchat.async_chat.__init__(self)
        self.query = query
        self.callback = callback
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.push(self.query + '\n')
        self.connect(host)
        self.inbuf = ''
        self.set_terminator(None)

    def handle_connect(self):
        pass

    def collect_incoming_data(self, data):
        self.inbuf += data

    def handle_close(self):
        self.callback(self.inbuf)
        self.close()

if __name__ == '__main__':
    import asyncore

    def p(x):
        print x

    r = finger(('finger.lanl.gov', 79), '121726', p)
    asyncore.loop()
