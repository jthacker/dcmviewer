from __future__ import absolute_import
import logging

from dcmviewer import __version__


def view(path=None):
    from dcmviewer.ui import DicomSeriesViewer

    if path is None:
        path = os.path.abspath('.')
    viewer = DicomSeriesViewer(path=path)
    viewer.configure_traits()
    return viewer


def main():
    import os
    from terseparse import Parser, Arg, KW

    logging.getLogger().setLevel(logging.DEBUG)
    logging.basicConfig()

    p = Parser('dcmviewer', 'Display dicom series for viewing and editing ROIs',
            Arg('--version', 'show version', action='version',
                version='%(prog)s ({})'.format(__version__)),
            Arg('directory', 'Working directory to start the viewer in',
                default=os.path.abspath('.'), nargs='?'))
    _, args = p.parse_args()
    view(args.ns.directory)
