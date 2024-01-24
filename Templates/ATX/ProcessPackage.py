# -*- coding: utf-8 -*-

'''
Created on 07.02.2014

Erzeugt aus dem übergebenen Package die ATX Struktur im Speicher.

@author: Christoph Groß <christoph.gross@tracetronic.de>
'''

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

from collections import OrderedDict

from .Config import Config
from .Node import Node
from .Utils import FilterSUCCESS, FilterShortName, ConvertConditionBlocks,\
    ReplaceAsciiCtrlChars, IsDownstreamAnalysis
from .ReviewUtils import  GetReviewsForReportItem, GetReviewsForPackage, UpdateRefOnReviews
from .TraceAnalysisJob import TraceAnalysisJob
from .ProcessTestStepImage import ProcessTestStepImage


class ProcessPackage(object):
    '''
    Konvertiert ein ECU-TEST Package in ein ATX TestCase.
    '''
    def __init__(self, report, refPath):
        '''
        Konstruktor.
        @param report: Durchgereichtes ReportApi Objekt.
        @type report: tts.core.report.parser.ReportApi
        @param refPath: Ref Pfad des Packages
        @type refPath: str
        '''
        self.__createTestSteps = Config.GetSetting(report, u'includePkgTestSteps') == u"True"
        # Wenn der nächsten captureSpecialTestSteps hinzugefügt wird, sollte dies über ein Enum geregelt werden!
        self.__captureCalcTestSteps = u"Calculation" in Config.GetSetting(report, u'captureSpecialTestSteps')
        self.captureSubPackageOnVerdict = self.__GetCaptureSubPackageOnVerdictList(report)
        self.__traceJobIds = []
        self.__refPath = refPath
        self.__reviews = []
        self.rootNode = None
        self.__skipStepFlag = _SkipFlag()
        self.subPackages = []
        self.__traceJobs = []
        self.swkIds = []
        self.__imageProcessor = ProcessTestStepImage()
        self.__convertedPkg = None
        self.__loopRun = _LoopRun(self.__skipStepFlag)

    def __GetCaptureSubPackageOnVerdictList(self, report):
        '''
        Ermittelt aus der Konfig, bei welchen ECU-TEST Verdicts ggf. die TestSteps der SubPackages
        mit erfasst werden sollen.
        @param report: ReportApi für den Zugriff auf die Konfigurationseinstellungen
        @type report: tts.core.report.parser.ReportApi
        @return: Liste mit Strings der ATX-Verdicts welche vearbeitet werden
        @rtype: list
        '''
        configValue = Config.GetSetting(report, u'captureSubPackageOnVerdict')

        if not configValue:
            return []

        return [FilterSUCCESS(each.strip()) for each in configValue.split(u";")]

    def GetSwkIds(self):
        '''
        @return: Liste (ohne Doppelungen) von enthaltenen SWK-Ids, welche verwendet wurden.
        @rtype: list
        '''
        return list(set(self.swkIds))

    def GetConvertedPkg(self):
        '''
        Gibt das konvertierte Package zurück.
        @return: Das konvertierte Package.
        @rtype: dict
        '''
        return self.__convertedPkg

    def GetTestStepImages(self):
        """
        :return: die Test-Step ATX-RefPaths mit der Datei-Liste der Bilder, welche in diesem
                 Test-Step erstellt wurden.
        :rtype: dict[str, list[str]]
        """
        return self.__imageProcessor.GetTestStepImages()

    def GetTraceJobs(self):
        '''
        @return: Liste der TraceAnalysisJob aus diesem Package.
        @rtype: list
        '''
        return self.__traceJobs

    def GetReviews(self, reportRefPath):
        '''
        Gibt die Reviews des Packages zurück.
        @param reportRefPath: REF Pfad zum Report TestCase
        @type reportRefPath: str
        @return: Liste der Reviews
        @rtype: List->Review
        '''
        return UpdateRefOnReviews(self.__reviews, reportRefPath)

    def GetSubPackages(self):
        '''
        @return: Ermittelte SubPackages des aktuellen Package
        @rtype: list->ReportItem
        '''
        return self.subPackages

    def _CreateReviewsForTestCase(self, report, package):
        '''
        Ermittelt alle direkten Nachbewertungen auf dem Package und erzeugt für jede ein
        Review Objekt.
        @param report: Durchgereichtes ReportApi Objekt
        @type report: tts.core.report.parser.ReportApi
        @param package: Das zu konvertierende Package.
        @type package: Package
        @return: True, wenn es eine Nachbewertung auf dem kompletten Testfall gab, sonst False.
        @rtype: boolean
        '''
        resultReviews = GetReviewsForPackage(report, package)
        self.__reviews.extend(resultReviews)
        return len(resultReviews) > 0

    def CreateReviewsForTestStep(self, report, teststep):
        '''
        Ermittelt alle Nachbewertungen zu dem TestStep und erzeugt für jede ein Review Objekt.
        @param report: Durchgereichtes ReportApi Objekt
        @type report: tts.core.report.parser.ReportApi
        @param teststep: TestStep, zu dem Nachbewertungen erfasst werden
        @type teststep: ReportItem
        '''
        self.__reviews.extend(GetReviewsForReportItem(report, teststep))

    def ConvertPkg(self, report, pkg):
        '''
        Führt die Konvertierung aus.
        @param report: Durchgereichtes ReportApi Objekt.
        @type report: tts.core.report.parser.ReportApi
        @param pkg: Das zu konvertierende Package.
        @type pkg: tts.core.report.parser.Package.Package
        '''

        # Reviews für dieses Package/Testfall erzeugen!
        hasTestCaseReview = self._CreateReviewsForTestCase(report, pkg)

        for testStep in pkg.GetTestCase(True).IterTestSteps():

            self.ConvertTestStep(report, testStep, hasTestCaseReview)

            # Wenn ein Review für den Testfall vorhanden ist, dann gilt dieses und nicht die
            # TestStep-Reviews
            if not hasTestCaseReview:
                # Reviews für diesen Teststep erzeugen
                self.CreateReviewsForTestStep(report, testStep)

        # Wenn das Package leer ist, dann prüfen ob es Fehler gab und diese als TestStep
        # hinterlegen
        if not self.rootNode:
            if pkg.GetCallError() is not None:
                self._CreateErrorPkgTestStep(pkg)
            else:
                return

        testSteps = self.rootNode.GetList()

        if pkg.HasAnalysisJobs(True):
            for analysisJobItem in pkg.IterAnalysisJobs(True):
                if IsDownstreamAnalysis(analysisJobItem):
                    continue

                job = TraceAnalysisJob(analysisJobItem, self.__refPath, report)

                self.__traceJobs.append(job)

                cjob = job.GetConvertedJob()
                if cjob:
                    testSteps[u'testSteps'].extend(cjob[u'testSteps'])
                    testSteps[u'reportSteps'].extend(cjob[u'reportSteps'])

        self.__convertedPkg = ConvertConditionBlocks(testSteps[u'testSteps'], testSteps[u'reportSteps'])

    def _CreateErrorPkgTestStep(self, pkg):
        '''
        Erzeugt im Falle eines Packages, welches zum Beispiel nicht geladen werden kann, ein Error-
        TestStep mit der Fehlermeldung als Block-Inhalt, damit das Package im TEST-GUIDE auch
        erfasst wird da leere Packages ignoriert werden.
        @param pkg: Das Package zu welchem der ErrorTestStep erzeugt werden soll.
        @type pkg: tts.core.report.parser.Package.Package
        '''
        self.rootNode = Node(-1, {u'SHORT-NAME': self.__refPath})
        pkgVerdict = FilterSUCCESS(pkg.GetOriginalResult())

        errorPkgTestStep = _AtxTestStep(0,
                                        u'{0}'.format(pkg.GetCallError()),
                                        pkgVerdict)

        self.rootNode.AddNode(0, errorPkgTestStep.CreateTestStepAtxDict())

    def ConvertTestStep(self, report, testStep, hasTestCaseReview):
        '''
        Konvertiert einen TestStep nach ATX.
        @param report: Durchgereichtes ReportApi Objekt.
        @type report: tts.core.report.parser.ReportApi
        @param testStep: TestStep von ECU-TEST
        @type testStep:  tts.core.report.parser.Package.ReportItem
        @param hasTestCaseReview: True, wenn schon ein Package-Review vorhanden ist und
                                  dies das TestStep-Review überschreibt, sonst False
        @type hasTestCaseReview: bool
        @return: Gibt für Tests den ermittelen AtxTestStep zurück oder None
        @rtpye: _AtxTestStep
        '''

        if not self.__createTestSteps:
            return

        execLevel = testStep.GetExecLevel()
        activity = testStep.GetActivity()
        srcType = testStep.GetSrcType()
        name = testStep.GetName()

        # Wenn keine ID-Referenz vorhanden ist, dann überspringen!
        if testStep.GetSrc() is None:
            return

        # Jeden Activity auf Großbuchstaben konvertieren und damit vergleichen!
        if activity is None:
            activity = u''
        cmpActivity = activity.upper()

        if cmpActivity == u'ABORT':
            return

        # Jeden Namen auf Großbuchstaben konvertieren und damit vergleichen!
        if name is None:
            name = u''
        cmpName = name.upper()

        # Prüfung ob Testschrittabarbeitungen übersprungen werden sollen.
        if self.__skipStepFlag.skip:
            if self.__skipStepFlag.execLevel < execLevel:
                return
            # Wenn das aktuelle Exec-Level kleiner als das Skip-Flag liegt,
            # dann kann das Flag einem Reset unterzogen werden, da
            # der kritische Block verlassen wurde.
            if self.__skipStepFlag.execLevel >= execLevel:
                self.__skipStepFlag.Reset()

        if srcType == u'UTILITY' and (cmpActivity.startswith((u'SWITCHDEF',
                                                              u'IF')) or
                                      cmpName.startswith(u'IFDEF')):
            # critical block (If, IfDef): ignore subsequent blocks until flag is released
            self.__skipStepFlag.Set(execLevel)
            if cmpName.startswith(u'IFDEF'):
                return

        # Falls noch kein Root-Knoten vorhanden ist wird er angelegt (erster valider
        # Iterationsschritt)
        if not self.rootNode:
            # root Knoten bekommt als SHORT-NAME den Ref Pfad seines TestCases -> wird im else
            # von Node.getRefPath() abgerufen
            self.rootNode = Node(execLevel - 1, {u'SHORT-NAME': self.__refPath})

        images = []

        atxTestStep = self.__CreateAtxTestStep(testStep, images, report, hasTestCaseReview)

        if atxTestStep:
            testStepDict = atxTestStep.CreateTestStepAtxDict()
            self.rootNode.AddNode(execLevel, testStepDict)
            self.__imageProcessor.ComputeImageRefPaths(images,
                                                       self.rootNode,
                                                       testStepDict[u'SHORT-NAME'])
            return atxTestStep

    def __CreateAtxTestStep(self, teststep, images, report, hasTestCaseReview):

        rules = [
                # _Loop muss als erstes verarbeitet werden, da dieser bei der Abarbeitung
                # das Skip-Flag ggfs. setzt
                _Loop(self.__loopRun),
                _TraceCheckPlot(images, self.__imageProcessor),
                _Block(),
                _MultiCheck(),
                _AnalyzeJob(self.__traceJobIds),
                _Calculation(self.__captureCalcTestSteps),
                _PackageCalls(self, report, hasTestCaseReview),
                _AxsCall()]

        wrapTestStep = _PkgTestStepWrapper(teststep)

        for eachRule in rules:
            result = eachRule.Evaluate(wrapTestStep)
            if result:
                return result

        return None

