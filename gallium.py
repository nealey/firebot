#! /usr/bin/env python
# -*- coding: utf-8 -*-

import firebot
import irc
import re
import os
import random
import feedparser
from procbot import ProcBot, Runner

class Gallium(firebot.FireBot, ProcBot):
    opall = False
    bindings = []

    def cmd_invite(self, sender, forum, addl):
        # Join any channel to which we're invited
        self.write('JOIN', forum.name())

    def cmd_join(self, sender, forum, addl):
        #firebot.FireBot.cmd_join(self, sender, forum, addl)
        if self.opall:
            if sender.name() == self.nick:
                # If it was me, get a channel listing and beg for ops
                self.write('WHO %s' % (forum.name()))
                forum.notice('If you op me, I will op everyone who joins this channel.')
            else:
                # Otherwise, op the user
                forum.write(['MODE', forum.name(), '+o'], sender.name())

    def cmd_352(self, sender, forum, addl):
        # Response to WHO
        forum = irc.Channel(self, addl[0])
        who = irc.User(self, addl[4], addl[1], addl[2])
        self.add_luser(who, forum)

    def server_status(self, sender, forum, addl, match):
        loadavg = file('/proc/loadavg').read().strip()
	io_status = file('/proc/io_status').read().strip()
	forum.msg('%s; load %s' % (io_status, loadavg))
    bindings.append((re.compile(r"^\008[:, ]+server status"),
                    server_status))

    def unsafe_eval(self, sender, forum, addl, match):
        if self.debug:
            txt = match.group(1)
            r = eval(txt)
            forum.msg('%s: %r' % (sender.name(), r))
    bindings.append((re.compile(r"^\008[:, ]+eval (.*)$"),
                     unsafe_eval))

    def randglyph(self, sender, forum, addl, match):
        count = 0
        tries = []
        while count < 6:
            i = random.randint(0, 0xffff)
            k = 'U+%04x' % i
            tries.append(k)
            r = self.get(k)
            if r:
                forum.msg('%s %s' % (k, r))
                return
            count += 1
        forum.msg("Nothing found (tried %s)" % tries)
    bindings.append((re.compile(r"^u\+rand$"),
                     randglyph))

    bindings.extend(firebot.FireBot.bindings)


class Wiibot(Gallium):
    def __init__(self, *args, **kwargs):
        Gallium.__init__(self, *args, **kwargs)
        self.wiis = []
        self.add_timer(27, self.check_wiis)

    def check_wiis(self):
        d = feedparser.parse('http://www.wiitracker.com/rss.xml')
        try:
            nt = []
            for e in d.entries:
                t = e.title
                if 'no stock at this time' not in t:
                  nt.append(t)
            if self.wiis != nt:
                if nt:
                    for t in nt:
                        self.announce('[wii] ' + t)
                else:
                    self.announce('[wii] No more wiis')
            self.wiis = nt
        except:
            pass

        self.add_timer(27, self.check_wiis)


if __name__ == '__main__':
    import shorturl
    import socket
    import daemon
    import sys

    debug = False
    if "-d" in sys.argv:
        debug = True

    if not debug:
        # Become a daemon
        log = file('gallium.log', 'a')
        daemon.daemon('gallium.pid', log, log)

    # Short URL server
    us = shorturl.start(('', 0))
    firebot.URLSERVER = (socket.gethostbyaddr(socket.gethostname())[0],
                         us.getsockname()[1])

    # gallium
    gallium = Wiibot(('localhost', 6667),
                     ['gallium'],
                     "I'm a little printf, short and stdout",
                     ["#woozle", "#gallium"])
    gallium.shorturlnotice = False
    gallium.debug = debug

    # fink
    fink = Wiibot(('irc.oftc.net', 6667),
                  ['fink'],
                  "Do you like my hat?",
                  ["#fast-food"],
                  dbname='fink.cdb')
    fink.debug = debug

    irc.run_forever(0.5)
