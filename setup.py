import os
import re
from setuptools import setup

exec(open('dcmviewer/_version.py').read())

setup(name='dcmviewer',
      description='Project Description',
      packages=['dcmviewer'],
      version=__version__,
      url='https://github.com/jthacker/dcmviewer/',
      download_url='https://github.com/jthacker/dcmviewer/archive/v{}.tar.gz'.format(__version__),
      author='Jon Thacker',
      author_email='thacker.jon@gmail.com',
      keywords=[],
      classifiers=[],
      install_requires=[
          'arrview',
          'jtmri',
          'terseparse'
      ],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      entry_points = {'console_scripts': [
          'dcmviewer = dcmviewer.cli:main'
          ]},
      long_description="")
