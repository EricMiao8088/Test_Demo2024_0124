import os
import os.path
import sys
ApiPath = r'C:\Program Files\ECU-TEST 2022.4\Templates\ApiClient'#需要填写一下ApiClient的路径，如果安装在C盘下，只要改个ET的版本号
sys.path.append(ApiPath)
from ApiClient import ApiClient
api = ApiClient()
def search(path,keyFolder,BusPkgFolder):
    '''
    path可以是V216_IEM_SiC_PP20230307的路径，也可以的Packages的路径
    keyFolder是关键文件夹，就是存放要修改的package，例如TC_SWTD这类文件夹
    BusPkgFolder是报文package所在的文件夹

    '''
    for parent, dirnames, filenames in os.walk(path):
        if keyFolder in parent:
            for i in range(len(filenames)):
                modifyPkg = os.path.join(parent,filenames[i])
                print(modifyPkg)
                pkg = api.PackageApi.OpenPackage(modifyPkg)#填写要修改的package的路径
                a = pkg.GetTestSteps(recursive=True)
                for i in a:
                    if i.GetType() == 'TsWriteBusSignalGroupCyclic' or i.GetType() == 'TsWriteBusSignalGroup' or i.GetType() == 'TsReadBusSignalGroup':#查看error位置是否是Write BusSignalGroup
                        #print('步骤类型是：{}'.format(i.GetType()))
                        Nu = i.GetLineNo()#获取BUS步骤的位置
                        if pkg.GetTestStepByLineNo(Nu-1).GetType() != 'TsBlock':
                            print('类型错误，步骤位置是：{}'.format(Nu))
                        #print('步骤的名字是：{0},上一个层级的类别是：{1}'.format(pkg.GetTestStepByLineNo(Nu).GetActionColumnText(),pkg.GetTestStepByLineNo(Nu-1).GetType()))
                        #print('步骤位置是：{}'.format(Nu))
                        Errorname = i.GetActionColumnText()#获取这个error步骤的相关名字
                        BusSignalGroupName = i.GetActionColumnText().split('/')[-1]#获取writesignalgroup的名字
                        #print('错误名字是{}'.format(BusSignalGroupName))
                        '''
                        要遍历package的名字，找到对应bussignalgroup的package
                        '''
                        pkgpath = os.path.join(BusPkgFolder,BusSignalGroupName+'.pkg')
                        #print(pkgpath)
                        pkg.GetTestStepByLineNo(Nu).SetEnabled(False)#将signalgroup注释掉
                        insertpkg = api.PackageApi.TestStepApi.CreateTsPackage(pkgpath)
                        pkg.GetTestStepByLineNo(Nu-1).AppendTestStep(insertpkg)
                        pkg.Save()
                    else:
                        exit

search(r'C:\ET2022_4\1_Exercises\2_ECU-TEST_Advanced\Packages\威睿电驱动','TC_SWTD',r'C:\ET2022_4\1_Exercises\2_ECU-TEST_Advanced\Packages\test')#填写package的路径