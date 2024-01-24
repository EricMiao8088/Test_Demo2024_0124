import sys
import os
#ApiClientPath = r'C:\Program Files\ECU-TEST '+'\2021.3'+'\Templates\ApiClient' #如果ECU-TEST是安装在默认位置，那只需要修改一下版本号
ApiClientPath = r'C:\Program Files\ECU-TEST '+'2023.4'+'\Templates\ApiClient'#注意：想要用package globalmapping，必须得用这行导入python库
sys.path.append(ApiClientPath)
from ApiClient import ApiClient
api = ApiClient()

def pkg2mapping(PackageFolderPath,xamfilename):
    globalmappingfile = api.GlobalMappingApi.CreateMapping()
    globalmappingfile.Save(xamfilename+'.xam')#默认保存在当前workspace下面的parameters文件夹
    '''
    首先找到Package文件夹下面所有的pkg文件夹
    '''
    for root,dirs,files in os.walk(PackageFolderPath):
        # print(root,dirs,files)
        for file in files:
            # print(file,'111')
            # print(root,'333')
            # print(os.path.join(root,file,'222'))
            if file.split('.')[-1] == 'pkg':
                pkgpath = os.path.join(root,file)
                # print(pkgpath.split('Packages'))
                ReferenceName = pkgpath.split('Packages')[-1][1:].split('.')[0]
                nameSpace = None #nameSpace如果为None，默认是当前workspace下面的package文件夹
                pkgmapping = api.PackageApi.MappingApi.CreatePackageMappingItem(pkgpath,referenceName=ReferenceName,
                                                                                namespace=nameSpace,checkTarget=True)
                openmappingfile = api.GlobalMappingApi.OpenMapping(xamfilename+'.xam')
                if openmappingfile.HasItem(pkgmapping) == False:
                    openmappingfile.AddItem(pkgmapping)
                    openmappingfile.Save()
        
pkgfolder = r'C:\ET2023_4\2_ECU-TEST_Advanced\Packages'
xamfilename = 'pkg2mapping'
pkg2mapping(pkgfolder,xamfilename)
