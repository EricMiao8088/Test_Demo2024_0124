import winreg as winreg
import os
import sys

versionNumber='2024.2'
reg=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\TraceTronic\ecu.test {}'.format(str(versionNumber)))
etDir=winreg.QueryValueEx(reg,'Path')[0]
reg.Close()
ApiClientPath=os.path.join(etDir,'Templates\ApiClient')
sys.path.append(ApiClientPath)
from ApiClient import ApiClient
api=ApiClient()

def Disable(MainPackagePath,PRJName):
    prj=api.ProjectApi.OpenProject(PRJName)
    PkgCallList=prj.GetPackageCalls()
    PkgList=[]
    for j in PkgCallList:
        PKG=j.GetAbsolutePath()
        PkgList.append(PKG)
    LineNo=PkgList.index(MainPackagePath)+1
    Name=PkgList[LineNo]

    pkg=api.PackageApi.OpenPackage(Name)
    TestStepList=pkg.GetTestSteps(skipDisabledSteps=True, recursive=False, whiteList=None, blackList=None)
    for i in TestStepList:
        i.SetEnabled(state=False)
    pkg.Save(Name)  

