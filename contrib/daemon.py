#! /usr/bin/env python

import os
import sys

def daemon(pidfile=None, stdout=None, stderr=None):
    # Do this first so errors print out right away
    if pidfile:
        f = file(pidfile, 'w')
    else:
        f = None

    pid = os.fork()
    if pid:
        # Exit first parent
        os._exit(0)

    # Decouple from parent
    os.setsid()

    # Second fork
    pid = os.fork()
    if pid:
        # Exit second parent
        os._exit(0)

    # Remap std files
    os.close(0)
    if stdout:
        sys.stdout = stdout
        os.close(1)
    if stderr:
        sys.stderr = stderr
        os.close(2)

    # Write pid
    if f:
        f.write(str(os.getpid()))
        f.close()

