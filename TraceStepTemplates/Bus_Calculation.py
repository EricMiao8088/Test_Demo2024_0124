import numpy

if any(
    name not in globals()
    for name in ("NumpyBasedTraceStep", "ParameterDefinition", "SignalDefinition")
):
    from NumpyBasedTraceStep import NumpyBasedTraceStep, ParameterDefinition, SignalDefinition


class Bus_Calculation(NumpyBasedTraceStep):
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
        return "1. 计算最大周期，最小周期，平均周期时间；\n2.计算发送失败次数"

    @classmethod
    def GetSignals(cls):
        """
        Returns the incoming and outgoing signals of the trace step.

        :rtype: list[SignalDefinition]
        """
        return [SignalDefinition("Bus_Signal", "IN", optional=False, description="")]

    @classmethod
    def GetParameters(cls):
        """
        Returns the input and return parameters of the trace step.

        :rtype: list[ParameterDefinition]
        """
        return [
            ParameterDefinition("Min_Cycle_Time", "OUT", description="报文的最小时间"),
            ParameterDefinition("Max_Cycle_Time", "OUT", description="报文的最大时间"),
            ParameterDefinition("Average_Cycle_Time", "OUT", description="报文的平均发送时间"),
            ParameterDefinition("Failure_Count", "OUT", description="报文发送失败次数"),
            ParameterDefinition("Target_Min_Time", "IN", description="报文发送失败的最小时间周期"),
            ParameterDefinition("Target_Max_Time", "IN", description="报文发送失败的最大时间周期"),
            ParameterDefinition("Frame_ID", "IN", description="需要计算的目标Frame")
        ]

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

    def Process(self, parameters, report, timeAxis, ranges, signals):
        """
        Method for executing the trace step template. Calculations can be performed based on
        the given signal values and their results can be stored in outgoing signals. Evaluation
        results and return parameters can be set.

        :note: It is recommended to evaluate over the given trigger ranges and set the result for
               each trigger range. The overall result will be automatically determined.

               It is possible to manually set the overall result using the :class:`Report` object;
               the automatic mechanism will be deactivated if used.

               Detailed spots are also reported on trigger ranges.
        :note: Access to values: All signal values within a trigger range can be accessed
               by its :class:`TriggerRange` object. Alternatively, all values of a signal can be
               accessed by the :class:`Signal` object.
        :note: To store calculated values in an outgoing signal the :class:`Signal` object is used:
               Signal.Emit(timestamps, values)
        :param parameters: Dictionary of parameter values.
        :type parameters: dict[str, object]
        :param report: The report object.
        :type report: :class:`Report`
        :param timeAxis: The common time axis of the signals over the entire trace. A limitation
                         to the trigger ranges can be provided by a :class:`TriggerRange` object.
        :type timeAxis: numpy.ndarray
        :param ranges: List of trigger ranges.
        :type ranges: list[TriggerRange]
        :param signals: Dictionary of signals.
        :type signals: dict[str, :class:`Signal`]
        """
        Bus_Sgnal = signals['Bus_Signal']
        # print(Bus_Sgnal,'-------------')
        Frame_ID = parameters['Frame_ID']
        print(Frame_ID)
        print(hex(Frame_ID)[2:],type(hex(Frame_ID)[2:]))
        Target_Min_Time = parameters['Target_Min_Time']
        Target_Max_Time = parameters['Target_Max_Time']
        Target_Time = []
        Failure_count = []
        Table_row1 = []
        Table_row2 = []
        count_range = {}
        for triggerRange in ranges:
            time = Bus_Sgnal.GetTimestamps().tolist()
            for i in range(len(time)):
                time[i]*= 1000
            signal_value = Bus_Sgnal.GetValues().tolist()
            # print(signal_value)
            for i in range(len(signal_value)):
                
                if signal_value[i] == int(hex(Frame_ID)[2:]):
                    # print(type(signal_value[i]))
                    Target_Time.append(time[i]) 
            # print(Target_Time)
            '''
            针对某一个ID，计算平均时间,最大周期，最小周期
            '''
            Difference_Time = [b - a for a,b in zip(Target_Time,Target_Time[1:])]
            parameters['Average_Time'] = sum(Difference_Time)/len(Difference_Time)
            '''
            计算失败次数
            '''
            for j in range(len(Difference_Time)):
                if Difference_Time[j] < Target_Min_Time or Difference_Time[j] > Target_Max_Time:
                    Failure_count.append(Difference_Time[j])
            parameters['Failure_Count'] = len(Failure_count)
            # print(parameters['Failure_Count'])
            parameters['Min_Cycle_Time'] = str(round(min(Difference_Time),2))+'ms'
            parameters['Max_Cycle_Time'] = str(round(max(Difference_Time),2))+'ms'
            parameters['Average_Cycle_Time'] = str(round(parameters['Average_Time'],2))+'ms'
            '''
            计算时间戳相邻差值
            '''
            differs = [round(Target_Time[i+1]-Target_Time[i],2) for i in range(len(Target_Time)-1)]
            bins = numpy.arange(Target_Min_Time,Target_Max_Time,0.8)#定义区间，最小值，最大值，间隔，间隔为0.8，可根据需求修改，也可以留出接口自定义
            # 初始化字典来存储每个区间的个数
            
            for i in range(len(bins)-1):
                
                keys = f"({bins[i]:.2f} ms,{bins[i+1]:.2f} ms)"
                count_range[keys] = 0 
            # print(count_range)
            
            # 统计每个差值落在哪个区间
            for diff in differs:
                for i in range(len(bins)-1):
                    # print(diff)
                    if bins[i] <= diff <bins[i+1]:
                        keys = f"({bins[i]:.2f} ms,{bins[i+1]:.2f} ms)"
                        count_range[keys] += 1
                        break
                    # print(count_range)
            #获取统计区间以及统计值
            for range_key,count in count_range.items():
                Table_row1.append(range_key)
                Table_row2.append(count)
            #形成表格，添加到报告中
            table = report.Table('table',Table_row1)
            table.AddRow(Table_row2)
            # table = report.Table('table',['≤{}ms'.format(Target_Min_Time),'{}ms-{}ms'.format(Target_Min_Time,Target_Min_Time+0.8)])
            # table.AddRow([0,1])
            # table2 = report.Table('22',['2','4','/n','4','8'])
            # table2.AddRow([2,6,'/n','9',0])