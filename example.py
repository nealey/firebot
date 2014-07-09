#! /usr/bin/env python

import irc

SERVER = ('irc.synirc.net', 6667)
NAMES = ['idiot15']
INFO = "Example bot"
CHANNELS = ["#idiotbot"]

class IdiotBot(irc.Bot):
    debug = True

    # Every time anybody says anything, respond like an idiot.
    def cmd_privmsg(self, sender, forum, addl):
        forum.msg("I am an idiot!")

l2 = IdiotBot(SERVER, NAMES, INFO, CHANNELS)

irc.run_forever()
