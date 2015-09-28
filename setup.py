from __future__ import print_function
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import io
import codecs
import os
import sys

import dustmaker

here = os.path.abspath(os.path.dirname(__file__))

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

long_description = read('README.md')

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)

setup(
    name='dustmaker',
    version=dustmaker.__version__,
    url='http://github.com/msg555/dustmaker/',
    license='Apache Software License',
    author='Mark Gordon',
    tests_require=['pytest'],
    install_requires=[],
    cmdclass={'test': PyTest},
    author_email='msg555@gmail.com',
    description='Dustforce level scripting framework',
    long_description=long_description,
    packages=['dustmaker'],
    include_package_data=True,
    platforms='any',
    test_suite='dustmaker.test.test_dustmaker',
    extras_require={
        'testing': ['pytest'],
    }
)
