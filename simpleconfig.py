import yaml

def load_config(infile, defaults={}):
    conf = dict(defaults)
    try:
        cfg = yaml.safe_load(infile)
        for k,v in cfg.items():
            conf[k] = v
    except: pass

    return conf

