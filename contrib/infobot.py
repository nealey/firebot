from bindingsbot import BindingsBot
import re
import irc
import seedyb
import time

class InfoBot(BindingsBot):
    """A cheap knock-off of the famous InfoBot.

    """

    msg_cat = {}
    msg_cat.update(BindingsBot.msg_cat)
    bindings = []
    chatty = True

    def __init__(self, host, nicks, gecos, channels, dbname='info.cdb'):
        BindingsBot.__init__(self, host, nicks, gecos, channels)
        self._db = seedyb.open(dbname)
        self.seen = {}
        self.ignore_case = True

    def sync(self):
        now = time.time()
        self._db.sync()

    def close(self):
        self.sync()
        BindingsBot.close(self)

    def cmd_ping(self, sender, forum, addl):
        BindingsBot.cmd_ping(self, sender, forum, addl)
        self.sync()


    msg_cat['unknown'] = ("I don't know anything about %(key)s, %(sender)s.",)
    msg_cat['stats']   = ("I know about %(things)s things.",)
    msg_cat['is']      = ("Rumor has it that %(key)s is %(val)s",
                          "I believe %(key)s is %(val)s",
                          "My sources tell me %(key)s is %(val)s",
                          'Gosh, %(sender)s, I think %(key)s is %(val)s',
                          "%(key)s is %(val)s")
    msg_cat['_is_']    = ("%(key)s is %(val)s",)
    msg_cat['dunno']   = ("Search me, %(sender)s.",
                          "I have no earthly idea, %(sender)s.",
                          "I wish I knew, %(sender)s.")
    msg_cat['same']    = ('I already had it that way, %(sender)s.',
                          "That's what I have for %(key)s too, %(sender)s.")
    msg_cat['but']     = ('...but %(key)s is %(old)s',)
    msg_cat['locked']  = ('Sorry, %(sender)s, %(key)s is locked.',)
    msg_cat['tell']    = ('%(sender)s wants you to know: %(string)s',)
    msg_cat['synced']  = ('Synchronized in %(time)f seconds.',)
    msg_cat['quiet']   = ("Fine, %(sender)s, I'll shut up.",)
    msg_cat['chatty']  = ("Thanks, %(sender)s, I've been chomping at the bit.",)


    def do_sync(self, sender, forum, addl, match):
        now = time.time()
        self.sync()
        forum.msg(self.gettext('synced',
                               sender=sender.name(),
                               time=(time.time() - now)))
    bindings.append((re.compile(r"^\008[,: ]+(sync|synchronize|flush)$"),
                     do_sync))

    def encode_key(self, key):
        if self.ignore_case:
            key = key.lower()
        return key

    def get(self, key, *args, **kwargs):
        return self._db.get(self.encode_key(key), *args, **kwargs)

    def getall(self, key, **kwargs):
        return self._db.getall(self.encode_key(key), **kwargs)

    def set(self, key, val, **kwargs):
        return self._db.set(self.encode_key(key), val, **kwargs)

    def delete(self, key, **kwargs):
        self._db.delete(self.encode_key(key), **kwargs)

    def lock(self, key):
        return self._db.lock(self.encode_key(key))

    def unlock(self, key):
        return self._db.unlock(self.encode_key(key))

    def stats(self, sender, forum, addl, match):
        forum.msg(self.gettext('stats', things=len(self._db)))
    bindings.append((re.compile(r"^\008[,: ]+statu?s$"),
                     stats))


    # Delete part of an entry
    def forget_from(self, sender, forum, key, substr):
        val = self.getall(key)
        if not val:
            raise KeyError()

        possibilities = []
        newval = []
        for i in val:
            if substr in i:
                possibilities.append(i)
            else:
                newval.append(i)

        if len(possibilities) == 1:
            try:
                self.set(key, tuple(newval))
            except seedyb.Locked:
                forum.msg(self.gettext('locked', key=key,
                                       sender=sender.name()))
                return
            forum.msg(self.gettext('forgot',
                                   key=key,
                                   val=possibilities[0],
                                   sender=sender.name()))
        elif len(possibilities) == 0:
            forum.msg(self.gettext('not in',
                                   key=key,
                                   substr=substr,
                                   sender=sender.name()))
        else:
            forum.msg(self.gettext('ambiguous forget',
                                   key=key,
                                   substr=substr,
                                   num=len(possibilities),
                                   sender=sender.name()))
    msg_cat['not in']    = ("I don't see any entries for %(key)s containing %(substr)s, %(sender)s",)
    msg_cat['ambiguous forget'] = ("There are %(num)d matches for %(substr)s in %(key)s.  Try a more specific substring!",)
    msg_cat['forgot'] = ('Okay, %(sender)s, I forgot \"%(val)s\" from \"%(key)s\".',)

    # Delete an entry
    def forget(self, sender, forum, addl, match):
        key = match.group('key')
        ekey = self.encode_key(key)
        try:
            self.delete(ekey)
            forum.msg(self.gettext('okay', key=key, sender=sender.name()))
        except KeyError:
            if ' from ' in key:
                substr, k = key.split(' from ', 1)
                try:
                    return self.forget_from(sender, forum, k, substr)
                except KeyError:
                    pass
            forum.msg(self.gettext('unknown', key=key, sender=sender.name()))
        except seedyb.Locked:
            forum.msg(self.gettext('locked', key=key,
                                   sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+forget (?P<key>.+)$", re.IGNORECASE),
                     forget))

    # Lock an entry
    def lock_entry(self, sender, forum, addl, match):
        key = match.group('key')
        self.lock(key)
        forum.msg(self.gettext('okay', key=key, sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+lock (?P<key>.+)$", re.IGNORECASE),
                     lock_entry))

    # Unlock an entry
    def unlock_entry(self, sender, forum, addl, match):
        key = match.group('key')
        self.unlock(key)
        forum.msg(self.gettext('okay', key=key, sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+unlock (?P<key>.+)$", re.IGNORECASE),
                     unlock_entry))

    def obliterate(self, sender, forum, addl, match):
        key = match.group('key')
        try:
            self.delete(key)
        except KeyError:
            pass
        self.lock(key)
        forum.msg(self.gettext('okay', key=key, sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+obliterate (?P<key>.+)$", re.IGNORECASE),
                     obliterate))

    # Literal entry
    def literal(self, sender, forum, addl, match):
        key = match.group('key')
        val = self.getall(key)
        if val:
            sv = `val`
            out = []
            while len(sv) > 300:
                s = sv[:300]
                sv = sv[300:]
                out.append('db[%r] == %s ...' % (key, s))
            out.append('db[%r] == %s' % (key, sv))
            self.despool(forum, out)
        else:
            forum.msg(self.gettext('unknown', key=key, sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+literal (?P<key>.+)$", re.IGNORECASE),
                     literal))

    # Look something up in the DB
    def lookup(self, sender, forum, addl, match):
        if not self.chatty:
            if not match.group('me'):
                return True
        key = match.group('key')

        # Try looking it up verbatim
        val = self.get(key)
        if not val:
            # Try the cleaned version
            key = key.rstrip('.?! ')
            val = self.get(key)
        if val:
            val = val % {'me': self.nick,
                         'forum': forum.name(),
                         'sender': sender.name()}
            if len(val) > 300:
                val = val[:297] + '...'
            if val[0] == '\\':
                forum.msg(val[1:])
            elif val[0] == ':':
                forum.act(val[1:])
            else:
                forum.msg(self.gettext('is', key=key, val=val, sender=sender.name()))
        elif match.group('me'):
            forum.msg(self.gettext('dunno', key=key, sender=sender.name()))
        elif match.group('question'):
            # Don't allow storage of things like 'what is that?'
            pass
        else:
            return True

    def do_store(self, sender, forum, key, val, me, no, also):
        resp = False
        old = self.getall(key)
        okay = self.gettext('okay', sender=sender.name())
        try:
            if old:
                if val in old:
                    if me:
                        resp = self.gettext('same', key=key, val=val, old=old,
                                            sender=sender.name())
                    else:
                        # Ignore duplicates
                        resp = self.gettext('same', key=key, val=val, old=old,
                                            sender=sender.name())
                        pass
                elif me:
                    if also:
                        self.set(key, old + [val])
                        resp = okay
                    elif no:
                        self.set(key, [val])
                        resp = okay
                    else:
                        if len(old) == 1:
                            old = old[0]
                        resp = self.gettext('but', key=key, val=val, old=old,
                                            sender=sender.name())
                else:
                    self.set(key, old + [val])
                    resp = okay
            else:
                self.set(key, (val,))
                resp = okay
        except seedyb.Locked:
            resp = self.gettext('locked', key=key,
                                sender=sender.name())

        if resp:
            if me:
                forum.msg(resp)
            return False
        return True

    # Write a new value to the DB
    def store(self, sender, forum, addl, match):
        key = match.group('key')
        val = match.group('val')
        # Change % to %%, except for %(
        val = val.replace('%', '%%')
        val = val.replace('%(', '(')
        me = match.group('me')
        no = match.group('no') and me
        also = val.startswith('also ')
        if also:
            val = val[5:]
        return self.do_store(sender, forum, key, val, me, no, also)

    def append_cmd(self, sender, forum, addl, match):
        key = match.group('key')
        val = match.group('val')
        return self.do_store(sender, forum, key, val, me=True, no=True, also=True)

    def chatty_on(self, sender, forum, addl, match):
        self.chatty = True
        forum.msg(self.gettext('chatty', sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+ be chatty", re.IGNORECASE),
                     chatty_on))

    def chatty_off(self, sender, forum, addl, match):
        self.chatty = False
        forum.msg(self.gettext('quiet', sender=sender.name()))
    bindings.append((re.compile(r"^\008[,: ]+ shut up", re.IGNORECASE),
                     chatty_off))


    # Pull in BindingsBot things
    bindings.extend(BindingsBot.bindings)

    # This is first to prevent storing "firebot: what is foo?"
    bindings.append((re.compile(r"^(?P<me>\008[,: ]+)?(?P<question>(what|who|where|wtf).*('s|'re| is| are) )(?P<key>.+)$",
                                re.IGNORECASE),
                     lookup))
    bindings.append((re.compile(r"^(?P<me>\008[,: ]+)append (?P<key>.+) <= (?P<val>.+)",
                                re.IGNORECASE),
                     append_cmd))
    bindings.append((re.compile((r"^(?P<me>\008)[,: ]+(?P<no>no, *)"
                                 r"(?P<key>.+?) (is|are) (?P<val>.+)$"),
                                re.IGNORECASE),
                     store))
    bindings.append((re.compile((r"^(?P<no>no,? *)?(?P<me>\008)[,: ]+"
                                 r"(?P<key>.+?) (is|are) (?P<val>.+)$"),
                                re.IGNORECASE),
                     store))
    bindings.append((re.compile(r"^([^:, ]+[:,] *)?(?P<no>)(?P<me>)(?P<key>.+) (is|are) (?P<val>.+)$",
                                re.IGNORECASE),
                     store))
    bindings.append((re.compile(r"^(?P<me>\008[,: ]+)?(?P<question>)(?P<key>.+)$",
                                re.IGNORECASE),
                     lookup))



