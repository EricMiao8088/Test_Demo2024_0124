class Students():
    student_property = '江苏'

    @classmethod
    def cm(cls):
        print('我是类方法，因为使用了classmethod')
    
    @staticmethod
    def method():
        print('我是静态方法，因为使用了staticmethod进行修饰')

# t1 = Students.student_property
# print(t1)
# Students.student_property = "苏州"
# t2 = Students.student_property
# print(t2)
print('--------类方法的使用-----------')
Students.cm()
print('-------静态方法的使用-----------')
Students.method()