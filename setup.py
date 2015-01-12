from setuptools import setup, find_packages
from pandoc_opml import __version__

setup(
    name = 'pandoc-opml',
    version = __version__,
    packages = find_packages(),
    author = 'Eric Davis',
    author_email = 'eric@davising.com',
    url = 'https://github.com/edavis/pandoc-opml',
    entry_points = {
        'console_scripts': [
            'pandoc-opml = pandoc_opml:main',
        ],
    },
)
