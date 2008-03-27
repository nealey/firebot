#! /usr/bin/env python

import firebot
from finger import Finger
from procbot import ProcBot, Runner
import shorturl
import asyncore
import irc
import re
import os
import time
import socket
import rp

def esc(arg):
    return "'" + arg.replace("'", r"'\''") + "'"

def lesc(args):
    return [esc(arg) for arg in args]

class Arsenic(firebot.FireBot, ProcBot):
    debug = False
    bindings = []
    ping_interval = 120
    chatty = True                       # Maybe #x can play nice now

    def __init__(self, *args, **kwargs):
        firebot.FireBot.__init__(self, *args, **kwargs)
        self.seen = {}
        self.lusers = {}
        self.heartbeat_interval=0.01
        self.lag = 0
        self.whinecount = 0

    def runcmd(self, sender, forum, addl, match):
        command = match.group('command')
        args = lesc(lesc(match.group('args').split(' ')))
        argstr = ' '.join(args)
        print argstr
        Runner('%s %s' % (command, argstr),
                   lambda l,r: self.proc_cb('%s: ' % command, sender, forum, l, r))
    bindings.append((re.compile(r"^(?P<command>whois) +(?P<args>.*)$"),
                     runcmd))
    bindings.append((re.compile(r"^(?P<command>host) +(?P<args>.*)$"),
                     runcmd))

    def rp(self, sender, forum, addl, match):
        long = match.group('long') and True
        conn = rp.make_connection()
        rows = rp.rp(match.group('args').strip(), conn=conn)
        ret = rp.format(rows, long=long)
        if long:
            forum.msg('[Sending privately]')
            self.despool(sender, ret)
        else:
            self.despool(forum, ret)
    bindings.append((re.compile(r"^rp +(?P<long>(-l|--long) +)?(?P<args>.*)$"),
                     rp))

    def finger(self, sender, forum, addl, match):
        command = 'finger'
        argstr = match.group('args')
        Finger(('finger.lanl.gov', 79),
               argstr,
               lambda l: self.proc_cb('%s: ' % command, sender, forum, l, 0))
    bindings.append((re.compile(r"^(?P<command>finger) +(?P<args>.*)$"),
                     finger))

    def lag(self, sender, forum, addl, match):
        forum.msg("My server lag is %.3f seconds." % self.lag)
    bindings.append((re.compile(r"^\008[,: ]+ (what is the )?(server )?lag"),
                     lag))


    bindings.extend(firebot.FireBot.bindings)

    ##
    ## IRC protocol-level extensions
    ##

    def add_luser(self, luser, channel):
        # Keeps track of what users have been on what channels, and
        # sends an invite to luser for every channel in which they're
        # listed.  If they're already in the channel, the server just
        # sends back an error.  This has the effect of letting people
        # get back into invite-only channels after a disconnect.
        who = luser.name()
        self.lusers[channel.name()][who] = luser
        for chan, l in self.lusers.iteritems():
            if chan == channel.name():
                continue
            t = l.get(who)
            if t and t.host == luser.host:
                self.write(['INVITE', who, chan])

    def cmd_join(self, sender, forum, addl):
        if sender.name() == self.nick:
            # If it was me, get a channel listing and beg for ops
            self.write(['WHO', forum.name()])
            forum.notice('If you op me, I will op everyone who joins this channel.')
            self.lusers[forum.name()] = {}
        else:
            # Otherwise, add the user
            self.add_luser(sender, forum)
            forum.write(['MODE', forum.name(), '+o'], sender.name())

    def cmd_352(self, sender, forum, addl):
        # Response to WHO
        forum = irc.Channel(self, addl[0])
        who = irc.User(self, addl[4], addl[1], addl[2])
        self.add_luser(who, forum)

    def cmd_invite(self, sender, forum, addl):
        # Join any channel to which we're invited
        self.write('JOIN', forum.name())

    def cmd_pong(self, sender, forum, addl):
        now = time.time()
        self.lag = now - float(addl[0])

    def cmd_482(self, sender, forum, addl):
        forum = self.recipient(addl[0])
        self.whinecount += 1
        if (self.whinecount == 2 or
            self.whinecount == 4 or
            self.whinecount == 8):
            forum.notice("Just a reminder: I can't op anyone unless I'm opped myself.")
        elif (self.whinecount == 16):
            forum.notice("This is the last time I'm going to beg for ops.  Puh-leaze?")



if __name__ == '__main__':
    import daemon
    import sys

    debug = False
    if "-d" in sys.argv:
        debug = True

    if not debug:
        # Become a daemon
        log = file('arsenic.log', 'a')
        daemon.daemon('arsenic.pid', log, log)

    # Short URL server
    us = shorturl.start(('', 0))
    firebot.URLSERVER = (socket.gethostbyaddr(socket.gethostname())[0],
                         us.getsockname()[1])

    NICK = ['arsenic']
    INFO = "I'm a little printf, short and stdout"

    l1 = Arsenic(('irc.lanl.gov', 6667),
                 NICK,
                 INFO,
                 ["#x", "#csirt"],
                 ssl=False)
    l1.debug = debug

    irc.run_forever(0.01)
