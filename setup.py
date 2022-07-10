#!/usr/bin/env python3
import site
import sys

import setuptools

site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

setuptools.setup()
