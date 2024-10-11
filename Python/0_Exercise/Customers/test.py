import sys
import os
ET_install_path = r'C:\Program Files\ECU-TEST 2022.4'#ET安装路径,需要修改
internalApi = os.path.join(ET_install_path,r'Templates\ExampleWorkspaces\Tutorial-ProcessSeparation\PythonPath')
sys.path.append(internalApi)
#from ApiClient import ApiClient
from ApiProxy import ApiProxy
#import openpyxl#需要安装openpyxl库
api = ApiProxy()
mapping_file = api.ObjectApi.GlobalMappingApi.CreateMapping()

'''
在打开ECU-TEST的情况下，直接运行这个脚本就可以。
如果缺少python环境，那就将这个脚本放到UserPyModules这个文件夹下面，在ECU-TEST里面调用user.test.mapping()就可
'''
def mapping():
    model_list = api.DataBrowser.BrowseModel('Plant model').FindElements('*')#获取plant model下面所有的mapping
    #print(model_list)
    Type = 'Plant model'
    for i in model_list:
        '''
        这里面的if，是用来筛选mapping的层级的，例如：在ECU-TEST里面，某个信号的mapping为：
        Plant model/Model Root/CLAMPS/Clamp15 [0|1]/Value，那在这个mapping里面，我就可以选择

        '''

        if r'Task Info/DS2210CAN_INT_B1_C1/' in i:
            referencename = i.split('/')[-2]+'_'+i.split('/')[-1]#设置mapping的名字
            category = 'model'#给mapping分类的类别
            mappingItem(Type,i,referencename,category)
            #print(i)
            '''
            如果有多个层级的信号要筛选的话，那就可以参照下面的elif，再添加条件即可，不需要的话，要将elif注释掉，只留else  
            '''
        elif r'Task Info/DS4302CAN_INT_B1_C3/' in i:
            referencename = i.split('/')[-2]+'_'+i.split('/')[-1]#设置mapping的名字
            #print(i,'--------')
            category = 'model_2'#给mapping分类的类别
            mappingItem(Type,i,referencename,category)
            #print(i,'-----------')
        elif  r'Task Info/DS4302CAN_INT_B1_C4/' in i:
            referencename = i.split('/')[-2]+'_'+i.split('/')[-1]#设置mapping的名字
            category = 'model_3'#给mapping分类的类别
            mappingItem(Type,i,referencename,category)
            #print(i,'+++++++++')
        else:
            pass
    mapping_file.Save('test0216.xam')
def mappingItem(Type,mappingpath,referencename,Category):#这个函数，是用来定义ECU-TEST里面生成global mapping的步骤
    mappingItem = api.ObjectApi.PackageApi.MappingApi.CreateMappingItem(Type,mappingpath,referencename)
    mappingItem.SetCategory(Category)
    mapping_file.AddItem(mappingItem)

if __name__ == "__main__":
    mapping()