class _SkipFlag(object):
    '''
    Flag um Teststep-Abarbeitungen zu Überspringen.
    '''

    def __init__(self):
        self.skip = False
        self.execLevel = -1

    def Set(self, execLevel):
        '''
        Setzt das Flag.
        '''
        self.skip = True
        self.execLevel = execLevel

    def Reset(self):
        '''
        Reset des Flags, somit werden keine Teststeps
        übersprungen.
        '''
        self.skip = False
        self.execLevel = -1

class _LoopRun(object):
    '''
    Info ob die Verarbeitung eines Loops gerade stattfindet.
    Verschachtelung von Loops sind damit nicht möglich!
    '''

    def __init__(self, skipStepFlag):
        self.__skipStepFlag = skipStepFlag
        # Verdict, für dessen ersten Loop-Pfad die weiteren
        # Teststeps erfasst werden sollen.
        self.loopVerdict = None
        # Info ob die Verarbeitung eines Loop-Pfades gerade
        # stattfindet
        self.loopBranchRun = False
        # Level der Abarbeitung des TestSteps um abbrechen
        # zu können
        self.execLevel = float('inf')

    def StartLoop(self, verdict, currentpkgExecLevel):
        '''
        Loop-Run starten.
        '''
        self.loopVerdict = verdict
        self.execLevel = currentpkgExecLevel

    def IsStartSubLoopRun(self, verdict, currentpkgExecLevel):
        '''
        @return: True, wenn es sich beim aktuellen TestSteps um die Erfassung eines
                 Sub-Loop-Runs handelt, sonst False
        @rtype: boolean
        '''
        # Wenn Abarbeitung im Loop-Run
        if self.IsLoopRun():
            # Dann pürfen ob der Sub-Knoten erfasst werden soll.
            if self.loopVerdict == verdict:
                self.loopBranchRun = True
                self.execLevel = currentpkgExecLevel
                # Tiefen Rekursion für den Sub-Knoten zur Erfassung der
                # Teststeps erlauben
                self.__skipStepFlag.Reset()
                return True
            else:
                # Optimierung: Keine tiefen Rekursionen auf den unwichtigen Sub-Knoten
                # mit deren Teststeps durchführen
                self.__skipStepFlag.Set(currentpkgExecLevel)

        return False

    def EndLoop(self, currentpkgExecLevel):
        '''
        Loop-Run Erfassung beenden.
        Weitere mögliche Sub-Loop-Knoten werden übersprungen.
        '''
        self.loopBranchRun = False
        self.loopVerdict = None

        # Nach der Loop weitere Daten verarbeiten
        self.__skipStepFlag.Set(currentpkgExecLevel - 1)

    def IsLoopRun(self):
        '''
        @return: True, wenn aktuell TestSteps in einem Loop verarbeitet werden, sonst False
        @rtype: boolean
        '''
        return self.loopVerdict is not None


