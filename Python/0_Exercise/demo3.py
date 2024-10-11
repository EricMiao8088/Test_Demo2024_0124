class Person(object):
    def __init__(self,name,age):
        self.name = name
        self.age = age
    def info(self):
        print(self.name,self.age)

class student(Person):
    def __init__(self,name,age,stu_no):
        super().__init__(name,age)
        self.stu_no = stu_no

class teacher(Person):
    def __init__(self, name, age,teacheryear):
        super().__init__(name, age)
        self.teacheryear = teacheryear

stu1 = student('张三',20,1001)
teach1 = teacher('李四',50,10)

stu1.info()
teach1.info()