#!/usr/bin/python
from setuptools import setup
import src.version as version

setup_args = {}
setup_args['packages'] = ['bbs2ch']
setup_args['package_dir'] = {'bbs2ch':'src'}

if __name__ == '__main__':
    setup(name='bbs2ch'
         ,version=version.__version__
         ,author='mei raka'
         ,**setup_args)

