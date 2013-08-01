__author__ = "ardevelop"

from distutils.core import setup

setup(
    author='Anatolie Rotaru',
    author_email='public@ardevelop.com',
    name="ardaemon",
    url="https://pypi.python.org/pypi/ardaemon",
    version="0.1",
    packages=["ardaemon",],
    license="MIT License",
    platforms=["UNIX"],
    description="A library for running Python programs as Unix daemons.",
    long_description=open('README.txt').read(),
)