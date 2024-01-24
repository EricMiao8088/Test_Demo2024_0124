# -*- coding: utf-8 -*-

"""
Created on 09.07.2015

:author: Philipp Schneider <philipp.schneider@tracetronic.de>
"""

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import unittest

try:
    # FakeApiModules importieren, damit alte Pfade gefunden werden
    import tts.core.application.FakeApiModules  # @UnusedImport
except ImportError:
    # FakeApiModules erst ab ECU-TEST 8.1 verfügbar
    pass

# pylint: disable=protected-access
# pylint: disable=missing-docstring
# pylint: disable=import-outside-toplevel


class GenerateAtxDataSetTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        import gettext
        gettext.NullTranslations().install()

    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def testGetWildcardWordsFromWordListWithAsterisk(self):
        """
        Prüfe RegEx Erfassung z.B. der Attribute mit *-Wildcard.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        word = u'Section*'
        words = [u'SectionA', u'SectionB', u'SectionC', u'Sectio', u'SectionB2', u'SectionBXyZ']

        # ACT
        wildcardWordsFromWordList = GenerateAtxDataSet.GetWildcardWordsFromWordList(word, words)

        # ASSERT
        self.assertEqual([u'SectionA', u'SectionB', u'SectionC', u'SectionB2', u'SectionBXyZ'],
                         wildcardWordsFromWordList)

    def testGetWildcardWordsFromWordListWithQuestionMark(self):
        """
        Prüfe RegEx Erfassung z.B. der Attribute mit ?-Wildcard.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        word = u'?ection??'
        words = [u'ASectionA0', u'SectionA', u'SectionB', u'SectionC', u'Sectio', u'SectionB2',
                 u'SectionB1', u'SectionBXyZ']

        # ACT
        wildcardWordsFromWordList = GenerateAtxDataSet.GetWildcardWordsFromWordList(word, words)

        # ASSERT
        self.assertEqual([u'SectionB2', u'SectionB1'], wildcardWordsFromWordList)

    def testGetWildcardWordsFromWordListWithoutWildCards(self):
        """
        Prüfe Erfassung der Attribute.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        word = u'Sectio'
        words = [u'ASectionA0', u'SectionA', u'SectionB', u'SectionC', u'Sectio', u'SectionB2',
                 u'SectionB1', u'SectionBXyZ']

        # ACT
        wildcardWordsFromWordList = GenerateAtxDataSet.GetWildcardWordsFromWordList(word, words)

        # ASSERT
        self.assertEqual([u'Sectio'], wildcardWordsFromWordList)

    def testGetAttributeDelimiter(self):
        """
        Prüfe das Auslesen der Trennzeichen für Attribute-Splitting.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        confgInput = u'ReqId=-'
        expected = {}
        expected[u'ReqId'] = u'-'

        # ACT
        result = GenerateAtxDataSet.GetAttributeDelimiterFromConfig(confgInput)

        # ASSERT
        self.assertEqual(expected, result)

    def testGetEmptyAttributeDelimiter(self):
        """
        Prüfe das Auslesen der Trennzeichen für Attribute-Splitting.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        confgInput = u'ReqId=_;Empty='
        expected = {}
        expected[u'ReqId'] = u'_'

        # ACT
        result = GenerateAtxDataSet.GetAttributeDelimiterFromConfig(confgInput)

        # ASSERT
        self.assertEqual(expected, result)

    def testGetAttributeSingleDelimiterWithEndingSemiconlon(self):
        """
        Prüfe das Auslesen der Trennzeichen für Attribute-Splitting.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        confgInput = u'ReqId=;;'
        expected = {}
        expected[u'ReqId'] = u';'

        # ACT
        result = GenerateAtxDataSet.GetAttributeDelimiterFromConfig(confgInput)

        # ASSERT
        self.assertEqual(expected, result)

    def testGetAttributeSingleDelimiterWithoutEndingSemiconlon(self):
        """
        Prüfe das Auslesen der Trennzeichen für Attribute-Splitting.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        confgInput = u'ReqId=;'
        expected = {}
        expected[u'ReqId'] = u';'

        # ACT
        result = GenerateAtxDataSet.GetAttributeDelimiterFromConfig(confgInput)

        # ASSERT
        self.assertEqual(expected, result)

    def testGetAttributeMultiDelimiter(self):
        """
        Prüfe das Auslesen der Trennzeichen für Attribute-Splitting.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet
        confgInput = u'ReqId=;;JIRA=-; Doors=_;Space= ;Redmine=-;'
        expected = {}
        expected[u'ReqId'] = u';'
        expected[u'JIRA'] = u'-'
        expected[u'Doors'] = u'_'
        expected[u'Space'] = u' '
        expected[u'Redmine'] = u'-'

        # ACT
        result = GenerateAtxDataSet.GetAttributeDelimiterFromConfig(confgInput)

        # ASSERT
        self.assertEqual(expected, result)

    def test_GetAttrSpecDefinitionName_ProjectAttributeName(self):
        """
        Prüfe das Abschneiden des Prefix bei Projekt Attribut Namen
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        expectedName = 'TestName'
        atxProjectAttributeName = '{0}{1}'.format(GenerateAtxDataSet.PRJ_ATT_PREFIX, expectedName)

        # ACT
        result = GenerateAtxDataSet._GetAttrSpecDefinitionName(atxProjectAttributeName)

        # ASSERT
        self.assertEqual(expectedName, result)

    def test_GetAttrSpecDefinitionName_PackageAttributeName(self):
        """
        Prüfe das Nicht Abschneiden des Prefix bei Package Attribut Namen
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        expectedName = 'TestName'
        atxPacakgeAttributeName = expectedName

        # ACT
        result = GenerateAtxDataSet._GetAttrSpecDefinitionName(atxPacakgeAttributeName)

        # ASSERT
        self.assertEqual(expectedName, result)

    def test_GetAttributeDelimiter_DelimiterConfig(self):
        """
        Prüfe das zurückgeben, des richtigen Delimiters aus der Delimiter Config
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        expectedName = 'TestName'
        expectedDelimiter = ';'
        atxPacakgeAttributeName = expectedName
        delimiterConfig = '{0}={1}'.format(expectedName, expectedDelimiter)

        # ACT
        result = GenerateAtxDataSet._GetAttributeDelimiter(
            atxPacakgeAttributeName,
            None,
            delimiterConfig)

        # ASSERT
        self.assertEqual(expectedDelimiter, result)

    def test_GetAttributeDelimiter_AttrSpec_MultiChoide(self):
        """
        Prüfe das zurückgeben, des richtigen Delimiters aus der AttrSpec falls 
        Attribute MultiChoice unterstützt
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        expectedName = 'TestName'
        expectedDelimiter = '!'
        atxPacakgeAttributeName = expectedName

        from tts.lib.attributes.AttrSpec import AttributeTreeValueDef
        definition = AttributeTreeValueDef(expectedName,
                                           valueSeparator=expectedDelimiter,
                                           isMultiChoice=True)

        # ACT
        result = GenerateAtxDataSet._GetAttributeDelimiter(
            atxPacakgeAttributeName,
            definition)

        # ASSERT
        self.assertEqual(expectedDelimiter, result)

    def test_GetAttributeDelimiter_Default(self):
        """
        Prüfe das zurückgeben, des default Delimiters
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        expectedName = 'TestName'
        expectedDelimiter = ','
        atxPacakgeAttributeName = expectedName

        # ACT
        result = GenerateAtxDataSet._GetAttributeDelimiter(
            atxPacakgeAttributeName,
            None)

        # ASSERT
        self.assertEqual(expectedDelimiter, result)

    # TODO: Mehr ATX Format Tests schreiben
    def test_GetATXAttributeFormat_Basic(self):
        """
        Prüfe das Erstellen des ATX Attribut Formats.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        attributeName = 'TestName'
        attrubuteValue = 'Val1,Val2,Val3'
        expectedValues = 3
        # ACT
        result = GenerateAtxDataSet._GetATXAttributeFormat(attributeName, attrubuteValue, False)

        # ASSERT
        self.assertEqual(attributeName, result[u'@GID'])
        self.assertEqual(expectedValues, len(result[u'*SDS']))

    def test_GetATXAttributeFormat_EliminateValueDuplicates(self):
        """
        Prüfe das Erstellen des ATX Attribut Formats.
        """
        # ARRANGE
        from .GenerateAtxDataSet import GenerateAtxDataSet

        attributeName = 'ECU'
        attrubuteValue = 'Val1,Val2,Val3,Val2,Val3'
        expectedValues = 3
        # ACT
        result = GenerateAtxDataSet._GetATXAttributeFormat(attributeName, attrubuteValue, False)

        # ASSERT
        self.assertEqual(attributeName, result[u'@GID'])
        self.assertEqual(expectedValues, len(result[u'*SDS']))

    def test_CreateTestParamValue_Shortname(self):
        """
        Prüfe das Erstellen des ATX Attribut Formats.
        """
        from .GenerateAtxDataSet import GenerateAtxDataSet

        # ARRANGE
        paramKey = u'hubbabubba'
        paramValue = u'IDONTCARE'

        # ACT
        generateAtxDataSet = GenerateAtxDataSet(None, None, None, None)
        testParamValue = generateAtxDataSet._CreateTestParamValue(paramKey, paramValue)

        # ASSERT
        shortName = testParamValue[u'TEST-PARAM-VALUE-SET-CAPTION'][u'SHORT-NAME']
        self.assertEqual(u'hubbabubba', shortName)

    def test_CreateTestParamValue_SimpleValue(self):
        """
        Prüfe das Erstellen des ATX Attribut Formats.
        """
        from .GenerateAtxDataSet import GenerateAtxDataSet

        # ARRANGE
        paramKey = u'IDONTCARE'
        paramValue = u'4711'

        # ACT
        generateAtxDataSet = GenerateAtxDataSet(None, None, None, None)
        testParamValue = generateAtxDataSet._CreateTestParamValue(paramKey, paramValue)

        # ASSERT
        self.assertEqual(1, len(testParamValue[u'TEST-PARAM-VALUES']))
        value = testParamValue[u'TEST-PARAM-VALUES'][0][u'VALUE']
        self.assertEqual(u'4711', value)

    def test_CreateTestParamValue_IterableValue(self):
        """
        Prüfe das Erstellen des ATX Attribut Formats.
        """
        from .GenerateAtxDataSet import GenerateAtxDataSet

        # ARRANGE
        paramKey = u'IDONTCARE'
        paramValue = u'[123, 456]'

        # ACT
        generateAtxDataSet = GenerateAtxDataSet(None, None, None, None)
        testParamValue = generateAtxDataSet._CreateTestParamValue(paramKey, paramValue)

        # ASSERT
        self.assertEqual(1, len(testParamValue[u'TEST-PARAM-VALUES']))
        value = testParamValue[u'TEST-PARAM-VALUES'][0][u'VALUE']
        self.assertEqual(u'[123, 456]', value)

if __name__ == '__main__':
    unittest.main()
