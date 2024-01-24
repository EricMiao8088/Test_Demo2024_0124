# -*- coding: utf-8 -*-

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import unittest
from unittest.mock import Mock

from tts.core.report.db import ReportItem
from tts.core.report.parser.ReportApi import ReportApi

try:
    # FakeApiModules importieren, damit alte Pfade gefunden werden
    import tts.core.application.FakeApiModules  # @UnusedImport
except ImportError:
    # FakeApiModules erst ab ECU-TEST 8.1 verfügbar
    pass

from .ProcessPackage import ProcessPackage

# pylint: disable=missing-class-docstring,redundant-u-string-prefix,protected-access
class ProcessPackageTest(unittest.TestCase):

    def test_ConvertCalculationTestStep(self):
        # ARRANGE
        settings = {u'includePkgTestSteps': u'True',
                    u'captureSpecialTestSteps': u'Calculation'}
        report = ReportApiDummy(settings)

        testStep = ReportItem()
        testStep.PSrc = 'SrcId'
        testStep.PSrcType = 'UTILITY'
        testStep.PSrcSubType = '4115FA00-5F3C-11DF-8A53-001C233B3528:Berechnung'
        testStep.PTargetValue = "Erwartungwert"
        testStep.PInfo = "Aktueller Wert"
        testStep.SetOriginalResult("FAILED",563737884)

        # ACT
        processPackage = ProcessPackage(report, "path/toTestCase")
        resultAtxStep = processPackage.ConvertTestStep(report, testStep, False)

        # ASSERT
        self.assertEqual('SrcId', resultAtxStep.testStepId)
        self.assertEqual('Berechnung: ', resultAtxStep.name)
        self.assertEqual('FAILED', resultAtxStep.verdict)
        self.assertEqual('Wert: Aktueller Wert', resultAtxStep.description)
        self.assertEqual(None, resultAtxStep.category)
        self.assertEqual('Erwartungwert', resultAtxStep.verdictDefinition)

    def test_ConvertMainLoopTestStep(self):
        # ARRANGE
        settings = {u'includePkgTestSteps': u'True'}
        report = ReportApiDummy(settings)

        testStep = ReportItem()
        testStep.PSrc = 'SrcId'
        testStep.PSrcType = 'UTILITY'
        testStep.PSrcSubType = '3DA58CF0-4FEF-11DC-BE56-0013728784EE:LOOP'
        testStep.PName = 'Schleife'
        testStep.PActivity = 'For loopCounter=1 to 5'
        testStep.PTargetValue = ""
        testStep.PInfo = ""
        testStep.SetOriginalResult("FAILED",563737884)

        # ACT
        processPackage = ProcessPackage(report, "path/toTestCase")
        resultAtxStep = processPackage.ConvertTestStep(report, testStep, False)

        # ASSERT
        self.assertEqual('SrcId', resultAtxStep.testStepId)
        self.assertEqual('For loopCounter=1 to 5', resultAtxStep.name)
        self.assertEqual('FAILED', resultAtxStep.verdict)
        self.assertEqual("Only the first block that resulted in the loop's aggregate result is displayed.",
                         resultAtxStep.description)
        self.assertEqual(None, resultAtxStep.category)
        self.assertEqual(None, resultAtxStep.verdictDefinition)

    def test_ConvertLoopTestStep(self):

        def CreateLoopItem(testStepId, name, result):
            item = ReportItem()
            item.PSrc = testStepId
            item.PSrcType = 'UTILITY'
            item.PSrcSubType = '3DA58CF0-4FEF-11DC-BE56-0013728784EE:LOOP'
            item.PActivity = name
            item.SetOriginalResult(result,563737884)
            return item

        # ARRANGE
        settings = {u'includePkgTestSteps': u'True'}
        report = ReportApiDummy(settings)

        loopRoot = CreateLoopItem('Root', 'For loopCounter=1 to 4', 'FAILED')

        loopBranch1 = CreateLoopItem('Branch1', 'loopCounter = 1', 'SUCCESS')
        loopBranch2 = CreateLoopItem('Branch2', 'loopCounter = 2', 'FAILED')
        loopBranch3 = CreateLoopItem('Branch3', 'loopCounter = 3', 'FAILED')
        loopBranch4 = CreateLoopItem('Branch4', 'loopCounter = 4', 'SUCCESS')

        # ACT
        processPackage = ProcessPackage(report, "path/toTestCase")
        resultRoot = processPackage.ConvertTestStep(report, loopRoot, False)
        resultBranch1 = processPackage.ConvertTestStep(report, loopBranch1, False)
        resultBranch2 = processPackage.ConvertTestStep(report, loopBranch2, False)
        resultBranch3 = processPackage.ConvertTestStep(report, loopBranch3, False)
        resultBranch4 = processPackage.ConvertTestStep(report, loopBranch4, False)

        # ASSERT
        self.assertEqual('Root', resultRoot.testStepId)

        self.assertIsNone(resultBranch1)

        self.assertEqual('Branch2', resultBranch2.testStepId)
        self.assertEqual('loopCounter = 2', resultBranch2.name)
        self.assertEqual('FAILED', resultBranch2.verdict)

        self.assertIsNone(resultBranch3)
        self.assertIsNone(resultBranch4)

    def test_ConvertLoopTestStepWithBlockTestSteps(self):

        def CreateLoopItem(testStepId, name, result, execLevel):
            item = ReportItem()
            item.PSrc = testStepId
            item.PExecLevel = execLevel
            item.PSrcType = 'UTILITY'
            item.PSrcSubType = '3DA58CF0-4FEF-11DC-BE56-0013728784EE:LOOP'
            item.PActivity = name
            item.SetOriginalResult(result,563737884)
            return item

        def CreateBlockItem(testStepId, name, result, execLevel):
            item = ReportItem()
            item.PSrc = testStepId
            item.PExecLevel = execLevel
            item.PSrcType = 'UTILITY'
            item.PSrcSubType = '007:BLOCK'
            item.PActivity = name
            item.SetOriginalResult(result,563737884)
            return item

        # ARRANGE
        settings = {u'includePkgTestSteps': u'True'}
        report = ReportApiDummy(settings)

        loopRoot = CreateLoopItem('Root', 'For loopCounter=1 to 3', 'FAILED', 0)

        loopBranch1 = CreateLoopItem('Branch1', 'loopCounter = 1', 'SUCCESS', 1)
        block1 = CreateBlockItem('Branch1', 'Loop Block 1', 'SUCCESS', 2)
        loopBranch2 = CreateLoopItem('Branch2', 'loopCounter = 2', 'FAILED', 1)
        block2 = CreateBlockItem('Branch2', 'Loop Block 2', 'FAILED', 2)
        loopBranch3 = CreateLoopItem('Branch3', 'loopCounter = 3', 'FAILED', 1)
        block3 = CreateBlockItem('Branch3', 'Loop Block 3', 'FAILED', 2)

        block4 = CreateBlockItem('OnRoot', 'Block after root loop', 'SUCCESS', 0)

        # ACT
        processPackage = ProcessPackage(report, "path/toTestCase")
        # Exce-Level 0
        resultRoot = processPackage.ConvertTestStep(report, loopRoot, False)
        # Exce-Level 1 und 2
        resultBranch1 = processPackage.ConvertTestStep(report, loopBranch1, False)
        resultBlock1 = processPackage.ConvertTestStep(report, block1, False)
        resultBranch2 = processPackage.ConvertTestStep(report, loopBranch2, False)
        resultBlock2 = processPackage.ConvertTestStep(report, block2, False)
        resultBranch3 = processPackage.ConvertTestStep(report, loopBranch3, False)
        resultBlock3 = processPackage.ConvertTestStep(report, block3, False)
        # Exce-Level 0
        resultBlock4 = processPackage.ConvertTestStep(report, block4, False)

        # ASSERT
        self.assertEqual('Root', resultRoot.testStepId)

        self.assertIsNone(resultBranch1)
        self.assertIsNone(resultBlock1)

        self.assertEqual('Branch2', resultBranch2.testStepId)
        self.assertEqual('loopCounter = 2', resultBranch2.name)
        self.assertEqual('FAILED', resultBranch2.verdict)
        self.assertEqual('Loop Block 2', resultBlock2.name)
        self.assertEqual('FAILED', resultBlock2.verdict)

        self.assertIsNone(resultBranch3)
        self.assertIsNone(resultBlock3)

        self.assertEqual('Block after root loop', resultBlock4.name)
        self.assertEqual('PASSED', resultBlock4.verdict)

    def test_ConvertSwkTaTestStep(self):

        # ARRANGE
        settings = {u'includePkgTestSteps': u'True',
                    u'captureSubPackageOnVerdict':'FAILED'}
        report = ReportApiDummy(settings)
        pkgMock = Mock()
        pkgMock.IterParameterVariables = Mock(return_value=[])
        report.pkgMock = pkgMock

        # Mock müsste auf folgender Klasse basieren:
        # from tts.core.report.parser.Package import ReportItem
        testStep = Mock()
        testStep.GetSrc = Mock(return_value='SrcId')
        testStep.GetSrcType = Mock(return_value='PACKAGE')
        testStep.GetName = Mock(return_value='SWK Status')
        testStep.GetActivity = Mock(return_value='Egal')
        testStep.GetExecLevel = Mock(return_value=1)
        testStep.IterEntities = Mock(return_value=[])
        testStep.GetOriginalResult = Mock(return_value="FAILED")

        # ACT
        processPackage = ProcessPackage(report, "path/toTestCase")
        swkTaStep = processPackage.ConvertTestStep(report, testStep, False)

        # ASSERT
        self.assertEqual('SrcId', swkTaStep.testStepId)
        self.assertEqual('SWK Status', swkTaStep.name)
        self.assertEqual('FAILED', swkTaStep.verdict) 

    def test_CheckAtxConvertOfExampleTestStep(self):
        # ARRANGE
        settings = {u'includePkgTestSteps': u'True',
                    u'captureSpecialTestSteps': u'Calculation'}
        report = ReportApiDummy(settings)

        testStep = ReportItem()
        testStep.PSrc = 'SrcId'
        testStep.PSrcType = 'UTILITY'
        testStep.PSrcSubType = '4115FA00-5F3C-11DF-8A53-001C233B3528:Berechnung'
        testStep.PTargetValue = "Erwartungwert"
        testStep.PInfo = "Aktueller Wert"
        testStep.SetOriginalResult("FAILED",563737884)

        # ACT
        processPackage = ProcessPackage(report, "path/toTestCase")
        resultAtxDict = processPackage.ConvertTestStep(report,
                                                        testStep,
                                                        False).CreateTestStepAtxDict()

        # ASSERT
        self.assertEqual('step_SrcId', resultAtxDict['SHORT-NAME'])
        self.assertEqual(False, resultAtxDict['CATEGORY'])
        self.assertEqual('FAILED', resultAtxDict['VERDICT'])
        self.assertEqual('Berechnung: ', resultAtxDict['LONG-NAME']['L-4']['#'])
        self.assertEqual('Wert: Aktueller Wert', resultAtxDict['DESC']['L-2']['#'])
        self.assertEqual('Erwartungwert', resultAtxDict['VERDICT-DEFINITION']['EXPECTED-RESULT']['P']['L-1']['#'])


# pylint: disable=super-init-not-called
class ReportApiDummy(ReportApi):

    def __init__(self, settings):
        self._settings = settings
        self.pkgMock = None

    def GetSetting(self, name):
        return self._settings.get(name, u'')

    def GetPackage(self, reportItem):
        return self.pkgMock