class _PkgTestStepWrapper(object):
    '''
    Wrapper Klasse für eine Package TestStep um für die Umwandlung zu den
    AtxTestSteps die notwendigen Methoden anzubieten, die ständig benötigt werden.
    '''

    def __init__(self, pkgTestStep):
        '''
        @param pkgTestStep: TestStep von ECU-TEST
        @type pkgTestStep:  tts.core.report.parser.Package.ReportItem
        '''
        self._pkgTestStep = pkgTestStep

    def GetOriginPkgTestStep(self):
        return self._pkgTestStep

    def GetTestStepId(self):
        '''
        @return: die TestStep-Id des Package-Teststeps (in der Regel der Shortname)
        @rtype: string
        '''
        return FilterShortName(self._pkgTestStep.GetSrc())

    def GetName(self):
        '''
        @return: Die Bezeichnung des Package-Teststeps, kann auch ein Leerstring sein,
                 wenn nicht gesetzt.
        @rtype: string
        '''
        name = self._pkgTestStep.GetName()
        if name is None:
            name = u''
        return name

    def GetInfo(self):
        '''
        @return: Zusätzliche Info des Package-Teststeps, kann auch None sein
        @rtype: string
        '''
        return self._pkgTestStep.GetInfo()

    def GetActivity(self):
        '''
        @return: Die Aktivitätsbezeichnung des Package-Teststeps, kann auch ein Leerstring sein,
                 wenn nicht gesetzt.
        @rtype: string
        '''
        activity = self._pkgTestStep.GetActivity()
        if activity is None:
            activity = u''
        return activity

    def GetVerdict(self):
        '''
        @return: Die Verdict des Package-Teststeps.
        @rtype: string
        '''
        return FilterSUCCESS(self._pkgTestStep.GetOriginalResult())

    def GetSrcType(self):
        '''
        @return: Der Src-Typ des Package-Teststeps zur Identifikation.
        @rtype: string
        '''
        return self._pkgTestStep.GetSrcType()

    def GetCmpSubSrcType(self):
        '''
        @return: Die Source-Sub-Type des Package-Teststeps zur Idenfitikation.
                 Wird immer in Großbuchstaben konvertiert für die notwendigen String-Vergleiche.
                Kann auch ein Leerstring sein.
        @rtype: string
        '''
        subSrcType = self._pkgTestStep.GetSrcSubType()
        if subSrcType is None:
            subSrcType = u""
        return subSrcType.upper()

    def HasDeepRevaluation(self):
        '''
        Nachbewertungen/Kommentare in Packages erfassen, wenn
        1. es eine gibt und die Bewertung ändert
        2. es sich um eine Errorpackage handelt.
        @rtype: boolean
        '''
        lineNo = self._pkgTestStep.GetSrcIndex()
        return (self._pkgTestStep.GetResult() != self._pkgTestStep.GetOriginalResult() or
                    lineNo == "ERRORPACKAGE")


