import matplotlib.pyplot
import matplotlib.pyplot
import matplotlib.pyplot
import matplotlib.pyplot
import numpy

if any(
    name not in globals()
    for name in ("NumpyBasedTraceStep", "ParameterDefinition", "SignalDefinition")
):
    from NumpyBasedTraceStep import NumpyBasedTraceStep, ParameterDefinition, SignalDefinition


class Comparing_Signals(NumpyBasedTraceStep):
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
        return "This is an array-based NumPy trace step."

    @classmethod
    def GetSignals(cls):
        """
        Returns the incoming and outgoing signals of the trace step.

        :rtype: list[SignalDefinition]
        """
        return [
            SignalDefinition("Signal_A", "IN", optional=False, description="这是目标信号，需要进行两次变化的，其中第一次变化通过trigger，第二次变化在于此脚本"),
            SignalDefinition("Signal_B", "IN", optional=False, description="这是平移信号"),
            SignalDefinition("Out_Signal","OUT",optional=False, description="这是平移后的信号"),
        ]

    @classmethod
    def GetParameters(cls):
        """
        Returns the input and return parameters of the trace step.

        :rtype: list[ParameterDefinition]
        """
        return [ParameterDefinition("Diff_Value", "IN", description="误差精度")]

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
        signal_A = signals['Signal_A']#目标信号
        signal_B = signals['Signal_B']#偏移信号
        Out_Signal = signals['Out_Signal']
        print(type(Out_Signal))
        difference = []
        Diff = parameters["Diff_Value"]
        # import matplotlib
        # print(signal_A.GetMappingItemName())
        for triggerRange in ranges:
            trigger_time = triggerRange.GetTimestamps()
            # print(trigger_time)
            # print(triggerRange.GetStartTime(),trigger_time.index(triggerRange.GetStartTime()))
            # A_np = triggerRange.GetValues('Signal_A')
            # B_np = triggerRange.GetValues('Signal_B')
            A = triggerRange.GetValues('Signal_A').tolist()
            B = triggerRange.GetValues('Signal_B').tolist()
            # print(A,B)
            Time = triggerRange.GetTimestamps().tolist()
            # print(Time)
            '''
            假定信号A为首先变化的信号，获取信号A第一次的变化时间点
            '''
            for i in range(1,len(A)):
                if A[i] != A[i-1]:
                    # print(A[i-2],A[i-1],A[i],Time[i],Time.index(Time[i]))
                    for j in range(1,len(B)):
                        if B[j] != B[j-1]:
                            # print(B[j-2],B[j-1],B[j],Time[j],Time.index(Time[i]),Time.index(Time[j]))
                            #确认采样点平移的个数
                            distance = Time.index(Time[i])-Time.index(Time[j])
                            print(distance)
                            if distance > 0:
                                #信号B，向右平移
                                C_1 = [None]*distance + B[:-distance]
                                C = C_1[distance:]
                                A = A[distance:]
                                # print(A,C)
                                #进行数据比较，并且校验是否一致
                                for k in range(len(A)):
                                    #两者差值的绝对值小于误差值，即可认为是一致的,那差值大于误差值，就添加到列表中，列表长度大于0的，即两条曲线不一致
                                    if abs(C[k] - A[k]) > Diff:
                                        difference.append(Time[k])
                                print(difference,len(difference),'--------')
                                if len(difference) == 0:
                                    print('11111')
                                    triggerRange.SetResultSuccess()
                                    report.SetResultText('信号{0}向右平移{1}个采样点后，与信号{2}一致'.format(signal_B.GetMappingItemName(),distance,signal_A.GetMappingItemName()))
                                    Out_Signal.Emit(trigger_time,numpy.array(C_1))
                                    # print(len(trigger_time),len(C_1))
                                    break
                                else:
                                    triggerRange.SetResultFailed()
                                    report.SetResultText('信号{0}向右平移{1}个采样点后，以下时间点与信号{2}不一致：/n{3}'.format(signal_B.GetMappingItemName(),distance,signal_A.GetMappingItemName(),difference))
                                # print(difference)
                                #信号B，平移distance个采样点
                                # shift_B = numpy.roll(A_np,distance)
                                # print(shift_B)
                                # print(A_np)
                                # matplotlib.pyplot.plot(trigger_time,A_np,label='平移前曲线')
                                # matplotlib.pyplot.plot(trigger_time,shift_B,label = '平移{0}个采样点曲线'.format(distance),linestyle = '--',color='r',marker = '*')
                                # matplotlib.pyplot.savefig(image_save_path+'\\test.png')
                                # #matplotlib.pyplot.show()
                                # report.Image(image_save_path+'\\test.png')
                                # break
                            else:
                                triggerRange.SetResultFailed()
                                report.SetResultText('未找到两个信号的相同值，两个曲线变化趋势不一致，请手动确认！！！')
                                break
                    break

