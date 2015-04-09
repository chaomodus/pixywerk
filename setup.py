from setuptools import setup

setup(name='pixywerk',
      version='alpha8',
      description='A simple filesystem based WSGI CMS',
      url='https://github.com/chaomodus/pixywerk/',
      author='Cas Rusnov',
      author_email='rusnovn@gmail.com',
      license='MIT',
      packages=['pixywerk'],
      scripts=['start-pixywerk'],
      zip_safe=True)
