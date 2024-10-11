'''
Descripttion: 
version: 
Author: Morgan
Date: 2024-05-20 10:05:22
LastEditors: Morgan
LastEditTime: 2024-05-20 13:16:09
'''
import subprocess
import os
import pickle

def call_32bit_python(python_path, dll_path, seed, seed_len, security_level, variant):
    p = subprocess.run([python_path, os.path.dirname(__file__)+'\\process_seed.py',
                        dll_path,seed,seed_len,security_level,variant],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout = p.stdout
    stderr = p.stderr
    if p.returncode != 0:
        raise Exception('出错！' + stderr.decode('gbk'))
    print('='*10)
    with open(os.path.dirname(__file__)+'\\key_dump','rb') as f:
        key_list = pickle.load(f)
        print(key_list)
    return key_list
    
if __name__ == '__main__':
    # print(__file__)
    # print(os.path.dirname(__file__))
    python_path = r'C:\Users\92126\AppData\Local\Programs\Python\Python37-32\python.exe'
    dll_path = r'C:\ET2021_4\1_Diag_27_Demo\SeednKeyDiagnostics_Dll\SeednKeyDLL_FAW.dll'
    seed = '34 20 11 19'
    seed_len = '4'
    sec = '1'
    variant = '1'
    call_32bit_python(python_path,dll_path,seed,seed_len,sec,variant)
