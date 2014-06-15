import types
import datetime

class Logger(object):
    def __init__(self, *args, **kwargs):
        self.ports = list()
        self.external_ports = list()
        for item in args:
            if type(item) in types.StringTypes:
                try:
                    p = file(item, 'a')
                    self.ports.append(p)
                except:
                    continue
            else:
                try:
                    item.write
                    self.external_ports.append(item)
                except AttributeErrror:
                    continue


    def __call__(self, caller, system, message, **var):
        output = datetime.datetime.now().isoformat() + " ["+system+"] "+message.format(**var)

        for p in self.ports+self.external_ports:
            p.write(output + "\n")


    def reopen(self):
        newports = list()
        for p in self.ports:
            f = p.name
            p.close()
            try:
                p = file(f,'a')
                newports.append(p)
            except:
                continue
        self.ports = newports