class _AtxTestStep(object):
    '''
    Repräsentation eines TestSteps für die ATX Darstellung.
    '''

    def __init__(self, testStepId, name, verdict):
        self.testStepId = testStepId # shortname
        self.verdict = verdict
        self.name = name # longname
        self.category = None
        self.description = None
        self.verdictDefinition = None

    def CreateTestStepAtxDict(self):
        '''
        Erzeugt aus den übergebenen Argumenten das TestStep Dict.
        @return: TestStep Objekt.
        @rtype: dict
        '''
        defaultLang = {u'language': u'DE'}

        ret = {
            u'SHORT-NAME': u'step_{0}'.format(self.testStepId),
            u'LONG-NAME': {
                u'L-4': {
                    u'@L': defaultLang[u'language'],
                    u'#': ReplaceAsciiCtrlChars(self.name),
                }
            },
            u'CATEGORY': False,
            u'VERDICT': self.verdict,
        }

        if self.category:
            ret[u'CATEGORY'] = ReplaceAsciiCtrlChars(self.category)

        if self.description:
            ret[u'DESC'] = {
                u'L-2': {
                    u'@L': defaultLang[u'language'],
                    u'#': ReplaceAsciiCtrlChars(self.description),
                }
            }

        verdictDefinition = ReplaceAsciiCtrlChars(self.verdictDefinition)
        if verdictDefinition:
            verdictDef = OrderedDict({u'VERDICT-DEFINITION':
                                      OrderedDict([(u'REPORT-FREQUENCY', u'SINGLE'),
                                                   (u'PROVIDES-VERDICT', u'EVALUATE'),
                                                   (u'EXPECTED-RESULT', {
                                                       u'P': {
                                                           u'L-1': {
                                                               u'@L': defaultLang[u'language'],
                                                               u'#': verdictDefinition,
                                                           }
                                                       }
                                                   }), ])
                                      },)
            ret.update(verdictDef)
        return ret


