#定义一个类
class step_batch():
    def __init__(self,lr = 10):
        self.lr = lr
    
    def run(self):
        print(self.lr)

    def update(self):
        self.lr = self.lr/2
    

if __name__ == "__main__":
    step_batch().run()