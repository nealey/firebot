from firebot import FireBot
import irc
import re

class Gallium(FireBot):
    #debug = True
    bindings = []

    bindings.extend(FireBot.bindings)


NICK = ['gallium']
INFO = "I'm a little printf, short and stdout"
HOSTS = [('woozle.org', 6667),
         ('209.67.60.33', 6667)]

l1 = Gallium(("woozle.org", 6667),
             NICK,
             INFO,
             ["#test"])

irc.run_forever()
