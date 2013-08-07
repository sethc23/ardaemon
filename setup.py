__author__ = "ardevelop"

from distutils.core import setup

setup(
    author='Anatolie Rotaru',
    author_email='public@ardevelop.com',
    name="ardaemon",
    url="https://github.com/ardevelop/ardaemon",
    version="1.0",
    packages=["ardaemon",],
    license="MIT License",
    platforms=["UNIX"],
    description="A library for running Python programs as Unix daemons.",
    long_description=open('README.txt').read(),
)