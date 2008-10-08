#! /usr/bin/env python

import asynchat
import adns
import urlparse
import socket

resolver = adns.init()

proxy = None

class WebRetriever(asynchat.async_chat):
    def __init__(self, url, body_cb):
        asynchat.async_chat.__init__(self)
        self.body_cb = body_cb
        if proxy:
            self.host, self.port = proxy
            self.query = ''
            self.fragment = ''
            self.path = url
        else:
            (self.scheme,
             self.netloc,
             self.path,
             self.query,
             self.fragment) = urlparse.urlsplit(url)
            assert self.scheme == 'http'
            try:
                self.host, port = self.netloc.split(':')
                self.port = int(port)
            except ValueError:
                self.host = self.netloc
                self.port = 80
        self.set_terminator('\n')
        self.in_headers = True
        self.inbuf = ''
        self.body = []
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dnsq = resolver.submit(self.host, adns.rr.A)
        self.resolved = False

    def readable(self):
        if not self.resolved:
            try:
                self.resolved = self.dnsq.check()
                self.connect((self.resolved[3][0], self.port))
            except adns.NotReady:
                return False
        return asynchat.async_chat.readable(self)

    def writable(self):
        return self.resolved and asynchat.async_chat.writable(self)

    def collect_incoming_data(self, data):
        self.inbuf += data

    def handle_connect(self):
        path = urlparse.urlunsplit((None, None, self.path, self.query, self.fragment))
        self.push('GET %s HTTP/1.0\r\n' % path)
        self.push('Host: %s\r\n' % self.host)
        self.push('\r\n')

    def found_terminator(self):
        data, self.inbuf = self.inbuf, ''
        if self.in_headers:
            if not data.strip():
                self.in_headers = False
        else:
            self.body.append(data + self.get_terminator())

    def handle_close(self):
        asynchat.async_chat.close(self)
        self.body_cb(self.body)

if __name__ == '__main__':
    import asyncore

    def p(data):
        print ''.join(data)

    e = WebRetriever('http://quote.yahoo.com/d/quotes.csv?s=wgrd&f=sl1d1t1c1ohgvj1pp2owern&e=.csv', p)
    asyncore.loop()
