#! /usr/bin/env python

import urllib2
import shelve
import sys
import InfoBot

def main():
    db = shelve.DbfilenameShelf('info.db')
    count = 0
    for url in sys.argv[1:]:
        print url
        f = urllib2.urlopen(url)
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            try:
                key, val = line.split(' => ', 1)
            except ValueError:
                continue
            db[key] = (InfoBot.locked, val)
            count += 1
    print "Added %d facts." % count

if __name__ == '__main__':
    main()

