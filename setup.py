#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='wagtail-transfer',
    version='0.3',
    description="Content transfer for Wagtail",
    author='Matthew Westcott',
    author_email='matthew.westcott@torchbox.com',
    url='https://github.com/wagtail/wagtail-transfer',
    packages=find_packages(exclude=('tests',)),
    include_package_data=True,
    install_requires=[
    ],
    extras_require={
        'docs': [
            'mkdocs>=1.0,<1.1',
            'mkdocs-material>=4.6,<4.7',
        ],
    },
    license='BSD',
    long_description="An extension for Wagtail allowing content to be transferred between multiple instances of a Wagtail project",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django',
        'Framework :: Wagtail',
        'Framework :: Wagtail :: 2',
    ],
)
