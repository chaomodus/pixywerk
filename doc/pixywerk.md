

I LOVE THE WAY YOU WERK IT


TO GET
======

Get source codes from gitorious:

  git clone https://github.com/chaomodus/pixywerk
  git clone https://github.com/chaomudos/ppcode (for bbcode support, optional)

Get these additional python packages:

  setuptools (package python-setuptools on debian derivatives, standard on most python installs)
  jinja2 (package python-jinja2 in debian derivatives)
  gevent (package python-gevent on debian derivatives) (self hossting / start-pixywerk)

  markdown (package python-markdown in debian derivatives) (for markdown support, optional)

Install source codes:

  cd pixywerk
  sudo python setup.py install
  cd ..
  cd ppcode
  sudo python setup.py install
  cd ..

You now have installed the base system for pixywerk.

TO RUN
======

Serve your first page~

PixyWerk requires a configuration file in JSON, an example of which is shipped with the source. Basically it is a dictionary with several options, minimally:

* *name* - the name of this pixywerk instance
* *root* - the full path to the filesystem tree this instance will serve from
* *template_paths* - this is a json list of template paths relative to the root path that are searched for templates (jinja has a template search/load system)

Additional configuration keys:

* *pathelement_blacklist* - a list of items if they appear as a full path element will prevent the tree from being further walked.

Basic Deployment Layout
--------------------------------------

Here's a suggested directory layout, although the only real constraint is that the template folder be beneath the root folder ( the configruation file can reside anywhere desired)

$deployment/
   config.json
   htdocs/
     templates/
       default.html
       default-fs.html
     index.html

Notes: $deployment is a placeholder for example purposes, in real life  it'd be something like /home/production;  in the configuration the *root* key is set to $deployment/htdocs; the default.html and default-fs.html are hardcoded template names-see the test/ folder in the source distribution for example default templates that you can start with. See the template section for more details as to their contents.

PixyWerk gets its configuration from the environment variable PIXYWERK_CONFIG.  Set this to the full path to the configuration JSON including the file name.

Running A Test Deployment
-----------------------------------------
