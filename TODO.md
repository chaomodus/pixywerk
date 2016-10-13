TODO List
=========

* Docker template
* Authentication for trees.
* Allowing trees to be stored in a database would be nice.
* Support HUP with state reset.
* start-pixywerk:
  - Options for logging.
  - Options for gevent settings
  - Perhaps instead of using env var for config, pass config on command line (and generate from options) [curry do_werk with configs]

* State in wsgi.py is a mess. SHould be able to get a state blob and curry it with the application to make the fully-realized WSGI app.
  - Issue with this is that logger doesn't have encapsulatable state. We can cause it to rotate logs at least though on reset. Or just
    ignore the logging entirely (except that we can manipulate the setings from the config arggh)
