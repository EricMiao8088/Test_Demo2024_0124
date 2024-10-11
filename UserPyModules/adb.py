import subprocess
def excute_command():
    command1 = 'adb devices'
    command2 = 'adb shell ps'
    command3 = 'adb version'
    process1 = subprocess.Popen(command1,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    
    # print(process1.returncode)
    #process1.wait()
    process2 = subprocess.Popen(command2,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    #process2.wait()
    process3 = subprocess.Popen(command3,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    #process3.wait()
    # print(process1.returncode)
    #print(process.returncode)
    output1,error1 = process1.communicate()
    output2,error2=process2.communicate()
    output3,error3=process3.communicate()
    print(output1,output2,output3)
    # if error1 and error2 and error3 == None:
    #     print(output1)
    # print(output1,output2,output3)
    #return output
    # print(output,error)
excute_command()