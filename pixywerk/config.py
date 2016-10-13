import yaml
import logging

log = logging.getLogger('pixywerk.config')

def load_config_file(infile, defaults={}):
    """read JSON file and return dictionary.

Keyword arguments:
** infile - filename of input
** defaults - dictionary to prepopulate result dictionary with (file values
   overrides contents).
"""
    conf = dict(defaults)
    try:
        cfg = yaml.safe_load(infile)
        for k, v in cfg.items():
            conf[k] = v
    except:
        log.error('error loading {0}'.format(infile.name, ))
    return conf
