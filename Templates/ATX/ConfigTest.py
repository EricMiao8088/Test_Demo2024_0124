# -*- coding: utf-8 -*-

'''
Created on 27.10.2014

:author: Philipp Schneider <philipp.schneider@tracetronic.de>
'''

__copyright__ = "Copyright © by TraceTronic GmbH, Dresden"
__license__ = "This file is distributed as an integral part of TraceTronic's software products " \
              "and may only be used in connection with and pursuant to the terms and conditions " \
              "of a valid TraceTronic software product license."

import unittest

from mockito import mock, when

from .Config import Config, SettingsFromServerMode, Settings


class ConfigTest(unittest.TestCase):

    def testGetUnknownSetting(self):
        '''
        Prüft das bei unbekannten Settings (auch in der config.xml) ein None zurückgegeben wird.
        '''
        # ARRANGE
        settingName = u'unknownSetting'
        reportApiMock = mock()
        when(reportApiMock).GetSetting(settingName).thenReturn(None)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)

        # ASSERT
        self.assertEqual(None, value,
                         (u"Der Settingswert sollte None lauten für unbekannt Settings."))

    def testGetValidSetting(self):
        '''
        Prüft ob bei valider Setting diese auch korrekt zurückgegeben wird.
        '''
        # ARRANGE
        settingName = u'serverPort'
        expectedValue = 8085
        reportApiMock = mock()
        when(reportApiMock).GetSetting(settingName).thenReturn(expectedValue)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        # ASSERT
        self.assertEqual(expectedValue, value,
                         (u"Der Settingswert sollte {0} lauten.").format(expectedValue))

    def testGetValidButUnknownReportApiSetting(self):
        '''
        Prüft das aus der config.xml der Default-Wert für eine gültige Settings in der config.xml
        aber noch nicht bekannte Settings in der ReportApi (Problem AutoUpdate) ermittelt wird.
        '''
        # ARRANGE
        settingName = u'serverURL'
        reportApiMock = mock()
        when(reportApiMock).GetSetting(settingName).thenReturn(None)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        # ASSERT
        self.assertEqual(u"127.0.0.1", value,
                         (u"Der Defaultwert der noch nicht bekannten Settings sollte aus der "
                          u"config.xml ausgelesen werden."))

    def testExternalSettingsOverwriteInternal(self):
        # ARRANGE
        settingName = u'maxUploadTries'
        expectedValue = 333
        reportApiMock = mock()
        when(reportApiMock).GetSetting(settingName).thenReturn(1230975)
        Config.LoadExternalSettings([{"key": settingName, "value": expectedValue}],
                                    SettingsFromServerMode.ALWAYS)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        Config.ClearExternalSettings()

        # ASSERT
        self.assertEqual(expectedValue, value,
                         (u"Der Settingswert sollte {0} lauten.").format(expectedValue))

    def testExternalSettingsRespectDefaultValue(self):
        # ARRANGE
        settingName = u'maxUploadTries'
        reportApiMock = mock()
        Config.LoadExternalSettings([], SettingsFromServerMode.ALWAYS)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        Config.ClearExternalSettings()

        # ASSERT
        self.assertEqual(u"42", value,
                         (u"Der Defaultwert der nicht gesetzten Settings sollte aus der "
                          u"config.xml ausgelesen werden."))

    def testExternalSettings_UseKeyword(self):
        # ARRANGE
        settingName = u'maxUploadTries'
        reportApiMock = mock()
        remoteConfigValue = u'RemoteConfiguration'
        keyword = u'Friendship is magic'
        when(reportApiMock).GetSetting(settingName).thenReturn(keyword)
        Config.LoadExternalSettings([{u'key': settingName, u'value': remoteConfigValue}],
                                    SettingsFromServerMode.WHEREKEYWORD, keyword)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        Config.ClearExternalSettings()

        # ASSERT
        self.assertEqual(remoteConfigValue, value,
                         u'Die Konfiguration vom Server sollte verwendet worden sein.')

    def testExternalSettings_UseKeyword_SkipServerSettings(self):
        # ARRANGE
        settingName = u'maxUploadTries'
        reportApiMock = mock()
        keyword = u'Friendship is magic'
        settingValue = u'anything'
        when(reportApiMock).GetSetting(settingName).thenReturn(settingValue)
        Config.LoadExternalSettings([{u'key': settingName, u'value': u'RemoteConfiguration'}],
                                    SettingsFromServerMode.WHEREKEYWORD, keyword)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        Config.ClearExternalSettings()

        # ASSERT
        self.assertEqual(settingValue, value,
                         u'Die Konfiguration vom Server sollte ignoriert worden sein.')

    def testExternalSettings_UseKeyword_UndefindedOnServerUsesDefault(self):
        # ARRANGE
        settingName = u'maxUploadTries'
        reportApiMock = mock()
        keyword = u'Friendship is magic'
        when(reportApiMock).GetSetting(settingName).thenReturn(keyword)

        Config.LoadExternalSettings([], SettingsFromServerMode.WHEREKEYWORD, keyword)

        # ACT
        value = Config.GetSetting(reportApiMock, settingName)
        Config.ClearExternalSettings()

        # ASSERT
        self.assertEqual('42', value,
                         u'Der Default-Wert aus der config.xml sollte verwendet worden sein.')


