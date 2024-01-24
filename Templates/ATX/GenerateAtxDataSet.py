# -*- coding: utf-8 -*-

"""
Created on 07.02.2014

@author: Christoph Groß <christoph.gross@tracetronic.de>
"""

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import fnmatch
import json
import os
import re
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime

from log import DPrint, EPrint, LEVEL_VERBOSE, WPrint

from .GenerateAtxConstants import GenerateAtxConstants, SpecialConstantCategory
from .GenerateRecording import GenerateRecording
from .Config import Config, Settings
from .ProcessPackage import ProcessPackage
from .ScanReportDir import ScanReportDir
from .Utils import (ConvertConditionBlocks, EmptyReportException, FilterSUCCESS, FilterShortName,
                    FilterUniqueShortName, FindDictInList, ATXValidationError,
                    GetExtendedWindowsPath, GetIsoDate, GetNextShortNameInList, GetVerdictWeighting,
                    HashFileContents, IsSkipped, SplitVersionString,
                    ReplaceAsciiCtrlChars, FileToArchive)
from .Version import GetVersion


class ATXData(object):
    """
    Containerklasse für das ATX-Object um daraus die komplette Zip schnüren zu können.
    """
    def __init__(self, atxReport, archiveFiles, reviews, traceFiles, reportRefPaths):
        self.atxReport = atxReport
        self.archiveFiles = archiveFiles
        self.reviews = reviews
        self.traceFiles = traceFiles
        self.reportRefPaths = reportRefPaths


class TestCaseAtxReferences(object):
    """
    Containerklasse speichert die ATX-Referenz-Pfade, diese werden benötigt um
    z.B. archiveMiscFiles zu erfassen, in Abhängigkeit des Package-Ergebnisses.
    """

    def __init__(self, refPath, pkgVerdict):
        """
        @type refPath: str
        @type pkgVerdict: str
        """
        self.refPath = refPath
        self.pkgVerdict = pkgVerdict

    def __eq__(self, other):
        """
        Überschrieben, damit Reference-Pfade einfach verglichen werden können
        """
        if isinstance(other, TestCaseAtxReferences):
            return self.refPath == other.refPath and self.pkgVerdict == other.pkgVerdict
        return NotImplemented

    def __ne__(self, other):
        """
        Überschrieben, damit Reference-Pfade einfach verglichen werden können
        """
        x = self.__eq__(other)
        if x is NotImplemented:
            return NotImplemented
        return not x

    def __hash__(self):
        hashValue = hash((self.refPath, self.pkgVerdict))
        return hashValue


