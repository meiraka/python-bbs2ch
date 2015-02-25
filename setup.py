#!/usr/bin/python
from setuptools import setup
import bbs2ch.version

setup_args = {}
setup_args['packages'] = ['bbs2ch']

if __name__ == '__main__':
    setup(name='bbs2ch'
         ,version=bbs2ch.version.__version__
         ,author='mei raka'
         ,**setup_args)

