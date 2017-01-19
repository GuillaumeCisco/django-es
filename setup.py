# -*- coding: utf-8 -*-
from os.path import join, dirname
from setuptools import setup, find_packages

VERSION = (0, 0, 1)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

long_description = 'Should have been loaded from README.md.'
with open(join(dirname(__file__), 'README.rst')) as f:
    long_description = f.read().strip()


install_requires = [
    'django>=1.8',
    'elasticsearch-dsl>=0.0.4',
    'elasticsearch==2.1.0',
    'python-dateutil',
    'six',
]

setup(
    name="django_es",
    description="A Django elasticsearch wrapper for model and helper using elasticsearch-dsl-py high level library.",
    license="BSD-3",
    url="http://gitlab.jacquieetmichel.net/main/django-es",
    long_description=long_description,
    version=__versionstr__,
    author="Guillaume Cisco",
    author_email="guillaumecisco@gmail.com",
    packages=find_packages(
        where='.',
    ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Framework :: Django"
    ],
    keywords="elasticsearch haystack django bungiesearch django_es",
    install_requires=install_requires,
    dependency_links=['https://github.com/elasticsearch/elasticsearch-dsl-py#egg=elasticsearch-dsl-py'],
)
