import yaml
import logging

log = logging.getLogger('pixywerk.simpleconfig')

def load_config(infile, defaults={}):
    conf = dict(defaults)
    try:
        cfg = yaml.safe_load(infile)
        for k,v in cfg.items():
            conf[k] = v
    except: log.error('error loading {0}'.format(infile.name,))
    return conf
