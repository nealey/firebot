#! /usr/bin/env python

"""OpBot -- Hands out channel ops

This bot joins every channel on the server, and if opped in a channel
will op anyone who joins.  It will poll the server for a channel list
and join any new channels as they appear.  Once it has joined, it never
leaves a channel.

"""

import irc

class NopBot(irc.Bot):
    #debug = True
    heartbeat_interval = 60

    def cmd_001(self, sender, forum, addl):
        irc.Bot.cmd_001(self, sender, forum, addl)
        self.write(['LIST'])

    def cmd_322(self, sender, forum, addl):
        self.write(['JOIN', addl[0]])

    def cmd_join(self, sender, forum, addl):
        if sender.name() == self.nick:
            forum.notice('If you op me, I will op everyone who joins this channel.')
        forum.write(['MODE', forum.name(), '+o'], sender.name())

    def heartbeat(self):
        irc.Bot.heartbeat(self)
        self.write(['LIST'])

n = NopBot(('woozle.org', 6667),
           ['OpBot'],
           'Op me!',
           [])
irc.run_forever()