class _TestStepRule(object):
    '''
    Interface zur Verarbeitung eines Package-TestSteps.
    '''

    def Evaluate(self, pkgTestStep):
        '''
        Prüft ob die Rule für den übergebenen Package-Step angewandt werden kann.
        @param pkgTestStep: TestStep von ECU-TEST
        @type pkgTestStep: _PkgTestStepWrapper
        @return: AtxTestStep, wenn die Rule zutrifft, sonst None
        @rtype: _AtxTestStep
        '''

class _TraceCheckPlot(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Traceschritt-Plot-TestSteps.
    '''

    def __init__(self, images, imageProcessor):
        super(_TraceCheckPlot, self).__init__()
        self.__images = images
        self.__imageProcessor = imageProcessor

    def Evaluate(self, pkgTestStep):
        if pkgTestStep.GetSrcType() == u'UNDEFINED':
            # Nur Images Undefined zulassen.
            if pkgTestStep.GetCmpSubSrcType() == u"IMAGE":
                reportId = int(pkgTestStep.GetOriginPkgTestStep().GetReportItemId())
                images = self.__imageProcessor.GetImageFilesForTestStep(reportId, pkgTestStep.GetOriginPkgTestStep())

                atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                            pkgTestStep.GetActivity(),
                                            pkgTestStep.GetVerdict())

                if images:
                    self.__images.extend(images)
                    atxTestStep.category = u"TRACE_ANALYSIS_PLOT"

                atxTestStep.verdictDefinition = pkgTestStep.GetInfo()

                return atxTestStep


class _Loop(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Loop-TestSteps.
    '''

    def __init__(self, loopRun):
        super(_Loop, self).__init__()
        self.__loopRun = loopRun

    def Evaluate(self, pkgTestStep):

        currentpkgExecLevel = pkgTestStep.GetOriginPkgTestStep().GetExecLevel()

        # Befinden wir uns in einem Loop-Sub-Run der gerade bearbeitet wird
        if self.__loopRun.loopBranchRun:
            # Dann alle Blöcke, der für das Ergebnis des Loop-Sub-Runs verantwortlich
            # sind übernehmen, alle anderen Loop-Sub-Knoten überspringen
            if currentpkgExecLevel <= self.__loopRun.execLevel:
                self.__loopRun.EndLoop(currentpkgExecLevel)
            return

        if pkgTestStep.GetSrcType() == u'UTILITY':

            if u"3DA58CF0-4FEF-11DC-BE56-0013728784EE" in pkgTestStep.GetCmpSubSrcType():
                atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                            pkgTestStep.GetActivity(),
                                            pkgTestStep.GetVerdict())

                # Wenn Loop-Sub-Knoten aufgerufen wird
                if self.__loopRun.IsLoopRun():
                    # Dann prüfen ob dieser auf Grund des Verdicts erfasst werden soll
                    if self.__loopRun.IsStartSubLoopRun(pkgTestStep.GetVerdict(),
                                                        currentpkgExecLevel):
                        # Relevanten Loop-Subknoten zurückgeben
                        return atxTestStep
                    # else -> ignorieren
                else:
                    # Root Loop Knoten erstellen
                    self.__loopRun.StartLoop(pkgTestStep.GetVerdict(), currentpkgExecLevel)
                    atxTestStep.description = "Only the first block that resulted in the loop's aggregate result is displayed."
                    return atxTestStep


