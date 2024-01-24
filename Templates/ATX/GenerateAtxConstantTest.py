# -*- coding: utf-8 -*-

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import unittest
from unittest.mock import MagicMock

try:
    # FakeApiModules importieren, damit alte Pfade gefunden werden
    import tts.core.application.FakeApiModules  # @UnusedImport
except ImportError:
    # FakeApiModules erst ab ECU-TEST 8.1 verfügbar
    pass

from .GenerateAtxConstants import Constant, SpecialConstantCategory, GenerateAtxConstants
from tts.core.report.db import ReportItem


class GenerateAtxConstantsTest(unittest.TestCase):

    def test_SuperDownloaderSpecialConstantIsAdded(self):
        # ARRANGE
        package = ReportItem()
        package.reportItemId = 4711
        generateAtxConstants = GenerateAtxConstants(MagicMock())

        # ACT
        constants = generateAtxConstants.CollectConstants(package, {}, '', None, None, None)

        # ASSERT
        superDownloaderConstant = Constant(SpecialConstantCategory.REPORT_INFO,
                                           'TT_ECUTEST_REPORT_ID', '4711', u'')
        self.assertIn(superDownloaderConstant, constants)
