import numpy

if any(
    name not in globals()
    for name in ("NumpyBasedTraceStep", "ParameterDefinition", "SignalDefinition")
):
    from NumpyBasedTraceStep import NumpyBasedTraceStep, ParameterDefinition, SignalDefinition


class plot(NumpyBasedTraceStep):
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
            SignalDefinition("Signal_0", "IN", optional=False, description=""),
            SignalDefinition("Signal_1", "IN", optional=False, description=""),
            SignalDefinition("Signal_2", "IN", optional=False, description=""),
        ]

    @classmethod
    def GetParameters(cls):
        """
        Returns the input and return parameters of the trace step.

        :rtype: list[ParameterDefinition]
        """
        return [ParameterDefinition("signal_count", "IN", description="")]

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
        import matplotlib.pyplot as plt
        from matplotlib.pyplot import MultipleLocator
        s1 = signals["Signal_0"]
        s2 = signals['Signal_1']
        s3 = signals["Signal_2"]
        for triggerRange in ranges:
            s1_value = s1.GetValues().tolist()
            s2_value = s2.GetValues().tolist()
            s3_value = s3.GetValues().tolist()
            print(type(s1_value))
            print(s1_value,s2_value,s3_value)
            p1 = plt.plot(s1_value,s2_value,c='r',lw=2,label='速度')
            pp = plt.plot(s1_value,s3_value,c='b',lw=3,label='距离')
            plt.legend(loc='best')
            plt.xlabel('X刻度')
            plt.ylabel('Y刻度')
            '''
            设置时间间隔
            '''
            x_major_locator = MultipleLocator(1)
            y_major_locator = MultipleLocator(10)
            ax = plt.gca()
            ax.xaxis.set_major_locator(x_major_locator)
            ax.yaxis.set_major_locator(y_major_locator)
            '''
            保存图片
            '''
            p2 = plt.savefig(r'C:\ET2023_4\2_ECU-TEST_Advanced\Images\test.png')
            print(type(p1),type(p2))
            report.Image(r'C:\ET2023_4\2_ECU-TEST_Advanced\Images\test.png',name='s1_s2',title="test",embedded=True,limitPreviewSize=True)
