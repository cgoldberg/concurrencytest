"""setup/install script for concurrencytest"""

from setuptools import setup


setup(
    name="concurrencytest",
    version="0.1.4",
    py_modules=["concurrencytest"],
    install_requires=["python-subunit", "testtools"],
    author="Corey Goldberg",
    description="testtools extension for running unittest suites concurrently",
    long_description="testtools extension for running unittest suites concurrently",
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
