#! /usr/bin/env python
import os
import string

class error(Exception):
    pass

def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
    mychr = chr
    myatoi = int
    list = s.split('%')
    res = [list[0]]
    myappend = res.append
    del list[0]
    for item in list:
        if item[1:2]:
            try:
                myappend(mychr(myatoi(item[:2], 16))
                     + item[2:])
            except ValueError:
                myappend('%' + item)
        else:
            myappend('%' + item)
    return "".join(res)

def quote(s, safe):
    """quote('abc def') -> 'abc%20def'."""
    res = list(s)
    for i in range(len(res)):
        c = res[i]
        if c not in safe:
            res[i] = '%%%02X' % ord(c)
    return ''.join(res)

class FileDBM:
    """File Database class.

    This stores strings as files in a directory.

    Note, no locking is done.  It would be wise to make sure there is
    only one writer at any given time.

    """

    safe = string.letters + string.digits + ',!@#$^()-_+='

    def __init__(self, base, mode='r'):
        self.base = os.path.abspath(base)
        if mode in ('r', 'w'):
            if not os.path.isdir(base):
                raise error("need 'c' or 'n' flag to open new db")
            if mode == 'r':
                self.writable = True
            else:
                self.writable = False
        elif mode == 'c':
            if not os.path.isdir(base):
                os.mkdir(base)
            self.writable = True
        elif mode == 'n':
            if os.path.isdir(base):
                os.removedirs(base)
            os.mkdir(base)
            self.writable = True
        else:
            raise error("flags should be one of 'r', 'w', 'c', or 'n'")

    def key2path(self, key):
        """Transform key to a pathname.

        By default this does URL quoting on safe characters.
        Be sure to provide a path2key method if you override this.

        """

        return os.path.join(self.base,
                            quote(key, self.safe))

    def path2key(self, path):
        """Transform a pathname to a key."""

        if not path.startswith(self.base):
            raise error("Not a valid path")
        key = path[len(self.base) + 1:] # +1 gets the /
        if os.path.sep in key:
            raise error("Not a valid path")
        return unquote(key)

    def __len__(self):
        count = 0
        for i in self.iterkeys():
            count += 1
        return count

    def __getitem__(self, key):
        if not (type(key) == type('')):
            raise TypeError("keys must be strings")
        path = self.key2path(key)
        try:
            return file(path).read()
        except IOError:
            raise KeyError

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key, val):
        if not (type(key) == type(val) == type('')):
            raise TypeError("keys and values must be strings")
        path = self.key2path(key)
        file(path, 'w').write(val)

    def setdefault(self, key, default):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def __delitem__(self, key):
        path = self.key2path(key)
        try:
            os.remove(path)
        except OSError:
            raise KeyError()

    def __contains__(self, value):
        # This could be a lot slower than the user would expect.  If you
        # need it, use has_value.  Of course, you could make a derived
        # class that sets __contains__ = has_value
        raise error("You didn't really want to do this.")

    def has_key(self, key):
        return os.path.exists(self.key2path(key))

    def has_value(self, value):
        for val in self.itervalues():
            if val == value:
                return True
        return False

    def iterkeys(self):
        for root, dirs, files in os.walk(self.base):
            for f in files:
                path = os.path.join(root, f)
                try:
                    yield self.path2key(path)
                except error:
                    pass

    def __iter__(self):
        return self.iterkeys()

    def itervalues(self):
        for key, val in self.itervalues():
            yield val

    def iteritems(self):
        for k in self.iterkeys():
            yield (k, self[k])

    def keys(self):
        keys = []
        for k in self.iterkeys():
            keys.append(k)
        return keys

    def items(self):
        items = []
        for i in self.iteritems():
            items.append(i)
        return items

    def values(self):
        values = []
        for v in self.itervalues():
            values.append(v)
        return values



