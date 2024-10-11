'''
向文件输出内容为：奋斗成就更好的你
'''

fp = open(r'C:\ET2022_4\1_Exercises\2_ECU-TEST_Advanced\Python\0_Exercise\实操案例\demo1\demo1.txt','w')
print('奋斗成就更好的你',file=fp)
fp.close