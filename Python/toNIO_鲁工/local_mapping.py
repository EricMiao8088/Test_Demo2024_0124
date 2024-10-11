import openpyxl
import os
import sys
ApiPath = r'C:\Program Files\ECU-TEST 2024.2\Templates\ApiClient'
sys.path.append(ApiPath)
from ApiClient import ApiClient
api = ApiClient()
local_mapping_dict = {}
def Achieve_local_mapping(pkg_path):
    openpkg = api.PackageApi.OpenPackage(pkg_path)
    local_mapping = openpkg.GetMapping().GetItems()
    #获取targetpath
    if len(local_mapping)>0:
        for mapping in local_mapping:
            local_mapping_path = mapping.GetTargetPath()
            local_mapping_name = mapping.GetReferenceName()
            local_mapping_dict[local_mapping_name] = local_mapping_path
    else:
        print('当前测试用例{0}未获取到有效mapping'.format(pkg_path))
    return local_mapping_dict

# print(Achieve_local_mapping(r'C:\ET2024_2\2_ECU-TEST_Advanced\Packages\BasicDrive.pkg'))