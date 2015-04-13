"""a very simplistic wrapper for loading JSON files while also providing
defaults."""

import yaml
import logging

log = logging.getLogger('pixywerk.simpleconfig')


def load_config(infile, defaults={}):
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
