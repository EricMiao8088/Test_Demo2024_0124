# encoding: ISO-8859-1
import os
import re
from openpyxl import load_workbook

import tt

from lib.project.ParamGenerator import ParamGenerator
from lib.PathHandler import MakeAbsolutePkgPath
from application.api import Api
internalApi = Api.Api()


class ParamSetGenerator_one(ParamGenerator):
    """
    This is a small example on how a parameter generator should be implemented.
    """

    ID = '9554bd2c-566b-4972-9a66-fc7819ad8c7f'
    NAME = 'IO_ParamGenerator_one'
    DESCRIPTION = 'Read cells from excel'
    SERIALIZE = {'filename' : ('FILENAME', 'unicode', r''),
                 'sheetname': ('SHEETNAME', 'unicode', '')}
    COLUMN_CAN_Frame = 1
    COLUMN_CAN_Signal = 2
    COLUMN_frameCycle = 3
    COLUMN_Meas = 4
    COLUMN_testValues = 5
    COLUMN_getvalues = 6
    ecuKey = 'Powertrain'
    busKey = 'A-CAN'
    
    """
    Here the instance variables are declared for serialization.
    """

    def __init__(self):
        """
        Method, to initalize the instance variables.
        """
        self.filename = r''
        """
        Initialize the name of the file.
        """
        self.workbook = None
        self.sheetname = ''
        self.paramSheet = None
        self.objectApi = None

    def GetFileName(self):
        """
        Returns name of csv file.
        For use in the configuration dialog.
        @return: Name of csv file.
        @rtype: str
        """
        return self.filename

    def SetFileName(self, name):
        """
        Sets name of csv file.
        For use in the configuration dialog.
        @param filename: Name of csv file.
        @type filename: str
        """
        self.filename = name

    def SetSheetName(self, name):
        self.sheetname = name

    def GetDialog(self):
        """
        Returns the configuration dialog of the parameter generator.
        The dialog needs a reference to the parameter generator for getting and setting
        the parameter generator data.
        @rtype: L{DlgFileSelect}
        @return: wxDialog
        """
        from .DlgFileSelect import DlgFileSelect
        return DlgFileSelect(None, self, self.api.GetSetting('workspacePath'))

    def PreGeneration(self):
        """
        A file descriptor to the excel file will be opend.
        """
        filePath = self.GetFileName()

        self.workbook = load_workbook(filePath)
        self.paramSheet = self.workbook.get_sheet_by_name(self.sheetname)

    def GenerationIterator(self):
        """
        Method, to implement the iteration over the lines in the excel file.
        """        
        for row in range(self.paramSheet.max_row - 1):
                     
            frameCycle = self.paramSheet.cell(row=row + 2, column=self.COLUMN_frameCycle).value
            testValues = str(self.paramSheet.cell(row=row + 2, column=self.COLUMN_testValues).value)
            CAN_Frame = str(self.paramSheet.cell(row=row + 2, column=self.COLUMN_CAN_Frame).value)
            CAN_Signal = str(self.paramSheet.cell(row=row + 2, column=self.COLUMN_CAN_Signal).value)
            Meas = str(self.paramSheet.cell(row=row + 2, column=self.COLUMN_Meas).value)
            getvalues = str(self.paramSheet.cell(row=row + 2, column=self.COLUMN_getvalues).value)
            cycleData = self.CreateCycleData(name="[{name}]".format(name=str(Meas)))
            
            #pg = cycleData.PackageGenerator
            objectApi=internalApi.ObjectApi
			
            # Create Measurement mapping item
            #xaMeas = pg.CreateXaMeas('VALUE', self.ecuKey, label=Meas)
            xaMeas=objectApi.PackageApi.MappingApi.CreateMeasurementMappingItem(self.ecuKey,Meas,variableType='VALUE',referenceName='Meas')

            # Create Bus signal mapping item
            dbcData = internalApi.GetDataBrowser().BrowseBus(self.busKey)
            busEntities = dbcData.ListSignals(CAN_Frame, filter=CAN_Signal)
            signalPath = busEntities[0].GetPath()
            signalPathList = re.split(r'[/]', signalPath)
            nodeName = signalPathList[1]
            pduName = signalPathList[3]
            # Enable manipulation, i.e., bus signal can be written.
            #xaBus = pg.CreateXaBusLabelByPdu(self.busKey, pduName, CAN_Signal, manipulation=True, useRawValue=None, nodeName=nodeName)
            xaBus=objectApi.PackageApi.MappingApi.CreateBusSignalWithPduMappingItem(self.busKey,CAN_Signal,nodeName=nodeName,pduName=pduName,referenceName='CAN_Signal')
            xaBus.SetSignalManipulation(0)
            cycleData.AddParameter('testValues_str', testValues)
            cycleData.AddParameter('getvalues_str', getvalues)
            cycleData.AddParameter('frameCycle', frameCycle)
            #cycleData.AddMappingByXAKey('CAN_Signal', xaBus)
            #cycleData.AddMappingByXAKey('Meas', xaMeas)
            cycleData.AddMappingItem(xaBus)
            cycleData.AddMappingItem(xaMeas)
            
            yield cycleData

    def Check(self):
        '''
        Is executed when the containing project is checked.
        Verify the existence of the file.
        '''
        errors = []
        try:
            self.__ValidatePath(self.filename)
        except Exception as e:
            errors.append(str(e))

        return errors

    def __ValidatePath(self, filePath):
        '''
        Checks the referenced file path. Returns an absolute path, if the referenced file exist.
        
        @param filePath: absolute or relative to the packages directory.
        @type filePath: unicode
        
        @return: absolute file path
        @rtype: unicode
        
        @raise tt.Error: if the referenced file path is invalid.  
        '''
        if not filePath:
            raise tt.Error('Undefined excel file path!')

        filePath = MakeAbsolutePkgPath(filePath)
        if not os.path.isfile(filePath):
            raise tt.Error('"%s" is not a valid file path!' % filePath)

        return filePath
