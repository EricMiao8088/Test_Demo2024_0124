# -*- coding: utf-8 -*-

"""
ACHTUNG! Der ATX-Generator muss Python 2.7 kompatibel sein, da sich noch ältere ECU-TEST Versionen
         im Produktiveinsatz befinden.

Created on 27.02.2014

@author: Christoph Groß <christoph.gross@tracetronic.de>
"""

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import re
import sys

from .Config import Config
from .Review import Review
from .Utils import GetVerdictWeighting, FilterSUCCESS

if sys.version_info < (3,):
    str = unicode


def GetReviewsForPackage(report, pkg):
    """
    Ermittelt alle direkten Nachbewertungen auf den Package und erzeugt für jede ein Review Objekt.

    @param report: Durchgereichtes ReportApi Objekt
    @type report: tts.core.report.parser.ReportApi
    @param pkg: Package zu dem Nachbewertungen erfasst werden
    @type pkg: Package
    @return Reviews aus Nachbewertungen
    @rtype: list->Review
    """
    result = []
    for comment in list(report.IterUserComments(pkg.GetReportItemId())):
        if comment.GetAuthor():
            # Custom Verdict auf Packages wird im Moment nicht untertützt
            result.append(Review(comment, u"TA", -1, -1, None))
    return result


def GetReviewsForReportItem(report, reportItem):
    """
    Ermittelt alle Nachbewertungen zu dem ReportItem und erzeugt für jede ein Review Objekt.

    @param report: Durchgereichtes ReportApi Objekt
    @type report: ReportApi
    @param reportItem: ReportItem, zu dem Nachbewertungen erfasst werden
    @type reportItem: ReportItem
    @return Reviews aus Nachbewertungen
    @rtype: list->Review
    """
    result = []
    name = u'#{0} {1} ({2})'.format(reportItem.GetSrcIndex(), reportItem.GetName(),
                                    reportItem.GetActivity())

    for comment in list(report.IterUserComments(reportItem.GetId())):
        if comment.GetAuthor():
            abortCode = None
            if Config.GetSetting(report, u'reviewUseAbortCodeAsCustomEvaluation') == u"True":
                abortCode = reportItem.GetAbortCode()
                if abortCode:
                    abortCode = abortCode.strip("'")

            review = Review(comment,
                            name,
                            reportItem.GetExecLevel(),
                            reportItem.GetSrcIndex(),
                            abortCode)

            # TAGS
            # ECU-TEST versions before 2023.2 could return None
            commentText = comment.GetText() or ''
            detectTags = __ParseListFromString(Config.GetSetting(report, u'detectReviewTags'))

            for tag in __FindInReviewComment(commentText, detectTags, u'#'):
                review.AddReviewTag(tag)

            for tag in __FindInReviewCommentWithNewSyntax(commentText, u'tag', detectTags):
                review.AddReviewTag(tag)

            # DEFECT CLASS

            detectDefects = __ParseListFromString(Config.GetSetting(report, u'detectReviewDefects'))

            foundDefect = None

            for defect in __FindInReviewComment(commentText, detectDefects, u'|'):
                if foundDefect:
                    ReviewCommentException.RaiseForDuplicateDefectClass(defect)
                foundDefect = defect

            for defect in __FindInReviewCommentWithNewSyntax(commentText,
                                                             u'defectClass',
                                                             detectDefects):
                if foundDefect:
                    ReviewCommentException.RaiseForDuplicateDefectClass(defect)
                foundDefect = defect

            review.SetDefectClass(foundDefect)

            # SUMMARY

            foundSummary = None

            for summary in __FindInReviewCommentWithNewSyntax(commentText, u'summary'):
                if foundSummary:
                    ReviewCommentException.RaiseForDuplicateSummary(summary)
                foundSummary = summary

            review.SetSummary(foundSummary)

            # VERDICT

            foundVerdict = None

            for verdict in __FindInReviewCommentWithNewSyntax(commentText, u'verdict'):
                if foundVerdict:
                    ReviewCommentException.RaiseForDuplicateVerdict(verdict)
                foundVerdict = verdict

            if foundVerdict:
                foundVerdict = FilterSUCCESS(foundVerdict)

                if not GetVerdictWeighting(foundVerdict):
                    ReviewCommentException.RaiseForInvalidVerdict(foundVerdict)

                review.SetRevaluationVerdict(foundVerdict)

            result.append(review)

    return result