class LongFileDBM(FileDBM):
    """A file database supporting any-length keys.

    It does this by splitting keys up into directories.

    """

    # A special string to append to directories, so that no file will
    # ever have the same path as a directory
    dirsuffix = '%%'

    # In the worst case, quote makes the string 3x bigger.
    # So any key longer than 80 characters gets split up.  This
    # gives us plenty of room with a 255-character filename limit,
    # which seems to be the minimum limit on any OS these days.
    dirlen = 80

    def split(self, key):
        """Split a key into its path components.

        Each component in the list returned will be a directory.  Called
        before quoting parts.

        This is probably what you want to override.  You may need to do
        join() too.

        """

        parts = []
        while key:
            parts.append(key[:self.dirlen])
            key = key[self.dirlen:]
        return parts

    def join(self, parts):
        """Join directory parts into a single string.

        This is called after unquoting parts.

        """
        return ''.join(parts)

    def key2path(self, key, makedirs=False):
        parts = self.split(key)
        path = self.base

        for part in parts[:-1]:
            # Escape the part
            d = quote(part, self.safe)

            # Append a safe string so no shorter key can have this
            # path
            d = d + self.dirsuffix

            # Stick it on the end
            path = os.path.join(path, d)

            # Make directory if requested
            if makedirs and not os.path.isdir(path):
                os.mkdir(path)

        # Now we can add the filename
        path = os.path.join(path, quote(parts[-1], self.safe))

        return path

    def path2key(self, path):
        """Transform a pathname to a key."""

        if not path.startswith(self.base):
            raise error("Not a valid path")
        key = ""
        parts = path[len(self.base) + 1:].split(os.path.sep)
        parts_ = []
        for p in parts:
            # Strip the special string
            if p.endswith(self.dirsuffix):
                p = p[:-len(self.dirsuffix)]
            parts_.append(unquote(p))

        key = self.join(parts_)
        return key

    def __setitem__(self, key, val):
        if not self.writable:
            raise IOError('database was not opened writable')
        if not (type(key) == type(val) == type('')):
            raise TypeError("keys and values must be strings")
        path = self.key2path(key, True)
        file(path, 'w').write(val)

    def __delitem__(self, key):
        path = self.key2path(key)
        try:
            os.remove(path)
        except OSError:
            raise KeyError()

        # Now try to clean up any directories
        while True:
            path = os.path.dirname(path)
            if len(path) <= len(self.base):
                break
            try:
                os.rmdir(path)
            except OSError:
                # Guess it's not empty
                break

    def iterkeys(self):
        for root, dirs, files in os.walk(self.base):
            for f in files:
                path = os.path.join(root, f)
                try:
                    yield self.path2key(path)
                except error:
                    pass

class WordFileDBM(LongFileDBM):
    """A layout using the first word as the top-level directory.

    I use this in my firebot, but it's included here more as an example
    of how you could extend LongFileDBM.

    """

    # I like having spaces in my filenames
    safe = LongFileDBM.safe + ' '

    def split(self, key):
        # Three cases:
        #
        # 1. no_spaces,_short
        # 2. one/one or more spaces
        # 3. _long/really_really_really_really_..._long
        #
        # This means that keys beginning with "_long " will be filed
        # with long keys.
        #
        # In any case, the first directory, if any, can be stripped
        # completely.

        split = LongFileDBM.split(self, key)

        # Split up into words
        parts = key.split(' ', 1)
        if len(parts) == 1 and len(split) == 1:
            # No spaces
            return split
        elif len(parts[0]) <= self.dirlen:
            # >= 2 words, first word <= dirlen chars
            return [parts[0]] + split
        else:
            return ['_long'] + split

    def join(self, parts):
        # Two cases:
        #
        # ["one_part"]
        # ["more", "more than one part"]

        if len(parts) == 1:
            return parts[0]
        else:
            return LongFileDBM.join(self, parts[1:])

open = LongFileDBM

if __name__ == '__main__':
    def asserteq(a, b):
        assert a == b, "%s != %s" % (`a`, `b`)

    f = LongFileDBM('/tmp/db', 'n')
    asserteq(f.key2path('this is a thing'), '/tmp/db/this%20is%20a%20thing')
    asserteq(f.key2path('1234567890' * 8), '/tmp/db/12345678901234567890123456789012345678901234567890123456789012345678901234567890')
    asserteq(f.key2path('1234567890' * 20), '/tmp/db/12345678901234567890123456789012345678901234567890123456789012345678901234567890%%/12345678901234567890123456789012345678901234567890123456789012345678901234567890%%/1234567890123456789012345678901234567890')

    f = WordFileDBM('/tmp/db', 'n')
    asserteq(f.path2key(f.key2path('this is a thing')), 'this is a thing')
    asserteq(f.path2key(f.key2path('1234567890' * 8)), '1234567890' * 8)
    asserteq(f.path2key(f.key2path('1234567890' * 20)), '1234567890' * 20)

    asserteq(f.get('grape'), None)
    asserteq(f.setdefault('grape', 'red'), 'red')
    asserteq(f.get('grape'), 'red')
    asserteq(f.setdefault('grape', 'green'), 'red')

    longstr = '1234567890' * 10
    f[longstr] = '1'
    asserteq(f[longstr], '1')

    asserteq(f.keys(), ['grape', longstr])

    del f['grape']
    del f[longstr]
    asserteq(f.keys(), [])
