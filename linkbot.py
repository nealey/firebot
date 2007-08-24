#! /usr/bin/env python

import irc

NAME = ['arsenic']
INFO = "I'm a little teapot, short and stout"

class MultiChannel(irc.Channel):
    """Multiple-channel recipient

    The idea is that this object can represent multiple channels, so
    when it's told to do something, it will happen in more than one
    place.

    """

    def __init__(self, ifchans, name):
        self._ifchans = ifchans
        self._name = name

    def cmd(self, cmd, text):
        for iface, chans in self._ifchans:
            for chan in chans:
                iface.write([cmd, chan], text)


class LinkBot(irc.Bot):
    """Linkbot stuff.

    The strategy here is to relay messages to the
    others, then get the others to act as if they had just seen the
    message from their server.

    """

    def __init__(self, *data):
        self.others = []
        self.fora = None
        if data:
            irc.Bot.__init__(self, *data)

    def handle_cooked(self, op, sender, forum, addl):
        """The crux of the linkbot.

        By replacing forum with a multi-channel forum, forum-directed
        replies go to all channels.

        """

        if self.fora and forum and forum.is_channel():
            forum = MultiChannel(self.fora, forum.name())
        irc.Bot.handle_cooked(self, op, sender, forum, addl)

    def set_others(self, others):
        self.others = others
        self.fora = []
        for i in [self] + others:
            self.fora.append((i, i.channels))

    def broadcast(self, text):
        for i in self.others:
            i.announce(text)

    def cmd_privmsg(self, sender, forum, addl):
        if forum.is_channel():
            self.broadcast('<%s> %s' % (sender.name(), addl[0]))

    def cmd_cprivmsg(self, sender, forum, addl):
        if forum.is_channel():
            cmd = addl[0]
            text = ' '.join(addl[1:])
            if cmd == 'ACTION':
                self.broadcast('* %s %s' % (sender.name(), text))

    def cmd_nick(self, sender, forum, addl):
        self.broadcast(' *** %s is now known as %s' % (addl[0], sender.name()))

    def cmd_join(self, sender, forum, addl):
        self.broadcast(' *** %s has joined' % (sender.name()))

    def cmd_part(self, sender, forum, addl):
        self.broadcast(' *** %s has left' % (sender.name()))
    cmd_quit = cmd_part

if __name__ == '__main__':
    l1 = LinkBot(('209.67.60.33', 6667),
                 NAME,
                 INFO,
                 ['#disney'])
    l2 = LinkBot(('woozle.org', 6667),
                 NAME,
                 INFO,
                 ['#woozle'])
    l1.set_others([l2])
    l2.set_others([l1])
    irc.run_forever()
