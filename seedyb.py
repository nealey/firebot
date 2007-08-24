#! /usr/bin/env python

import cdb
import random
import codecs

_encode = codecs.getencoder('utf-8')
(_encode, _decode, _, _) = codecs.lookup('utf-8')
def encode(str):
    return _encode(str)[0]

def decode(str):
    return _decode(str)[0]

class Locked(Exception):
    pass

class SeedyB:
    """firebot-specific database using cdb.

    Why CDB?  Because everything else keeps going corrupt.

    Notes:
    *   This doesn't preserve unsynced additions.  If you crash before
        running sync(), you lose.
    *   If you set a value to [], is is effectively deleted.
    *   You can lock something that's not in the database.  You might
        want to do this for words like 'that', so the bot doesn't pick
        up on them.
    """

    def __init__(self, filename):
        self.filename = filename
        self.tempfile = "%s.tmp" % filename

        self.db = {}
        try:
            self.cdb = cdb.init(self.filename)
        except cdb.error:
            d = cdb.cdbmake(self.filename, self.tempfile)
            d.finish()
            del d
            self.cdb = cdb.init(self.filename)

    def __del__(self):
        self.sync(force=True)

    def __len__(self):
        return len(self.cdb) + len(self.db)

    def __delitem__(self, key):
        self.delete(key)

    def __getitem__(self, key):
        val = self.get(key)
	if val is None:
	    raise KeyError(key)

    def __contains__(self, key):
        return (key in self.db) or (key in self.cdb)

    def length(self):
        return (len(self.cdb), len(self.db))

    def sync(self, force=False):
        if not self.db:
            return

        tmp = cdb.cdbmake(self.filename, self.tempfile)

        # Copy original
        r = self.cdb.each()
        while r:
            k,v = r
            dk = decode(k)
            if k not in self.db:
                tmp.add(*r)
            r = self.cdb.each()

        # Add new stuff
        for k,l in self.db.iteritems():
            for v in l:
                try:
                    tmp.add(k,v)
                except:
                    print (k,v)
                    raise

        tmp.finish()
        self.cdb = cdb.init(self.filename)
        self.db = {}

    def getall(self, key, special=None):
        """Return all values for a key"""

        if special:
            key = '\016%s:%s\017' % (special, key)
        ekey = encode(key)
        vals = self.db.get(ekey, None)
        if vals is None:
            vals = self.cdb.getall(ekey)
        return [decode(v) for v in vals]

    def get(self, key, default=None, special=None):
        """Get a value at random"""

        vals = self.getall(key, special)
        if vals:
            return random.choice(vals)
        else:
            return default

    def set(self, key, val, special=None):
        if special:
            key = '\016%s:%s\017' % (special, key)
        ekey = encode(key)
	if type(val) not in (type([]), type(())):
	    val = [val]
        if not special and self.is_locked(key):
            raise Locked()
        self.db[ekey] = [encode(v) for v in val]

    def delete(self, key, special=None):
	val = self.get(key, special=special)
	if not val:
	    raise KeyError(key)
        self.set(key, [], special)

    ##
    ## Locking
    ##

    def lock(self, key):
        self.set(key, [''], special='lock')

    def unlock(self, key):
        self.set(key, [], special='lock')

    def is_locked(self, key):
        l = self.get(key, special='lock')
        if l:
            return True
        return False


open = SeedyB
