'''
Descripttion: 
version: 
Author: Morgan
Date: 2024-05-20 10:00:09
LastEditors: Morgan
LastEditTime: 2024-05-29 16:25:22
'''
import ctypes
import pickle
import os
import sys

def SA_DLL(dllpath, seed, seed_len, securityLevel, variant):
    """
    dllpath, seed, seed_len, securityLevel, variant
    """
    DLL = ctypes.CDLL(dllpath)  # indicate DLL file path here.
    # convert ByteStream to raw byte sequence if neccessary.
    returnAsByteStream = False        
    # if isinstance(seed, ByteStream):
    #    print(type(seed))
    #    seed = seed.HexString()
    #    print(type(seed))
    #    returnAsByteStream = True 
    seed_len = int(seed_len)
    variant = int(variant)
    securityLevel = int(securityLevel)
    li = seed.split(" ")#以空格切片

    seed_pointer_type = ctypes.c_ubyte * 4
    ipSeedArray_pointer = seed_pointer_type(int(li[0], 16), int(li[1], 16), int(li[2], 16),
                                            int(li[3], 16))
    # iSeedArraySize = ctypes.c_int(seed_len)
    # iSecurityLevel = ctypes.c_int(securityLevel)
    # ipVariant = ctypes.c_char_p(variant)
    # ipOptions = ctypes.c_char_p(variant)
    # iMaxKeyArraySize = iSeedArraySize
    # iopKeyArray = ctypes.create_string_buffer(seed_len)
    # oActualKeyArraySize = ctypes.pointer((ctypes.c_int(seed_len)))
    iSeedArraySize = ctypes.c_int(seed_len)
    iSecurityLevel = ctypes.c_int(securityLevel)
    ipVariant = ctypes.c_char_p(variant)
    iopKeyArray = ctypes.create_string_buffer(seed_len)
    oActualKeyArraySize = ctypes.c_uint(seed_len)
    
    # VKeyGenResultEx GenerateKeyEx
    # (
    # const unsigned char* ipSeedArray,
    # unsigned int iSeedArraySize,
    # const unsigned int iSecurityLevel,
    # const char* ipVariant,
    # unsigned char* iopKeyArray,
    # unsigned int iMaxKeyArraySize,
    # unsigned int& oActualKeyArraySize
    # );

    key = DLL.GenerateKeyEx(ipSeedArray_pointer, iSeedArraySize, iSecurityLevel, ipVariant, iopKeyArray, oActualKeyArraySize)
    #print(key)
    #print(iopKeyArray)
    key_List = [ord(c) for c in iopKeyArray]
    #print(key_List)
    return key_List
    # if returnAsByteStream:
    #     return ByteStream.FromRawString(iopKeyArray.raw)
    # else:
    #     print(key_List)
    #     return key_List

if __name__ == '__main__':
    dll_path, seed, seed_len, security_level, variant = sys.argv[1:]
    key_list = SA_DLL(dll_path, seed, seed_len, security_level, variant)
    pickle_bytes = pickle.dumps(key_list)
    with open(os.path.dirname(__file__)+'\\key_dump','wb') as f:
        try:
            pickle.dump(key_list,f)
        except:
            print('写入异常')