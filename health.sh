#! /bin/sh
## Restart the bot if it's not running

# Gallium assumes everything's in the cwd
cd $(basename $0)

kill -0 $(cat gallium.pid) 2>/dev/null || ./gallium.py
