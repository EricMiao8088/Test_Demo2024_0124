import os
def pkgcount(targetpath):
    count_pkg = 0
    count_prj = 0
    base_dir = targetpath
    for dirpath,dirnames,filenames in os.walk(base_dir):#遍历目标文件下面的所有文件路径，文件夹，文件名字
        for filename in filenames:#遍历所有的文件名字
            if filename.split('.')[-1] == 'pkg':#计算所有pkg的数量
                count_pkg+=1
            if filename.split('.')[-1] == 'prj':#计算所有prj的数量
                count_prj+=1
    print('{0}路径下面包含{1}个package,{2}个project，pkg和prj总共数量为{3}'.format(targetpath,count_pkg,count_prj,count_pkg+count_prj))
if __name__ == "__main__":
    pkgcount(r'C:\ET2023_3\2_ECU-TEST_Advanced\Packages')