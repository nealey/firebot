#! /usr/bin/env python

import seedyb
import shelve
import cPickle as pickle
import codecs

def main():
    a = shelve.open('new.db')
    d = seedyb.open('info.cdb')

    dec = codecs.getdecoder('utf-8')
    enc = codecs.getencoder('utf-8')

    for k,l in a.iteritems():
        try:
            tl = type(l)
            if tl == type(13) and k[0] == '\x0b':
                # Whuffie
                k = k[1:]
                d.set(k, str(l), special='whuffie')
            elif tl == type(()):
                locked = False
		try:
		    k = dec(k)[0]
		except UnicodeDecodeError:
		    continue
                # Factoid
                if l and l[0] == ('locked',):
                    locked = True
                    l = l[1:]
                try:
                    d.set(k, l)
                except UnicodeDecodeError:
                    continue
                if locked:
                    d.lock(k)
        except:
            print (k, l)
            raise

    d.sync()

main()
