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
        try:
            io_status = file('/proc/io_status').read().strip()
        except IOError:
            io_status = "xen is awesome"
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

    def rollthebones(self, sender, forum, addl, match):
        what = match.group(0)
        howmany = int(match.group(1))
        sides = int(match.group(2))
        mult = int(match.group(4) or 1)
        dice = []
        acc = 0
        for i in range(howmany):
            j = random.randint(1, sides)
            dice.append(j)
            acc += j
        acc *= mult
        if howmany > 1:
            forum.msg('%s: %d %r' % (what, acc, dice))
        else:
            forum.msg('%s: %d' % (what, acc))
    bindings.append((re.compile(r'\b([1-9][0-9]*)d([1-9][0-9]*)(x([1-9][0-9]*))?\b'),
                     rollthebones))

    bindings.extend(firebot.FireBot.bindings)



class Wiibot(Gallium):
    def __init__(self, *args, **kwargs):
        Gallium.__init__(self, *args, **kwargs)
        self.wiis = []
        self.add_timer(30, self.check_wiis)

    def check_wiis(self):
        d = feedparser.parse('http://www.wiitracker.com/rss.xml')
        try:
            nt = []
            for e in d.entries:
                t = e.title
                if 'no stock at this time' not in t:
                    try:
                        price = int(t[-3:])
                    except:
                        price = 1
                    if price < 450:
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

        self.add_timer(23, self.check_wiis)


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
    gallium = Gallium(('localhost', 6667),
                      ['gallium'],
                      "I'm a little printf, short and stdout",
                      ["#woozle", "#gallium"])
    gallium.shorturlnotice = False
    gallium.debug = debug

    # fink
    if False:
        fink = Gallium(('irc.oftc.net', 6667),
                       ['fink'],
                       "Do you like my hat?",
                       ["#fast-food"],
                       dbname='fink.cdb')
        fink.debug = debug
        fink.chatty = False

    irc.run_forever(0.5)
