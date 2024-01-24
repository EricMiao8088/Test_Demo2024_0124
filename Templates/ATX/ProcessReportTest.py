# -*- coding: utf-8 -*-

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import os.path
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
from lxml import etree as ET
from io import BytesIO
from unittest import TestCase

from tts.core.report.parser.ReportApi import ReportApi
from .UploadSettings import UploadSettings

try:
    # FakeApiModules importieren, damit alte Pfade gefunden werden
    import tts.core.application.FakeApiModules  # @UnusedImport
except ImportError:
    # FakeApiModules erst ab ECU-TEST 8.1 verfügbar
    pass

from .ProcessReport import ProcessReport
from tts.lib.common.files.PathHandler import GetUnitTestDataDir

REPORT_FOLDER_NAME = 'EngineSpeed'
DB_FILE = os.path.join(GetUnitTestDataDir(), 'ATX', REPORT_FOLDER_NAME, 'EngineSpeed.trf')

# pylint: disable=missing-docstring

class ProcessReportTest(TestCase):
    tempDir = None

    def setUp(self) -> None:
        self.tempDir = tempfile.mkdtemp(prefix='ATX')

    def tearDown(self) -> None:
        shutil.rmtree(self.tempDir, ignore_errors=True)

    def test_GeneratePackageReport(self):
        settings = {}

        reportApi = None
        try:
            reportApi = ReportApi(DB_FILE, self.tempDir, None, None, settings)
            uploadSettings = UploadSettings('guddelaune', 123, False, '', '', {}, 77)
            ProcessReport(reportApi, True, uploadSettings)
        finally:
            reportApi.Close()

        zipPath = os.path.join(self.tempDir, REPORT_FOLDER_NAME + '.zip')
        self.assertTrue(os.path.exists(zipPath))
        with zipfile.ZipFile(zipPath) as zipFile:
            fileList = zipFile.namelist()

        self.assertEqual(5, len(fileList))
        baseFileNames = [os.path.basename(x) for x in fileList]
        self.assertIn('report.xml', baseFileNames)
        self.assertIn('mapping.xml', baseFileNames)
        self.assertIn('reviews.xml', baseFileNames)
        self.assertIn('EngineSpeed.trf', baseFileNames)
        self.assertIn('Plot 0.png', baseFileNames)

    @unittest.skipIf(sys.platform != 'win32', 'Test funktioniert nicht unter Linux')
    def test_GeneratePackageReport_Recording(self):
        settings = {
            'archiveRecordings': 'True',
            'archiveMiscFiles': '*',
            'archiveFilesPerPackage': '*.*;**/*.*',
            'archiveFilesExcludeRecordings': 'True'
        }

        reportApi = None
        try:
            reportApi = ReportApi(DB_FILE, self.tempDir, None, None, settings)
            uploadSettings = UploadSettings('guddelaune', 123, False, '', '', {}, 77)
            ProcessReport(reportApi, True, uploadSettings)
        finally:
            reportApi.Close()

        zipPath = os.path.join(self.tempDir, REPORT_FOLDER_NAME + '.zip')
        self.assertTrue(os.path.exists(zipPath))
        with zipfile.ZipFile(zipPath) as zipFile:
            fileList = zipFile.namelist()

            # Prüfen, dass Aufnahmen in der ATX-ZIP enthalten sind
            baseFileNames = [os.path.basename(x) for x in fileList]
            self.assertIn('TC Variables Trace_EngineSpeed.csv.zip', baseFileNames)
            self.assertNotIn('TC Variables Trace_EngineSpeed.csv', baseFileNames)
            self.assertIn('TC Variables Trace_EngineSpeed.csv.metadata', baseFileNames)
            self.assertIn('Job_1_Signals.astrace', baseFileNames)
            self.assertIn('Job_1_Signals.astrace.metadata', baseFileNames)

            miscZipFile = self.__FindMiscZipFile(fileList)
            self.assertIsNotNone(miscZipFile)

            # Prüfen, dass Aufnahmen NICHT in der Misc-ZIP enthalten sind
            with zipfile.ZipFile(BytesIO(zipFile.read(miscZipFile))) as miscZip:
                baseFileNames = [os.path.basename(x) for x in miscZip.namelist()]
                self.assertNotIn('Job_1_Signals.astrace', baseFileNames)
                self.assertNotIn('TC Variables Trace_EngineSpeed.csv', baseFileNames)

            # Prüfe auf korrekten relativen Pfad am Beispiel von Job_1_Signals.astrace
            tree = ET.fromstring(zipFile.read('mapping.xml'))
            asFile = tree.xpath('/FILES/FILE[FILENAME/text() = "Job_1_Signals.astrace"]')[0]
            self.assertEqual(asFile.xpath('REL-PATH/text()')[0], 'EngineSpeed')

    @unittest.skipIf(sys.platform != 'win32', 'Test funktioniert nicht unter Linux')
    def test_GeneratePackageReport_OnlyArchiveMiscFiles(self):
        settings = {
            'archiveRecordings': 'False',
            'archiveTrf': 'False',
            'archivePlots': 'False',
            'archiveImages': 'False',
            'archiveMiscFiles': '*.*;**/*.*'
        }

        reportApi = None
        try:
            reportApi = ReportApi(DB_FILE, self.tempDir, None, None, settings)
            uploadSettings = UploadSettings('guddelaune', 123, False, '', '', {}, 77)
            ProcessReport(reportApi, True, uploadSettings)
        finally:
            reportApi.Close()

        zipPath = os.path.join(self.tempDir, REPORT_FOLDER_NAME + '.zip')
        self.assertTrue(os.path.exists(zipPath))
        with zipfile.ZipFile(zipPath) as zipFile:
            fileList = zipFile.namelist()

            # Prüfen, dass nur die Default-Dateien und die Mics-ZIP vorhanden ist
            self.assertEqual(4, len(fileList))

            miscZipFile = self.__FindMiscZipFile(fileList)
            self.assertIsNotNone(miscZipFile)

            # Prüfen, dass die gewünschten Dateien in der Misc-ZIP enthalten sind
            with zipfile.ZipFile(BytesIO(zipFile.read(miscZipFile))) as miscZip:
                baseFileNames = [os.path.basename(x) for x in miscZip.namelist()]
                self.assertIn('Job_1_Signals.astrace', baseFileNames)
                self.assertIn('TC Variables Trace_EngineSpeed.csv', baseFileNames)
                self.assertIn('speed.log', baseFileNames)
                self.assertIn('ECU_TEST_OUT.log', baseFileNames)
                self.assertIn('ECU_TEST_ERR.log', baseFileNames)
                self.assertIn('EngineSpeed.trf', baseFileNames)
                self.assertEqual(6, len(baseFileNames))

    def __FindMiscZipFile(self, fileList):
        miscZipFile = None
        for file in fileList:
            try:
                datetime.strptime(os.path.basename(file), u'%Y-%m-%d_%H%M%S.zip')
                miscZipFile = file
            except ValueError:
                pass

        return miscZipFile