class _Block(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Block-TestSteps.
    '''

    def Evaluate(self, pkgTestStep):
        if pkgTestStep.GetSrcType() == u'UTILITY':
            cmpSubSrcType = pkgTestStep.GetCmpSubSrcType()
            # Bei Block-Testschritten die Erwartungswerte (info) erfassen, wenn vorhanden
            if (u":BLOCK" in cmpSubSrcType or
                u":PRECONDITION" in cmpSubSrcType or
                u":POSTCONDITION" in cmpSubSrcType):

                atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                            pkgTestStep.GetActivity(),
                                            pkgTestStep.GetVerdict())
                if pkgTestStep.GetInfo():
                    atxTestStep.verdictDefinition = pkgTestStep.GetInfo()

                return atxTestStep


class _MultiCheck(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Multi-Check-TestSteps.
    '''

    def Evaluate(self, pkgTestStep):
        if pkgTestStep.GetSrcType() == u'UTILITY':
            if u":MULTI-CHECK" in pkgTestStep.GetCmpSubSrcType():
                atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                            u"Multi-Check",
                                            pkgTestStep.GetVerdict())
                if pkgTestStep.GetInfo():
                    atxTestStep.verdictDefinition = pkgTestStep.GetInfo()

                return atxTestStep


class _AnalyzeJob(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Analyse-Job-TestSteps.
    '''

    def __init__(self, traceJobIds):
        super(_AnalyzeJob, self).__init__()
        self.__traceJobIds = traceJobIds

    def Evaluate(self, pkgTestStep):

        if pkgTestStep.GetSrcType() == u'UTILITY':
            if pkgTestStep.GetName().upper() == _(u'Analyse-Job').upper():
                info = pkgTestStep.GetInfo()
                # Wenn die TraceAnalyse noch nicht bekannt ist wird sie angelegt und mit 0
                # initialisiert
                i = 0
                traceJobId = u'traceanalyse_{0}'.format(FilterShortName(info))
                while traceJobId in self.__traceJobIds:
                    i += 1
                    traceJobId = u'{0}_{1}'.format(traceJobId, i)

                # Die id des Schritts wird für TraceAnalysen überschrieben, da hier ein
                # Fehler in der ReportApi dazu führt,
                # dass TraceAnalysen im Gegensatz zu normalen Blöcken usw. bei
                # Parametrierten Packages keine feste id haben.
                atxTestStep = _AtxTestStep(traceJobId,
                                            info,
                                            pkgTestStep.GetVerdict())
                atxTestStep.category = u'TRACEANALYSE'

                return atxTestStep


class _Calculation(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Berechnungs-TestSteps.
    '''

    def __init__(self, captureCalcTestSteps):
        super(_Calculation, self).__init__()
        self.__captureCalcTestSteps = captureCalcTestSteps

    def Evaluate(self, pkgTestStep):
        if self.__captureCalcTestSteps and pkgTestStep.GetSrcType() == u'UTILITY':
            # Berechnung-Schritte erfassen - UUID ist eindeutig
            if u"4115FA00-5F3C-11DF-8A53-001C233B3528:" in pkgTestStep.GetCmpSubSrcType():
                atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                            u"{0}: {1}".format(_(u"Berechnung"),
                                             pkgTestStep.GetOriginPkgTestStep().GetLabel()),
                                            pkgTestStep.GetVerdict())

                if pkgTestStep.GetOriginPkgTestStep().GetTargetValue():
                    # Erwartungswert
                    atxTestStep.verdictDefinition = pkgTestStep.GetOriginPkgTestStep().GetTargetValue()

                if pkgTestStep.GetInfo():
                    # Wert-Spalte
                    atxTestStep.description = u"{0}: {1}".format(_(u'Wert'), pkgTestStep.GetInfo())

                return atxTestStep



