#! /usr/bin/env python
# -*- coding: utf-8 -*-

import firebot
import irc
import re
import os
import random

class Gallium(firebot.FireBot):
    bindings = []

    bindings.extend(firebot.FireBot.bindings)

    def __init__(self, *args, **kwargs):
        firebot.FireBot.__init__(self, *args, **kwargs)
        self.heartbeat_interval=3
        self.debug = True

    def randglyph(self, sender, forum, addl, match):
        count = 0
        while count < 5:
            i = random.randint(0, 0xffff)
            r = self.get('U+%x' % i)
            if r:
                forum.msg('U+%X %s' % (i, r))
                return
            count += 1
        forum.msg("I tried %d random numbers and none of them was defined." % count)
    bindings.append((re.compile(r"^u\+rand$"),
                     randglyph))

    def whuffie_up(self, sender, forum, addl, match):
        nick = match.group('nick')
        if nick.lower() == sender.name().lower():
            forum.msg(self.gettext('whuffie whore', sender=sender.name()))
            return
        if match.group('dir') == 'up':
            amt = 1
        else:
            amt = -1
        self.whuffie_mod(nick, amt)
    bindings.append((re.compile(r"^,(?P<dir>up|down)\s+(?P<nick>\w+)$"),
                     whuffie_up))


if __name__ == '__main__':
    import shorturl
    import socket

    # Short URL server
    us = shorturl.start(('', 0))
    firebot.URLSERVER = (socket.gethostbyaddr(socket.gethostname())[0],
                         us.getsockname()[1])

    snowbot = Gallium(('irc.freenode.net', 6667),
                      ['dorkbot'],
                      "I'm a little printf, short and stdout",
                      ["#rcirc"],
                      dbname='dorkbot.db')

    irc.run_forever(0.5)