class GenerateAtxDataSet(object):
    """
    Klasse zur Generierung von ATX Dokumenten aus ECU-TEST Reports.
    """

    PRJ_ATT_PREFIX = u'Project_'

    # besonderer Datentyp
    PRIMITIVE_CONSTANT_TYPE = OrderedDict([
        (u'@type', u'APPLICATION-PRIMITIVE-DATA-TYPE'),
        (u'SHORT-NAME', u'ConstType')
    ])

    # ArPackage für besondere Datentypen (bspw. Konstanten)
    DATA_TYPE = OrderedDict([
        (u'@type', u'AR-PACKAGE'),
        (u'SHORT-NAME', u'ApplicationDataTypes'),
        (u'ELEMENTS', [PRIMITIVE_CONSTANT_TYPE]),
        (u'AR-PACKAGES', []),
    ])

    FIND_DEFAULT_VALUE_PARAM_REG_EXP = re.compile(r' \(Default\)')

    def __init__(self, reportApi, firstName, firstDate, isPackageExecution):
        """
        Konstruktor.
        @param reportApi: Oberstes Report Objekt.
        @type reportApi: tts.core.report.parser.ReportApi
        @param firstName: zu erst gefundener Name im reportElement.
        @type firstName: str
        @param firstDate: zu erst gefundenes Datum im reportElement.
        @type firstDate: datetime
        @param isPackageExecution: Handelt es sich um ein PackageReport.
        @type isPackageExecution: bool
        """
        # Import verlagert, damit Unit-Test möglich.
        from application.api.Api import Api

        if not isinstance(isPackageExecution, bool):
            EPrint(u'isPackageExecution ist kein boolscher Wert!')
            return

        self.__report = reportApi
        self.__reportDir = self.__report.GetDbDir()
        self._settings = Settings(reportApi)

        self.__atxDate = firstDate

        self._generateAtxConstants = GenerateAtxConstants(reportApi)

        self.__overrideParamMapping = (
            Config.GetSetting(self.__report, u'overrideParamSetNameMapping') == u'True' and not
        isPackageExecution)

        self.__captureExecutionTime = Config.GetSetting(self.__report,
                                                        u'captureExecutionTime') == u'True'

        self.__useProjectElementName = (
            Config.GetSetting(self.__report,
                              'mapProjectElementNameAsTestCaseName') == u'True' and not
            isPackageExecution)

        self.__convertOnlyPkgTestCase = Config.GetSetting(
            self.__report, u'onlyIncludePkgTestCases') == u'True'
        self.__mapTcfTesterAsConstant = Config.GetSetting(
            self.__report, u'mapTcfTesterAsConstant') == u'True'
        self.__mapTcfInfoToConstant = Config.GetSetting(
            self.__report, u'mapTCFPropertyAsConstant') == u'True'
        self.__mapTbcInfoToConstant = Config.GetSetting(
            self.__report, u'mapTbcToolAsConstant') == u'True'
        self.__maxSubPkgLevel = Config.Cast2Int(
            Config.GetSetting(self.__report, u'mapSubPackageAsTestCaseLevel'), 0)
        self.__mapSeparateProjectExecutionAsSingleTestplan = Config.GetSetting(
            self.__report, u'mapSeparateProjectExecutionAsSingleTestplan') == u'True'

        self.__isMapSwkIdsAsAttribute = Config.GetSetting(
            self.__report, u'mapSwkIdsAsAttribute') == u'True'

        self.__localePackagesDir = Api().GetSetting(u'packagePath')
        self.__workspaceDir = Api().GetSetting(u'workspacePath')

        self.__hasEnv = False
        self.__tcfPath = False
        self.__mappingFiles = []
        self.__tbcPath = False
        self.__pgkCounter = 0
        self.__pkgFiles = []
        self.__reviews = []

        recordingsByAttribute = Config.GetSetting(reportApi, u'archiveRecordings') == u'ByAttribute'
        self.__archive = {
            u'enabled': Config.GetSetting(reportApi, u'enableArchive') == u'True',
            u'trf': Config.GetSetting(reportApi, u'archiveTrf') == u'True',
            u'tcf': Config.GetSetting(reportApi, u'archiveTcf') == u'True',
            u'tbc': Config.GetSetting(reportApi, u'archiveTbc') == u'True',
            u'pkg': Config.GetSetting(reportApi, u'archivePkg') == u'True',
            u'xam': Config.GetSetting(reportApi, u'archiveMapping') == u'True',
            u'mafi': Config.GetSetting(reportApi, u'archiveMapping') == u'True',
            u'recordings': (Config.GetSetting(reportApi, u'archiveRecordings') == u'True' or
                            recordingsByAttribute),
            u'recordingsByAttribute': recordingsByAttribute,
            u'recordingMetadata':
                Config.GetSetting(reportApi, u'archiveRecordingMetadata') == u'True',
            u'plot': Config.GetSetting(reportApi, u'archivePlots') == u'True',
        }
        # Erfassung aller TestCase ATX-Referenzpfade
        self.__reportRefPaths = set()

        self.__uploadPictures = Config.GetSetting(
            self.__report, u'archiveDescriptionImages') == u'True'

        self.__archiveImages = Config.GetSetting(self.__report, u'archiveImages') == u'True'

        self.__archiveFilesPerPackage = Config.GetSetting(reportApi,
                                                          u'archiveFilesPerPackage').strip()

        self.__archiveByVerdicts = self.__GetArchiveByVerdictOption(reportApi)

        self.__archiveRecordingsByAttributes = self._settings.GetDict(
            u'archiveRecordingsByAttributes')

        # Dict der zu setzenden Config.xml Attribute
        self.__configAttributes = self._settings.GetDict(u'setAttributes')

        # Konvertiert die übergebene statischen Review-Tags aus der config.xml in eine Liste
        self.__configReviewTags = self._settings.GetList(u'setReviewTags')

        # Testplan-Namen ermitteln
        firstName = self.__GetProjectName(firstName)

        # Aktiviert die Debug Prints
        self.__DebugEnabled = False

        self.__hashCache = {}

        # Dient als Merkhilfe, um die mehrfache Verwendung eines ShortNames bei TestCases zu
        # vermeiden.
        # Ist ein refPath bereits als Key vorhanden, lässt das den Rückschluß zu, dass es bereits
        # einen Testcase auf der selben Ebene mit dem gleichen ShortName gibt.
        # Der Key hat als Value einen Zähler, der inkrementiert wird, wenn ein neuer TestCase
        # das oben beschriebene Kriterium erfüllt.
        # Der Value wird als Suffix an den ShortName angehängt damit dieser in seiner Ebene
        # eindeutig bleibt.
        self.__refPaths = {}

        # Speichert Projekte mit ihrer Hierarchieebene
        self.__projectCache = {}

        # TestSpec für Spec
        self.__topTestSpec = OrderedDict([
            (u'@type', u'TEST-SPEC'),
            (u'SHORT-NAME', u'TestSpecification'),
            (u'CATEGORY', u'ATX_TEST_SPEC'),
            (u'TEST-OBJECT-REFS', []),
            (u'TEST-ENVIRONMENT-REFS', []),
            (u'TEST-CASES', []),
        ])

        # ArPackage für Spec Daten
        self.__topArPkg = OrderedDict([
            (u'@type', u'AR-PACKAGE'),
            (u'SHORT-NAME', u'TestSpecs'),
            (u'ELEMENTS', [self.__topTestSpec]),
            (u'AR-PACKAGES', []),
        ])

        self.__topArPkgKonfiguration = OrderedDict([
            (u'@type', u'AR-PACKAGE'),
            (u'SHORT-NAME', u'Configurations'),
            (u'ELEMENTS', []),
            (u'AR-PACKAGES', []),
        ])

        self.__ConfigRef = None

        # TestExecutionPlan
        self.__topTestExecutionPlan = OrderedDict([
            (u'@type', u'TEST-EXECUTION-PLAN'),
            # Setzt den ShortName des TestExecutionPlans für PackageReports
            (u'SHORT-NAME', (u'SinglePackageExecution' if isPackageExecution else
                             FilterShortName(firstName))),
            (u'TEST-ENVIRONMENT-REFS', []),
            (u'TEST-OBJECT-REFS', []),
            (u'PLANNED-TEST-CASES', []),
        ])

        # ArPackage für TestExecutionPlans
        self.__topArPTestExecutionPlan = OrderedDict([
            (u'@type', u'AR-PACKAGE'),
            (u'SHORT-NAME', u'TestExecutionPlans'),
            (u'ELEMENTS', [self.__topTestExecutionPlan]),
            (u'AR-PACKAGES', []),
        ])

        # TestSpec für Report Daten
        self.__reportSpec = OrderedDict([
            (u'@type', u'TEST-SPEC'),
            (u'SHORT-NAME', FilterShortName(firstName)),
            (u'CATEGORY', u'ATX_TEST_REPORT'),
            (u'ADMIN-DATA', OrderedDict([
                (u'LANGUAGE', u'DE'),
                (u'DOC-REVISIONS', [
                    OrderedDict([
                        (u'@type', u'DOC-REVISION'),
                        # ,(u'ISSUED-BY', u'John Doe')
                        (u'REVISION-LABEL', u'1.0.0'),
                        (u'STATE', u'IMPLEMENTED'),
                        (u'DATE', self.__GetATXReportDate()),
                    ]),
                ]),
                (u'SDGS', []),
            ])),
            (u'ORIGIN-REF', OrderedDict([
                (u'@DEST', u'TEST-EXECUTION-PLAN'),
                (u'#', u'/{0}/{1}'.format(self.__topArPTestExecutionPlan[u'SHORT-NAME'],
                                          self.__topTestExecutionPlan[u'SHORT-NAME'])),
            ])),
            (u'TEST-OBJECT-REFS', []),
            (u'TEST-ENVIRONMENT-REFS', []),
            (u'TEST-CASES', []),
        ])

        # ArPackage für Report Daten
        self.__reportArPkg = OrderedDict([
            (u'@type', u'AR-PACKAGE'),
            (u'SHORT-NAME', u'TestReports'),
            (u'ELEMENTS', [self.__reportSpec]),
            (u'AR-PACKAGES', []),
        ])

        # ArPackage für Test Parameter
        self.__testData = OrderedDict([
            (u'@type', u'AR-PACKAGE'),
            (u'SHORT-NAME', u'TestData'),
            (u'ELEMENTS', []),
            (u'AR-PACKAGES', []),
        ])

        self.__primitiveConstantType = self.PRIMITIVE_CONSTANT_TYPE
        self.__dataTypes = self.DATA_TYPE

        # Erzeugt das Root ATX Element
        self.__atxBody = OrderedDict([
            (u'CATEGORY', u'STANDARD'),
            (u'ADMIN-DATA', OrderedDict([
                (u'LANGUAGE', u'DE'),
                (u'DOC-REVISIONS', [
                    OrderedDict([
                        (u'@type', u'DOC-REVISION'),
                        # ,(u'ISSUED-BY', u'John Doe')
                        (u'REVISION-LABEL', u'1.0.0'),
                        (u'DATE', self.__GetATXReportDate()),
                    ]),
                ]),
            ])),
            (u'AR-PACKAGES', [
                self.__topArPkg,
                self.__topArPkgKonfiguration,
                self.__topArPTestExecutionPlan,
                self.__testData,
                self.__reportArPkg,
                deepcopy(self.__dataTypes),
            ]),
            (u'SDGS', []),
        ])

        # Eindeutige ID dem Report zuweisen um ggf. über diese den Report
        # zu ersetzen oder zu aktualisieren
        if hasattr(self.__report.GetInfo(), u'GetUUID'):
            self.__atxBody[u'SDGS'].append(OrderedDict([
                (u'@type', u'SDG'),
                (u'@GID', u'DocumentData'),
                (u'SD', {u'@GID': u'UUID', u'#': u'{0}'.format(self.__report.GetInfo().GetUUID())}),
            ]))

        # ATX ApplicationType wird Lazy initialisiert.
        self.__recordingType = None
        self.__parameterType = None

        self.__generateRecording = GenerateRecording(self.__archive, self.__pkgFiles, self.__report,
                                                     self.__workspaceDir, self.__dataTypes,
                                                     self.__primitiveConstantType)

        separateSubProjectExecutionPaths = self.__GetSeparateSubProjectExecutionPaths()

        if len(separateSubProjectExecutionPaths) > 0:
            DPrint(LEVEL_VERBOSE,
                   u'SeparatePrjExecutionAsPlannedTestCaseFolder(): {0}'.
                   format(separateSubProjectExecutionPaths))
            testExecutionPlanPointer = self.__topTestExecutionPlan[u'PLANNED-TEST-CASES']
            self.__SeparatePrjExecutionAsPlannedTestCaseFolder(self.__report,
                                                               separateSubProjectExecutionPaths,
                                                               0, testExecutionPlanPointer)
        else:
            self.__ReportProjectElement(self.__report, {}, 0,
                                        self.__topTestExecutionPlan[u'PLANNED-TEST-CASES'], {})
        # Wenn keine Testcases erzeugt wurden ist der Report überflüssig und wird verworfen
        if len(self.__topTestSpec[u'TEST-CASES']) == 0:
            raise EmptyReportException()

    def __GetArchiveByVerdictOption(self, reportApi):
        """
        Ermittelt aus der Konfig, die Ergebnisse, bei welchen die Daten archiviertw werden sollen.
        @param reportApi: ReportApi zum Zugriff auf die Config
        @type reportApi: tts.core.report.parser.ReportApi
        @return: Liste der Verdicts, für welche die Daten archiviert werden sollen.
        @rtype: list
        """
        archiveBy = u'NONE;PASSED;INCONCLUSIVE;FAILED;ERROR'

        if Config.GetSetting(reportApi, u'archiveBy') is not None:
            archiveBy = Config.GetSetting(reportApi, u'archiveBy').strip(u';')

        result = archiveBy.split(u';')
        DPrint(LEVEL_VERBOSE, u'GetArchiveByVerdictOption(): {0}'.format(result))
        return result

    def __SeparatePrjExecutionAsPlannedTestCaseFolder(self, reportApi,
                                                      separateSubProjectExecutionPaths,
                                                      projectExecLevel,
                                                      testExecutionPlanPointer):
        """
        Erzeugt auf Grundlage der separat ausgeführten Projekte, die PlannedTestCaseFolders, welche
        im Report über die Report-Info-Tabelle abgefragt werden können.
        @param reportApi: ReportApi zum Zugriff auf die Report-DB
        @type reportApi: tts.core.report.parser.ReportApi
        @param separateSubProjectExecutionPaths:
        @type separateSubProjectExecutionPaths: list
        @param projectExecLevel: Indikator für die Hierarchieebene des Elements im Projektbaum.
        @type projectExecLevel: int
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        """
        if len(separateSubProjectExecutionPaths) == 1:
            self.__ReportProjectElement(reportApi, {}, projectExecLevel - 1,
                                        testExecutionPlanPointer, {})
            return

        plannedTestCaseFolderName = separateSubProjectExecutionPaths[0]

        prjExecFolder = self.__CreatePlannedTestCaseFolder(plannedTestCaseFolderName,
                                                           projectExecLevel)
        testExecutionPlanPointer.append(prjExecFolder)
        # Nächste Ebene aufrufen, mit dem Rest der bekanntne Pfade
        self.__SeparatePrjExecutionAsPlannedTestCaseFolder(reportApi,
                                                           separateSubProjectExecutionPaths[1:],
                                                           projectExecLevel + 1,
                                                           prjExecFolder[u'PLANNED-TEST-CASES'])

    def __GetSeparateSubProjectExecutionPaths(self):
        """
        @return: Liste mit den vorangegangenen Projektpfaden, welche durch die separate Ausführung
                 verloren gegangen sind. Beispiel:
                 MasterPrj
                 |- SubPrj1 (sep Execution)
                 |    |----- SubSubPrjA (sep Execution)

                 Bei Ausführung von SubSubPrjA wird der Pfad [SubPrj1,SubSubPrjA] zurückgegeben.
        @rtype: list
        """
        projectPath = self.__GetProjectPath()

        if projectPath is not None:
            paths = projectPath.split(u'/')
            if len(paths) > 1:
                # 'Projekt/subA/subB' -> gibt nur [subA,sbuB] zurück
                return paths[1:]

        return []

    def __GetProjectName(self, currentProjectName):
        """
        Ermittelt über die ReportApi ob der gesetzte Projektname auch der richtige ist, im Falle
        es handelt sich um eine separate SubProjekt-Ausführung.
        @param currentProjectName: momentan gesetzter Name des Projektes, welches ausgeführt wurde.
        @type currentProjectName: str
        @return: Name des Projektes, welches ausgeführt wurde.
        @rtype: str
        """

        projectPath = self.__GetProjectPath()
        if projectPath is None:
            return currentProjectName

        return projectPath.split(u'/')[0]

    def __GetProjectPath(self):
        """
        @return: Gibt den kompletten Projektpfad zurück, dies ist einer Projektausführung die der
                 Name des Projektes und bei einer separaten Projektausführung
                 z.B. MasterProjekt/SubProjekt1 oder None, wenn das Feature für die Abfrage der
                 Projektpfade nicht unterstützt wird.
        @rtype: str or None
        """

        # Wenn explizit gewollt ist, dass separat ausgeführte Unterprojekte als extra Testplan
        # angezeigt werden sollen (diese nicht vom Masterprojekt erben), dann dies hier
        # berücksichtigen.
        if self.__mapSeparateProjectExecutionAsSingleTestplan:
            return None

        reportInfo = self.__report.GetInfo()
        # Feature ab ECU-TEST 6.4
        if hasattr(reportInfo, u'GetProjectExecutionPath'):
            return self.__report.GetInfo().GetProjectExecutionPath()

        return None

    def GetData(self):
        """
        Gibt die erzeugten Daten zurück.
        @return: Erzeugte Daten: ATX Objekt und List der verwendeten Dateien
        @rtype: dict
        """
        if not self.__hasEnv:
            pos = 0
            for index, arp in enumerate(self.__atxBody[u'AR-PACKAGES']):
                if arp[u'SHORT-NAME'] == self.__topArPkgKonfiguration[u'SHORT-NAME']:
                    pos = index
                    break
            self.__atxBody[u'AR-PACKAGES'].pop(pos)

        archiveFiles = [each for each in self.__pkgFiles
                        if each[u'packageVerdict'] in self.__archiveByVerdicts]

        reportRefPaths = set([each.refPath for each in self.__reportRefPaths
                              if each.pkgVerdict in self.__archiveByVerdicts])

        return ATXData(self.__atxBody, archiveFiles, self.__reviews,
                       self.__generateRecording.GetTraceFiles(),
                       reportRefPaths)

    def __GetElementSize(self, elementGenerator):
        """
        Ermittelt die Anzahl der Subelemente des Elements.
        @param elementGenerator: beliebiger Generator
        @type elementGenerator: Generator
        @return: Anzahl Subelemente
        @rtype: int
        """
        return sum([1 for _elem in elementGenerator])

    def __AddFile(self, file, refPath, comment, refPathType, removeFileAfterZipped, packageVerdict):
        """
        Fügt eine Datei für die Archivierung in der Zip Datei hinzu.
        @param file: FileToArchive-Objekt, welches den Pfad zur Datei und ggf. den Originalpfad
            hält, falls die Datei in einen temporären (ATX-)Arbeitsordner kopiert wurde.
        @type file: FileToArchive
        @param refPath: Ref Pfad des Report Testcases, zu dem die Datei gehört.
        @type refPath: str
        @param comment: Upload-Kommentar
        @type comment: str | None
        @param refPathType: ATX-Klasse, welche mit dem RefPath referenziert wird.
        @type refPathType: str
        @param removeFileAfterZipped: True, wenn die übergebene Datei nach dem sie in das Zip
                                      integriert wurde wieder gelöscht werden kann, weil sie nur
                                      eine TEMP-Datei ist, sonst False
        @type removeFileAfterZipped: boolean
        @param packageVerdict: Orginal-Ergebnis des Packages, was zum Filter der Archivdateien
                               verwendet werden kann.
        @type packageVerdict: str
        """
        path = file.GetPath()
        for pkgFile in self.__pkgFiles:
            if pkgFile['file'] == path and pkgFile['ref'] == refPath:
                return
        if file.Exists():
            # Datei muss für das ATX-Archiv auch wirklich existieren
            relPath = file.GetRelPath(self.__reportDir)
            self.__pkgFiles.append({u'file': path,
                                    u'relPath': relPath,
                                    u'ref': refPath,
                                    u'comment': comment,
                                    u'refPathType': refPathType,
                                    u'removeFileAfterZipped': removeFileAfterZipped,
                                    u'packageVerdict': packageVerdict})

    def __AddArchiveFile(self, file, refPath, packageVerdict, comment=None):
        """
        Fügt eine Datei für die Archivierung in der Zip Datei hinzu (pkg, tbc, tcf, ...).
        Führt eine Abgleich der Dateiendung mit den Angaben in der config.xml durch.
        @param file: Datei-Objekt.
        @type file: FileToArchive
        @param refPath: Ref Pfad des Report Testcases, zu dem die Datei gehört.
        @type refPath: str
        @param packageVerdict: Orginal-Ergebnis des Packages.
        @type packageVerdict: str
        @param comment: optionaler Upload-Kommentar
        @type comment: str
        """
        ext = os.path.splitext(file.GetPath())[1][1:]
        if ext in self.__archive and self.__archive[ext]:
            self.__AddFile(file, refPath, comment, u'TEST-CASE', False, packageVerdict)

    def __AddTestStepImageToArchive(self, file, testStepRefPath, packageVerdict):
        """
        Erfasst das hinterlegte Image für eine mögliche Archivierung und TEST-STEP Zuweisung.
        @param file: Datei-Objekt.
        @type file: FileToArchive
        @param testStepRefPath: Ref Pfad des Report Test-Steps, zu dem die Datei gehört.
        @type testStepRefPath: str
        @param packageVerdict: Orginal-Ergebnis des Packages.
        @type packageVerdict: str
        """
        # Nur übernehmen, wenn Image explizit erwünscht!
        if self.__archiveImages:
            self.__AddFile(file, testStepRefPath, None, u'TEST-STEP', True, packageVerdict)

    def __AddTestStepPlotToArchive(self, file, testStepRefPath, packageVerdict):
        """
        Erfasst die hinterlegten Plots für eine mögliche Archivierung und TEST-STEP Zuweisung.
        @param file: Datei-Objekt.
        @type file: FileToArchive
        @param testStepRefPath: Ref Pfad des Report Test-Steps, zu dem die Datei gehört.
        @type testStepRefPath: str
        @param packageVerdict: Orginal-Ergebnis des Packages.
        @type packageVerdict: str
        """
        # Nur übernehmen, wenn Plot explizit erwünscht!
        if self.__archive[u'plot']:
            self.__AddFile(file, testStepRefPath, None, u'TEST-STEP', True, packageVerdict)

    def __AddCfgFiles(self, refPath, packageVerdict):
        """
        Fügt die Config Dateien für die Archivierung in der Zip Datei hinzu.
        @param refPath: Ref Pfad des Report Testcases, zu dem die Datei gehört.
        @type refPath: str
        @param packageVerdict: Orginal-Ergebnis des Packages.
        @type packageVerdict: str
        """
        if self.__hasEnv:
            if self.__tcfPath:
                self.__AddArchiveFile(FileToArchive(self.__tcfPath), refPath, packageVerdict)
            if self.__tbcPath:
                self.__AddArchiveFile(FileToArchive(self.__tbcPath), refPath, packageVerdict)

    def __AddMappingFiles(self, refPath, packageVerdict):
        """
        Fügt die geladenen Mapping-Dateien für die Archivierung in der Zip Datei hinzu.
        @param refPath: Ref Pfad des Report Testcases, zu dem die Datei gehört.
        @type refPath: str
        @param packageVerdict: Orginal-Ergebnis des Packages.
        @type packageVerdict: str
        """
        if self.__hasEnv:
            for each in self.__mappingFiles:
                self.__AddArchiveFile(FileToArchive(each), refPath, packageVerdict)

    def __GetReportConfig(self, config, scope, name=_(u'Konfiguration')):
        """
        Erzeugt aus den Konfigurationsdaten die TestEnvironment Daten.
        @param config: Konfigurations-Objekt aus der ReportApi.
        @type config: ReportApi
        @param scope: Dictonary mit Informationen, welche bei der Verarbeitung in
                        Kind-Knoten benötigt werden. (siehe Kommentar
                        in __CreateNewScopeFromParentScope Methode)
        @type scope: dict
        @return ATX-TestEnvironment Objekt.
        @rtype: dict
        """
        cfgShortName = name
        counter = 0
        while self.__ListHasShortName(cfgShortName, self.__topArPkgKonfiguration[u'ELEMENTS']):
            counter += 1
            cfgShortName = u'{0}_{1}'.format(name, counter)

        cfg = OrderedDict([
            (u'@type', u'TEST-ENVIRONMENT-SET'),
            (u'SHORT-NAME', cfgShortName),
            (u'TEST-ENVIRONMENTS', []),
        ])
        if config.HasTestBenchConfiguration():
            testBench = config.GetTestBenchConfiguration()
            self.__tbcPath = testBench.GetPath()

            if not self.__tbcPath:
                WPrint(_(u'Der TBC-Dateipfad konnte nicht ermittelt werden.'))
            else:
                self.__hasEnv = True
                tbcFileName = os.path.basename(self.__tbcPath)
                if len(tbcFileName) > 255:
                    WPrint(_(u"Der Name der {0} Datei '{1}' ist länger als 255 Zeichen.\n"
                             u"Dies führt zu einer Beschränkung in der Suche nach Testumgebungen in"
                             u" TEST-GUIDE.").format(u'TBC', tbcFileName))
                cfg[u'TEST-ENVIRONMENTS'].append(OrderedDict([
                    (u'@type', u'TEST-ENVIRONMENT'),
                    (u'SHORT-NAME', u'TBC'),
                    (u'LONG-NAME', {
                        u'L-4': {
                            u'@L': u'DE',
                            u'#': tbcFileName
                        }
                    }),
                    (u'DESC', {
                        u'L-2': {
                            u'@L': u'DE',
                            u'#': self.__tbcPath
                        }
                    }),
                ]))

            # TBC Informationen als Constante erfassen, wenn gewünscht.
            if (self.__mapTbcInfoToConstant and
                hasattr(testBench, u'IterTools')):

                for eachTool in testBench.IterTools():
                    if eachTool.GetStatus() in (u'ON',):

                        def ExtractOnlyLocation(location):
                            '''
                            Aus dem Location-String die eigentliche Location ermitteln.
                            @param location: Location der Form: local (2020.4.105605+9f5971e 64bit)
                            @type location: str
                            @return: eigentliche Location am Beispiel hier ist das Ergebnis: local
                            @rtype: str
                            '''
                            result = ""
                            if location:
                                result = location.split("(", -1)
                                if len(result) > 1:
                                    result = result[0].strip()
                            return result

                        tbcValue = u"{0}{1}".format(eachTool.GetVersion()
                                                    if eachTool.GetVersion()
                                                    else u'unknown-version',
                                                    u" ({0})".format(ExtractOnlyLocation(
                                                        eachTool.GetLocation()))
                                                    if eachTool.GetLocation()
                                                    else u"")

                        self._generateAtxConstants.AppendTestConstantElement(
                            scope,
                            u'TBC_TOOL_{0}'.format(eachTool.GetName()),
                            SpecialConstantCategory.TBC_INFO,
                            u'TBC tool setting',
                            tbcValue)


        if config.HasTestConfiguration():

            # Testbench mit erfassen
            if self.__mapTcfInfoToConstant:
                testStand = self.__report.GetInfo().GetTeststand()
                if testStand:
                    self._generateAtxConstants.AppendTestConstantElement(
                        scope,
                        u'TCF_HOSTNAME',
                        SpecialConstantCategory.TCF_INFO,
                        u'TCF: Name of the host',
                        testStand)

            testConfig = config.GetTestConfiguration()

            # Wenn gewünscht, Tester als Konstante erfassen.
            if self.__mapTcfTesterAsConstant:

                author = testConfig.GetEditor()
                if author:
                    self._generateAtxConstants.AppendTestConstantElement(
                        scope,
                        u'TCF_TESTER',
                        SpecialConstantCategory.TCF_INFO,
                        u'TCF: Name of tester',
                        author)

            self.__tcfPath = testConfig.GetPath()
            if not self.__tcfPath:
                WPrint(_(u'Der TCF-Dateipfad konnte nicht ermittelt werden.'))
            else:
                self.__hasEnv = True
                tcfFileName = os.path.basename(self.__tcfPath)
                if len(tcfFileName) > 255:
                    WPrint(_(u"Der Name der {0} Datei '{1}' ist länger als 255 Zeichen.\n"
                             u"Dies führt zu einer Beschränkung in der Suche nach Testumgebungen in"
                             u" TEST-GUIDE.").format(u'TCF', tcfFileName))
                cfg[u'TEST-ENVIRONMENTS'].append(OrderedDict([
                    (u'@type', u'TEST-ENVIRONMENT'),
                    (u'SHORT-NAME', u'TCF'),
                    (u'LONG-NAME', {
                        u'L-4': {
                            u'@L': u'DE',
                            u'#': tcfFileName
                        }
                    }),
                    (u'DESC', {
                        u'L-2': {
                            u'@L': u'DE',
                            u'#': self.__tcfPath
                        }
                    }),
                ]))

                # TCF Informationen als Constante erfassen, wenn gewünscht.
                if (self.__mapTcfInfoToConstant and
                    hasattr(testConfig, u'IterEcuConfigurations') and
                    self.__GetElementSize(testConfig.IterEcuConfigurations()) > 0):

                    for eachTcfEcu in testConfig.IterEcuConfigurations():
                        ecuName = eachTcfEcu.GetTcfEcuId()

                        # Ignore Leerstring
                        if eachTcfEcu.GetA2lFile():
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_A2L_{0}'.format(ecuName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF A2L File',
                                os.path.basename(
                                    eachTcfEcu.GetA2lFile()))

                        # Ignore Leerstring
                        if eachTcfEcu.GetHexFile():
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_HEX_{0}'.format(ecuName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF Hex File',
                                os.path.basename(eachTcfEcu.GetHexFile()))
                        # Ignore Leerstring
                        if eachTcfEcu.GetSgbd():
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_SGBD_{0}'.format(ecuName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF SGBD File',
                                os.path.basename(eachTcfEcu.GetSgbd()))

                            # kommt ggf. immer unbekannt zurück.
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_SGBD_VERSION_{0}'.format(ecuName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF SGBD File version',
                                eachTcfEcu.GetSgbdVersion())

                        # Ignore Leerstring
                        if hasattr(eachTcfEcu, u'GetElfs') and eachTcfEcu.GetElfs():

                            # es kann mehrere ELF-Dateien geben, welche durch ; zurückgegeben werden
                            # Beispiel: APPLICATION: Data\test.elf; BOOT: Data\second.elf
                            for eachElf in eachTcfEcu.GetElfs().split(u';'):
                                # Bsp.: APPLICATION: Data\test.elf
                                # bzw. APPLICATION: c:\Data\test.elf
                                elfLabel, elfFile = eachElf.split(u':', 1)

                                self._generateAtxConstants.AppendTestConstantElement(
                                    scope,
                                    u'TCF_ELF_{0}_{1}'.format(elfLabel, ecuName),
                                    SpecialConstantCategory.TCF_INFO,
                                    u'TCF ELF File',
                                    os.path.basename(elfFile.strip()))
                            # Ignore Leerstring
                            if eachTcfEcu.GetDebugHex():
                                self._generateAtxConstants.AppendTestConstantElement(
                                    scope,
                                    u'TCF_DEBUG_HEX_{0}'.format(ecuName),
                                    SpecialConstantCategory.TCF_INFO,
                                    u'TCF DEBUG HEX File',
                                    os.path.basename(eachTcfEcu.GetDebugHex()))

                if (self.__mapTcfInfoToConstant and
                    hasattr(testConfig, u'IterBusConfigurations') and
                    self.__GetElementSize(testConfig.IterBusConfigurations()) > 0):

                    for eachTcfBus in testConfig.IterBusConfigurations():
                        busName = eachTcfBus.GetTcfBusId()
                        fbxChannel = eachTcfBus.GetFbxChn()
                        # Ignore Leerstring
                        if eachTcfBus.GetDbPath():
                            busValue = u"{0}{1}".format(os.path.basename(eachTcfBus.GetDbPath()),
                                                        (u" ({0})".format(fbxChannel)
                                                         if fbxChannel else ""))
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_BUS_{0}'.format(busName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF BUS File',
                                busValue)

                if (self.__mapTcfInfoToConstant and
                    hasattr(testConfig, u'IterEfsConfigurations') and
                    self.__GetElementSize(testConfig.IterEfsConfigurations()) > 0):

                    for eachTcfFiu in testConfig.IterEfsConfigurations():
                        fiuName = eachTcfFiu.GetTcfEfsId()
                        # Ignore Leerstring
                        if eachTcfFiu.GetDb():
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_FIU_{0}'.format(fiuName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF FIU File',
                                os.path.basename(eachTcfFiu.GetDb()))

                if (self.__mapTcfInfoToConstant and
                    hasattr(testConfig, u'IterModelConfigurations') and
                    self.__GetElementSize(testConfig.IterEcuConfigurations()) > 0):

                    for eachTcfModel in testConfig.IterModelConfigurations():
                        modelName = eachTcfModel.GetTcfModelId()
                        modelPath = eachTcfModel.GetModel()

                        # Ignore Leerstring
                        if modelName and modelPath:
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                u'TCF_MODEL_{0}'.format(modelName),
                                SpecialConstantCategory.TCF_INFO,
                                u'TCF Model File', modelPath)

                if (hasattr(testConfig, u'HasConstConfigurations') and
                    callable(getattr(testConfig, u'HasConstConfigurations')) and
                    testConfig.HasConstConfigurations()):
                    if self.__GetElementSize(testConfig.IterConstConfigurations()) > 0:
                        for constConfig in testConfig.IterConstConfigurations():
                            self._generateAtxConstants.AppendTestConstantElement(
                                scope,
                                constConfig.GetId(),
                                SpecialConstantCategory.CONSTANT,
                                constConfig.GetDescription(),
                                constConfig.GetValue())

                # Neue Mapping-Files erfassen
                self.__mappingFiles = []
                for eachMappingFile in testConfig.IterMappingFiles():
                    fullMappingFilePath = os.path.join(self.__workspaceDir, eachMappingFile)
                    self.__mappingFiles.append(fullMappingFilePath)

        if self.__hasEnv:
            return cfg

        return False

    def __GetTestManagementIdFormItem(self, item):
        """
        Ermittelt ob es auf diesem übergebenen Item die Möglichkeit gibt eine TestManagementId
        abzufragen, wenn nicht, wird None zurückgegeben.
        Dient zum Auslesen der Projekt- sowie der TestCase-Testmanagement-Ids.
        @param item: Item, aus welchem die Ids ausgelesen werden sollen.
        @type item: lib.report.parser.ReportProjectElement.ReportProjectElement
        @return: die jeweilige verknüpfte Testmanagement-ID oder None
        @rtype: str or None
        """
        result = None

        if hasattr(item, u'GetTestManagementId'):
            result = item.GetTestManagementId()

        return result

    def __GetTestScriptIdFormItem(self, item):
        """
        Ermittelt ob es auf diesem übergebenen Item die Möglichkeit gibt eine TestSkriptId
        abzufragen, wenn nicht, wird None zurückgegeben.
        @param item: Item, aus welchem die Ids ausgelesen werden sollen.
        @type item: tts.core.report.parser.Package.Package
        @return: die jeweilige verknüpfte TestSkript-ID oder None
        @rtype: str or None
        """
        result = None

        if hasattr(item, u'GetTestScriptId'):
            result = item.GetTestScriptId()

        return result

    def __ReportPackage(self, package, scope, testExecutionPlanPointer, projectAttributes,
                        testManagementTestSuiteId, pkgLevel=0):
        """
        Erstellt für das Package die ATX Elemente.
        @param package: Package.
        @type package: ReportApi
        @param scope: Dictonary mit Informationen, welche bei der Verarbeitung in
                      Kind-Knoten benötigt werden. (siehe Kommentar in
                      __CreateNewScopeFromParentScope Methode)
        @type scope: dict
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @param testManagementTestSuiteId: Bei einer Koppelung an ein TMS-System wird zu einem
                                          Testfall die dazugehörige TestSuite-Id übergeben.
        @type testManagementTestSuiteId: str
        @param pkgLevel: Tiefe in der sich ein SubPackage relativ vom MainPackage befindet
        @type pkgLevel: int
        """

        # Wenn die Option gesetzt ist nur Packages, welches als Testfall gekennzeichnet
        # sind zu erfassen, dann dies hier überprüfen bevor ein Package in ATX-TestCase
        # gewandelt wird.
        if self.__convertOnlyPkgTestCase and not package.GetIsTestcase():
            return

        testManagementTestCaseId = self.__GetTestManagementIdFormItem(package)
        testScriptId = self.__GetTestScriptIdFormItem(package)

        refPath, dummy = self.__ConvertPkgToTestCase(package, False, scope,
                                                     testExecutionPlanPointer,
                                                     projectAttributes,
                                                     testManagementTestSuiteId,
                                                     testManagementTestCaseId,
                                                     testScriptId,
                                                     pkgLevel=pkgLevel)
        if refPath is not None:
            self.__ConvertPkgToPlannedTestCase(package, False, testExecutionPlanPointer, refPath)

    def __ReportPackageSet(self, packageSet, scope, testExecutionPlanPointer, projectAttributes,
                           testManagementTestSuiteId):
        """
        Erstellt für ein PackageSet die ATX Elemente.
        @param packageSet: PackageSet.
        @type packageSet: ReportApi
        @param scope: Dictonary mit Informationen, welche bei der Verarbeitung in
                      Kind-Knoten benötigt werden. (siehe Kommentar in
                      __CreateNewScopeFromParentScope Methode)
        @type scope: dict
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @param testManagementTestSuiteId: Bei einer Koppelung an ein TMS-System wird zu einem
                                          Testfall die dazugehörige TestSuite-Id übergeben.
        @type testManagementTestSuiteId: str
        @return: True, wenn im übergebenen PackageSet auch Kindelemente gefunden wurden,
                 sonst false.
        @rtype: boolean
        """
        testCasePointer = None
        refPath = None
        hasChilds = False
        for pkgItem in packageSet.IterItems():
            hasChilds = True

            if pkgItem.__class__.__name__ == u'Package':

                # Wenn die Option gesetzt ist nur Packages, welches als Testfall gekennzeichnet
                # sind zu erfassen, dann dies hier überprüfen bevor ein Package in ATX-TestCase
                # gewandelt wird.
                if self.__convertOnlyPkgTestCase and not pkgItem.GetIsTestcase():
                    continue

                testManagementTestCaseId = self.__GetTestManagementIdFormItem(pkgItem)
                testScriptId = self.__GetTestScriptIdFormItem(pkgItem)

                refPath, testCasePointer = self.__ConvertPkgToTestCase(pkgItem, True, scope,
                                                                       testExecutionPlanPointer,
                                                                       projectAttributes,
                                                                       testManagementTestSuiteId,
                                                                       testManagementTestCaseId,
                                                                       testScriptId,
                                                                       refPath, testCasePointer)

                if self.__overrideParamMapping and refPath is not None:
                    self.__ConvertPkgToPlannedTestCase(pkgItem, True, testExecutionPlanPointer,
                                                       refPath)
                    refPath = None
                    testCasePointer = None

                if not refPath:
                    continue

                self.__ConvertPkgToPlannedTestCase(pkgItem, True, testExecutionPlanPointer,
                                                   refPath)
            else:
                hasChilds = self.__ReportVariation(pkgItem, scope, testExecutionPlanPointer,
                                                   projectAttributes, testManagementTestSuiteId)

        return hasChilds

    def __MergeTestSteps(self, target, source):
        """
        Fügt die Steps der source Liste an das Ende der target Liste an.
        @param target: Liste die erweitert wird.
        @type target: list
        @param source: Liste mit neuen Steps, die angefügt werden.
        @type source: list
        """
        target[u'setup'].extend(source[u'setup'])
        target[u'execution'].extend(source[u'execution'])
        target[u'teardown'].extend(source[u'teardown'])
        target[u'reportSteps'][u'setup'].extend(source[u'reportSteps'][u'setup'])
        target[u'reportSteps'][u'execution'].extend(source[u'reportSteps'][u'execution'])
        target[u'reportSteps'][u'teardown'].extend(source[u'reportSteps'][u'teardown'])

    def __ConvertPkgToTestCase(self, package, isParameterSetElement, scope,
                               testExecutionPlanPointer, projectAttributes,
                               testManagementTestSuiteId, testManagementTestCaseId, testScriptId,
                               refPath=None, testCasePointer=None, pkgLevel=0):
        """
        Konvertiert das übergebene Package zu ATX-TestCase.
        @param package: zu konvertierendes Package.
        @type package: ReportApi
        @param isParameterSetElement: True, wenn es sich um ein Parametersatz-Projekt-Element
                                      handelt, sonst False.
        @type isParameterSetElement: boolean
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @param testManagementTestSuiteId: Bei einer Koppelung an ein TMS-System wird zu einem
                                          Testfall die dazugehörige TestSuite-Id übergeben.
        @type testManagementTestSuiteId: str or None
        @param testManagementTestCaseId: Bei einer Koppelung an ein TMS-System wird zu einem
                                         Testfall die dazugehörige TestCase-Id übergeben.
        @type testManagementTestCaseId: str or None
        @param testScriptId: Bei einer Koppelung an ein TMS-System wird zu einem
                             Testfall die dazugehörige TestSkript-Id übergeben.
        @type testScriptId: str or None
        @param refPath: REF Pfad des zugehörigen TestCases.
        @type refPath: str
        @param testCasePointer: Der bereits bekannte TestCase. Wird ggf. um fehlende TestSteps
                                ergänzt.
        @type testCasePointer: OrderedDict
        @param pkgLevel: Tiefe in der sich ein SubPackage relativ vom MainPackage befindet
        @type pkgLevel: int
        @return: REF-Pfad für den erzeugten TestCase., der bereits bekannte testCasePointer
        @rtype: str, testCasePointer
        """
        # Import verlagert, damit Unit-Tests möglich sind.
        from .TraceAnalysisJob import TraceAnalysisJob
        from application.api.Api import Api

        localScope = self.__CreateNewScopeFromParentScope(scope)

        # relativen Pfad aus dem Pkg Pfad extrahieren => Annahme: 'Packages' ist das
        # Root Verzeichnis im Workspace
        relPath = self.__SplitPkgPath(package.GetPath())
        if relPath is None:
            # etwas stimmt nicht mit dem Pkg, es hat keinen Pfad ...
            return None, None

        filteredSpecShortName = self.__GetName(package, True, isParameterSetElement)

        refRelPathFromPkgPath = filteredSpecShortName

        if len(relPath) > 0:
            relPathShortName = u'/'.join([FilterShortName(each) for each in relPath.split(u'/')])
            refRelPathFromPkgPath = u'{0}/{1}'.format(relPathShortName, filteredSpecShortName)

        if refPath is None:
            refPath = u'/{0}/{1}/{2}'.format(self.__topArPkg[u'SHORT-NAME'],
                                             self.__topTestSpec[u'SHORT-NAME'],
                                             refRelPathFromPkgPath)

        addPkgSpec = False
        if refPath in self.__refPaths:
            # Wenn der RefPath bereits bekannt ist, muss das Pkg nicht nochmal in die
            # Spezifikation übernommen werden,
            # dennoch muss sicher gestellt werden, dass keine Steps verloren gehend (bspw.
            # durch Return Statements)
            # Der ShortName des TestCase wird durch den Zähler erweitert.
            filteredReportShortName = FilterUniqueShortName(filteredSpecShortName,
                                                            self.__refPaths[refPath][u'count'])
            # Der Zähler wird erhöht
            self.__refPaths[refPath][u'count'] += 1
            testCasePointer = self.__refPaths[refPath][u'testCaseSpecPointer']
        else:
            addPkgSpec = True
            # Der ShortName wird initial mit einem Zähler '0' erweitert
            filteredReportShortName = FilterUniqueShortName(filteredSpecShortName, 0)
            # Den Zähler initialisieren
            self.__refPaths[refPath] = {u'count': 1,
                                        u'testCaseReportSpecPointer': None,
                                        u'testCaseSpecPointer': None}

        processedPackage = ProcessPackage(self.__report, refPath)
        processedPackage.ConvertPkg(self.__report, package)
        packageData = processedPackage.GetConvertedPkg()

        # Prüfen, ob das Package verwertbare Inhalte geliefert hat (Testblöcke etc.)
        traceJobs = processedPackage.GetTraceJobs()
        if not packageData:
            packageData = {
                u'setup': [],
                u'execution': [],
                u'teardown': [],
                u'reportSteps': {
                    u'setup': [],
                    u'execution': [],
                    u'teardown': []
                }
            }

            if package.HasTraceAnalyses():
                job = TraceAnalysisJob(package.GetTraceAnalyses(), refPath, self.__report)
                cjob = job.GetConvertedJob()
                if cjob:
                    traceJobs.append(job)
                    self.__MergeTestSteps(packageData, ConvertConditionBlocks(cjob[u'testSteps'],
                                                                              cjob[u'reportSteps']))
            elif package.HasAnalysisJobs(True):
                for analysisJobItem in package.IterAnalysisJobs(True):
                    job = TraceAnalysisJob(analysisJobItem, refPath, self.__report)
                    cjob = job.GetConvertedJob()
                    if cjob:
                        traceJobs.append(job)
                        self.__MergeTestSteps(packageData,
                                              ConvertConditionBlocks(cjob[u'testSteps'],
                                                                     cjob[u'reportSteps']))

            else:
                WPrint(_(u'Leeres Package: {0} in {1}').format(package.GetName(),
                                                               self.__report.GetDbFile()))

        if not testCasePointer:

            specPkg = OrderedDict([
                (u'@type', u'TEST-CASE'),
                (u'SHORT-NAME', filteredSpecShortName),
                (u'DESC', {
                    u'L-2': {
                        u'@L': u'DE',
                        u'#': package.GetDescription()
                    }
                }),
                (u'TEST-CASE-ATTRIBUTES', []),  # Spec keine Attribute mehr zuweisen!
                (u'TEST-OBJECT-REFS', []),
                (u'TEST-ENVIRONMENT-REFS', []),
                (u'ARGUMENT-LIST', []),
                (u'TEST-CONSTANTS', []),  # Spec nie Konstanten zuweisen!
                (u'TEST-SETUP-STEPS', []),
                (u'TEST-EXECUTION-STEPS', []),
                (u'TEST-TEARDOWN-STEPS', []),
            ])

            if self.__hasEnv:
                specPkg[u'TEST-ENVIRONMENT-REFS'].append(self.__ConfigRef.copy())

            if self.__refPaths[refPath][u'testCaseSpecPointer'] is None:
                self.__refPaths[refPath][u'testCaseSpecPointer'] = specPkg

            if addPkgSpec:
                # Fügt das specPkg zur Testspec hinzu, der übergebene Pfad dient der Zuordnung
                # der Hierarchie
                testCasePointer = self.__AddPkgToSpec(self.__topTestSpec[u'TEST-CASES'],
                                                      relPath, specPkg)

        # Attribute erfassen

        # Alle Attribute aus der config.xml immer setzen, werden ggf. von den TCF und Report
        # Parametern überschrieben.

        delimiterSetting = Config.GetSetting(self.__report, u'attributeDelimiter')

        for eachAttrKey, eachAttrValue in self.__configAttributes.items():
            sdg = self._GetATXAttributeFormat(
                eachAttrKey,
                eachAttrValue,
                False,
                delimiterSetting)
            localScope[u'testCaseAttributeElements'][u'SDGS'].append(sdg)

        # TestCase Attribute ermitteln
        atxAttributes = self.__CreateTestCaseAttributes(
            package,
            localScope[u'testCaseAttributeElements'],
            projectAttributes)

        # SWK-Ids als Attribut erfassen
        if self.__isMapSwkIdsAsAttribute:
            swkIds = processedPackage.GetSwkIds()
            if swkIds:
                # Values als Komma-Liste für den Auto-Split übergeben
                swkIdsValues = ','.join(swkIds)
                sdg = self._GetATXAttributeFormat(
                    u'TT_SWK_ID',
                    swkIdsValues,
                    False,
                    delimiterSetting)
                localScope[u'testCaseAttributeElements'][u'SDGS'].append(sdg)

        constants = self._generateAtxConstants.CollectConstants(
            package, atxAttributes, filteredSpecShortName, testManagementTestCaseId,
            testManagementTestSuiteId, testScriptId)

        for constant in constants:
            self._generateAtxConstants.AppendTestConstantElement(
                localScope, constant.name, constant.category, constant.description,
                constant.textValue)

        # Erzeugung des Report TestCase, analoge Struktur wie specPkg
        reportPkg = OrderedDict([
            (u'@type', u'TEST-CASE'),
            (u'SHORT-NAME', filteredReportShortName),
            (u'DESC', {
                u'L-2': {
                    u'@L': u'DE',
                    u'#': package.GetDescription()
                }
            }),
            (u'ADMIN-DATA', OrderedDict([
                (u'DOC-REVISIONS', [
                    OrderedDict([
                        (u'@type', u'DOC-REVISION'),
                        (u'REVISION-LABEL', u'1.0.0'),
                        (u'DATE', self.__GetLatestReportDate(package)),
                    ]),
                ]),
            ])),
            (u'VERDICT-RESULT', {
                u'VERDICT': FilterSUCCESS(package.GetOriginalResult())
            }),
            (u'EXECUTION-TIME', self.__GetExecutionTimeInSec(package)),
            (u'ORIGIN-REF', {
                u'@DEST': u'TEST-CASE',
                u'#': refPath
            }),
            (u'TEST-CASE-ATTRIBUTES', deepcopy(localScope[u'testCaseAttributeElements'])),
            (u'TEST-OBJECT-REFS', []),
            (u'TEST-ENVIRONMENT-REFS', []),
            (u'ARGUMENT-LIST', None),
            (u'TEST-CONSTANTS', deepcopy(localScope[u'testConstantElements'])),
            (u'TEST-SETUP-STEPS', packageData[u'reportSteps'][u'setup']),
            (u'TEST-EXECUTION-STEPS', packageData[u'reportSteps'][u'execution']),
            (u'TEST-TEARDOWN-STEPS', packageData[u'reportSteps'][u'teardown']),
        ])

        # Aufnahmen erfassen
        self.__generateRecording.CreateRecordings(package, reportPkg)

        # Input und Output Parameter erfassen
        parameters = self.__DetectParameters(package)

        if len(parameters) > 0:
            self.__CreateTestArgumentElementsFromPkgParameters(reportPkg, parameters)

        # Pointer zum ERSTEN TestCase mit Ergebnissen merken
        if not self.__refPaths[refPath][u'testCaseReportSpecPointer']:
            self.__refPaths[refPath][u'testCaseReportSpecPointer'] = reportPkg

        if self.__hasEnv:
            reportPkg[u'TEST-ENVIRONMENT-REFS'].append(self.__ConfigRef.copy())

        self.__AddPkgToSpec(self.__reportSpec[u'TEST-CASES'], relPath, reportPkg)
        self.__pgkCounter += 1

        # RefPath steht erst hier zur Verfügung!
        reportRefPath = self.__GetReportRefPath(reportPkg[u'SHORT-NAME'], refPath)
        if self.__archive[u'enabled']:

            pkgResult = package.GetOriginalResult()

            self.__reportRefPaths.add(TestCaseAtxReferences(reportRefPath, pkgResult))

            # Option: archiveFilesPerPackage -> Dateien pro Testfall einsammeln
            # Default für SinglePackage Execution
            reportPackageFolder = self.__reportDir

            # Unklar, warum diese Methode den Ordner im Testreport-Folder liefert
            # bei der Projektausführung
            packageFolder = package.GetAdditionalInfo()
            if packageFolder:
                reportPackageFolder = os.path.join(self.__reportDir, packageFolder)

            if os.path.exists(reportPackageFolder):
                excludedFiles = self.__generateRecording.GetTraceFiles() if Config.GetSetting(
                    self.__report, u'archiveFilesExcludeRecordings').strip() == u'True' else []

                for each in ScanReportDir(self.__report, Api(),
                                          reportPackageFolder,
                                          self.__archiveFilesPerPackage,
                                          excludedFiles
                                          ).GetScannedFiles():
                    self.__AddFile(FileToArchive(each), reportRefPath, u'', u'TEST-CASE', False,
                                   pkgResult)

            # Package selbst einsammeln
            self.__AddArchiveFile(FileToArchive(package.GetPath()), reportRefPath, pkgResult)

            # Bilder aus Package-Beschreibung übernehmen
            self.__AddImagesFromPackageDesc(package, pkgResult, reportPkg, reportRefPath)

            # Bilder aus den MultiMedia TestSteps übernehmen
            self.__AddImagesFromMultimediaTestSteps(pkgResult, processedPackage, reportRefPath)

            if self.__CheckArchiveRecording(atxAttributes):
                traceFiles = self.__generateRecording.MakeTraceFileArchiveFiles() \
                             + self.__generateRecording.MakeTraceMetadataArchiveFiles()

                for traceFile in traceFiles:
                    self.__AddFile(traceFile, reportRefPath, u'', u'TEST-CASE',
                                   removeFileAfterZipped=False, packageVerdict=pkgResult)

            # Package Nachbewertungskommentar mit erfassen!
            reportComments = []

            # Nachbewertungen des Packages ermitteln
            reportComments.extend(list(self.__report.IterUserComments(package.
                                                                      GetReportItemId())))

            # Nachbewertungen der TestSteps ermitteln
            for eachStepInPkg in package.GetTestCase().IterTestSteps():
                reportComments.extend(list(self.__report.IterUserComments(eachStepInPkg.
                                                                          GetReportItemId())))

            comment = None
            if reportComments:
                comment = u''
                for eachComment in reportComments:
                    timeLabel = time.strftime(u'%d.%m.%Y %H:%M', time.localtime(eachComment.
                                                                                GetTimestamp()))
                    comment = u'{0}{1} {2} [{3}] {4}\n'.format(comment,
                                                               timeLabel,
                                                               eachComment.GetAuthor(),
                                                               eachComment.GetOverriddenResult(),
                                                               eachComment.GetText())

            self.__AddArchiveFile(FileToArchive(self.__report.GetDbFile()),
                                  reportRefPath, pkgResult, comment)
            self.__AddCfgFiles(reportRefPath, pkgResult)
            self.__AddMappingFiles(reportRefPath, pkgResult)

            # Die ermittelten Plots für das Archiv bereitstellen
            for eachTJ in traceJobs:
                for eachTSReportRef, plots in eachTJ.GetTestStepPlots().items():
                    reportRef = self.__CreateFullTestStepRefPath(reportRefPath,
                                                                 eachTSReportRef)
                    if reportRef and len(reportRef) > 0:
                        for eachPlot in plots:
                            self.__AddTestStepPlotToArchive(FileToArchive(eachPlot),
                                                            reportRef,
                                                            pkgResult)

        # Reviews übernehmen
        self.__reviews.extend(processedPackage.GetReviews(reportRefPath))

        for tj in traceJobs:
            self.__reviews.extend(tj.GetReviews(reportRefPath))

        # SubPackages als Testfälle erfassen
        subPkgLevel = pkgLevel + 1
        if subPkgLevel <= self.__maxSubPkgLevel:
            for subPackage in processedPackage.GetSubPackages():
                self.__ReportPackage(subPackage, localScope, testExecutionPlanPointer,
                                     projectAttributes, testManagementTestSuiteId, subPkgLevel)

        # Erstes Review überprüfen, ob ggf. die veränderte Package-Bewertung für das Review
        # gelten sollte, wenn eine Nachbewertung stattgefunden hat!
        # Wenn aktuellste Nachbewertung besser ist als die Package-Bewertung, dann die
        # Package-(Nach-)Bewertung übernehmen
        packageAtxResult = FilterSUCCESS(package.GetResult())

        # TTSTM-5411: Falls kein Verdict gesetzt ist, mit einer Exception abbrechen
        if packageAtxResult is None:
            raise ATXValidationError(u"The package '{0}' has no evaluation! Processing the ATX "
                                     u"report cannot continue because a evaluation is a required "
                                     u"field.".format(filteredReportShortName))

        for eachReview in self.__reviews:
            # Static Review-Tags zuweisen
            for eachTag in self.__configReviewTags:
                eachReview.AddReviewTag(eachTag)

            # Nur für Reviews für das gleiche Package die Ergebnisanpassung vornehmen.
            if reportRefPath == eachReview.GetTestCaseRef():
                # Wenn eine Nachbewertung vorhanden ist und nicht nur ein Kommentar, dann prüfen...
                if (eachReview.GetRevaluationVerdict() and
                    GetVerdictWeighting(eachReview.GetRevaluationVerdict()) <
                    GetVerdictWeighting(packageAtxResult)):
                    eachReview.SetRevaluationVerdict(packageAtxResult)

        return refPath, testCasePointer

    def __AddImagesFromPackageDesc(self, package, pkgResult, reportPkg, reportRefPath):
        """
        Fügt Bilder der Packagebeschreibung hinzu.
        :type package:
        :type pkgResult: str
        :type reportPkg:
        :type reportRefPath: str
        """
        if self.__uploadPictures:
            desc = package.GetDescription()
            desc = "" if not desc else desc
            matches = re.finditer(r'<img[^>]+src=(?:\'|")([^"\']+)(?:\'|")',
                                  desc,
                                  re.IGNORECASE | re.MULTILINE)
            discoveries = []
            for match in matches:
                path = GetExtendedWindowsPath(match.group(1))
                if not os.path.exists(path):
                    path = GetExtendedWindowsPath(os.path.normpath(
                        os.path.join(self.__workspaceDir, match.group(1))))
                    if not os.path.exists(path):
                        continue
                self.__AddFile(
                    FileToArchive(path), reportRefPath, u'', u'TEST-CASE', False, pkgResult)
                fileHash = self.__HashFile(path)
                discoveries.insert(0, {'txt': fileHash,
                                       'start': match.start(1),
                                       'end': match.end(1)})
            descriptionCopy = desc
            for discovery in discoveries:
                descriptionCopy = (descriptionCopy[0:discovery['start']:] +
                                   discovery['txt'] +
                                   descriptionCopy[discovery['end']::])
            reportPkg[u'DESC'][u'L-2'][u'#'] = descriptionCopy

    def __AddImagesFromMultimediaTestSteps(self, pkgResult, processedPackage, reportRefPath):
        """
        :type pkgResult:
        :type processedPackage: ProcessPackage
        :type reportRefPath: str
        """
        if self.__archiveImages:
            for eachTSReportRef, images in processedPackage.GetTestStepImages().items():
                reportRef = self.__CreateFullTestStepRefPath(reportRefPath,
                                                             eachTSReportRef)
                if len(reportRef) > 0:
                    for eachImage in images:
                        self.__AddTestStepImageToArchive(
                            FileToArchive(eachImage), reportRef, pkgResult)

    def __CheckArchiveRecording(self, atxAttributes):
        '''
        Prüft, ob die Aufzeichnung überhaupt für den Upload mit erfasst werden soll.
        Dies ist abhängig von den eingestellten 'archiveRecordings' Parameter.
        :param atxAttributes: Alle Attribute (einschließlich Projekt-Attribute) mit Ihren Werten,
                 welche erfasst wurden.
        :type atxAttributes: dict
        :return: True, wenn die Aufzeichnung erfasst werden soll, sonst False.
        :rtype: bool
        '''
        # Sind Uploads in Abhängigkeit der Attriubte angegeben
        if self.__archive[u'recordingsByAttribute']:
            for eachKey, eachValue in self.__archiveRecordingsByAttributes.items():
                value = atxAttributes.get(eachKey)
                if value and value == eachValue:
                    return True
            return False
        else:
            # Nur übernehmen, wenn Recordings explizit erwünscht!
            return self.__archive[u'recordings']

    def __CreateFullTestStepRefPath(self, reportTestCaseRef, reportTestStepRef):
        """
        Erzeugt aus dem übergebenen TEST-STEP Report und TEST-CASE Report Ref-Paths den
        vollstaendigen TEST-STEP Report Ref-Path.
        @param reportTestCaseRef: TEST-CASE Report Ref-Paths des TEST-STEPS
        @type reportTestCaseRef: str
        @param reportTestStepRef: zum TEST-CASE relativer TEST-STEP Report Ref-Path
        @type reportTestStepRef: str
        @return: TEST-STEP Report Ref-Path
        @rtype: str
        """
        return u'{0}{1}'.format(reportTestCaseRef, reportTestStepRef)

    def __DetectParameters(self, package, detectOnlyParameter=False):
        """
        Ermittelt aus dem Package die enthaltenen Parameter und gibt diese aufbereitet zurück.
        @param package: Package Objekt aus der Report API.
        @type package: tts.core.report.parser.Package.Package
        @param detectOnlyParameter: True, wenn nur die Input-Parameter erfasst werden sollen und
                                    nicht auch noch die Rückgabewerte, sonst False.
        @type detectOnlyParameter: bool
        @return: Dict mit {Parametername: {value, direction, description}}
        @rtype: dict
        """
        # Input und Output Parameter erfassen
        parameters = {}

        if package.HasParams():
            # Neue API ab ECU-TEST 6.4 verwenden
            if hasattr(package, u'IterParameterVariables'):
                for each in package.IterParameterVariables():
                    """
                    @type each: lib.report.db.Variable.PackageParameterVariable
                    """
                    key = each.GetName()
                    value = each.GetValue()
                    desc = each.GetDescription() if each.GetDescription() is not None else u""
                    parameters[key] = {u'value': self.__FilterValueDefaultSuffix(value),
                                       u'direction': u'IN',
                                       u'description': desc}

        if package.HasReturnValues() and not detectOnlyParameter:
            # Neue API ab ECU-TEST 6.4 verwenden
            if hasattr(package, u'IterReturnVariables'):
                for each in package.IterReturnVariables():
                    """
                    @type each: lib.report.db.Variable.PackageReturnVariable
                    """
                    key = each.GetName()
                    value = each.GetValue()
                    desc = each.GetDescription() if each.GetDescription() is not None else u""
                    # zunächst schauen, ob der Parameter schon als Input Parameter vorhanden ist
                    direction = u'INOUT' if key in parameters else u'OUT'

                    parameters[key] = {u'value': self.__FilterValueDefaultSuffix(value),
                                       u'direction': direction,
                                       u'description': desc}
        return parameters

    def __CreateTestArgumentElementsFromPkgParameters(self, reportPkg, parameters):
        """
        Erzeugt TEST-ARGUMENT-ELEMENTs für die Package Parameter, Input wie Output-Parameter
        @param reportPkg: das neu erzeugte TEST-CASE Objekt
        @type reportPkg: OrderedDict
        @param parameters: Dict mit {Parametername: {value, direction, description}}
        @type parameters: dict
        """
        # ARGUMENT-LIST initialisieren, falls noch nicht vorhanden
        if not reportPkg[u'ARGUMENT-LIST']:
            # RETURN wird ignoriert, da es nicht benötigt wird
            reportPkg[u'ARGUMENT-LIST'] = {u'ARGUMENTS': []}

        # Daten Typ für Recording anlegen, falls noch nicht vorhanden
        if self.__parameterType is None:
            self.__parameterType = OrderedDict([
                (u'@type', u'APPLICATION-PRIMITIVE-DATA-TYPE'),
                (u'SHORT-NAME', u'String')
            ])
            self.__dataTypes[u'ELEMENTS'].append(self.__parameterType)

        for (key, value) in parameters.items():
            assert value[u'direction'] in [u'IN', u'OUT', u'INOUT', u'SUBJECT']

            # Entfernt die ASCII-Steuerzeichen aus dem Wert, wenn vorhanden!
            desc = ReplaceAsciiCtrlChars(value.get(u'description', u''))
            textValue = ReplaceAsciiCtrlChars(value.get(u'value', u''))

            # neues TEST-ARGUMENT-ELEMENT Objekt erzeugen
            newTestArgElem = OrderedDict([
                (u'@type', u'TEST-ARGUMENT-ELEMENT'),
                (u'SHORT-NAME', u'{0}'.format(FilterShortName(key))),
                (u'DESC', {u'L-2': {u'@L': u'DE',
                                    u'#': u'{0}'.format(desc)}}),
                (u'TYPE-REF', {
                    u'@DEST': self.__primitiveConstantType[u'@type'],
                    u'#': u'/{0}/{1}'.format(self.__dataTypes[u'SHORT-NAME'],
                                             self.__parameterType[u'SHORT-NAME'])
                }),
                (u'DIRECTION', value[u'direction']),
                (u'LITERAL-VALUE', {u'TEXT-VALUE-SPECIFICATION': {u'VALUE': textValue}}),
            ])

            # prüfen ob bereits ein Objekt exisistiert für den Parameter
            for eachTestArgElem in reportPkg[u'ARGUMENT-LIST'][u'ARGUMENTS']:
                if eachTestArgElem[u'SHORT-NAME'] == newTestArgElem[u'SHORT-NAME']:
                    # das Element ist bereits erfasst
                    return

            # Objekt zu Arguments hinzufügen
            reportPkg[u'ARGUMENT-LIST'][u'ARGUMENTS'].append(newTestArgElem)

    def __GetCoveredAttributes(self):
        """
        @return: Die gewünschten Attribute mit ';', welche erfasst werden sollen
                 aus der Config laden.
        @rtype: str
        """
        # gewünschte Attribute aus config.xml laden
        coveredAttributes = Config.GetSetting(self.__report, u'coveredAttributes')

        # Bereinigen des Strings
        if coveredAttributes.startswith(u';'):
            coveredAttributes = coveredAttributes[1:]
        if coveredAttributes.endswith(u';'):
            coveredAttributes = coveredAttributes[:-1]

        return coveredAttributes

    @staticmethod
    def GetAttributeDelimiterFromConfig(delimiterConfig):
        """
        Zerlegt die übergebene Trennzeichen-Konfiguration für das splitten von Attributenwerten
        in ein Dict zur weiteren Verarbeitung.
        Die Methode ist static, damit einfache Tests möglich sind!
        @param delimiterConfig: Angabe, wie die Attribute mit welchem Trennzeichen geteilt werden
                                sollen z.B. ReqId=,;JiraKey=-
        @type delimiterConfig: str
        @return: Dict mit Attributschlüsseln und dem dazugehörigen Trennzeichnen, wie dieses
                 Attribut ggf. zerlegt werden soll.
                 Z.B. ReqID:_ für ReqID=RQ1_RQ2_RQ3
        @rtype: dict
        """
        # Bereinigen des Strings
        if delimiterConfig.startswith(u';'):
            delimiterConfig = delimiterConfig[1:]
        if not delimiterConfig.endswith(u'=;') and delimiterConfig.endswith(u';'):
            delimiterConfig = delimiterConfig[:-1]

        # Wenn das Semikolon als Trennzeichen verwendet wird, dann muss ein Placeholder verwendet
        # werden, da sonst der Split nicht funktioniert.
        placeholderSemicolon = u'#SEMIKONLON#'
        delimiterConfig = delimiterConfig.replace(u'=;', u'={0}'.format(placeholderSemicolon))

        result = {}
        for each in delimiterConfig.split(u';'):
            # Führende Leerzeichen entfernen
            each = each.lstrip()
            if len(each.split(u'=')) == 2:
                key, value = each.split(u'=')
                # Nur wenn ein Wert enthalten ist, den Key übernehmen.
                if value:
                    result[key] = value.replace(placeholderSemicolon, u';')

        return result

    def __CreateTestCaseAttributes(self, package, testCaseAttributes, projectAttributes):
        """
        Erzeugt die Werte für die TestCase-Attribute.
        @param package: Package Objekt aus der Report API.
        @type package: Package
        @param testCaseAttributes: Dictonary, in das die erzeugten Attribute gespeichert werden.
        @type testCaseAttributes: OrderedDict
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @return: Alle Attribute (einschließlich Projekt-Attribute) mit Ihren Werten,
                 welche erfasst wurden.
        @rtype: dict
        """

        result = {}

        # Prüfe spezielle Mapping zu Attribut-Parameter
        mapIsTestCase = Config.GetSetting(self.__report, u'mapIsTestCaseAsAttribute') == u'True'
        mapTestCaseVersion = Config.GetSetting(self.__report,
                                               u'mapTestCaseVersionAsAttribute') == u'True'
        mapRevision = Config.GetSetting(self.__report, u'includePkgSVNRevision') == u'True'
        mapToolIdentifier = Config.GetSetting(self.__report, u'includeToolIdentifier') == u'True'

        mapIsStimulationPkg = Config.GetSetting(self.__report,
                                                u'mapIsStimulationAsAttribute') == u'True'
        mapIsAnalysisPkg = Config.GetSetting(self.__report, u'mapIsAnalysisAsAttribute') == u'True'

        # Wenn keine Attribute vorhanden, kein IsTestCase, keine Packageversion und
        # kein Nachbewertung erfassen stattfinden soll, dann nix erfassen
        if (not package.HasAttributes() and not mapIsTestCase and not mapRevision and
            not mapTestCaseVersion):
            testCaseAttributes = {}
            return result

        # verfügbare Attribute in Dictonary cachen
        attributes = {}
        for attr in package.IterAttributes():
            attributes[attr.GetName()] = u'{0}'.format(attr.GetValue())

        # gewünschte Attribute aus config.xml laden
        coveredAttributes = self.__GetCoveredAttributes()

        if mapToolIdentifier:

            productName = u'{0}'.format(self.__report.GetInfo().GetAppName())
            major, minor, patch, rev = SplitVersionString(self.__report.GetInfo().GetAppVersion())

            for label, value in [(u'ToolIdentifierName', productName),
                                 (u'ToolIdentifierVersion', u'{0}.{1}.{2}'.format(major,
                                                                                  minor,
                                                                                  patch)),
                                 (u'ToolIdentifierRevision', rev),
                                 (u'ToolIdentifierATXMakoVersion', GetVersion())]:
                attrLabel = label
                attributes[attrLabel] = u'{0}'.format(value)
                coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

        if mapRevision:
            svn = u'{status}'.format(status=package.GetSCMStatus())
            if package.GetRevision() is not None and len(package.GetRevision()) > 0:
                svn = u'{revision}'.format(revision=package.GetRevision())
            attrLabel = u'Revision'
            attributes[attrLabel] = u'{0}'.format(svn)
            coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

            if package.GetSCMUrl():
                svnUrl = u'{url}'.format(url=package.GetSCMUrl())
                attrLabel = u'RevisionUrl'
                attributes[attrLabel] = u'{0}'.format(svnUrl)
                coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

        # Option: Haken "Ist Testfall" als Attribut mit erfassen?
        if mapIsTestCase:
            attrLabel = u'isTestCase'
            attributes[attrLabel] = u'{0}'.format(package.GetIsTestcase())
            coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

        # Option: Stimulations-Package als Attribut mit erfassen?
        if mapIsStimulationPkg:
            if hasattr(package, u'IsStimulationPackage'):
                attrLabel = u'isStimulationPackage'
                attributes[attrLabel] = u'{0}'.format(package.IsStimulationPackage())
                coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

        # Option: Ob Analyse-Package als Attribut mit erfassen?
        if mapIsAnalysisPkg:
            if hasattr(package, u'IsAnalysisPackage'):
                attrLabel = u'isAnalysisPackage'
                attributes[attrLabel] = u'{0}'.format(package.IsAnalysisPackage())
                coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

        # Option:"Package-Versionsangabe" als Attribut mit erfassen?
        if mapTestCaseVersion:
            packageVersion = package.GetVersion()

            # Wenn nicht None oder Leerstring, dann erfassen
            if packageVersion:
                attrLabel = u'TestCaseVersion'
                attributes[attrLabel] = u'{0}'.format(packageVersion)
                coveredAttributes = u'{0};{1}'.format(coveredAttributes, attrLabel)

        # Mapping für festgelegte Attribute möglich 'Execution Priority': 'TEST-CASE-PRIORITY'
        # wird im Moment nicht verwendet - da die meisten Attribute nicht ATX XSD konform
        attrMapping = {}

        delimiterSetting = Config.GetSetting(self.__report, u'attributeDelimiter')

        # Vererbte Projekt-Attribute hinzufügen
        for eachAttrKey, eachAttrValue in projectAttributes.items():
            testCaseAttributes[u'SDGS'].append(self._GetATXAttributeFormat(eachAttrKey,
                                                                           eachAttrValue,
                                                                           True,
                                                                           delimiterSetting))
            result[eachAttrKey] = eachAttrValue

        # Package-Attribute erfassen
        for attrKey, attrValue in self.__GetCovAttrValues(coveredAttributes, attributes):
            if attrKey in attrMapping:
                testCaseAttributes[attrMapping[attrKey]] = attrValue
            else:
                sdg = self._GetATXAttributeFormat(
                    attrKey,
                    attrValue,
                    False,
                    delimiterSetting)

                # Bereits vorhandene identische Attriubt-Keys überschreiben
                toRemove = []
                existedAttrs = testCaseAttributes.get(u'SDGS', [])
                for each in existedAttrs:
                    if each.get(u'@GID', None) == attrKey:
                        toRemove.append(each)

                for each in toRemove:
                    existedAttrs.remove(each)

                # TTSTM-2498: Doppelungen für den gleichen Wert durch Projekt-Attribute vermeiden.
                if sdg not in testCaseAttributes[u'SDGS']:
                    testCaseAttributes[u'SDGS'].append(sdg)

            result[attrKey] = attrValue

        # falls keine Custom Attribute vorhanden sind, kann die SDGS Liste entfernt werden
        if not testCaseAttributes[u'SDGS']:
            testCaseAttributes[u'SDGS'] = None

        return result

    @staticmethod
    def __SupportsMultipleValues(definition):
        """
        Gibt an ob die übergebene Definition(AttrSpec) mehrere Werte unterstützt.
        @return True / False
        """
        # Old Definition
        supportsMultipleValues = None
        try:
            # ECU-TEST < 2020.1
            from lib.attributes.AttrSpec import AttributeMultipleChoiceDef
            supportsMultipleValues = isinstance(definition, AttributeMultipleChoiceDef)
        except ImportError:
            pass

        try:
            # ECU-TEST >= 2020.1
            from tts.lib.attributes.AttrSpec import AttributeTreeValueDef
            isVersionWithSupportedTreeDef = (isinstance(definition, AttributeTreeValueDef) and
                                             hasattr(definition, 'IsMultiChoice'))
            supportsMultipleValues = (definition.IsMultiChoice()
                                      if isVersionWithSupportedTreeDef else supportsMultipleValues)
        except ImportError:
            pass

        if supportsMultipleValues is None:
            raise ImportError('Attribute definition could not be imported.')
        return supportsMultipleValues

    @staticmethod
    def _GetAttrSpecDefinitionName(attrKey):
        """
        Gibt den AttributNamen aus dem ATX attrKey ohne ATX spezifischen Prefix zurück.
        """
        # ATX Generator spezifischen Prefix für lookup in AttrSpec entfernen
        if attrKey.startswith(GenerateAtxDataSet.PRJ_ATT_PREFIX):
            return attrKey.replace(GenerateAtxDataSet.PRJ_ATT_PREFIX, u"")
        else:
            return attrKey

    @staticmethod
    def __GetAttributeDefinition(isProjectAttr, attrKey):
        """
        Gibt die Attribut Definition aus der AttrSpec zurück
        @param: isProjectAttr: Gibt an ob es sich um ein Projekt Attribut handelt.
        @type: isProjectAttr: bool
        @param: attrKey: Name des Attributes
        @type: attrKey: string
        @return Attribut Definition aus AttrSpec (Package oder Projekt)
        """
        if isProjectAttr:
            from lib.project.ProjectAttributeManager import ProjectAttributeManager
            attributeManager = ProjectAttributeManager()
        else:
            attributeManager = GenerateAtxDataSet.__GetPackageAttributeManager()

        attrSpecName = GenerateAtxDataSet._GetAttrSpecDefinitionName(attrKey)
        return attributeManager.GetAttribute(attrSpecName)

    @staticmethod
    def _GetAttributeDelimiter(attrKey, attributDefiniton, delimiterSettings=""):
        """
        Gibt den Trenner zwischen den Werten für ein Attribut zurück.
        Mit folgender Prio:
            1. Delimiter aus ATX Config
            2. Delimiter aus AttrSpec oder None wenn nicht MultiChoice
            3. Standard Delimiter
        @return Trenner oder None, falls es nicht um Attribute mit mehreren Werten handelt.
        """
        # Prio 1: ATX Config Delimiter
        # spezielle Trennzeichen -> für spezielle Attribute ermitteln
        delimiterAttributes = GenerateAtxDataSet.GetAttributeDelimiterFromConfig(delimiterSettings)
        if attrKey in delimiterAttributes:
            return delimiterAttributes.get(attrKey)

        if attributDefiniton:
            # Wenn der Zugriff auf die *.spec Dateien aufzeigt das es sich bei dem Key um kein
            # MultipleChoice-Feld handelt, dann NICHT splitten
            if GenerateAtxDataSet.__SupportsMultipleValues(attributDefiniton):
                # Prio 2: Delimiter aus AttrSpec
                try:
                    # ECU-TEST >= 2020.1
                    from tts.lib.attributes.AttrSpec import AttributeTreeValueDef
                    if isinstance(attributDefiniton, AttributeTreeValueDef):
                        # Delimiter aus AttrSpec
                        return attributDefiniton.GetValueSeparator()
                except ImportError:
                    pass
            else:
                # Werte sind nicht zu splitten laut AttrSpec
                return None

        # Prio 3: Standard Delimiter
        return u','

    @staticmethod
    def _GetATXAttributeFormat(attrKey, attrValue, isProjectAttr, delimiterSettings=""):
        """
        Baut das ATX-Format für die Speicherung eines Attributs zusammen.
        @param attrKey: Attribut-Name
        @type attrKey: str
        @param attrValue: Attribut-Wert
        @type attrValue: str
        @param isProjectAttr: True, wenn Projektattribut, sonst False. Ist wichtig zur
                              Bestimmung ob es sich um ein MultipleChoiceFeld handelt.
        @type isProjectAttr: bool
        @param delimiterSettings: Das Delimiter Setting
        @type delimiterSettings: String
        @return: SDG-Dict für die ATX-TestCase Attribute
        @rtype: dict
        """
        sdg = OrderedDict([(u'@type', u'SDG'),
                           (u'*SDS', []),
                           (u'@GID', FilterShortName(attrKey))])

        definition = GenerateAtxDataSet.__GetAttributeDefinition(isProjectAttr, attrKey)

        # Bestimmen ob dieser Wert einen Trenner besitzt
        # - per delimiterSettings (lookup via attrKey)
        # - per definition ( multichoice & evtl. delimiter in definition )
        # - default falls multichoice
        # sonst None
        delimiter = GenerateAtxDataSet._GetAttributeDelimiter(attrKey, definition,
                                                              delimiterSettings)

        if delimiter:
            attrValueSplit = attrValue.split(delimiter)
        else:
            attrValueSplit = [attrValue]

        # Doppelte Werte bei der Zuweisung zu einem Schlüssel entfernen.
        attrValueSplit = list(set(attrValueSplit))

        for index, eachAttr in enumerate(attrValueSplit):
            value = eachAttr.strip()


            if value:
                sdg[u'*SDS'].append(OrderedDict([(u'@type', u'SD'),
                                                 (u'@GID', u'VALUE_{0}'.format(index)),
                                                 (u'#', value), ]))
            else:
                DPrint(LEVEL_VERBOSE,
                       u"Leeren Wert für Attribut '{0}' ausgespart.".format(attrKey))

        return sdg

    def __GetCovAttrValues(self, coveredAttributes, attributes):
        """
        Ermittelt aus den übergebenen Attributen, und den zu ermittelnden (coveredAttributes) eine
        Liste mit Tupeln von Keys und Values der zu speichernden Attribute.
        Die Wildcards werden beachtet.
        @param coveredAttributes: Aufzählung durch ; getrennt der zu erfassenden Attribute,
                                  wobei die Wildcards * sowie ? erlaubt sind.
        @type coveredAttributes: str
        @param attributes: Dict der zur Verfügung stehenden Attribute aus den Packages oder
                           Projekten.
        @type attributes: dict
        @return: Liste mit Tupeln von Attributename und Attributwert
        @rtype: list[tuple]
        """
        result = []
        knownAttributes = []
        for covAttrKey in coveredAttributes.split(u';'):
            for eachAttribute in self.GetWildcardWordsFromWordList(covAttrKey,
                                                                   list(attributes.keys())):

                if eachAttribute in knownAttributes:
                    continue
                knownAttributes.append(eachAttribute)

                covAttrVal = attributes[eachAttribute]

                # Attribute sind immer Strings
                if not covAttrVal:
                    # falls das Attribut leer ist wird es ignoriert - siehe TTSTM-999
                    continue

                result.append((eachAttribute, covAttrVal))

        return result

    @staticmethod
    def GetWildcardWordsFromWordList(word, words):
        """
        Ermittel alle vorkommen des übergebenen Wortes in der Wörterliste, dabei kann das übergebene
        Wort Wildcards enthalten und es somit mehrer Ergebnisse geben.
        @param word: Wort mit oder ohne Wildcards, welches in der Wörterliste gesucht werden soll.
        @type word: str
        @param words: zu prüfende Liste von Wörtern
        @type words: list[str]
        @return: Liste der Attribute, welche dem übergebenen Word in der Wortliste entsprechen.
        @rtype: list[str]
        """
        return [each for each in words if fnmatch.fnmatch(each, word)]

    def __ParseFloat(self, num):
        """
        Wandelt eine Zahl von String in eine Gleitkommazahl um.
        @param num: umzuwandelnde Zahl
        @type num: str
        @return: umgewandelte Nummer oder 0 bei Fehler
        @rtype: float
        """
        try:
            return float(num)
        except ValueError:
            return 0

    def __GetReportRefPath(self, findName, refPath):
        """
        Gibt den Ref Pfad des Report Testcases zurück.
        @param findName: Short Name des Report Testcases, dessen Ref Pfad benötigt wird.
        @type findName: str
        @param refPath: Referenz-Path zum Package um die Ordnerstruktur zur Suche des Short-Names
                        zu überprüfen ob diese eingehalten wird.
        @type refPath: str
        @return: Ref Pfad.
        @rtype: str
        """
        tcPath = self.__FindShortNameInTestcases(self.__reportSpec[u'TEST-CASES'],
                                                 findName,
                                                 refPath)[0]

        reportRefPath = u'/{0}/{1}/{2}'.format(self.__reportArPkg[u'SHORT-NAME'],
                                               self.__reportSpec[u'SHORT-NAME'], tcPath)
        self.__Debug(u'GetReportRefPath: {0}', reportRefPath)
        return reportRefPath

    def __FindShortNameInTestcases(self, testcases, findName, refPath):
        """
        Sucht im übergebenen Testcase-Pointer und seinen Unterordnern nach dem Testcase mit
        dem übergebenen ShortName und gibt dessen Ref Pfad im TestSpec zurück.
        @param testcases: Zeiger Liste, die zu durchsuchen ist.
        @type testcases: list
        @param findName: Gesuchter ShortName.
        @type findName: str
        @param refPath: Referenz-Path zum Package um die Ordnerstruktur zur Suche des Short-Names
                        zu überprüfen ob diese eingehalten wird.
        @type refPath: str
        @return: Paar aus RefPfad und bool, der einen Fund anzeigt
        @rtype: bool
        """
        for each in testcases:

            # Prüfe bei Foldern, ob die Namen der Folder auch immer im RefPath des zu verarbeitenden
            # Packages auch vorkommen, damit nicht einfach das erste Package in der falschen
            # Ordnerstruktur, was genau den gesuchten Namen trägt, verwendet wird.
            if each[u'@type'] == u'TEST-CASE-FOLDER' and each[u'SHORT-NAME'] not in refPath:
                continue

            if each[u'SHORT-NAME'] == findName:
                return (findName, True)
            elif each[u'@type'] == u'TEST-CASE-FOLDER':
                result = self.__FindShortNameInTestcases(each[u'TEST-CASES'], findName, refPath)
                if result[1]:
                    return (u'{0}/{1}'.format(each[u'SHORT-NAME'], result[0]), True)
        return (None, False)

    def __DiffAndAppendTestSteps(self, existingTestSteps, newTestSteps):
        """
        Vergleicht die bereits aufgebaute Liste von TestSteps mit einer Neuen und
        fügt neue, noch nicht enthaltene Elemente hinzu. Außerdem werden Steps
        geändert, die zuerst als Step vorhanden warne und dann zu Foldern werden.
        Dabei wird auf der übergebenen Liste gearbeitet, also die vorhandenen
        TestSteps modifiziert (call by reference).
        @param existingTestSteps: Liste von TestSteps, die bereits im TestCase ist.
        @type existingTestSteps: List->OrderedDict
        @param newTestSteps: Liste von TestSteps, die neu erstellte wurde.
        @type newTestSteps: List->OrderedDict
        """
        for index, newStep in enumerate(newTestSteps):
            if index >= len(existingTestSteps):
                # Der neue Step existiert nicht in der bereits vorhandenen Liste. Anfügen ...
                existingTestSteps.append(deepcopy(newStep))
            elif newStep[u'LONG-NAME'] == existingTestSteps[index][u'LONG-NAME'] and \
                newStep[u'@type'] != existingTestSteps[index][u'@type']:
                # Der neue Step ist bereits vorhanden! Selbe Struktur?
                if newStep[u'@type'] == existingTestSteps[index][u'@type']:
                    # Ja, gleiche Struktur. -> nichts unternehmen
                    pass
                elif newStep[u'@type'] == u'TEST-STEP' and \
                    existingTestSteps[index][u'@type'] == u'TEST-STEP-FOLDER':
                    # Nein, es war vorher ein StepFolder, nun nur noch ein Step.
                    # -> nichts unternehmen
                    pass
                else:
                    # Nein, es war vorher ein Step, nun ist es ein Folder
                    # -> Spec ersetzen, ID a.k.a. SHORT-NAME beibehalten
                    tempShortName = existingTestSteps[index][u'SHORT-NAME']
                    existingTestSteps[index] = deepcopy(newStep)
                    existingTestSteps[index][u'SHORT-NAME'] = tempShortName
            elif newStep[u'LONG-NAME'] != existingTestSteps[index][u'LONG-NAME']:
                existingTestSteps.append(deepcopy(newStep))

            foundOldTestStep = None
            for eachOldStep in existingTestSteps:
                if newStep[u'SHORT-NAME'] == eachOldStep[u'SHORT-NAME']:
                    foundOldTestStep = eachOldStep
                    break

            if not foundOldTestStep:
                existingTestSteps.append(newStep)
            else:
                if (newStep[u'@type'] == u'TEST-STEP-FOLDER' and
                    foundOldTestStep[u'@type'] == u'TEST-STEP-FOLDER'):
                    self.__DiffAndAppendTestSteps(foundOldTestStep[u'*TEST-STEPS'],
                                                  newStep[u'*TEST-STEPS'])
                elif newStep[u'@type'] != foundOldTestStep[u'@type']:
                    existingTestSteps[index][u'@type'] = u'TEST-STEP-FOLDER'
                    existingTestSteps[index][u'*TEST-STEPS'] = []

    def __GetExecutionTimeInSec(self, package):
        """
        Ermittelt aus dem übergebenen ReportApi-Package die Duration oder 0, wenn diese nicht
        gesetzt bzw. gewünscht ist.
        @param package: Report-Api Package
        @type package: Package
        @return: Laufzeit des Packages in Sekunden, wenn keine vorhanden ist dann 0
        @rtype: integer
        """
        if not self.__captureExecutionTime or package.duration is None:
            return 0
        return int(round(package.duration, 0))

    def __UseParameterSet(self, packageName, projectCompName):
        """
        Überprüft anhand des Packagenamens und der gerade laufenden Projektkomponente ob es sich um
        eine Parametersatzausführung handelt, in diesem Fall sollten die Namen unterschiedlich sein.
        @param packageName: Names des Packages welches ausgeführt wurde
        @type packageName: str
        @param projectCompName: Name des Projektschrittes, welcher ausgeführt wurde
        @type projectCompName: str
        @return: True, wenn es sich um einen Parametersatz handelt, sonst false.
        @rtype: bool
        """
        return packageName != projectCompName

    def __ConvertPkgToPlannedTestCase(self, package, isParameterSetElement,
                                      testExecutionPlanPointer, refPath):
        """
        Konvertiert das übergebene Package zu ATX-PlannedTestCase.
        @param package: zu konvertierendes Package.
        @type package: ReportApi
        @param isParameterSetElement: True, wenn es sich um ein Parametersatz-Projekt-Element
                                      handelt, sonst False.
        @type isParameterSetElement: bool
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param refPath: REF Pfad des zugehörigen TestCases.
        @type refPath: str
        """
        filteredSpecShortName = self.__GetName(package, True, isParameterSetElement)

        # Der ShortName leitet sich aus dem aktuellen Stand des Zählers in der Globalen Dictonary ab
        # count -1 notwendig, damit PlannedTestCases mit _0 beginnen!
        plannedShortName = FilterUniqueShortName(filteredSpecShortName,
                                                 self.__refPaths[refPath][u'count'] - 1)

        plannedTestCase = OrderedDict([
            (u'@type', u'PLANNED-TEST-CASE'),
            (u'SHORT-NAME', plannedShortName),
            (u'TEST-CASE-REF', {
                u'@DEST': u'TEST-CASE',
                u'#': refPath,
            }),
            (u'REPETITION', 1),
            (u'PLANNED-TEST-CASE-DATAS', []),
        ])
        testExecutionPlanPointer.append(plannedTestCase)

        parameters = self.__DetectParameters(package, True)

        if len(parameters) > 0 or self.__UseParameterSet(package.GetName(),
                                                         package.GetPrjCompName()):
            paramShortName = GetNextShortNameInList(self.__testData[u'ELEMENTS'],
                                                    FilterShortName(package.GetPrjCompName()))

            # TestCaseParamValues
            testCaseParamValues = OrderedDict([
                (u'@type', u'TEST-CASE-PARAM-VALUES'),
                (u'SHORT-NAME', paramShortName),
                (u'LONG-NAME', {
                    u'L-4': {
                        u'@L': u'DE',
                        u'#': package.GetPrjCompName()
                    }
                }),
                (u'TEST-CASE-REFS', [{
                    u'@type': u'TEST-CASE-REF',
                    u'@DEST': u'TEST-CASE',
                    u'#': refPath
                }]),
                (u'TEST-PARAM-VALUE-TABLE', []),
            ])

            for (paramKey, paramValue) in parameters.items():
                # desc = paramValue.get(u'description', u'')
                # Description gibt es für TEST-PARAM-VALUE nicht
                value = paramValue[u'value']
                testParamValue = self._CreateTestParamValue(paramKey, value)
                testCaseParamValues[u'TEST-PARAM-VALUE-TABLE'].append(testParamValue)

                plannedTestCase[u'PLANNED-TEST-CASE-DATAS'].append(OrderedDict([
                    (u'@type', u'PLANNED-TEST-CASE-DATA'),
                    (u'REPETITION', 1),
                    (u'TEST-VALUE-SET-REF', {
                        u'@DEST': u'TEST-PARAM-VALUE-SET-CAPTION',
                        u'#': u'/{0}/{1}/{2}'.format(self.__testData[u'SHORT-NAME'],
                                                     testCaseParamValues[u'SHORT-NAME'],
                                                     FilterShortName(paramKey)),
                    }),
                ]))

            self.__testData[u'ELEMENTS'].append(testCaseParamValues)

    def _CreateTestParamValue(self, paramKey, value):
        val = self.__FilterValueDefaultSuffix(value)
        return OrderedDict([
            (u'@type', u'TEST-PARAM-VALUE-SET'),
            (u'TEST-PARAM-VALUE-SET-CAPTION', OrderedDict([
                (u'SHORT-NAME', FilterShortName(paramKey)),
                # (u'LONG-NAME', {
                #     u'L-4': {
                #         u'@L': u'DE',
                #         u'#': package.GetPrjCompName()
                #     }
                # }),
            ])),
            (u'TEST-PARAM-VALUES',
             [self.__GetTestParamValueEntity(val)]),
        ])

    def __FilterValueDefaultSuffix(self, value):
        """
        Filtert das " (Default)" Suffix aus Parameterwerten und zusätzlich werden auch alle
        falschen Steuerzeichen entfernt!
        @param value: zu filternder String.
        @type value: str
        @return: gefilterten String
        @rtype: str
        """
        # Entfernt die ASCII-Steuerzeichen aus dem Wert, wenn vorhanden!
        value = ReplaceAsciiCtrlChars(value)
        return self.FIND_DEFAULT_VALUE_PARAM_REG_EXP.sub(u'', value)

    def __GetTestParamValueEntity(self, entity):
        """
        Erzeugt einen einzelnen Parameterwert in ATX.
        @param entity: Parameter.
        @return: ATX-ValueSpecifications.A
        @rtype: dict
        """
        entityAsString = str(entity)

        # Entfernt die ASCII-Steuerzeichen aus dem Wert, wenn vorhanden!
        entityAsString = ReplaceAsciiCtrlChars(entityAsString)

        return OrderedDict([
            (u'@type', u'TEXT-VALUE-SPECIFICATION'),
            (u'VALUE', entityAsString)
        ])

    def __ReportVariation(self, variation, scope, testExecutionPlanPointer, projectAttributes,
                          testManagementTestSuiteId):
        """
        Erzeugt aus den Variationen die ATX-Entsprechung.
        @param variation: Variation.
        @type variation: ReportApi
        @param scope: Dictonary mit Informationen, welche bei der Verarbeitung in
                      Kind-Knoten benötigt werden. (siehe Kommentar in
                      __CreateNewScopeFromParentScope Methode)
        @type scope: dict
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @param testManagementTestSuiteId: Bei einer Koppelung an ein TMS-System wird zu einem
                                          Testfall die dazugehörige TestSuite-Id übergeben.
        @type testManagementTestSuiteId: str
        @return: True, wenn Kindelemente verarbeitet wurden, sonst False.
        @rtype: bool
        """
        self.__Debug(u'__ReportVariation {0}', variation.GetElementName())
        return self.__ReportPackageSet(variation, scope, testExecutionPlanPointer,
                                       projectAttributes, testManagementTestSuiteId)

    def __ReportSubProject(self, subProject, scope, projectExecLevel, testExecutionPlanPointer,
                           projectAttributes, testManagementTestSuiteId):
        """
        Erstellt für das SubProjekt die ATX Elemente.
        @param project: SubProjekt.
        @type project: ReportApi
        @param scope: Dictonary mit Informationen, welche bei der Verarbeitung in
                      Kind-Knoten benötigt werden. (siehe Kommentar in
                      __CreateNewScopeFromParentScope Methode)
        @type scope: dict
        @param projectExecLevel: Indikator für die Hierarchieebene des Elements im Projektbaum.
        @type projectExecLevel: int
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @param testManagementTestSuiteId: Bei einer Koppelung an ein TMS-System wird zu einem
                                          Testfall die dazugehörige TestSuite-Id übergeben.
        @type testManagementTestSuiteId: str
        """
        if self.__GetElementSize(subProject.IterItems()) > 0:
            # neuen PlannedTestCaseFolder erzeugen und anhängen
            plannedTestCaseFolder = OrderedDict([
                (u'@type', u'PLANNED-TEST-CASE-FOLDER'),
                (u'SHORT-NAME', self.__GetName(subProject, False, False)),
                (u'PLANNED-TEST-CASES', []),
            ])

            testExecutionPlanPointer.append(plannedTestCaseFolder)

            # die nächste Hierarchieebene mit dem neuen PlannedTestCaseFolder als
            # TestExecutionPlan-Pointer starten
            self.__ReportProjectElement(subProject, scope, projectExecLevel,
                                        plannedTestCaseFolder[u'PLANNED-TEST-CASES'],
                                        projectAttributes, testManagementTestSuiteId)

    def __ReportProjectElement(self, projectElement, parentScope, projectExecLevel,
                               testExecutionPlanPointer, projectAttributes,
                               parentTestManagementTestSuiteId=None):
        """
        Verarbeitet die Kinder des übergebenen Elements.
        @param projectElement: Report Element.
        @type projectElement: tts.core.report.parser.ReportApi or ProjectElementItems
        @param parentScope: Dictonary mit Informationen, welche bei der Verarbeitung in
                            Kind-Knoten benötigt werden. (siehe Kommentar in
                            __CreateNewScopeFromParentScope Methode)
        @type parentScope: dict
        @param projectExecLevel: Indikator für die Hierarchieebene des Elements im Projektbaum.
        @type projectExecLevel: int
        @param testExecutionPlanPointer: Zeiger auf die aktuelle Liste mit den PLANNED-TEST-CASES.
        @type testExecutionPlanPointer: list
        @param projectAttributes: Dict mit den Projektattributen und deren Werten
        @type projectAttributes: dict
        @param parentTestManagementTestSuiteId: Bei einer Koppelung an ein TMS-System wird zu einem
                                          Testfall die dazugehörige TestSuite-Id übergeben.
                                          Welche auch von einem Parent übernommen werden kann,
                                          wenn der Report durch Ordner verschachtelt ist.
        @type parentTestManagementTestSuiteId: str
        """
        scope = self.__CreateNewScopeFromParentScope(parentScope)

        testManagementTestSuiteId = self.__GetTestManagementIdFormItem(projectElement)

        # Parent TestSuite-ID übernehmen, wenn aktuell keine TestSuite-Id vorhanden ist.
        # Parent ID kommt bei Ordner-Strukturen zum Tragen
        if parentTestManagementTestSuiteId and testManagementTestSuiteId is None:
            testManagementTestSuiteId = parentTestManagementTestSuiteId

        for item in projectElement.IterItems():
            itemType = item.__class__.__name__

            if IsSkipped(item):
                continue

            if itemType == u'Configuration' or itemType == u'ConfigChange':
                # Bei Konfig-Wechsel alle Konstanten bis dahin verwerfen!
                scope[u'testConstantElements'] = []

                cfg = (self.__GetReportConfig(item, scope) if itemType == u'Configuration' else
                       self.__GetReportConfig(item, scope, FilterShortName(item.GetName())))
                if not cfg:
                    continue

                counter = 0
                cfgShortName = cfg[u'SHORT-NAME']
                while FindDictInList(self.__topArPkgKonfiguration[u'ELEMENTS'],
                                     u'SHORT-NAME', cfgShortName) != -1:
                    counter += 1
                    cfgShortName = u'{0}_{1}'.format(cfg[u'SHORT-NAME'], counter)
                cfg[u'SHORT-NAME'] = cfgShortName

                self.__topArPkgKonfiguration[u'ELEMENTS'].append(cfg)
                self.__ConfigRef = OrderedDict([
                    (u'@type', u'TEST-ENVIRONMENT-REF'),
                    (u'@DEST', u'TEST-ENVIRONMENT-SET'),
                    (u'#', u'/{arp}/{tes}'.format(arp=self.__topArPkgKonfiguration[u'SHORT-NAME'],
                                                  tes=cfg[u'SHORT-NAME'])),
                ])

                self.__topTestExecutionPlan[u'TEST-ENVIRONMENT-REFS'].append(
                    self.__ConfigRef.copy())

            elif itemType == u'Package':
                self.__Debug(u'Package: {0} => {1}', self.__GetName(item, True, False),
                             projectExecLevel)
                self.__ReportPackage(item, scope, testExecutionPlanPointer, projectAttributes,
                                     testManagementTestSuiteId)
            elif itemType == u'Project':
                # Aktuellen Projekt-Attribute ermitteln und zuweisen
                # Bestands-Projekt-Attribute von höheren Ebenen mit kopieren
                attributes = deepcopy(projectAttributes)
                attributes.update(self.__GetProjectAttributes(item))

                prjExecFolderElement = None

                # Root-Projekt
                if projectExecLevel == 0:
                    self.__Debug(u'Project: {0} => {1}', self.__GetName(item, False, False),
                                 projectExecLevel)

                    prjExecFolderElement = testExecutionPlanPointer
                else:
                    self.__Debug(u'SubProject: {0} => {1}', self.__GetName(item, False, False),
                                 projectExecLevel)

                    prjExecFolder = self.__CreatePlannedTestCaseFolder(self.__GetName(item,
                                                                                      False,
                                                                                      False),
                                                                       projectExecLevel)

                    testExecutionPlanPointer.append(prjExecFolder)
                    prjExecFolderElement = prjExecFolder[u'PLANNED-TEST-CASES']

                self.__ReportProjectElement(item, scope, projectExecLevel + 1,
                                            prjExecFolderElement,
                                            attributes)
            elif itemType == u'ProjectElement':

                if item.GetSrcType() == u'PACKAGE_SET':
                    self.__Debug(u'ProjectElement {0}: if => {1}',
                                 self.__GetName(item, False, True),
                                 projectExecLevel)
                    if not self.__ReportPackageSet(item, scope, testExecutionPlanPointer,
                                                   projectAttributes,
                                                   testManagementTestSuiteId):

                        # Es wurden keine Kinder verarbeitet, wahrscheinlich ein Fehler aufgetreten!
                        self.__Debug(u'ProjectElement {0} has no childs',
                                     self.__GetName(item, False, True))

                        if item.GetOriginalResult() == u'ERROR':
                            EPrint(_(u'ProjectElement {0} hat keine Kinder und konnte als '
                                     u'ATX-Element nicht erfasst werden!').format(
                                self.__GetName(item, False, True)))
                else:
                    self.__Debug(u'ProjectElement {0}: else => {1}',
                                 self.__GetName(item, False, False),
                                 projectExecLevel)
                    self.__ReportSubProject(item, scope, projectExecLevel + 1,
                                            testExecutionPlanPointer, projectAttributes,
                                            testManagementTestSuiteId)

        # Wenn es einen Konfig-Wechsel gab, dann muss das Parent-Element diesen
        # Konfig-Wechsel ebenfalls erhalten, damit von dort aus die Konfig in der Ebene
        # weiterhin stimmt, ggf. bis hin in die oberste Ebene.
        parentScope[u'testConstantElements'] = deepcopy(scope[u'testConstantElements'])

    def __GetName(self, projectElement, isPkgElement, isParameterSetElement):
        """
        Ermittelt vom übergebenen Projekt-Element den Namen der im ATX verwendet werden soll.
        Dies kann zum einen der Parametersatzname oder auch der Projektreferenz-Name, welcher
        abweichend von Package-Namen ist, sein.
        @param projectElement: Projekt-Report-Element, dessen Name ermittelt werden soll.
        @type projectElement: tts.report.parser.ProjectElement.ProjectElement
        @param isPkgElement: True, wenn es sich um eine Package-Referenz handelt, sonst False.
        @type isPkgElement: bool
        @param isParameterSetElement: True, wenn es sich um ein Parametersatz-Projekt-Element
                                      handelt, sonst False.
        @type isParameterSetElement: bool
        """
        result = None

        hasPrjComName = hasattr(projectElement, u'GetPrjCompName')

        # Wenn der Parametersatzname verwendet werden soll:
        if isParameterSetElement and hasPrjComName and self.__overrideParamMapping:
            result = projectElement.GetPrjCompName()
        elif (hasPrjComName and isPkgElement and not isParameterSetElement and
              self.__useProjectElementName):
            # Soll der Projektreferenz-Name, statt der Packagename verwendet werden
            result = projectElement.GetPrjCompName()
        else:
            result = projectElement.GetName()

        return FilterShortName(result)

    def __CreatePlannedTestCaseFolder(self, plannedFolderName, projectExecLevel):
        """
        Erstellt die Struktur für ein neues PlannedTestCaseFolder.
        @param plannedFolderName: vorgesehener Name des PlannedTestCase-Folders
        @type plannedFolderName: str
        @param projectExecLevel: Indikator für die Hierarchieebene des Elements im Projektbaum.
        @type projectExecLevel: int
        @return: Gibt das Dict mit den PlannedTestCase-Folder Einträgen zurück.
        @rtype: OrderedDict
        """
        projectShortName = FilterShortName(plannedFolderName)
        # ist diese Ebene schon vermerkt?
        if projectExecLevel not in self.__projectCache:
            # nein -> hinzufügen
            self.__projectCache[projectExecLevel] = []

        pos = FindDictInList(self.__projectCache[projectExecLevel],
                             u'name', projectShortName)
        if pos == -1:
            # nein -> hinzufügen
            self.__projectCache[projectExecLevel].append({
                u'name': projectShortName,
                u'count': 0
            })
        else:
            # ja -> Zähler inkrementieren
            self.__projectCache[projectExecLevel][pos][u'count'] += 1

        modifiedProjectShortName = FilterUniqueShortName(projectShortName,
                                                         self.__projectCache[projectExecLevel][pos]
                                                         [u'count'])

        prjExecFolder = OrderedDict([
            (u'@type', u'PLANNED-TEST-CASE-FOLDER'),
            (u'SHORT-NAME', modifiedProjectShortName),
            (u'PLANNED-TEST-CASES', []),
        ])

        return prjExecFolder

    def __CreateNewScopeFromParentScope(self, parentScope):
        """
        Erzeugt ein neues Scope Dictonary anhand des übergebenen Dictonary. Dabei werden die
        Test Konstanten übernommen.
        Es werden nur die notwendigen Schlüsselwerte kopiert, damit eine Änderung am Scope
        sich nicht auf das Scope des Parents auswirkt.
        Zukünftig ggf. möglich: Das Scope Objekt könnte ebenfalls die ShortNames einer
        Hierarchieebene speichern und transportieren, damit könnte es ein einheitliches
        Vorgehen geben, wie geprüft wird, ob ein ShortName bereit in Verwendung ist.
        @param parentScope: Scope des Parents
        @type parentScope: dict
        @return: neues Scope Objekt
        @rtype: dict
        """
        scope = {u'testConstantElements': []}

        # TestCaseAttributes pro Package aufbauen
        scope[u'testCaseAttributeElements'] = OrderedDict([(u'TEST-CASE-PRIORITY', None),
                                                           (u'ESTIMATED-EXECUTION-TIME', None),
                                                           (u'SDGS', []), ])

        if u'testConstantElements' in parentScope:
            scope[u'testConstantElements'] = deepcopy(parentScope[u'testConstantElements'])

        return scope

    def __GetProjectAttributes(self, project):
        """
        Ermittelt aus dem übergebenen Projekt alle Attribute, wenn diese in der config.xml zum
        Mapping angegeben sind.
        @param project: Project des Reports
        @type project: Project
        @return: Dict mit den Projektattributen und dessen Werte, wenn die Attribute zum Mapping
                 angegeben wurden.
        @rtype: dict
        """
        projectTestCaseAttributes = {}

        # Option: Root-Projektattribute auf TestCase-Attribut erfassen und vererben?
        if Config.GetSetting(self.__report, u'mapRootPrjAttrToPkgAttr') == u'True':

            excludePrefix = self._settings.GetList(u'excludePrjAttrPrefixFor')

            attributes = {}
            for attr in project.IterAttributes():
                attributes[attr.GetName()] = u'{0}'.format(attr.GetValue())

            coveredAttributes = self.__GetCoveredAttributes()

            for attrKey, attrValue in self.__GetCovAttrValues(coveredAttributes, attributes):
                # Präfix "Project_" vor die Attribute schreiben, wenn nicht vorhanden oder
                # nicht gewünscht ist
                if attrKey.startswith(self.PRJ_ATT_PREFIX) or attrKey in excludePrefix:
                    projectTestCaseAttributes[u'{0}'.format(attrKey)] = attrValue
                else:
                    projectTestCaseAttributes[u'{0}{1}'.format(self.PRJ_ATT_PREFIX,
                                                               attrKey)] = attrValue

        return projectTestCaseAttributes

    def __ListHasShortName(self, candidateList, findName):
        """
        Prüft, ob eine Liste von Dictonarys bereits ein Kind mit dem gesuchten ShortName-Key enthält.
        @param candidateList: zu untersuchende Liste
        @type candidateList: list
        @param findName: gesuchter ShortName
        @type findName: str
        @return: True, wenn der ShortName schon wendet wird, sonst False
        @rtype: bool
        """
        return FindDictInList(candidateList, u'SHORT-NAME', findName) >= 0

    def __SplitPkgPath(self, pkgPath):
        """
        Teilt den Package Pfad und gibt den relativen Pfad im Workspace zurück.
        @param path: Pfad des Packages.
        @type path: str
        @return: relativer Pfad OHNE(!) Dateiname.
        @rtype: str
        """
        if pkgPath is None:
            # Pfad stand wohl nicht in der TRF
            return None
        npath = os.path.normpath(pkgPath)
        path = os.path.splitdrive(npath)[1]
        path = os.path.splitext(path)[0]

        folders = [_f for _f in path.split(os.sep) if _f]

        if u'Packages' in folders:
            pos = folders.index(u'Packages')
            return u'/'.join(folders[pos + 1:-1])

        if self.__localePackagesDir in pkgPath:
            # mit lokalen Workspace Einstellungen versuchen
            relPath = os.path.relpath(pkgPath, start=self.__localePackagesDir).split(os.sep)
            return u'/'.join(relPath[:-1])

        return u'/'.join(folders[:-1])

    def __AddPkgToSpec(self, testCasesPointer, relPath, specPkg):
        """
        Fügt den übergebenen TestCase in die TestCases der entsprechenden TestSpec hinzu.
        Dies erfolgt rekursiv, bis der gesuchte TestCaseFolder gefunden wurde.
        @param testCasesPointer: Zeiger auf die möglichen TestCases.
        @type testCasesPointer: list
        @param relPath: Relativer Pfad des Packages im Workspace.
        @type relPath: str
        @param specPkg: TestCase, der hinzugefügt werden soll.
        @type specPkg: OrderedDict
        @return: der Zeiger auf den hinzugefügten TestCase
        @rtype: OrderedDict
        """

        if u'/' in relPath:
            # Ziel noch nicht erreicht: neue Ebene erschließen
            (left, right) = relPath.split(u'/', 1)

            shortName = FilterShortName(left)

            for testCase in testCasesPointer:
                if testCase[u'SHORT-NAME'] == shortName:
                    return self.__AddPkgToSpec(testCase[u'TEST-CASES'], right, specPkg)

            testCasesPointer.append(OrderedDict([
                (u'@type', u'TEST-CASE-FOLDER'),
                (u'SHORT-NAME', shortName),
                (u'TEST-CASES', []),
            ]))

            return self.__AddPkgToSpec(testCasesPointer[-1][u'TEST-CASES'], right, specPkg)
        elif relPath == u'':
            # Ziel erreicht: specPkg einfügen
            # Prüfen ob nicht schon ein TCF mit dem selben ShortName in der Liste "testCasesPointer"
            # existiert!
            for tce in testCasesPointer:
                if tce[u'SHORT-NAME'] == specPkg[u'SHORT-NAME']:
                    raise NameError(specPkg[u'SHORT-NAME'])

            testCasesPointer.append(specPkg)
            return testCasesPointer[-1]  # gibt einen Zeiger auf die hinzugefügte TestSpec zurück
        else:
            # Ziel fast erreicht: noch einen TestCaseFolder [erzeugen / finden] und diesem
            # das specPkg hinzufügen

            shortName = FilterShortName(relPath)

            for testCase in testCasesPointer:
                if testCase[u'SHORT-NAME'] == shortName:
                    testCase[u'TEST-CASES'].append(specPkg)
                    return testCase[u'TEST-CASES'][-1]
            # for Schleife wurde vollständig durchlaufen, ohne einen TestCaseFolder mit dem Namen
            # zu finden => er existiert nicht und muss demzufolge neu erstellt werden
            testCasesPointer.append(OrderedDict([
                (u'@type', u'TEST-CASE-FOLDER'),
                (u'SHORT-NAME', shortName),
                (u'TEST-CASES', [specPkg]),
            ]))

            return testCasesPointer[-1][u'TEST-CASES'][-1]

    def __ReworkReportTestSteps(self, presentReport, recentSteps):
        """
        Gleicht die Origin Ref Pfade der TestSteps an, wenn Unterschiede festgestellt werden.
        @param presentReport: schon vorhandener TestCase-Report
        @type presentReport: OrderedDict
        @param recentSteps: neue hinzukommende TestSteps
        @type recentSteps: dict
        """
        self.__CompareAndFixTestStepOriginRefDifferences(presentReport[u'TEST-SETUP-STEPS'],
                                                         recentSteps[u'setup'])
        self.__CompareAndFixTestStepOriginRefDifferences(presentReport[u'TEST-EXECUTION-STEPS'],
                                                         recentSteps[u'execution'])
        self.__CompareAndFixTestStepOriginRefDifferences(presentReport[u'TEST-TEARDOWN-STEPS'],
                                                         recentSteps[u'teardown'])

    def __CompareAndFixTestStepOriginRefDifferences(self, present, recent):
        """
        Übergebene TestSteps miteinander vergleichen und unterschiedliche
        Origin Ref Pfade korrigieren, indem der Ref Pfad des neuen TestSteps
        mit dem des bereits vorhandenen überschrieben wird.
        @param present: schon vorhandene TestSteps
        @type present: list
        @param recent: neue hinzukommende TestSteps
        @type recent: list
        """
        for index, step in enumerate(recent):
            if index < len(present):
                # Nur TestSteps haben einen Origin Ref
                if step[u'@type'] == u'TEST-STEP':
                    recentOriginRef = step[u'ORIGIN-REF'][u'#']
                    if u'ORIGIN-REF' in present[index]:
                        presentOriginRef = present[index][u'ORIGIN-REF'][u'#']
                        if recentOriginRef != presentOriginRef:
                            step[u'ORIGIN-REF'][u'#'] = presentOriginRef
                # Nur TestStepFolder haben TestSteps
                elif present[index][u'@type'] == u'TEST-STEP-FOLDER':
                    self.__CompareAndFixTestStepOriginRefDifferences(present[index][u'*TEST-STEPS'],
                                                                     step[u'*TEST-STEPS'])

    def __GetLatestReportDate(self, package):
        """
        Bestimmt das letzte Ausführungsdatum des Packages, bspw. wenn eine Traceanalyse
        nachgelagert ausgeführt wurde.
        @param package: zu konvertierendes Package.
        @type package: ReportApi
        @return: letztes Ausführungsdatum des Package
        @rtype: str
        """
        reportDate = GetIsoDate(package.GetTime())
        if package.HasAnalysisJobs(True):
            dateOverridden = False
            for ajob in package.IterAnalysisJobs(True):
                if ajob.GetReportItemIdSource() is None:
                    comments = self.__report.IterUserComments(ajob.GetReportItemId())
                    for cmmt in comments:
                        if not cmmt.GetAuthor() and not cmmt.GetOverriddenResult():
                            dateOverridden = GetIsoDate(datetime.fromtimestamp(cmmt.GetTimestamp()))
            if dateOverridden:
                reportDate = dateOverridden

        return reportDate

    def __GetATXReportDate(self):
        """
        @return: Gibt den Zeitpunkt zurück, wann das ATX-Dokumente erstellt wurde, also wann die
                 Testausführung stattfand.
        @rtype: str
        """
        return self.__atxDate

    def __Debug(self, txt, *args):
        """
        Debug: Print Funktion.
        """
        if self.__DebugEnabled:
            WPrint(u'{0}'.format(txt.format(*args)))

    def __DumpJson(self, name, dicd):
        """
        Debug: Konvertiert dict oder list zu JSON und schreibt es in Datei.
        """
        with open(u'{path}/{name}.json'.format(path=self.__reportDir,
                                               name=name), u'w') as fh:
            json.dump(dicd, fh, indent=4)

    def __HashFile(self, file):
        """
        Erzeugt den MD5 Hash einer Datei wenn nicht bereits im Cache abrufbar.
        @return MD5 Hash über den Inhalt der Datei
        @rtype str
        """
        if file not in self.__hashCache:
            hashValue = HashFileContents(file)
            self.__hashCache[file] = hashValue
        return self.__hashCache[file]

    @staticmethod
    def __GetPackageAttributeManager():
        manager = GenerateAtxDataSet.__importPackageAttributeManagerFromET81()

        if manager is None:
            manager = GenerateAtxDataSet.__importPackageAttributeManagerFromET80()

        if manager is None:
            manager = GenerateAtxDataSet.__importLegacyPackageAttributeManager()

        return manager

    @staticmethod
    def __importPackageAttributeManagerFromET81():
        try:
            # ECU-TEST >= 8.1
            from tts.core.package.PackageAttributeManager import PackageAttributeManager
            manager = PackageAttributeManager()
            return manager
        except ImportError:
            return None

    @staticmethod
    def __importPackageAttributeManagerFromET80():
        try:
            # ECU-TEST = 8.0
            from lib.package.PackageAttributes import AttributeManager
            manager = AttributeManager()
            return manager
        except ImportError:
            return None

    @staticmethod
    def __importLegacyPackageAttributeManager():
        try:
            # ECU-TEST < 8.0
            from lib.PackageAttributes import AttributeManager
            manager = AttributeManager()
            return manager
        except ImportError:
            return None
