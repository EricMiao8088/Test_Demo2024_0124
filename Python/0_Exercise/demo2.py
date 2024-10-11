class Students():
    def __init__(self,name,age):
        self.name = name
        self.age = age
    def eat(self):
        print(self.name + '在吃饭')

stu1 = Students('张三',19)
stu2 = Students('李四',20)
print('---------为stu2动态添加属性-----------')
stu2.gender = '女'
print(stu1.name,stu1.age)
print(stu2.name,stu2.age,stu2.gender)
print('---------为stu1单独定义一个方法-----------')
def show():
    print('定义在类外面的，称为函数')
stu1.show = show
stu1.show()