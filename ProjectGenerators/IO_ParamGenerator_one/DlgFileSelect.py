# -*- coding: ISO-8859-1 -*-

import wx
import openpyxl

LBL1 = "Please select your Excel file"
LBL2 = "Please indicate the sheet name"

class DlgFileSelect(wx.Dialog):
    
    def __init__(self, parent, aPkgGenerator, workspacePath=None):
        wx.Dialog.__init__(self, parent, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, title = aPkgGenerator.GetName())
        
        self.thePkgGenerator = aPkgGenerator
        
        label1 = wx.StaticText(self, label = LBL1)
        label2 = wx.StaticText(self, label = LBL2)
        
        self.txtFileName = wx.TextCtrl(self, value = aPkgGenerator.GetFileName())
        
        self.myComboBox = wx.ComboBox(self, choices = [], style = wx.CB_READONLY)
        
        # configure buttons: "OK", "Cancel" and "Browse"
        
        button_OK = wx.Button(self, label = "OK")
        button_OK.SetToolTip("OK")
        button_OK.SetDefault()
        button_OK.Bind(wx.EVT_BUTTON, self.OnCmdOkButton)
        
        button_Cancel = wx.Button(self, label = "Cancel")
        button_Cancel.SetToolTip("Cancel")
        button_Cancel.Bind(wx.EVT_BUTTON, self.OnCmdCancelButton)
        
        button_Browse = wx.Button(self, label = "...")
        button_Browse.SetMinSize(wx.Size(23, 23))
        button_OK.SetToolTip("Please select an Excel File")
        button_Browse.Bind(wx.EVT_BUTTON, self.OnCmdBrowseButton)
        
        # configure button layout
        
        sizerButtons = wx.BoxSizer(wx.HORIZONTAL)
        sizerButtons.Add(button_OK, 0, border=5, flag=wx.ALL)
        sizerButtons.Add(button_Cancel, 0, border=5, flag=wx.ALL)

        boxSizer = wx.BoxSizer(wx.HORIZONTAL)
        boxSizer.Add(self.txtFileName, 1, border=0, flag=0)
        boxSizer.AddSpacer(8)
        boxSizer.Add(button_Browse, 0, border=0, flag=0)

        ctrlSizer = wx.BoxSizer(wx.VERTICAL)
        ctrlSizer.Add(label1, flag=wx.EXPAND)
        ctrlSizer.AddSpacer(8)
        ctrlSizer.Add(boxSizer, flag=wx.EXPAND)
        ctrlSizer.AddSpacer(8)
        ctrlSizer.Add(label2, flag=wx.EXPAND)
        ctrlSizer.AddSpacer(8)
        ctrlSizer.Add(self.myComboBox, flag=wx.EXPAND)

        sizerMain = wx.BoxSizer(wx.VERTICAL)
        sizerMain.Add(ctrlSizer, 0, border=15, flag=wx.ALL | wx.EXPAND)
        sizerMain.AddStretchSpacer()
        sizerMain.Add(sizerButtons, 0, border=0, flag=wx.ALIGN_BOTTOM | wx.ALIGN_CENTER)

        self.SetSizer(sizerMain)

        self.SetClientSize(wx.Size(356, 180))
        
    def OnCmdOkButton(self, event):
        self.thePkgGenerator.SetFileName(self.txtFileName.GetValue())
        self.thePkgGenerator.SetSheetName(self.myComboBox.GetStringSelection())
        self.EndModal(wx.ID_OK)
        
    def OnCmdCancelButton(self, event):
        self.EndModal(wx.ID_CANCEL)
        
    def OnCmdBrowseButton(self, event):
        fileDlg = wx.FileDialog(parent = self,
                                message = "Please select an Excel file",
                                wildcard = "File|*.*",
                                defaultDir = r"",
                                defaultFile = "")
        
        if fileDlg.ShowModal() == wx.ID_OK:
            self.txtFileName.SetValue(fileDlg.GetPath())
            wb = openpyxl.load_workbook(self.txtFileName.GetValue())
            self.myComboBox.SetItems(wb.sheetnames)
        fileDlg.Destroy()

