# -*- coding: utf-8 -*-

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import sys
from collections import namedtuple, OrderedDict

from enum import Enum

import requests
from log import DPrint, EPrint, LEVEL_VERBOSE, WPrint, TPrint

from .Config import Settings
from .Utils import FilterShortName, ReplaceAsciiCtrlChars

if sys.version_info < (3,):
    from urllib import pathname2url
else:
    from urllib.request import pathname2url


class SpecialConstantCategory(Enum):
    """
    Enum zur Kategorisierung der speziellen Konstanten, welche in TEST-GUIDE separat angezeigt
    werden.
    """
    TBC_INFO = 1
    TCF_INFO = 2
    USER_DEFINED_REPORT = 3
    ALM_SETTING = 4
    REPORT_INFO = 5
    CONSTANT = 6


Constant = namedtuple('Constant', 'category name textValue description')
UserReportData = namedtuple('Constant', ' key value description')


class GenerateAtxConstants(object):
    PRJ_ATT_PREFIX = u'Project_'

    def __init__(self, reportApi):
        self._reportApi = reportApi
        self._settings = Settings(reportApi)

        # Dict der zu setzenden Config.xml Konstanten
        self._configConstants = self._settings.GetDict(u'setConstants')
        # Dict mit den Konstanten des ResourcesAdapters setzen
        if self._settings.GetBoolean(u'includeResourceAdapterInfo'):
            self._configConstants.update(self.__GetResourceAdapterInfoConstants())

        # Konvertiert die übergebene Attribute aus der config.xml in ein Dict.
        self.__mapAttrAsConst = self._settings.GetList(u'mapAttributeAsConstant')

    def __GetResourceAdapterInfoConstants(self):
        """
        Stellt eine Verbindung, wenn möglich, zum aktuelle laufendem ResourceAdapter her und liest
        dessen ECU-TEST Plug-in Informationen aus und hängt diese als Konstante an alle TEST-CASES,
        damit die Benutzeransicht vom TEST-GUIDE Monitoring diese auch finden kann.
        @return: Dict mit dem Konstantenschlüssel, sowie dessen Wert.
        @rtype: dict[str]
        """
        locationId = u'TT_ResourceLocationId'
        projectLabel = u'TT_ResourceProjectLabel'

        result = {}
        try:
            # 1 Sekunden maximal warten
            response = requests.get(
                url=u'http://localhost:42042/ResourceAdapter/info/ECU-TEST/',
                timeout=1,
                verify=False)
            # Proxy für Localhost wird nicht benötigt!
            response.raise_for_status()

            jsonResponse = response.json()

            # Wenn Wert nicht gesetzt bzw. bekann, dann nicht übernehmen!
            if len(jsonResponse.get(locationId, u"")) > 0:
                result[locationId] = jsonResponse.get(locationId)

            if len(jsonResponse.get(projectLabel, u"")) > 0:
                result[projectLabel] = jsonResponse.get(projectLabel)

        except BaseException as err:
            # Wenn RA nicht vorhanden, dann keine Exception werfen, nur eine Info loggen
            DPrint(LEVEL_VERBOSE, u'ATX-Mako GetResourceAdapterInfoConstants()', err)
            result = {}

        return result

    def __GetSWKVersion(self, reportApi):
        """
        Ermittelt die verwendete SWK-Version um diese als Konstante bei allen Testfällen zu
        hinterlegen.
        @param reportApi: ReportApi zum Zugriff auf die Report-DB
        @type reportApi: tts.core.report.parser.ReportApi
        @return: verwendete SWK-Version
        @rtype: str or None
        """
        # Report GetSWKVersion ab ECU-TEST 6.5
        if hasattr(reportApi.GetInfo(), u'GetKeywordCatalog'):
            return reportApi.GetInfo().GetKeywordCatalog()
        return None

    def CollectConstants(self, package, atxAttributes, filteredSpecShortName,
                         testManagementTestCaseId, testManagementTestSuiteId, testScriptId):
        # Wenn die Option 'mapAttributeAsConstant' aktiviert ist, werden die Attribute als
        # Konstanten zusätzlich gemappt.
        self.__ConvertAttributesToConstants(atxAttributes)

        constants = []
        # Erfassung der Ids zur Koppelung ans TMS
        if testManagementTestSuiteId is not None:
            TPrint(u'Pgk: {0} -> TMS: TestSuite-Id: {1}',
                   filteredSpecShortName,
                   testManagementTestSuiteId)
            constants.append(Constant(SpecialConstantCategory.ALM_SETTING,
                                      u'TT_TESTSUITE_ID',
                                      testManagementTestSuiteId,
                                      u''))
        if testManagementTestCaseId is not None:
            TPrint(u'Pgk: {0} -> TMS: TestCase-Id: {1}',
                   filteredSpecShortName,
                   testManagementTestCaseId)
            constants.append(Constant(SpecialConstantCategory.ALM_SETTING,
                                      u'TT_TESTCASE_ID',
                                      testManagementTestCaseId,
                                      u''))
        if testScriptId is not None:
            TPrint(u'Pgk: {0} -> TMS: TestScript-Id: {1}',
                   filteredSpecShortName,
                   testScriptId)
            constants.append(Constant(SpecialConstantCategory.ALM_SETTING,
                                      u'TT_TESTSCRIPT_ID',
                                      testScriptId,
                                      u''))

        # Erfassung des Report-Pfades als spezielle Konstante.
        isMapTestReportPathAsConstant = self._settings.GetBoolean(u'mapTestReportPathAsConstant')
        if isMapTestReportPathAsConstant:
            localFilePathTRFLink = u'file:' + pathname2url(self._reportApi.GetDbFile())
            constants.append(Constant(SpecialConstantCategory.REPORT_INFO,
                                      u'TRF-Link',
                                      localFilePathTRFLink,
                                      u''))

        # Special TT constant for the Super-Downloader to enable jumping directly to a package
        constants.append(Constant(SpecialConstantCategory.REPORT_INFO,
                                  u'TT_ECUTEST_REPORT_ID',
                                  str(package.GetReportItemId()),
                                  u''))

        # Alle Konstanten aus der config.xml immer setzen, werden ggf. von den TCF und Report
        # Parametern überschrieben.
        for eachConstKey, eachConstValue in self._configConstants.items():
            constants.append(Constant(SpecialConstantCategory.CONSTANT,
                                      eachConstKey,
                                      eachConstValue,
                                      u''))

        # Konstanten pro Package erfassen, ab ECU-TEST 6.3
        if (hasattr(package, u'GetGlobalConstantsDefinedOnStart') and
            len(package.GetGlobalConstantsDefinedOnStart()) > 0):
            for eachConst in package.GetGlobalConstantsDefinedOnStart():
                constants.append(Constant(SpecialConstantCategory.CONSTANT,
                                          eachConst.GetName(),
                                          eachConst.GetValue(),
                                          eachConst.GetDescription()))

        # Report Projektspezifische Informationen als Konstante übernehmen, ab ECU-TEST 6.4
        if (hasattr(package, u'GetUserDefinedReportData') and
            len(package.GetUserDefinedReportData()) > 0):

            mapUserReportDataToConstant = self._settings.GetBoolean(
                u'mapUserDefinedReportDataAsConstant')
            if mapUserReportDataToConstant:
                for each in self.__GetUserReportDataContainers(package):
                    constants.append(Constant(SpecialConstantCategory.USER_DEFINED_REPORT,
                                              u'{0}{1}'.format(u'TCF_', each.key),
                                              each.value,
                                              each.description))

        # Report SWKVersion als Konstante übernehmen, ab ECU-TEST 6.5
        # SWK-Version die verwendet wird -> kann entsprechend None sein!
        swkVersion = self.__GetSWKVersion(self._reportApi)
        if swkVersion:
            constants.append(Constant(SpecialConstantCategory.REPORT_INFO,
                                      u'SWKVersion',
                                      swkVersion,
                                      u''))

        return constants

    def __ConvertAttributesToConstants(self, atxAttributes):
        """
        Wenn die Option 'mapAttributeAsConstant' gesetzt ist, werden die übergebenen ATX-Attribute
        in zu setzende Konstanten für das Package konvertiert.
        Dabei wird die Config für das Setzen von Konstanten erweitert.
        @param atxAttributes: Attribute mit den Values, die für das Package erfasst wurden.
        @type atxAttributes: dict
        """
        from .GenerateAtxDataSet import GenerateAtxDataSet

        for eachKey, eachValue in atxAttributes.items():
            toCheck = eachKey

            # Überprüfung der Projektattribute mit dem Prefix vornehmen.
            # Die Angabe der __mapAttrAsConst ist ohne Prefix, da der Nutzer nicht Project_I_Stufe
            # angeben wird, falls doch ist auch okay
            if toCheck not in self.__mapAttrAsConst \
                and eachKey.startswith(GenerateAtxDataSet.PRJ_ATT_PREFIX):
                toCheck = eachKey.replace(GenerateAtxDataSet.PRJ_ATT_PREFIX, u"")

            if toCheck in self.__mapAttrAsConst:
                self._configConstants[eachKey] = eachValue

    def __GetUserReportDataContainers(self, package):
        """
        Ermittelt zu jedem Package die enthaltenen UserReportData-Infos, welche als Konstanten im
        ATX erfasst werden.
        @param package: Package Objekt aus der Report API.
        @type package: tts.core.report.parser.Package.Package
        @return: Liste der gefundenen Container
        @rtype:  list<_UserReportDataContainer>
        """
        result = []

        def __CheckKey(key):
            """
            Wenn es einen Fehler bei der Erstellung gab, dann ist im Key eine Fehlermeldung.
            @param key: zu prüfender Key.
            @type key: str
            @return: True, wenn der Key okay ist, sonst False.
            @rtype: bool
            """
            return key not in (u'Fehler im Skript', u'Error in script')

        # Ab ECU-TEST 7.2 verfügbar
        if hasattr(package, u'GetUserReportData'):
            for eachReportKey, eachReportTuple in package.GetUserReportData().items():
                if __CheckKey(eachReportKey):
                    result.append(UserReportData(eachReportKey,
                                                 eachReportTuple[0],
                                                 eachReportTuple[1]))
                else:
                    DPrint(LEVEL_VERBOSE,
                           u'GetUserReportData konnten nicht ermittelt werden!')
        elif hasattr(package, u'GetUserDefinedReportData'):
            for eachReportKey, eachReportValue in package.GetUserDefinedReportData().items():
                if __CheckKey(eachReportKey):
                    result.append(UserReportData(eachReportKey,
                                                 eachReportValue,
                                                 u""))
                else:
                    DPrint(LEVEL_VERBOSE,
                           u'UserDefinedReportData konnten nicht ermittelt werden!')

        return result

    def AppendTestConstantElement(self, scope, constantName, constantCategory,
                                  constantDescription, constantTextValue):
        """
        Fügt dem jeweiligen Scope eine neue globale Konstante hinzu.
        @param scope: Dictonary mit Informationen, welche bei der Verarbeitung in
                        Kind-Knoten benötigt werden. (siehe Kommentar
                        in __CreateNewScopeFromParentScope Methode)
        @type scope: dict
        @param constantName: Name der Konstanten, welche noch in einen ShortName gewandelt wird,
                             falls die Kriterien noch nicht erfüllt sind.
        @type constantName: str
        @param constantCategory: Konstanten-Kategorie zur besserungen Struktuierung.
        @type constantCategory: SpecialConstantCategory
        @param constantDescription: Beschreibung der Konstanten.
        @type constantDescription: str
        @param constantTextValue: Wert der Konstanten.
        @type constantTextValue: str
        """
        constantShortName = FilterShortName(constantName)

        if scope.get(u'testConstantElements') is None:
            scope[u'testConstantElements'] = []

        # Wenn der Konstanten-Wert 'leer' ist, wird die Konstante nicht erfasst - siehe TTSTM-999
        # ggf. Anführungszeichen von Expressions entfernen
        checkTextValue = constantTextValue.strip(u"'")
        checkTextValue = checkTextValue.strip(u'"')
        checkTextValue = checkTextValue.strip()

        # Entfernt die ASCII-Steuerzeichen aus dem Wert, wenn vorhanden!
        checkTextValue = ReplaceAsciiCtrlChars(checkTextValue)

        if not checkTextValue:
            DPrint(LEVEL_VERBOSE,
                   u'Leere Konstante({0}:{1}) ausgespart.'.format(constantShortName,
                                                                  constantTextValue))
            return

        # Prüfe ob Shortname, also Konstante schon bekannt ist, wenn ja, dann überschreiben.
        toRemoveIdx = [
            index for index, each in enumerate(scope[u'testConstantElements'])
            if each.get(u'SHORT-NAME') == constantShortName]
        # Bereits vorhandene Konstante entfernen.
        for eachIndex in toRemoveIdx:
            del scope[u'testConstantElements'][eachIndex]

        # Entfernt die ASCII-Steuerzeichen aus dem Wert, wenn vorhanden!
        cleanConstantTextValue = ReplaceAsciiCtrlChars(constantTextValue)
        constantDescription = ReplaceAsciiCtrlChars(constantDescription)

        # Konstante hinzufügen
        from .GenerateAtxDataSet import GenerateAtxDataSet
        scope[u'testConstantElements'].append(OrderedDict([
            (u'@type', u'TEST-CONSTANT-ELEMENT'),
            (u'SHORT-NAME', constantShortName),
            (u'DESC', {
                u'L-2': {
                    u'@L': u'DE',
                    u'#': constantDescription
                }
            }),
            (u'CATEGORY', constantCategory.name),
            (u'TYPE-REF', {
                u'@DEST': GenerateAtxDataSet.PRIMITIVE_CONSTANT_TYPE[u'@type'],
                u'#': u'/{0}/{1}'.format(GenerateAtxDataSet.DATA_TYPE[u'SHORT-NAME'],
                                         GenerateAtxDataSet.PRIMITIVE_CONSTANT_TYPE[u'SHORT-NAME'])
            }),
            (u'VALUE', {
                u'TEXT-VALUE-SPECIFICATION': {
                    u'VALUE': {
                        u'#': u'{0}'.format(cleanConstantTextValue)
                    }
                }
            }),
        ]))
