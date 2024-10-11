import os
import os.path
import sys
ApiPath = r'C:\Program Files\ECU-TEST 2022.4\Templates\ApiClient'#需要填写一下ApiClient的路径，如果安装在C盘下，只要改个ET的版本号
sys.path.append(ApiPath)
from ApiClient import ApiClient
api = ApiClient()


def Insert(rootDir,InsertPkgPath):
    for parent, dirnames, filenames in os.walk(path):
        print(parent,"---",dirnames,"***",filenames,"+++",len(filenames))
        if len(filenames) != 0:#filenames里面有pkg文件
            for pkg in filenames:
                if '.prj' in pkg:
                    None
                else:
                    pkgpath = os.path.join(parent,pkg)#获取每个pkg的路径
                    openpkg = api.PackageApi.OpenPackage(pkgpath)#打开pkg
                    '''
                    先删除之前的错误pkg
                    '''
                    targetpkg = openpkg.GetTestStepByLineNo(3)#获取的是第三个步骤的package
                    openpkg.RemoveTestStep(targetpkg)
                    createpkg = api.PackageApi.TestStepApi.CreateTsPackage(ResetPkgPath)#创建reference pkg
                    openpkg.InsertTestStep(createpkg,2)#插入package
                    openpkg.Save()#保存pkg

if __name__ == "__main__":
    path = r'C:\ET2022_4\1_Exercises\2_ECU-TEST_Advanced\Packages\滴滴Test'#需要填写pkg的总文件夹路径
    ResetPkgPath = r'C:\ET2022_4\1_Exercises\2_ECU-TEST_Advanced\Packages\StartWatchTime.pkg'#需要Reset.pkg的路径
    Insert(path,ResetPkgPath)

