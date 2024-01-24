# -*- coding: utf-8 -*-

'''
Created on 29.10.2014

@author: Christoph Groß <christoph.gross@tracetronic.de>
'''

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import unittest
import tempfile
import shutil
from datetime import datetime
from xml.etree import ElementTree

from mockito import mock, when, any, eq

try:
    # FakeApiModules importieren, damit alte Pfade gefunden werden
    import tts.core.application.FakeApiModules  # @UnusedImport
except ImportError:
    # FakeApiModules erst ab ECU-TEST 8.1 verfügbar
    pass

import gettext
gettext.NullTranslations().install()

from tts.core.report.db.ReportItemComment import ReportItemComment
from .ReviewUtils import (GroupReviewsPerPackage, GetReviewsForReportItem, ReviewCommentException)


# pylint: disable=missing-docstring

class ReviewUtilsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(ReviewUtilsTest, cls).setUpClass()
        try:
            cls.__tmpDir = tempfile.mkdtemp(u'_ReviewUtilsTest')
        except BaseException:
            cls.tearDownClass()

    @classmethod
    def tearDownClass(cls):
        super(ReviewUtilsTest, cls).tearDownClass()
        shutil.rmtree(cls.__tmpDir, True)

    def setUp(self):
        unittest.TestCase.setUp(self)

    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def testGroupReviewsPerPackage(self):
        # ARRANGE

        from .Review import Review

        reportCommentMock1 = mock()
        when(reportCommentMock1).GetText().thenReturn(u'Comment')
        when(reportCommentMock1).GetAuthor().thenReturn(u'WerkOhneNamen')
        when(reportCommentMock1).GetOverriddenResult().thenReturn(u'SUCCESS')
        when(reportCommentMock1).GetTimestamp().thenReturn(2)
        review1 = Review(reportCommentMock1, "Level 1", 1, 1, None)

        reportCommentMock2 = mock()
        when(reportCommentMock2).GetText().thenReturn(u'Comment')
        when(reportCommentMock2).GetAuthor().thenReturn(u'WerkOhneNamen')
        when(reportCommentMock2).GetOverriddenResult().thenReturn(u'FAILED')
        when(reportCommentMock2).GetTimestamp().thenReturn(3)
        review2 = Review(reportCommentMock2, "Level 1", 1, 2, None)

        reportCommentMock3 = mock()
        when(reportCommentMock3).GetText().thenReturn(u'Comment')
        when(reportCommentMock3).GetAuthor().thenReturn(u'WerkOhneNamen')
        when(reportCommentMock3).GetOverriddenResult().thenReturn(u'ERROR')
        when(reportCommentMock3).GetTimestamp().thenReturn(1)
        review3 = Review(reportCommentMock3, "Level 1", 1, 3, None)

        reportCommentMock4 = mock()
        when(reportCommentMock4).GetText().thenReturn(u'Comment')
        when(reportCommentMock4).GetAuthor().thenReturn(u'WerkOhneNamen')
        when(reportCommentMock4).GetOverriddenResult().thenReturn(u'ERROR')
        when(reportCommentMock4).GetTimestamp().thenReturn(1)
        review4 = Review(reportCommentMock4, "Level 1", 2, 3, None)

        # ACT
        result = GroupReviewsPerPackage([review1, review3, review4, review2])

        # ASSERT
        self.assertEqual("ERROR", result.pop(0).GetRevaluationVerdict())
        self.assertEqual("FAILED", result.pop(0).GetRevaluationVerdict())
        self.assertEqual("PASSED", result.pop(0).GetRevaluationVerdict())
        self.assertEqual(0, len(result))

    def testGetReviewsForReportItem_Defect(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        reviewDefect = u'Fehlerklasse'

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(), u'Kommentar |{0}|'.format(reviewDefect), None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn( item for item in [review] )
        when(reportApi).GetSetting(eq(u'detectReviewDefects')).thenReturn(reviewDefect)

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        result[0].SetTestCaseRef('ref')
        xml = ElementTree.tostring(result[0].GetXml(), encoding='unicode', method='xml')
        self.assertIn(u'<DEFECT>{0}</DEFECT>'.format(reviewDefect), xml)

    def testGetReviewsForReportItem_DefectNewSyntax(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        reviewDefect = u'Fehlerklasse'

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!defectClass {0}!#'.format(reviewDefect), None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])
        when(reportApi).GetSetting(eq(u'detectReviewDefects')).thenReturn(reviewDefect)

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        result[0].SetTestCaseRef('ref')
        xml = ElementTree.tostring(result[0].GetXml(), encoding='unicode', method='xml')
        self.assertIn(u'<DEFECT>{0}</DEFECT>'.format(reviewDefect), xml)

    def testGetReviewsForReportItem_OnlyOneDefect(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        reviewDefect = u'Fehlerklasse1;Fehlerklasse2'

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(), u'Kommentar |Fehlerklasse1| |Fehlerklasse2|', None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn( item for item in [review] )
        when(reportApi).GetSetting(eq(u'detectReviewDefects')).thenReturn(reviewDefect)

        # ACT + ASSERT
        with self.assertRaises(ReviewCommentException):
            GetReviewsForReportItem(reportApi, reportItem)

    def testGetReviewsForReportItem_OnlyOneDefectOldAndNewSyntax(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        reviewDefect = u'Fehlerklasse1;Fehlerklasse2'

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'|Fehlerklasse1| #!defectClass Fehlerklasse2!#', None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])
        when(reportApi).GetSetting(eq(u'detectReviewDefects')).thenReturn(reviewDefect)

        # ACT + ASSERT
        with self.assertRaises(ReviewCommentException):
            GetReviewsForReportItem(reportApi, reportItem)

    def testGetReviewsForReportItem_OnlyOneDefectNewSyntax(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        reviewDefect = u'Fehlerklasse1;Fehlerklasse2'

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!defectClass Fehlerklasse1!# #!defectClass Fehlerklasse2!#',
                                   None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])
        when(reportApi).GetSetting(eq(u'detectReviewDefects')).thenReturn(reviewDefect)

        # ACT + ASSERT
        with self.assertRaises(ReviewCommentException):
            GetReviewsForReportItem(reportApi, reportItem)

    def testGetReviewsForReportItem_Tags(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#Tag2# Kommentar #Tag1# und #Tag3# #!tag Tag5!# #!tag Tag4!#'
                                   u'etc.pp.', None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn( item for item in [review] )
        when(reportApi).GetSetting(eq(u'detectReviewTags')).thenReturn(u'Tag1;Tag2;Tag3;Tag4;Tag5')

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        result[0].SetTestCaseRef('ref')
        xml = ElementTree.tostring(result[0].GetXml(), encoding='unicode', method='xml')
        self.assertIn(u'<TAGS>', xml)
        self.assertIn(u'<TAG>Tag1</TAG>', xml)
        self.assertIn(u'<TAG>Tag2</TAG>', xml)
        self.assertIn(u'<TAG>Tag3</TAG>', xml)
        self.assertIn(u'<TAG>Tag4</TAG>', xml)
        self.assertIn(u'<TAG>Tag5</TAG>', xml)
        self.assertIn(u'</TAGS>', xml)

    def testGetReviewsForReportItem_Summary(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'blabla#!summary Das ist eine Summary!!#', None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        self.assertEqual(u'Das ist eine Summary!', result[0].GetSummary())

    def testGetReviewsForReportItem_OnlyOneSummary(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!summary 1!##!summary 2!#', None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])

        # ACT + ASSERT
        with self.assertRaises(ReviewCommentException):
            GetReviewsForReportItem(reportApi, reportItem)

    def testGetReviewsForReportItem_Verdict(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!verdict FAILED!#',None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        self.assertEqual(u'FAILED', result[0].GetRevaluationVerdict())

    def testGetReviewsForReportItem_VerdictSuccess(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!verdict SUCCESS!#', None)

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        self.assertEqual(u'PASSED', result[0].GetRevaluationVerdict())

    def testGetReviewsForReportItem_OnlyOneVerdict(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!verdict FAILED!##!verdict PASSED!#', u'SUCCESS')

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])

        # ACT + ASSERT
        with self.assertRaises(ReviewCommentException):
            GetReviewsForReportItem(reportApi, reportItem)

    def testGetReviewsForReportItem_InvalidVerdict(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   u'#!verdict irgendwasAberKeinVerdict!#', u'SUCCESS')

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])

        # ACT + ASSERT
        with self.assertRaises(ReviewCommentException) as cm:
            GetReviewsForReportItem(reportApi, reportItem)

        self.assertIn(u'irgendwasAberKeinVerdict', str(cm.exception))

    def testGetReviewsWithEmptyReviewComment(self):
        # ARRANGE
        reportItem = mock()
        when(reportItem).GetSrcIndex().thenReturn(1)
        when(reportItem).GetName().thenReturn(u'Name')
        when(reportItem).GetActivity().thenReturn(u'abc')
        when(reportItem).GetId().thenReturn(1)
        when(reportItem).GetAbortCode().thenReturn(u'')
        when(reportItem).GetExecLevel().thenReturn(1)

        review = ReportItemComment(1, 1, u'Author', datetime.now().timestamp(),
                                   None, u'-')

        reportApi = mock()
        when(reportApi).IterUserComments(any()).thenReturn(item for item in [review])
        when(reportApi).GetSetting(eq(u'detectReviewTags')).thenReturn(u'Tag1;Tag2')

        # ACT
        result = GetReviewsForReportItem(reportApi, reportItem)

        # ASSERT
        self.assertEqual(u'-', result[0].GetRevaluationVerdict())

if __name__ == '__main__':
    unittest.main()
