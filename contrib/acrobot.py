#! /usr/bin/env python

import irc
import random

SERVER = ('woozle.org', 6667)
NAMES = ['acrobot']
INFO = "Acrophobia!"
CHANNELS = ["#acro"]

LETTERS = (
    'A' * 176 +
    'B' * 167 +
    'C' * 251 +
    'D' * 136 +
    'E' * 104 +
    'F' * 101 +
    'G' * 91 +
    'H' * 107 +
    'I' * 105 +
    'J' * 30 +
    'K' * 30 +
    'L' * 89 +
    'M' * 146 +
    'N' * 53 +
    'O' * 50 +
    'P' * 195 +
    'Q' * 13 +
    'R' * 103 +
    'S' * 273 +
    'T' * 132 +
    'U' * 20 +
    'V' * 41 +
    'W' * 71 +
    'X' * 1 +
    'Y' * 11 +
    'Z' * 6)

class AcroBot(irc.Bot):
    def cmd_privmsg(self, sender, forum, addl):
        if forum.name() in self.channels:
            return
        self.command(sender, addl)

    def command(self, sender, addl):
        print (sender, addl)

    def _make_acro(self, min, max):
        letters = []
        for i in range(random.randint(min, max)):
            letters.append(random.choice(LETTERS))
        return letters

    def cmd_join(self, sender, forum, addl):
        self.debug = True
        if sender.name() in self.nicks:
            self.heartbeat()

    def heartbeat(self):
        if True:
            acro = ''.join(self._make_acro(3, 8))
            self.announce(acro)

l2 = AcroBot(SERVER, NAMES, INFO, CHANNELS)

irc.run_forever()
