import os.path
import sys
import logging
from threading import Thread

## arrview must be imported before traits so that the qt backend will be used
from arrview import view
from arrview.reports import SummaryReportDialog, CombineForm722ReportDialog

import jtmri.dcm
import jtmri.roi
from jtmri.fit import fit_r2star_with_threshold
from jtmri.reports.summary import DicomStudySummaryReport

from traits.api import (HasStrictTraits, Set, List, Int, Str, Button, Instance,
                        Directory, Any, Event, Bool, File, Enum, Property, on_trait_change)
from traitsui.api import (View, Group, HGroup, TableEditor, EnumEditor, Item, MenuBar, Menu, Action,
                          Controller, spring)
from traitsui.table_column import ObjectColumn
from traitsui.extras.checkbox_column import CheckboxColumn

from traitsui.qt4.file_editor import SimpleEditor as SimpleFileEditor
from traitsui.editors.file_editor import ToolkitEditorFactory as FileEditorFactory
from pyface.qt import QtGui


log = logging.getLogger(__name__)


class CustomDirectoryEditor(SimpleFileEditor):
    """Create a Directory Editor that still shows files"""
    def _create_file_dialog(self):
        """ Creates the correct type of file dialog.
        """
        print('custom directory editor created')
        dlg = QtGui.QFileDialog(self.control)
        dlg.selectFile(self._file_name.text())
        dlg.setFileMode(QtGui.QFileDialog.Directory)
        return dlg


class DirectoryEditorFactory(FileEditorFactory):
    @classmethod
    def _get_toolkit_editor(cls, class_name):
        return CustomDirectoryEditor


class DicomSeries(HasStrictTraits):
    series_number = Int
    description = Str
    images = Int
    slices = Int
    rois = Str
    roi_tags = List
    series = Any

    def __init__(self, series):
        self.series = series
        self.update()
        
    def update(self):
        series = self.series
        s = series.first
        self.series_number = s.SeriesNumber
        self.description = s.SeriesDescription
        self.images = len(series)
        try:
            self.slices = len(series.all_unique.SliceLocation)
        except AttributeError:
            self.slices = 0
        try:
            rois = sorted(s.meta.roi.groupby('tag').apply(len).iteritems(), key=lambda x: x[0])
            self.rois = ' '.join('%s: %d' % (k[0], v) for k, v in rois)
            self.roi_tags = [k[0] for k, _ in rois]
        except AttributeError:
            self.rois = ' '
            self.roi_tags = []


dicomseries_editor = TableEditor(
    sortable = False,
    configurable = False,
    auto_size = True,
    show_toolbar = False,
    selection_mode = 'rows',
    selected = 'selection',
    dclick = 'series_dclick',
    columns = [ ObjectColumn(name='series_number', label='Series', editable=False),
                ObjectColumn(name='description', label='Description', editable=False,
                             width=0.8),
                ObjectColumn(name='slices', label='Slices', editable=False),
                ObjectColumn(name='images', label='Images', editable=False),
                ObjectColumn(name='rois', label='ROIs', editable=False, width=0.2)])


class DicomReaderThread(Thread):
    def __init__(self, path, progress=lambda x:x, finished=lambda x:x):
        super(DicomReaderThread, self).__init__()
        self.dcms = []
        self.count = 0
        self.path = path
        self.progress = progress
        self.finished = finished

    def run(self):
        self.dcms = jtmri.dcm.read(self.path, progress=self.progress, disp=False)
        self.finished(self.dcms) 