class _PackageCalls(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines Subpackage-TestStep-Aufrufs.
    '''

    def __init__(self, processPackage, report, hasTestCaseReview):
        '''
        Damit die rekursive Verarbeitungen von Subpackage erfolgen kann,
        muss das kann 'processPackage' samt dem Report für die
        Weiterverarbeitung zur Verfügung stehen.
        '''
        super(_PackageCalls, self).__init__()
        self.__processPackage = processPackage
        self.__report = report
        self.__hasTestCaseReview = hasTestCaseReview
        self.__rootNode = processPackage.rootNode
        self.__subPackages = processPackage.subPackages
        self.__swkIds = processPackage.swkIds

    def Evaluate(self, pkgTestStep):
        srcType = pkgTestStep.GetSrcType()
        if srcType in [u'PACKAGE', u'PARALLEL_PACKAGE']:
            result = pkgTestStep.GetVerdict()
            atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                        pkgTestStep.GetName(),
                                        result)
            atxTestStep.category = u'SUB_PACKAGE'

            # SubPackages für separate Erfassung als Testfall mit speichern
            pkg = self.__report.GetPackage(pkgTestStep.GetOriginPkgTestStep())

            swkTaTestStep = pkg.GetActivity().startswith('SWK -> TA')
            # Wenn kein SWK Generic Step erfasst wird, sondern ein Package, dann dieses erfassen
            if not swkTaTestStep:
                self.__subPackages.append(pkg)

            # ggf. die SWK-Ids ermitteln und bereitstellen
            self.__swkIds.extend(self.__ExtractSWKTestStepId(pkgTestStep.GetOriginPkgTestStep()))

            # ggf. die SWK-Erwartungen erfassen
            swkExpectation = self.__ConvertSWKTestStepExpectationToVerdictDefinition(
                pkgTestStep.GetOriginPkgTestStep())
            if swkExpectation:
                atxTestStep.verdictDefinition = swkExpectation
            else:
                pkgParamLabel = self.__GetPackageCallParameterToVerdictDefinition(pkg)
                if pkgParamLabel:
                    atxTestStep.verdictDefinition = u"({0})".format(pkgParamLabel)

            # Wenn Generic SWK-Steps (also ohne Package-Mapping)
            # dann kann hier abgebrochen werden
            if swkTaTestStep:
                return atxTestStep

            # 1. SubPackages (nicht parallel ausgeführte) ausklappen, als TestSteps,
            #    wenn das SubPackge bei entsprechendem Fehler erfasst werden soll.
            #
            # 2. Nachbewertungen/Kommentare in Packages erfassen, wenn
            # 2.1 es eine gibt und die Bewertung ändert
            # 2.2 es sich um eine Errorpackage handelt.
            if (self.__CaptureSubPackageOnVerdict(srcType, result) or
                    pkgTestStep.HasDeepRevaluation()):

                # Bestandkonten hinzufügeun und unter diesem die neuen Teststeps anordnen.
                execLevel = pkgTestStep.GetOriginPkgTestStep().GetExecLevel()
                self.__rootNode.AddNode(execLevel, atxTestStep.CreateTestStepAtxDict())

                for eachTestStep in pkg.GetTestCase(True).IterTestSteps():
                    self.__processPackage.ConvertTestStep(self.__report, eachTestStep,
                                                           self.__hasTestCaseReview)

                    if not self.__hasTestCaseReview:
                        self.__processPackage.CreateReviewsForTestStep(self.__report, eachTestStep)

            return atxTestStep

    def __CaptureSubPackageOnVerdict(self, srcType, verdict):
        return (srcType in [u'PACKAGE'] and
                verdict in self.__processPackage.captureSubPackageOnVerdict)

    def __GetPackageCallParameterToVerdictDefinition(self, pkg):
        '''
        Ermittelt die Parameter des Packages, welche als Label im TEST-GUIDE für den Package-Call
        angezeigt werden soll.
        @param pkg: Package
        @type pkg: :class:`~Package.Package`
        @return: Label für den Package-Call
        @rtype: str
        '''
        result = ""
        for pkgParam in pkg.IterParameterVariables():
            result = u"{0}, {1}={2}".format(result,
                                            pkgParam.GetName(),
                                            pkgParam.GetValue())
            result = result.strip(", ")
        return result

    def __ConvertSWKTestStepExpectationToVerdictDefinition(self, testStep):
        '''
        Ermittelt aus dem TestStep die SWK-SOLL-Erwartungen, falls es sich bei dem TestStep um
        einen SWK-Aufruf handelt.
        @param testStep: Aktueller Package Teststep
        @type testStep: tts.core.report.parser.Package.ReportItem
        @return: Leeren String oder die Erwartung
        @rtype: str
        '''
        # Tabel-Entities durchsuchen
        for eachEntity in testStep.IterEntities():
            if (eachEntity.GetType() == u"tableentity_cell" and
                    eachEntity.GetName() == u"keywordReprCompare"):
                for each in eachEntity.IterRows():
                    # Wenn der folgende String vorhanden ist, dann den SWK-Soll-Wert daraus
                    # ermitteln.
                    # Beispielaufbau: [u'SOLL:', u'Abbiegelicht', u"'beidseitig'", u"'aus'"]
                    if _(u"SOLL:") in each:
                        # nur die Parameter und Erwartungen erfassen
                        if len(each) > 2:
                            return u" ".join(each[2:])
                    # abbrechen nach der ersten Zeile, da nur dort der Soll-Wert enthalten ist
                    break
        return u""

    def __ExtractSWKTestStepId(self, testStep):
        '''
        Ermittelt aus dem TestStep die SWK-Ids, falls es sich bei dem TestStep um
        einen SWK-Aufruf handelt.
        @param testStep: Aktueller Package Teststep
        @type testStep: tts.core.report.parser.Package.ReportItem
        @return: Liste von enthaltenen SWK-Ids
        @rtype: list
        '''
        result = []
        # Tabel-Entities durchsuchen
        for eachEntity in testStep.IterEntities():
            if (eachEntity.GetType() == u"tableentity_cell" and
                    eachEntity.GetName() == u"keywordId"):
                for each in eachEntity.IterRows():
                    # Wenn der folgende String vorhanden ist, dann die SWK-Id daraus
                    # ermitteln. Beispielaufbau: ['2660']
                    result.extend(each)
                    break
        return result


class _AxsCall(_TestStepRule):
    '''
    Klasse zur Verarbeitung eines AXS-TestStep-Aufrufs.
    '''

    def Evaluate(self, pkgTestStep):
        if pkgTestStep.GetSrcType() == u'CALL':
            atxTestStep = _AtxTestStep(pkgTestStep.GetTestStepId(),
                                        pkgTestStep.GetName(),
                                        pkgTestStep.GetVerdict())
            atxTestStep.category = u'AXS'

            return atxTestStep
