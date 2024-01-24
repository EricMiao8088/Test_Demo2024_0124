# -*- coding: utf-8 -*-

'''
Created on 28.10.2014

:author: Philipp Schneider <philipp.schneider@tracetronic.de>
'''

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

try:
    from urllib.parse import quote
except ImportError:  # anderer Importpfad für Python 2.7
    from urllib import quote

from .UploadSettings import UploadSettings
from .Version import GetDownloadLinkForATXMako, _GetDownloadLinkForATXMako


class VersionTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def GetClientVersion(self):
        from constantsVersionInfo import GetFullName, GetVersionString
        return quote(u"{0}__v{1}".format(GetFullName().replace(" ", "_"), GetVersionString()))

    def testGetDownloadLinkForATXMakoWithoutContextPath(self):
        # ARRANGE
        uploadSettings = UploadSettings(u'localhost', 8080, False, u'', u'', None, 1)
        
         # ACT
        link = GetDownloadLinkForATXMako(uploadSettings)
        # ASSERT
        self.assertEqual(u"http://localhost:8080/api/download-file/ATXGenerator?clientVersion={0}&"
                         u"authKey=".format(self.GetClientVersion()), link)

    def testGetDownloadLinkForATXMakoWithoutHttps(self):
        # ARRANGE
        uploadSettings = UploadSettings(u'localhost', 8080, False, u'ttstm', u'MyKey', None, 1)
        
        # ACT
        link = GetDownloadLinkForATXMako(uploadSettings)
        # ASSERT
        self.assertEqual(u"http://localhost:8080/ttstm/api/download-file/ATXGenerator?"
                         u"clientVersion={0}&authKey=MyKey".format(self.GetClientVersion()), link)

    def testGetDownloadLinkForATXMakoWithHttps(self):
        # ARRANGE
        uploadSettings = UploadSettings(u'localhost', 8080, True, u'ttstm', u'Key', None, 1)
        
        # ACT
        link = GetDownloadLinkForATXMako(uploadSettings)
        
        # ASSERT
        self.assertEqual(u"https://localhost:8080/ttstm/api/download-file/ATXGenerator?"
                         u"clientVersion={0}&authKey=Key".format(self.GetClientVersion()), link)

    def testGetDownloadLinkForATXMako_QuoteSpecialChars(self):
        # ARRANGE
        uploadSettings = UploadSettings(u'localhost', 8080, True, u'ttstm', u'Key', None, 1)

        # ACT
        link = _GetDownloadLinkForATXMako(uploadSettings, "IQTEST###ALPHA###2011.11.11")

        # ASSERT
        self.assertEqual(u"https://localhost:8080/ttstm/api/download-file/ATXGenerator?"
                         u"clientVersion=IQTEST%23%23%23ALPHA%23%23%232011.11.11&authKey=Key", link)


if __name__ == "__main__":
    unittest.main()
