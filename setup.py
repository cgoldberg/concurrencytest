"""setup/install script for concurrencytest"""

import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="concurrencytest",
    version="0.1.5",
    py_modules=["concurrencytest"],
    install_requires=["python-subunit", "testtools"],
    author="Corey Goldberg",
    description="Python testtools extension for running unittest suites concurrently",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cgoldberg/concurrencytest",
    download_url="https://pypi.org/project/concurrencytest",
    keywords="test testing testtools unittest concurrency parallel".split(),
    license="GNU GPLv2+",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
    ],
)
