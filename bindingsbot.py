import irc
import re
import random
import types

class Match:
    """A wrapper around a regex match, to replace \008 with a word.

    """

    def __init__(self, m, txt):
        self.m = m
        self.txt = txt

    def group(self, grp):
        g = self.m.group(grp)
        if g:
            g = g.replace('\008', self.txt)
        return g


class BindingsBot(irc.Bot):
    """An IRC bot with regex function bindings

    You can bind functions to things said in the channel by regular
    expression with this.  See wouldmatch for an example of how to do
    this.
    """

    msg_cat = {}                        # message catalog
    bindings = []                       # function/catalog bindings to regexen

    def __init__(self, *gar):
        irc.Bot.__init__(self, *gar)
        self.last_tb = "Nothing's gone wrong yet!"

    def err(self, exception):
        """Save the traceback for later inspection"""
        irc.Bot.err(self, exception)
        t,v,tb = exception
        tbinfo = []
        while 1:
            tbinfo.append ((
                tb.tb_frame.f_code.co_filename,
                tb.tb_frame.f_code.co_name,
                str(tb.tb_lineno)
                ))
            tb = tb.tb_next
            if not tb:
                break
        # just to be safe
        del tb
        file, function, line = tbinfo[-1]
        info = '[' + '] ['.join(map(lambda x: '|'.join(x), tbinfo)) + ']'
        self.last_tb = '%s %s %s' % (t, v, info)
        print self.last_tb

    def matches(self, text):
        matches = []
        btext = text.replace(self.nick, '\008')
        for b in self.bindings:
            m = b[0].match(btext)
            if m:
                matches.append((m, b))
        return matches

    def cmd_privmsg(self, sender, forum, addl):
        for m, b in self.matches(addl[0]):
            f = b[1]
            if callable(f):
                cont = f(self, sender, forum, addl, Match(m, self.nick))
            elif type(f) == types.StringType:
                forum.msg(self.gettext(f, sender=sender.name(),
                                       forum=forum.name(), me=self.nick))
                cont = False
            else:
                raise ValueError("Can't handle type of %s", `f`)
            if not cont:
                break

    def gettext(self, msg, **dict):
        """Format a message from the message catalog.

        Retrieve from the message catalog the message specified by msg,
        filling in arguments as specified by dict.

        """

        m = random.choice(self.msg_cat[msg])
        return m % dict

    def tbinfo(self, sender, forum, addl, match):
        forum.msg(self.last_tb)
    bindings.append((re.compile(r"^\008[,: ]+(tbinfo|traceback)$"),
                     tbinfo))

    def wouldmatch(self, sender, forum, addl, match):
        """Show what binding would be matched"""

        text = match.group(1)
        matches = self.matches(text)
        m = [i[1][1] for i in matches]
        forum.msg('%s => %s' % (`text`, `m`))
    bindings.append((re.compile(r"^\008[,: ]+match (.+)$"),
                     wouldmatch))

    #
    # Message catalog
    #

    msg_cat['okay']    = ('Okay, %(sender)s.',)



