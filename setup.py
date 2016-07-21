import os
import re
from setuptools import setup


PROJECT='dcmviewer'


def get_version(project_path):
    version_path = os.path.join(project_path, '_version.py')
    version_regex = r"^__version__ = ['\"]([^'\"]*)['\"]"
    string = open(version_path).read()
    m = re.search(version_regex, string, re.M)
    if not m:
        raise RuntimeError('Unable to find version string in {!r}.'.format(version_path))
    return m.group(1)


version = get_version(PROJECT)


setup(name=PROJECT,
      description='Project Description',
      packages=[PROJECT],
      version=version,
      url='https://github.com/jthacker/{{PROJECT}}/' + PROJECT,
      download_url='https://github.com/jthacker/{{PROJECT}}/{}/archive/v{}.tar.gz'.format(PROJECT, version),
      author='Jon Thacker',
      author_email='thacker.jon@gmail.com',
      keywords=[],
      classifiers=[],
      install_requires=[
          'arrview',
          'jtmri',
      ],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      entry_points = {'console_scripts': [
          'dcmviewer = dcmviewer.dcmviewer:main'
          ]},
      long_description="")