def __ParseListFromString(configParameter):
    '''
    :param configParameter: Wert eines Konfigurationsparameters, der eine per Semikolon getrennte
    Liste enthält
    :return: Die einzelnen Werte der Liste
    '''
    return configParameter.strip().strip(u';').split(u';')


def __FindInReviewComment(haystack, configParameters, circumfix):
    """
    :param str haystack: Text der durchsucht wird
    :param list configParameters: Erlaubte Werte der Konfiguration
    :param str circumfix: umschließendes Zeichen
    :yield: ermittelte Werte
    """
    for each in configParameters:
        needle = each.strip()
        if needle:
            needle = u'{0}{1}{0}'.format(circumfix, needle)
            if haystack.find(needle) > -1:
                yield each


def __FindInReviewCommentWithNewSyntax(haystack, key, allowedValues=None):
    """
    :param haystack: Text, der durchsucht wird
    :param key: Schlüssel, nach dem gesucht wird (summary, defectClass, tag)
    :param allowedValues: Erlaubte Werte oder None, wenn alle Werte erlaubt sind
    :yield: Ermittelte Werte
    """
    regEx = u'#!{0} (.*?)!#'.format(key)
    for match in re.finditer(regEx, haystack):
        value = match.group(1)
        if not allowedValues or value in allowedValues:
            yield value


def UpdateRefOnReviews(reviews, reportRefPath):
    """
    Aktuelle die übergebenen Reviews, anhand des passenden REF-Pfades zum Report TestCase.

    @param reviews: Liste der Reviews, welche aktualisiert werden sollen.
    @type reviews: List->Review
    @param reportRefPath: REF Pfad zum Report TestCase
    @type reportRefPath: str
    @return: Liste der Reviews in der korrekten Reihenfolge
    @rtype: List->Review
    """
    for review in reviews:
        review.SetTestCaseRef(reportRefPath)

    resultList = GroupReviewsPerPackage(reviews)
    return resultList


def GroupReviewsPerPackage(reviews):
    """
    Gruppiert die übergebenen Reviews eines Packages anhand der Reviews auf den Ebenen.
    Dabei werden Reviews unterer Ebenen dem übergeordneten Review als Kommentar-Anhang mitgeteilt.

    @param reviews: Liste der Reviews in einem Package, welche gruppiert werden sollen.
    @type reviews: list[Review]
    @return: Liste der gruppierten Reviews
    @rtype: list[Review]
    """
    result = []

    currentLevel = 1000000
    lastReview = None
    for each in sorted(reviews):
        # Reviews auf gleicher Ebene erfassen, durch das sorted(reviews) gewinnt zeitlich
        # immer das Letzte Review -> ist dann das aktuellste
        if each.GetExecLevel() <= currentLevel:
            currentLevel = each.GetExecLevel()
            lastReview = each
            result.append(lastReview)
        elif lastReview is not None:
            lastReview.AppendReview(each)

    return result


class ReviewCommentException(Exception):
    """
    Ungültiger Review-Kommentar
    """

    @staticmethod
    def RaiseForDuplicateDefectClass(defectClass):
        msg = u'There can be only one defect class per review. ' \
              u'The defect class "{0}" could not be assigned.'.format(defectClass)
        raise ReviewCommentException(msg)

    @staticmethod
    def RaiseForDuplicateSummary(summary):
        msg = u'There can be only one summary per review. ' \
              u'The summary "{0}" could not be assigned.'.format(summary)
        raise ReviewCommentException(msg)

    @staticmethod
    def RaiseForDuplicateVerdict(verdict):
        msg = u'There can be only one verdict per review. ' \
              u'The verdict "{0}" could not be assigned.'.format(verdict)
        raise ReviewCommentException(msg)

    @staticmethod
    def RaiseForInvalidVerdict(verdict):
        msg = u'The value \'{0}\' is not a valid verdict.'.format(verdict)
        raise ReviewCommentException(msg)
