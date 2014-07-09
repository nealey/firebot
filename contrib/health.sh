#! /bin/sh
## Restart the bot if it's not running

# You can specify which bot to run as a command line option;
# default gallium
bot=${1:-gallium}

cd $(dirname $0)

kill -0 $(cat $bot.pid) 2>/dev/null || ./$bot.py
