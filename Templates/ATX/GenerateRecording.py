# -*- coding: utf-8 -*-

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import hashlib
import json
import os
from collections import namedtuple, defaultdict, OrderedDict

from lib.report.db import Recording
from log import LEVEL_NORMAL, DPrint, ExcPrint

from .TraceMetadata import GenerateRecordingMetadata, GenerateTraceMetadata
from .Utils import GetExtendedWindowsPath, CopyFile, MakeCompressedZip, GetConsumedFilesFromJobItem, \
    HashFileContents, FindAssociatedFilesForTrace, FileToArchive

TraceFileInfo = namedtuple('TraceFileInfo', ['hash', 'associatedFiles'])


class GenerateRecording(object):
    """
    Erstellt die ATX-Daten für die Recordings und sammelt alle Tracedateien ein,
     die mit in die hochzuladene Zip kommen sollen.
    """

    def __init__(self, archive, pkgFiles, report, workspaceDir, dataTypes, primitiveConstantType):
        self.__archive = archive
        self.__report = report
        self.__workspaceDir = workspaceDir
        self.__dataTypes = dataTypes
        self.__primitiveConstantType = primitiveConstantType
        self.__pkgFiles = pkgFiles

        # Dict der Aufnahmedateien samt Datei-Hash welche archiviert/gespeichert werden sollen.
        self.__traceFilesToArchive = {}
        # Dict der Aufnahmedateien auf die ermittelten Trace-Metadaten.
        self.__traceMetadata = {}
        self.__recordingType = None

        self.__allTraceFiles = []

    def GetTraceFiles(self):
        """
        :return: Liste aller Trace-Dateien jeweils als relativer Dateipfad
        :rtype: list[str]
        """
        return self.__allTraceFiles

    def CreateRecordings(self, package, reportPkg):
        """
        Erstellt Aufnahmen in ATX und ermittelt Metadaten.

        :param package: Package Objekt aus der Report API.
        :type package: tts.core.report.parser.Package.Package
        :param reportPkg: das neu erzeugte TEST-CASE Objekt
        :type reportPkg: OrderedDict
        """
        DPrint(LEVEL_NORMAL, '', 'Create Recordings')
        reportDir = self.__report.GetDbDir()
        archiveMetadata = self.__archive['recordingMetadata'] and self.__archive['recordings']

        createdFiles = set()
        consumedFiles = set()
        recordingMetadata = defaultdict(list)

        # Aufnahmen aus Aufnahmentabelle
        recordings = {
            recording.GetRecordingId(): recording
            for recording in package.GetRecordings().IterRecordings()
        }

        # verwendete Aufnahmen aus Traceanalysen
        for analysisJobItem in package.IterAnalysisJobs(True):
            job = next(analysisJobItem.IterTraceItems(), None)
            if job:
                for recording in GetConsumedFilesFromJobItem(job):
                    recordings[recording.GetRecordingId()] = recording
                    consumedFiles.add(recording.GetResolvedPath(reportDir, self.__workspaceDir))

        # Informationen pro Datei aggregieren
        for recording in recordings.values():
            filePath = recording.GetResolvedPath(reportDir, self.__workspaceDir)
            try:
                if archiveMetadata:
                    recordingDict = GenerateRecordingMetadata(filePath, recording)
                else:
                    recordingDict = {}
                recordingMetadata[filePath].append(recordingDict)

            except Exception:
                # Wenn die Extraktion auf Grund eines unbekannten Formates nicht möglich ist
                # ist die Okay, bedeutet aber das der TREX nicht funktioniert.
                ExcPrint(level=LEVEL_NORMAL,
                         prefix=_('Extraktion von Aufnahmemetadaten fehlgeschlagen'))

            # Fix für alte ECU-TEST Versionen: recording.GetGroupName() == "TC Variables"
            FLAG_STIMULATION = getattr(Recording, 'SOURCE_FLAG_STIMULATION', 0x100)  # ab ET 8.0
            isManualRecording = (recording.GetSource() & 0xFF == Recording.SOURCE_MANUAL and
                                 recording.GetGroupName() != 'TC Variables')
            if not isManualRecording and recording.GetSource() & FLAG_STIMULATION == 0:
                createdFiles.add(filePath)
            else:
                consumedFiles.add(filePath)

        # Informationen pro Datei auswerten
        for filePath, details in recordingMetadata.items():
            inout = 'IN' if filePath in consumedFiles else ""
            if filePath in createdFiles:
                inout += 'OUT'

            extFilePath = GetExtendedWindowsPath(filePath)
            fileHash = HashFileContents(extFilePath) if os.path.exists(extFilePath) else None

            # TODO: associated files auch in md5 hash einbeziehen?
            associatedFiles = FindAssociatedFilesForTrace(filePath)

            self.__CreateTestArgumentElementRecording(reportPkg, filePath, inout, fileHash,
                                                      associatedFiles)
            if fileHash is not None and archiveMetadata:
                try:
                    self.__traceMetadata[extFilePath] = GenerateTraceMetadata(
                        extFilePath, fileHash, details, filePath in createdFiles)
                except Exception:
                    # Wenn die Extraktion auf Grund eines unbekannten Formates nicht möglich ist
                    # ist die Okay, bedeutet aber das der TREX nicht funktioniert.
                    ExcPrint(level=LEVEL_NORMAL,
                             prefix=_('Extraktion von Aufnahmemetadaten fehlgeschlagen'))

    def __CreateTestArgumentElementRecording(self, reportPkg, filePath, direction, fileHash,
                                             associatedFiles):
        """
        Fügt ein neues TEST-ARGUMENT-ELEMENT für Aufnahmen in die ARGUMENT-LIST ein, falls es
        nicht schon vorhanden ist.
        @param reportPkg: das neu erzeugte TEST-CASE Objekt
        @type reportPkg: OrderedDict
        @param filePath: Pfad zur Trace-Datei
        @type filePath: str
        @param direction: Richtung des Parameters
        @type direction: str
        @param fileHash: MD5-Hash von Datei oder None, wenn sie nicht mehr existiert
        @type fileHash: str
        @param associatedFiles: Zusätzliche zugehörige Dateien (z.B. Side-Car-Files)
        @type associatedFiles: Iterable[str]
        """
        assert direction in [u'IN', u'OUT', u'INOUT', u'SUBJECT']

        # ARGUMENT-LIST initialisieren, falls noch nicht vorhanden
        if not reportPkg[u'ARGUMENT-LIST']:
            # RETURN wird ignoriert, da es nicht benötigt wird
            reportPkg[u'ARGUMENT-LIST'] = {u'ARGUMENTS': []}

        # Daten Typ für Recording anlegen, falls noch nicht vorhanden
        if self.__recordingType is None:
            self.__recordingType = OrderedDict([
                (u'@type', u'APPLICATION-PRIMITIVE-DATA-TYPE'),
                (u'SHORT-NAME', u'Recording')
            ])
            self.__dataTypes[u'ELEMENTS'].append(self.__recordingType)

        if fileHash:
            extFilePath = GetExtendedWindowsPath(filePath)
            self.__AddTraceToArchive(extFilePath, fileHash, associatedFiles)
        else:
            fileHash = u'not_found_{0}'.format(hashlib.md5(filePath.encode(u'utf-8')).hexdigest())

        # neues TEST-ARGUMENT-ELEMENT Objekt erzeugen
        newTestArgElem = OrderedDict([
            (u'@type', u'TEST-ARGUMENT-ELEMENT'),
            (u'SHORT-NAME', u'trace_{0}'.format(fileHash)),
            (u'TYPE-REF', {
                u'@DEST': self.__primitiveConstantType[u'@type'],
                u'#': u'/{0}/{1}'.format(self.__dataTypes[u'SHORT-NAME'],
                                         self.__recordingType[u'SHORT-NAME'])
            }),
            (u'DIRECTION', direction),
            (u'LITERAL-VALUE', {u'TEXT-VALUE-SPECIFICATION': {u'VALUE': filePath}}),
        ])

        # prüfen ob bereits ein Objekt exisistiert für die Datei
        for eachTestArgElem in reportPkg[u'ARGUMENT-LIST'][u'ARGUMENTS']:
            if eachTestArgElem[u'SHORT-NAME'] == newTestArgElem[u'SHORT-NAME']:
                # das Element ist bereits erfasst
                return

        # Objekt zu Arguments hinzufügen
        reportPkg[u'ARGUMENT-LIST'][u'ARGUMENTS'].append(newTestArgElem)

    def __AddTraceToArchive(self, path, fileHash, associatedFiles):
        """
        Erfasst die übergebene Aufnahmedatei für eine mögliche Archivierung.
        @param path: Dateipfad.
        @type path: str
        @param fileHash: Hash-Summe der Datei um beim Zip später Dopplungen zu erkennen
        @type fileHash: str
        @param associatedFiles: Zusätzliche zugehörige Dateien (z.B. Side-Car-Files)
        @type associatedFiles: Iterable[str]
        """
        # Nur übernehmen, wenn Recordings explizit erwünscht!
        if self.__archive[u'recordings']:
            extPath = GetExtendedWindowsPath(path)
            if os.path.exists(extPath):
                self.__traceFilesToArchive[extPath] = TraceFileInfo(
                    hash=fileHash,
                    associatedFiles=[
                        GetExtendedWindowsPath(associatedFile)
                        for associatedFile in associatedFiles
                        if os.path.exists(GetExtendedWindowsPath(associatedFile))
                    ]
                )
                self.__allTraceFiles.append(extPath)

    def MakeTraceFileArchiveFiles(self):
        """
        Fügt alle gefundenen Aufnahmedatei als komprimierte Zip Datei für die Archivierung hinzu.

        :return Liste der Tracedatein, die zu archivieren sind
        :rtype list[FileToArchive]
        """
        # Nur übernehmen, wenn Recordings explizit erwünscht!
        if not self.__archive[u'recordings']:
            return []

        DPrint(LEVEL_NORMAL, '', 'Prepare {} recording files for zip archiving'.format(
            len(self.__traceFilesToArchive)))
        traceFiles = []
        for eachTraceFile, eachInfo in self.__traceFilesToArchive.items():
            filename = os.path.basename(eachTraceFile)

            # Sicherstellen, dass jede Aufnahme ein eigenes Verzeichnis besitzt,
            # aber Doppelungen auch erkennen und wiederverwenden
            randomDirName = eachInfo.hash

            # TTSTM-2604: AS und AS3 Traces nicht kompimiert übertragen, da diese schon komprimiert
            # sind; MP4 ebenfalls nicht -> lohnt sich nicht
            if os.path.splitext(filename)[1].lower() in ('.astrace', '.as3trace', '.mp4'):
                tmpFile = GetExtendedWindowsPath(os.path.join(self.__report.GetReportDir(),
                                                              randomDirName,
                                                              u'{0}'.format(filename)))
                # Wenn die Datei noch nicht bekannt ist, dann zur Verfügung stellen
                if not os.path.exists(tmpFile):
                    CopyFile(eachTraceFile, tmpFile)
            else:
                tmpFile = GetExtendedWindowsPath(os.path.join(self.__report.GetReportDir(),
                                                              randomDirName,
                                                              u'{0}.zip'.format(filename)))

                # Wenn die Datei noch nicht bekannt ist, dann als Zip zur Verfügung stellen
                if not os.path.exists(tmpFile):
                    MakeCompressedZip([eachTraceFile] + eachInfo.associatedFiles, tmpFile)

            traceFiles.append(FileToArchive(tmpFile, eachTraceFile))

        # Nach Erzeugung die gefundenen Dateien für diesen refPath leeren!
        self.__traceFilesToArchive = {}
        return traceFiles

    def MakeTraceMetadataArchiveFiles(self):
        """
        Erstellt alle Trace-Metadatendateien und fügt sie hinzu.

        :return Liste der Trace-Metadaten, die zu archivieren sind
        :rtype list[FileToArchive]
        """
        if not self.__archive[u'recordingMetadata'] or not self.__archive[u'recordings']:
            return []

        DPrint(LEVEL_NORMAL, '', 'Prepare {} recording metadata files for zip archiving'.format(
            len(self.__traceMetadata)))
        traceMetadataFiles = []
        for filePath, metadata in self.__traceMetadata.items():
            fileName = os.path.basename(filePath)

            tmpFile = GetExtendedWindowsPath(os.path.join(
                self.__report.GetReportDir(),
                metadata['md5Hash'], u'{}.metadata'.format(fileName)))
            if not os.path.exists(os.path.dirname(tmpFile)):
                os.makedirs(os.path.dirname(tmpFile))
            with open(tmpFile, 'wb') as fp:
                fp.write(json.dumps(
                    metadata, separators=(',', ':'), ensure_ascii=True).encode('ascii'))

            traceMetadataFiles.append(FileToArchive(tmpFile, u'{}.metadata'.format(filePath)))

        self.__traceMetadata = {}
        return traceMetadataFiles