class ConfigTest(unittest.TestCase):

    def test_ReadStringSetting(self):
        # ARRANGE
        settings2 = {'horst': '34'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetString('horst')

        self.assertEqual('34', value)

    def test_ReadBooleanSettingWhichIsTrue(self):
        # ARRANGE
        settings2 = {'isHorstCool': 'True'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetBoolean('isHorstCool')

        self.assertEqual(True, value)

    def test_ReadBooleanSettingWhichIsFalse(self):
        # ARRANGE
        settings2 = {'isHorstHot': 'False'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetBoolean('isHorstHot')

        self.assertEqual(False, value)

    def test_ReadListSetting(self):
        # ARRANGE
        settings2 = {'colors': 'pink;cyan;yellow'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetList('colors')

        self.assertEqual(['pink', 'cyan', 'yellow'], value)

    def test_ReadListSettingWithOneEntry(self):
        # ARRANGE
        settings2 = {'colors': 'pink'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetList('colors')

        self.assertEqual(['pink'], value)

    def test_ReadListSettingWithTrailingSemicolon(self):
        # ARRANGE
        settings2 = {'colors': 'pink;'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetList('colors')

        self.assertEqual(['pink'], value)

    def test_ReadListSettingWithEmptyValue(self):
        # ARRANGE
        settings2 = {'colors': ''}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetList('colors')

        self.assertEqual([], value)

    def test_ReadListSettingWithNoneValue(self):
        # ARRANGE
        settings2 = {'colors': None}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetList('colors')

        self.assertEqual([], value)

    def test_ReadDictSetting(self):
        # ARRANGE
        settings2 = {'abilities': 'dex=3;int=7'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetDict('abilities')

        self.assertEqual({'dex': '3', 'int': '7'}, value)

    def test_ReadDictSettingWithOneEntry(self):
        # ARRANGE
        settings2 = {'abilities': 'dex=3'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetDict('abilities')

        self.assertEqual({'dex': '3'}, value)

    def test_ReadDeicSettingWithEmptyValue(self):
        # ARRANGE
        settings2 = {'abilities': ''}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetDict('abilities')

        self.assertEqual({}, value)

    def test_ReadDictSettingWithNoneValue(self):
        # ARRANGE
        settings2 = {'abilities': None}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT
        value = settings.GetDict('abilities')

        self.assertEqual({}, value)

    def test_ReadDictSettingWithInvalidValue(self):
        # ARRANGE
        settings2 = {'abilities': 'dex:3;int=7'}
        reportApi = ReportApiDummy(settings2)
        settings = Settings(reportApi)

        # ACT & ASSERT
        self.assertRaises(Exception, settings.GetDict, 'abilities')


class ReportApiDummy(object):
    def __init__(self, settings):
        self._settings = settings

    def GetSetting(self, name):
        return self._settings.get(name, u'')


if __name__ == "__main__":
    unittest.main()
