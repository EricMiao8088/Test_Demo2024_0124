import openpyxl
import os
import sys
ECUTEST_installation = r'C:\Program Files\ECU-TEST 2022.4'
ApiProxyPath = os.path.join(ECUTEST_installation,r'Templates\ExampleWorkspaces\Tutorial-ProcessSeparation\PythonPath')
sys.path.append(ApiProxyPath)
#print(ApiProxyPath)
from ApiProxy import ApiProxy
api = ApiProxy()
'''
对应的excel表格，一般来说一列name就对应一个A2l文件，所以在脚本里面以两个A2l文件作为例子，分别生成2个xam文件
根据需要可以进行删减
'''
ECU_KEY1 = 'Battery-Control'#与ECU-TEST里面的tcf的port名字对应
#ECU_KEY2 = 'Engine-Control'
mappingfile_ECU_KEY1 = api.ObjectApi.GlobalMappingApi.CreateMapping()
#mappingfile_ECU_KEY2 = api.ObjectApi.GlobalMappingApi.CreateMapping()


def mapping(excelpath,old_name,new_name):#需要定义你的excel的路径，old_name指的是不变的名字，new_name指的是要变更的path

    
    wb = openpyxl.load_workbook(excelpath)
    ws = wb[wb.sheetnames[0]]
    #A2l_ECU_KEY1 = api.DataBrowser.BrowseA2l(ECU_KEY1).GetLabelNameList('')
    #A2l_ECU_KEY2 = api.DataBrowser.BrowseA2l(ECU_KEY2).GetLabelNameList('')
    #print(A2l)
    for i in range(ws.max_row-1):
        col_new_Name = ws.cell(row = i + 2,column = new_name).value
        #print(col_G2_9_Name)
        col_old_Name = ws.cell(row = i + 2,column = old_name).value
        #print(col_G4_9_Name)
        if col_old_Name != 'NA':
            mappingitem = api.ObjectApi.PackageApi.MappingApi.CreateMappingItem(ECU_KEY1,col_new_Name,col_old_Name)
            mappingfile_ECU_KEY1.AddItem(mappingitem)
        else:
            pass
    mappingfile_ECU_KEY1.Save(ECU_KEY1+'.xam')



Excelpath = r'C:\ET2022_4\1_Exercises\2_ECU-TEST_Advanced\Python\toNIO_鲁工\test.xlsx'
mapping(Excelpath,1,3)