from spack import *


class PyPsycopg2(Package):
    """The PyPA recommended tool for installing Python packages."""

    homepage = "https://pypi.python.org/pip"
    url = "https://pypi.python.org/pip"
    
    version('2.6.2', pip='psycopg2', version='2.6.2')
    version('2.6.1', pip='psycopg2', version='2.6.1')

    extends('python')
    depends_on('py-pip')

    def install(self, spec, prefix):
        pip('install', *std_pip_args)