class DicomSeriesViewer(HasStrictTraits): 
    viewseries = Button
    path = Directory
    load = Button
    roi_tag = Enum(values='_roi_tag_values')
    _roi_tag_values = Property(depends_on='selection')
    _roi_tag_prev = Str

    message = Str('Select a directory to load dicoms from')
    series = List(DicomSeries, [])
    selection = List(DicomSeries)
    series_dclick = Event

    dicomReaderThread = Instance(Thread)

    def _get__roi_tag_values(self):
        if len(self.selection) == 1:
            return ['None'] + self.selection[0].roi_tags
        return ['None']

    def _get_roi_filename(self, series):
        try:
            rois = series.first.meta.roi.by_tag(self.roi_tag)
            return rois.first.props['abspath']
        except (AttributeError, IndexError):
            return None

    def _series_dclick_fired(self):
        self._viewseries_fired()

    def _viewseries_fired(self):
        assert len(self.selection) == 1
        series = self.selection[0].series
        roi_filename = self._get_roi_filename(series)
        if roi_filename is None:
            file_dir = os.path.dirname(series.first.filename)
            # Create ROIs directory if it does not exist
            # Assume that the ROIs will be saved to series_##.h5
            rois_dir = os.path.join(file_dir, 'rois')
            if not os.path.exists(rois_dir):
                os.mkdir(rois_dir)
            series_number = series.first.SeriesNumber
            series_name = 'series_%02d.h5' % series_number
            log.info('rois_dir: {} series: {}'.format(rois_dir, series_name))
            roi_filename = os.path.join(rois_dir, series_name)

        def rois_updated(filename, self=self, series=series):
            assert len(self.selection) == 1
            jtmri.dcm.dcminfo.update_metadata_rois(series)
            self.selection[0].update()

        grouper = ['SliceLocation'] if self.selection[0].slices > 0 else []
        view(series.data(grouper),
             title='Patient:{} Series:#{} {!r}'.format(series.first.PatientName,
                                                       series.first.SeriesNumber,
                                                       series.first.SeriesDescription),
             roi_filename=roi_filename,
             rois_updated=rois_updated)

    def _load_fired(self):
        self._read_directory()
        
    def _path_default(self):
        return os.path.abspath('.')
   
    def _path_changed(self):
        self._read_directory()

    def _read_directory(self):
        self.series = []
        self._update_progress()
        self.dicomReaderThread = DicomReaderThread(self.path,
                progress=self._update_progress,
                finished=self._directory_finished_loading)
        self.dicomReaderThread.start()

    def _update_progress(self, count=0):
        self.message = 'Read %d dicoms from %s' % (count, self.path)

    def _directory_finished_loading(self, dcms):
        self.selection = []
        self.series = map(DicomSeries, dcms.series())
        self.dicomReaderThread = None

    def default_traits_view(self):
        return View(
            Group(
                HGroup(
                    Item('path',
                        enabled_when='dicomReaderThread is None',
                        show_label=False,
                        editor=DirectoryEditorFactory()),
                    Item('load',
                        label='Reload',
                        enabled_when='dicomReaderThread is None',
                        visible_when='False',
                        show_label=False)),
                Group(
                    Item('series',
                        show_label=False,
                        editor=dicomseries_editor,
                        style='readonly',
                        visible_when='len(series) > 0'),
                    Item('message',
                        show_label=False,
                        style='readonly',
                        visible_when='len(series) == 0'),
                    springy=True),
                HGroup(
                    Item('viewseries',
                        label='View',
                        show_label=False,
                        enabled_when='len(selection) == 1'),
                    spring,
                    Item('roi_tag',
                         label='ROI',
                         enabled_when='len(selection) == 1'),
                    visible_when='len(series) > 0'),
                springy=True),
            menubar = MenuBar(
                Menu(
                    Action(name='Quit', action='_quit'),
                    name='File'),
                Menu(
                    Action(name='Images', action='_view_images',
                           enabled_when='len(selection) == 1'),
                    Action(name='R2* Map', action='_view_r2star_map',
                           enabled_when='len(selection) == 1'),
                    name='View'),
                Menu(
                    Action(name='Summary', action='_create_summary_report',
                           enabled_when='len(selection) > 0'),
                    Action(name='COMBINE 722', action='_create_combine_722_report',
                           enabled_when='len(selection) > 0'),
                    name='Reports')),
            title='Dicom Viewer',
            height=400,
            width=600,
            resizable=True,
            handler=DicomViewerHandler())


class DicomViewerHandler(Controller):
    def _quit(self, info):
        log.debug('closing window')
        self.close(info, is_ok=True)
        sys.exit(0)

    def _view_images(self, info):
        info.object._viewseries_fired()

    def _create_summary_report(self, info):
        selected_series = info.object.selection
        SummaryReportDialog(series=selected_series).configure_traits()
    
    def _create_combine_722_report(self, info):
        selected_series = info.object.selection
        CombineForm722ReportDialog(series=selected_series).configure_traits()

    def _view_r2star_map(self, info):
        '''Create R2star map or read the saved version'''
        log.debug('view R2*')
        dv = info.object
        assert len(dv.selection) == 1
        grouper = ['SliceLocation'] if dv.selection[0].slices > 0 else []
        series = dv.selection[0].series
        roi_filename = dv._get_roi_filename(series)
        data = series.data(grouper)
        echo_times = series.all_unique.EchoTime / 1000.
        r2star, _ = fit_r2star_with_threshold(echo_times, data)
        view(r2star, roi_filename=roi_filename)
