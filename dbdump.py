#! /usr/bin/env python
import anydbm

d = anydbm.open('info.db')
n = anydbm.open('new.db', 'c')

for k,v in d.iteritems():
    n[k] = v

