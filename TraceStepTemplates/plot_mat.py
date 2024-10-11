import numpy
import os
import scipy.io
ApiClientPath = r'C:\Program Files\ECU-TEST 2023.4\Templates\ExampleWorkspaces\Tutorial-ProcessSeparation\PythonPath'
import sys
sys.path.append(ApiClientPath)
from ApiProxy import ApiProxy
api = ApiProxy()

if any(
    name not in globals()
    for name in ("NumpyBasedTraceStep", "ParameterDefinition", "SignalDefinition")
):
    from NumpyBasedTraceStep import NumpyBasedTraceStep, ParameterDefinition, SignalDefinition


class plot_mat(NumpyBasedTraceStep):
    """
    This is an implementation of NumpyBasedTraceStep.

    Use the interface as reference for available methods. Abstract methods have to be implemented.
    Other methods like GetDescription() are optionally overwritten. There are utility functions
    like CalculateRanges(), FitToAxis() that can be used in your code.
    """

    @staticmethod
    def GetInterfaceRevision():
        """
        Returns the interface revision of the trace step template.

        :note: This method is auto-generated for new implementations of NumpyBasedTraceStep. So do
               not delete or modify this method!

        :rtype: int
        """
        return 1

    @classmethod
    def GetDescription(cls):
        """
        Returns the description of the trace step.

        :rtype: str
        """
        description = "此函数能够将MATLAB中生成的mat文件复制到ecu.test报告文件夹中,并且替换时间轴,新生成带有_newTime的mat文件。"
        return description

    @classmethod
    def GetSignals(cls):
        """
        Returns the incoming and outgoing signals of the trace step.

        :rtype: list[SignalDefinition]
        """
        return [SignalDefinition("Signal_0", "IN", optional=False, description="")]

    @classmethod
    def GetParameters(cls):
        """
        Returns the input and return parameters of the trace step.

        :rtype: list[ParameterDefinition]
        """
        return [ParameterDefinition("Matfile_source_path", "IN", description="matlab中生成的mat文件的绝对路径")]

    @classmethod
    def GetTimeAxisDefinition(cls):
        """
        Returns how the common time axis is determined. Only the logical operators **and** and
        **or** as well as references to the time axes of the signals by using the signal name are
        permitted. The use of brackets is allowed.

        :note: If a signal is not defined on the common time axis, its value is determined
               according to its interpolation rule.

        :return: Convention for building the common time axis (e.g. **'Sig1 or Sig2'**). If an
                 empty string is returned, all time axes are merged into one common time axis.
                 This corresponds to an OR concatenation of the individual time axes.
        :rtype: str
        """
        # e.g. 'Sig1 or Sig2' - timestamps either from Sig1 or Sig2 (default behavior)
        # e.g. 'Sig1 and Sig2' - only timestamps common to both Sig1 and Sig2
        return ""

    def Check(self, parameters):
        """
        Is called initially before trace analysis execution and should check the parameterization.
        In case of error, raise a TypeError or ValueError.

        :param parameters: Dictionary of parameter values.
        :type parameters: dict[str, object]
        :raise TypeError: Invalid type of a parameter.
        :raise ValueError: Invalid value of a parameter.
        """
    def copy_rename_file(self,source_path):
        # '''
        # # source_path:给的是源文件带后缀的路径，例如：C:\Users\92126\Desktop\myfile_1.mat
        # # destination_path：复制文件至目标文件夹，例如：C:\ET2023_4\2_ECU-TEST_Advanced\New_data
        # '''
        import shutil
        #----拆分旧文件，文件名+扩展名
        counter = 1
        self.destination_path = api.TestEnvironment.ExecutionInfo.ReportDbFolder
        newfilepath = os.path.join(self.destination_path,source_path.split('\\')[-1])
        # print(newfilepath,'init')
        base,extension = os.path.splitext(newfilepath)
        #----判断是否是重名的文件
        while os.path.exists(newfilepath):
            #此处的文件名字可以自己定义命名，可以按照以日期时间的方式命名，此处默认按照myfile_1.mat的方式，如遇到名字重复的，自动变为myfile_1_1.mat的方式
            newfilepath = f"{base}_{counter}{extension}"
            counter=counter+1    
        #---copy文件至新路径
        shutil.copy2(source_path,newfilepath)
        print('新文件的路径为：{0}'.format(newfilepath))
        # return newfilepath
    
    # def myfiledat(self,matfile):        
        
    #     data = scipy.io.loadmat(matfile)
    #     if 'opvar_1' in data:
    #         data1 = data['opvar_1']
    #         return data1
    #     else:
    #         print('opvar_1未找到，请将opvar_1修改为：{0}'.format(data.keys()[0]))
    def pic_generate(self,x_data,y_data,color='r',legendlabel='',y_label='',pic_name='',Title=''):
        '''
        x_data:这个参数指的是图片x轴，一般指的是时间；
        y_data:这个参数指的是图片y轴，一般指的是信号数据；
        color：指的是线条颜色，默认是红色
        legendlabel：指的是图片的图例内容
        y_label指的是y轴的名称
        pic_name:这个参数是保存的图片的名字，默认保存的位置为workspace文件下面的Image这个文件夹
        Title是图形的图例名称
        '''
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size': 15})
        plt.figure()
        plt.plot(x_data,y_data,color=color,label=legendlabel)
        plt.xlim(0,x_data[-1]+0.5)
        plt.title(Title,fontweight='bold')
        plt.legend(frameon=False)
        plt.xlabel('t/s')
        plt.ylabel(y_label)
        savepicpath = api.GetSetting('imagePath')+'\\'+pic_name+'.png'
        plt.savefig(savepicpath) 
       
    def Process(self, parameters, report, timeAxis, ranges, signals):
        self.sourcefilepath = parameters['Matfile_source_path']
        import matplotlib.pyplot as plt
        #-----复制文件，此处文件路径是需要自己定义            
        self.copy_rename_file(self.sourcefilepath)
        #print(self.copy_rename_file(destinationfile,sourcefile))
        data = scipy.io.loadmat(self.sourcefilepath)
        if 'opvar_1' in data:
            data1 = data['opvar_1']
            #第一组数据，时间，刻度是2，持续时间为10s
            d1 = data1.tolist()[0]
            x_time = numpy.linspace(0,d1[-1]-d1[0],len(d1))#设置x轴时间坐标
            '''
            将新的时间数据替换原来mat文件中的时间（默认第一行）
            '''
            data1[0,:] = x_time
            new_path = self.destination_path = api.TestEnvironment.ExecutionInfo.ReportDbFolder+'\\'+self.sourcefilepath.split('\\')[-1].split('.mat')[0]+'_newTime.mat'
            scipy.io.savemat(new_path,data)
            # print(data1[0,:])
            # print(data1,type(data1))
        else:
            print('opvar_1未找到，请将opvar_1修改为：{0}'.format(data.keys()[0]))
        #分别获取剩下八组数据
        Pinv,Qinv,Vinv,Ppoc,Qpoc,Vpoc,Vset,Fset = data1.tolist()[1:9]
        #设定画图参数
        plot_para = [
            (Pinv,'Pinv','Pinv_pic','t-Pinv'),
            (Qinv,'Qinv','Qinv_pic','t-Qinv'),
            (Vinv,'Vinv','Vinv_pic','t-Vinv'),
            (Ppoc,'Ppoc','Ppoc_pic','t-Ppoc'),
            (Qpoc,'Qpoc','Qpoc_pic','t-Qpoc'),
            (Vpoc,'Vpoc','Vpoc_pic','t-Vpoc'),
            (Vset,'Vset','Vset_pic','t-Vset'),
            (Fset,'Fset','Fset_pic','t-Fset')  
        ]
        for Y_Data,LegendLabel,Pic_Name,title in plot_para:
            self.pic_generate(x_time.tolist(),Y_Data,'r',f"{LegendLabel}/pu",Pic_Name,Title=title)
            
        image_details = [
            ('Pinv_pic.png','Pinv'),
            ('Qinv_pic.png','Qinv'),
            ('Vinv_pic.png','Vinv'),
            ('Ppoc_pic.png','Ppoc'),
            ('Qpoc_pic.png','Qpoc'),
            ('Vpoc_pic.png','Vpoc'),
            ('Vset_pic.png','Vset'),
            ('Fset_pic.png','Fset')
        ]
        '''
        将图片添加到报告中
        '''
        for pic_path,title in image_details:
            path = f"C:\\ET2023_4\\2_ECU-TEST_Advanced\\Images\\{pic_path}"
            report.Image(path,name='test',title=title,embedded=True,limitPreviewSize=True)
       