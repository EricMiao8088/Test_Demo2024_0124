# encoding: ISO-8859-1
import os
import re
from openpyxl import load_workbook

import tt

from tts.core.project.generator.ParamGenerator import ParamGenerator
from tts.lib.common.files.PathHandler import MakeAbsolutePkgPath
from application.api import Api
internalApi = Api.Api()


class ParamSetGenerator_input(ParamGenerator):
    """
    This is a small example on how a parameter generator should be implemented.
    """

    ID = u'329deeae-f7td-61o9-90p8-d412B8r1hhdU'
    NAME = u'IO_ParamGenerator_input'
    DESCRIPTION = u'Read cells from excel'
    SERIALIZE = {'filename' : ('FILENAME', 'unicode', r''),
                 'sheetname': ('SHEETNAME', 'unicode', u'')}
    COLUMN_currentTime_Value = 1
    # COLUMN_db = 2
    # COLUMN_variable_name = 3
    # COLUMN_com_variable = 4
    # COLUMN_Min_Value = 5
    # COLUMN_Middle_Value = 6
    # COLUMN_Max_Value = 7
    # COLUMN_Tolerance_Value = 8
    # COLUMN_CAN_Signal = 9
    # COLUMN_CAN_Frame = 10
    # COLUMN_CAN_Channel = 11

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
        self.sheetname = u''
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
        return DlgFileSelect(None, self, self.api.GetSetting(u'workspacePath'))

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
        for row in range(self.paramSheet.max_row - 2):

            current_Value = str(self.paramSheet.cell(row=row + 2, column=self.COLUMN_currentTime_Value).value)
            # com_variable = str(self.paramSheet.cell(row=row + 3, column=self.COLUMN_com_variable).value)
            # Min_Value = int(self.paramSheet.cell(row=row + 3, column=self.COLUMN_Min_Value).value)
            # Middle_Value = int(self.paramSheet.cell(row=row + 3, column=self.COLUMN_Middle_Value).value)
            # Max_Value = int(self.paramSheet.cell(row=row + 3, column=self.COLUMN_Max_Value).value)
            # Tolerance_Value = int(self.paramSheet.cell(row=row + 3, column=self.COLUMN_Tolerance_Value).value)
            # CAN_Signal = str(self.paramSheet.cell(row=row + 3, column=self.COLUMN_CAN_Signal).value)
            # CAN_Frame = str(self.paramSheet.cell(row=row + 3, column=self.COLUMN_CAN_Frame).value)
            # CAN_Channel = str(self.paramSheet.cell(row=row + 3, column=self.COLUMN_CAN_Channel).value)
            # testValues_list = []
            # testValues_list.append(Min_Value)
            # testValues_list.append(Middle_Value)
            # testValues_list.append(Max_Value)
            # block_name = str(str(CAN_Channel) + '_' + str(CAN_Frame))

            cycleData = self.CreateCycleData(name="[{name}]".format(name='current_Time_'+str(current_Value)))
            
            cycleData.AddParameter('Test_Value1', int(current_Value))
            # cycleData.AddParameter('com_variable', str(com_variable))
            # cycleData.AddParameter('testValues_list', testValues_list)
            # cycleData.AddParameter('tolerance', int(Tolerance_Value))
            # cycleData.AddParameter('block_name', str(block_name))
            # cycleData.AddParameter('CAN_Signal', str(CAN_Signal))
            
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
            raise tt.Error(u'Undefined excel file path!')

        filePath = MakeAbsolutPkgPath(filePath)
        if not os.path.isfile(filePath):
            raise tt.Error(u'"%s" is not a valid file path!' % filePath)

        return filePath
