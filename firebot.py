#! /usr/bin/env python

import os
import sys
import re
import random
from webretriever import WebRetriever
import asynchat, asyncore
import socket
import csv
import adns
import time

import procbot
import shorturl
import infobot

Runner = procbot.Runner
esc = procbot.esc

URLSERVER = ("", 0)

class SSLSock:
    def __init__(self, sock):
        self.sock = sock
        self.sock.setblocking(1)
        self.ssl = socket.ssl(sock)

    def send(self, data):
        self.ssl.write(data)

    def recv(self, bufsize):
        return self.ssl.read(bufsize)

    def close(self):
        self.sock.close()

class FireBot(infobot.InfoBot, procbot.ProcBot):
    #debug = True

    bindings = []
    msg_cat = {}
    heartbeat_interval = 0.5
    ping_interval = 120

    def __init__(self, host, nicks, gecos, channels,
                 dbname='info.cdb', ssl=False, **kwargs):
        infobot.InfoBot.__init__(self, host, nicks, gecos, channels,
                                 dbname=dbname, **kwargs)
        self.ssl = ssl
        self.seen = {}

    def handle_connect(self):
        if self.ssl:
            self.plain_sock = self.socket
            self.socket = SSLSock(self.socket)
        infobot.InfoBot.handle_connect(self)

    def send_ping(self):
        # Send keepalives to the server to see if we've lost
        # connection.  For some reason, using SSL prevents us from
        # getting a RST.
        self.write('PING %f' % time.time())
        self.add_timer(self.ping_interval,
                       self.send_ping)

    def cmd_001(self, sender, forum, addl):
        infobot.InfoBot.cmd_001(self, sender, forum, addl)
        self.add_timer(self.ping_interval,
                       self.send_ping)


    def cmd_privmsg(self, sender, forum, addl):
        infobot.InfoBot.cmd_privmsg(self, sender, forum, addl)

        if forum.is_channel():
            who = sender.name()

            # Update seen
            text = addl[0]
            now = time.time()
            self.seen[who] = (now, text)

            # Deliver notes
            n = self.getall(who, special="note")
            if n:
                notes = ["Welcome back, %s.  You have %d notes:" % (who, len(n))]
                for note in n:
                    when, whom, what = note.split(':', 2)
                    try:
                        notes.append(u"%s: %s <%s> %s" % (who,
                                                          time.ctime(float(when)),
                                                          whom,
                                                          what))
                    except UnicodeDecodeError:
                        notes.append(u"%s" % ((who,
                                               time.ctime(note[0]),
                                               note[1],
                                               note[2]),))
                self.despool(forum, notes)
                self.delete(who, special="note")

    ##
    ## Firebot stuff
    ##

    def seen(self, sender, forum, addl, match):
        whom = match.group('whom')
        if whom == sender.name():
            forum.msg('Cute, %s.' % whom)
            return
        last = self.seen.get(whom)
        now = time.time()
        if last:
            when = now - last[0]
            units = 'seconds'
            if when > 120:
                when /= 60
                units = 'minutes'
                if when > 120:
                    when /= 60
                    units = 'hours'
                    if when > 48:
                        when /= 24
                        units = 'days'
            forum.msg('I last saw %s %d %s ago, saying "%s"' %
                      (whom, when, units, last[1]))
        else:
            forum.msg("I've never seen %s!" % (whom))
    bindings.append((re.compile(r"^seen +(?P<whom>.*)$"),
                     seen))

    def evalstr(self, sender, forum, addl, match):
        code = match.group('code')
        if code in (')', '-)'):
            return True
        try:
            ret = repr(eval(code, {"__builtins__": {}}, {}))
            if len(ret) > 400:
                ret = ret[:400] + '\026...\026'
        except:
            t, v, tb = sys.exc_info()
            forum.msg(self.gettext('eval', code=code, ret='\002%s\002: %s' % (t, v), sender=sender.name()))
        else:
            forum.msg(self.gettext('eval', code=code, ret=ret, sender=sender.name()))
    #bindings.append((re.compile(r"^\; *(?P<code>.+)$"), evalstr))
    #msg_cat['eval'] = ('%(code)s ==> %(ret)s',)

    shorturlnotice = True
    def shorturl(self, sender, forum, addl, match):
        url = match.group('url')
        print ('url', url)
        idx = shorturl.add(url)
        if self.shorturlnotice:
            f = forum.notice
        else:
            f = forum.msg
        return True
        f('http://%s:%d/%d' % (URLSERVER[0], URLSERVER[1], idx))
    bindings.append((re.compile(r".*\b(?P<url>\b[a-z]+://[-a-z0-9_=!?#$@~%&*+/:;.,\w]+[-a-z0-9_=#$@~%&*+/\w])"),
                     shorturl))

    def note(self, sender, forum, addl, match):
        whom = match.group('whom')
        what = match.group('what')
        when = time.time()
        note = "%f:%s:%s" % (when, sender.name(), what)
        n = self.getall(whom, special="note")
        n.append(note)
        self.set(whom, n, special="note")
        forum.msg(self.gettext('okay', sender=sender.name()))
    bindings.append((re.compile(r"^\008[:, ]+note (to )?(?P<whom>[^: ]+):? +(?P<what>.*)"),
                    note))
    bindings.append((re.compile(r"^\008[:, ]+later tell (?P<whom>[^: ]+):? +(?P<what>.*)"),
                    note))

    def cdecl(self, sender, forum, addl, match):
        jibberish = match.group('jibberish')
        o, i = os.popen2('/usr/bin/cdecl')
        o.write(jibberish + '\n')
        o.close()
        res = i.read().strip()
        if '\n' in res:
            forum.msg("Lots of output, sending in private message")
            self.despool(sender, res.split('\n'))
        else:
            forum.msg('cdecl | %s' % res)
    bindings.append((re.compile(r"^cdecl (?P<jibberish>.*)$"),
                     cdecl))

    def delayed_say(self, sender, forum, addl, match):
        delay = int(match.group('delay'))
        unit = match.group('unit')
        what = match.group('what')

        if not unit or unit[0] == 's':
            pass
        elif unit[0] == 'm':
            delay *= 60
        elif unit[0] == 'h':
            delay *= 3600
        elif unit[0] == 'd':
            delay *= 86400
        elif unit[0] == 'w':
            delay *= 604800
        else:
            forum.msg("I don't know what a %s is." % unit)
            return

        self.add_timer(delay, lambda : forum.msg(what))
        forum.msg(self.gettext('okay', sender=sender.name()))
    bindings.append((re.compile(r"^\008[:, ]+in (?P<delay>[0-9]+) ?(?P<unit>[a-z]*) say (?P<what>.*)"),
                     delayed_say))

    msg_cat['nodict'] = ("Sorry, boss, dict returns no lines for %(jibberish)s",)
    def dict(self, sender, forum, addl, match):
        jibberish = match.group('jibberish')
        i = os.popen('/usr/bin/dict %s 2>&1' % esc(jibberish))
        res = i.readlines()
        if not res:
            forum.msg(self.gettext('nodict', jibberish=jibberish))
            return
        res = [l.strip() for l in res]
        if match.group('long'):
            self.despool(sender, res)
        else:
            if len(res) <= 5:
                self.despool(forum, res)
            else:
                del res[:4]
                short = res[:]
                while short and ((not short[0]) or (short[0][0] not in '0123456789')):
                    del short[0]
                if not short:
                    short = res
                short = ['%s: %s' % (jibberish, r) for r in short[:4]]
                self.despool(forum, short + ['[truncated: use the --long option to see it all]'])
    bindings.append((re.compile(r"^dict (?P<long>--?l(ong)? +)?(?P<jibberish>.*)$"),
                     dict))

    def units(self, sender, forum, addl, match):
        f = match.group('from')
        t = match.group('to')
        if f.startswith('a '):
            f = '1 ' + f[2:]
        Runner('/usr/bin/units -v %s %s' % (esc(f), esc(t)),
               lambda l,r: self.proc_cb(None, sender, forum, l, r))
    bindings.append((re.compile(r"^(?P<from>.*) +-> +(?P<to>.*)$"),
                     units))
    bindings.append((re.compile(r"^how many (?P<to>.*) in (?P<from>[^?]*)[?.!]*$"),
                     units))

    def calc(self, sender, forum, addl, match):
	e = match.group('expr')
        Runner("echo %s | /usr/bin/bc -l" % procbot.esc(e),
               lambda l,r: self.proc_cb('%s = ' % e, sender, forum, l, r))
    bindings.append((re.compile(r"^(?P<expr>[0-9.]+\s*[-+*/^%]\s*[0-9.]+)$"),
                    calc))
    bindings.append((re.compile(r"^calc (?P<expr>.+)$"),
                    calc))

    def generic_cmd(self, sender, forum, addl, match):
        cmd = match.group('cmd')
        args = match.group('args').split(' ')
        args = procbot.lesc(args)
        argstr = ' '.join(args)
        Runner('%s %s' % (cmd, argstr),
               lambda l,r: self.proc_cb(None, sender, forum, l, r))
    bindings.append((re.compile(r"^(?P<cmd>host) (?P<args>.+)$"),
                     generic_cmd))
    bindings.append((re.compile(r"^(?P<cmd>whois) (?P<args>.+)$"),
                     generic_cmd))

    def pollen(self, sender, forum, addl, match):
        forecast_re = re.compile('fimages/std/(?P<count>[0-9]+\.[0-9])\.gif')
        predom_re = re.compile('Predominant pollen: (?P<pollens>[^<]*)')
        zip = match.group('zip')
        def cb(lines):
            forecast = []
            predom = ''
            for line in lines:
                match = forecast_re.search(line)
                if match:
                    forecast.append(match.group('count'))
                match = predom_re.search(line)
                if match:
                    predom = match.group('pollens')
            forum.msg('%s: 4-day forecast (out of 12.0): %s; predominant pollen: %s' %
                      (zip, ', '.join(forecast), predom))
        WebRetriever('http://www.pollen.com/forecast.asp?PostalCode=%s&Logon=Enter' % zip,
                     cb)
    bindings.append((re.compile('pollen (?P<zip>[0-9]{5})'),
                     pollen))

    def weather(self, sender, forum, addl, match):
        zip = match.group('zip')
        def cb(lines):
            print lines
            forum.msg('*HURR*')
        WebRetriever('http://www.srh.noaa.gov/zipcity.php?inputstring=%s' % zip,
                     cb)
    bindings.append((re.compile('weather (?P<zip>[0-9]{5})'),
                     weather))

    def quote(self, sender, forum, addl, match):
        def cb(lines):
            if not lines:
                forum.msg('oops, no data from server')
                return
            c = csv.reader([lines[0].strip()])
            vals = zip(('symbol', 'value', 'day', 'time', 'change',
                        'open', 'high', 'low', 'volume',
                        'market cap', 'previous close',
                        'percent change', 'open2', 'range',
                        'eps', 'pe_ratio', 'name'),
                       c.next())
            d = dict(vals)
            forum.msg(('%(name)s (%(symbol)s)'
                       '  last:%(value)s@%(time)s'
                       '  vol:%(volume)s'
                       '  cap:%(market cap)s'
                       '  prev-close:%(previous close)s'
                       '  chg:%(change)s(%(percent change)s)'
                       '  open:%(open)s'
                       '  1d:%(low)s - %(high)s'
                       '  52wk:%(range)s') %
                      d)

        symbol = match.group('symbol')
        WebRetriever('http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sl1d1t1c1ohgvj1pp2owern&e=.csv' % symbol,
                     cb)
    bindings.append((re.compile(r"^quote +(?P<symbol>[-^.a-zA-Z]+)$"),
                    quote))

    def currency(self, sender, forum, addl, match):
        amt = float(match.group('amt'))
        frm = match.group('from')
        to = match.group('to')

        def cb(lines):
            if not lines:
                forum.msg('oops, no data from server')
                return
            c = csv.reader([lines[0].strip()])
            vals = zip(('symbol', 'value', 'day', 'time', 'change',
                        'open', 'high', 'low', 'volume',
                        'market cap', 'previous close',
                        'percent change', 'open2', 'range',
                        'eps', 'pe_ratio', 'name'),
                       c.next())
            d = dict(vals)
            v = float(d['value'])
            ans = v * amt
            forum.msg(('%0.4f %s = %0.4f %s') %
                      (amt, frm, ans, to))

        WebRetriever(('http://download.finance.yahoo.com/d/quotes.csv?s=%s%s%%3DX&f=sl1d1t1c1ohgvj1pp2owern&e=.csv' %
                      (frm, to)),
                     cb)
    bindings.append((re.compile(r"^how much is (?P<amt>[0-9.]+) ?(?P<from>[A-Z]{3}) in (?P<to>[A-Z]{3})\??$"),
                    currency))

    def whuffie_mod(self, nick, amt):
        vs = self.get(nick, "0", special="whuffie")
	try:
	    val = int(vs)
	except:
	    val = 0
        val += amt
        self.set(nick, [str(val)], special="whuffie")

    def whuffie_modify(self, sender, forum, addl, match):
        nick = match.group('nick')
        if nick.lower() == sender.name().lower():
            forum.msg(self.gettext('whuffie whore', sender=sender.name()))
            return
        if match.group('mod') == '++':
            amt = 1
        else:
            amt = -1
        self.whuffie_mod(nick, amt)
    bindings.append((re.compile(r"^(?P<nick>[-\w]+)(?P<mod>\+\+|\-\-)[? ]*$"),
                     whuffie_modify))
    msg_cat['whuffie whore'] = ("Nothing happens.",
                                'A hollow voice says, "Fool."')

    def whuffie(self, sender, forum, addl, match):
        nick = match.group('nick')
        val = self.get(nick, special="whuffie")
        if val and val != "0":
            forum.msg("%s has whuffie of %s" % (nick, val))
        else:
            forum.msg("%s has neutral whuffie" % nick)
    bindings.append((re.compile(r"^(\008[,:] +)?([Ww]huffie|[Kk]arma) (for )?(?P<nick>\w+)[? ]*$"),
                     whuffie))

    #
    # This is all stuff that should just be stored in the usual manner.
    # But I wrote it here before I realized how programmable an Infobot
    # really is, so here it stays.
    #

    msg_cat['8ball']    = ("%(sender)s: Outlook good.",
                           "%(sender)s: Outlook not so good.",
                           "%(sender)s: My reply is no.",
                           "%(sender)s: Don't count on it.",
                           "%(sender)s: You may rely on it.",
                           "%(sender)s: Ask again later.",
                           "%(sender)s: Most likely.",
                           "%(sender)s: Cannot predict now.",
                           "%(sender)s: Yes.",
                           "%(sender)s: Yes, definitely.",
                           "%(sender)s: Better not tell you now.",
                           "%(sender)s: It is certain.",
                           "%(sender)s: Very doubtful.",
                           "%(sender)s: It is decidedly so.",
                           "%(sender)s: Concentrate and ask again.",
                           "%(sender)s: Signs point to yes.",
                           "%(sender)s: My sources say no.",
                           "%(sender)s: Without a doubt.",
                           "%(sender)s: Reply hazy, try again.",
                           "%(sender)s: As I see it, yes.")
    msg_cat['me']       = ('%(sender)s?',
                           '%(sender)s: Yes?',
                           'At your service, %(sender)s.',
                           'May I help you, %(sender)s?')
    msg_cat['thanks']   = ('It is my pleasure, %(sender)s.',
                           'Of course, %(sender)s.',
                           'I live but to serve, %(sender)s.',
                           "All in a day's work, %(sender)s.")
    bindings.append((re.compile(r"^(magic )?(8|eight ?)-?ball", re.IGNORECASE),
                     '8ball'))
    bindings.append((re.compile(r"^\008\?$", re.IGNORECASE),
                     'me'))
    bindings.append((re.compile(r"^thank(s| you),? *\008", re.IGNORECASE),
                     'thanks'))

    msg_cat.update(infobot.InfoBot.msg_cat)
    bindings.extend(infobot.InfoBot.bindings)


if __name__ == "__main__":
    import irc

    # Short URL server
    us = shorturl.start(('', 0))
    URLSERVER = (socket.gethostbyaddr(socket.gethostname())[0],
                 us.getsockname()[1])


    NICK = ['hal']
    INFO = 'Daisy, Daisy...'

    l1 = FireBot(("server1", 6667),
                 NICK,
                 INFO,
                 ["#ch1", "#ch2"])
    l2 = FireBot(('server2', 6667),
                 NICK,
                 INFO,
                 ["#ch3"])
    l1.set_others([l2])
    l2.set_others([l1])

    irc.run_forever(0.5)
