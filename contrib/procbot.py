#! /usr/bin/env python

import os
import irc
import async_proc

class Runner(async_proc.process_dispatcher):
    def __init__(self, cmdline, outfunc):
        f = os.popen('%s 2>&1' % (cmdline), 'r')
        self.outfunc = outfunc
        self.linebuf = ""
        async_proc.process_dispatcher.__init__(self, f)

    def handle_read(self):
        self.linebuf += self.recv(4098)

    def handle_close(self):
        ret = self.close()
        if self.linebuf:
            self.outfunc(self.linebuf, ret)


def esc(arg):
    "Shell-escape an argument"

    return "'" + arg.replace("'", "'\\''") + "'"


def lesc(args):
    "Shell-escape a list of arguments"

    return [esc(arg) for arg in args]


class ProcBot(irc.Bot):
    maxlines = 5

    def proc_cb(self, pfx, sender, forum, linebuf, ret):
        if not pfx:
            pfx = ""
        lines = []
        for line in linebuf.split('\n'):
            line = line.strip()
            if line:
                lines.append("%s%s" % (pfx, line))
        if ret and not lines:
            lines = ["%sThat generates an error (%d)." % (pfx, ret)]
        if len(lines) > self.maxlines:
            forum.msg("%sToo many lines, sending privately" % pfx)
            self.despool(sender, lines)
        else:
            self.despool(forum, lines)


if __name__ == '__main__':
    import bindingsbot
    import re

    class LsBot(ProcBot, bindingsbot.BindingsBot):
        bindings = bindingsbot.BindingsBot.bindings

        def ls(self, sender, forum, addl, match):
            r = Runner('ls', lambda linebuf, ret: self.proc_cb("ls: ",
                                                               sender, forum,
                                                               linebuf, ret))
        bindings.append((re.compile(r"^ls", re.IGNORECASE),
                         ls))


    p = LsBot(('irc.woozle.org', 6667),
              'procbot',
              'hi asl',
              ["#ch"])
    irc.run_forever()
