# Change Log
All notable changes to this project will be documented in this file.

## 0.0a6 - chaomodus
### Changed

* WSGI is an object now. It is up to the WSGI host to initialize the object first to bake in the config, the object then is a callable that complies with
  PEP 3333

* Renamed simpleconfig to config.
