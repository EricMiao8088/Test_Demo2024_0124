#-- encoding = utf-8
import sys
'''
猜年龄大小，有三点需求：
1.允许用户最多尝试三次；
2.每尝试三次之后，如果还没有猜对，就问用户是否还想继续，如果回答Y或者y，就继续
3.如果猜对了，就直接退出
'''

def guess():
    target_age = 20
    i = 0
    while i < 4:
        i = i+1
        if i <=3: 
            age = int(input('请输入猜测的年龄:'))      
            if age == 20:
                texts = '恭喜你，猜对啦，游戏结束！'
                print(texts)
            elif age < 20:
                texts = '年龄不对，猜小啦!,还剩下{0}机会'.format(3-i)
                print(texts)
            else:
                print('年龄不对，猜大啦,还剩下{0}次机会'.format(3-i))
        else:
            print('3次机会已满，你没机会啦')
            count = str(input('是否想要继续玩这个游戏？选择Y/N '))
            if count == 'Y' or count == 'y':
                i = 0
            else:
                print('游戏结束！')
                sys.exit
if __name__ == "__main__":
    guess()


