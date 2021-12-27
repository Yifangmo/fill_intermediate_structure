class A:
    def get(self):
        print(self.a)
        print("A class")

class AA(A):
    def __init__(self) -> None:
        super().__init__()
        print("aaaaaaaaaaaa")
        self.a = "a"

    def get(self):
        super().get()
        super(BB, self).get()


class BB(A):
    def __init__(self) -> None:
        super().__init__()
        print("bbbbbbbbbbb")
        self.a = "b"
    
    def get(self):
        super(BB, self).get()
        

class BAA(AA,BB):
    def get(self):
        super().get()


baa = BAA()
print(BAA.mro())
baa.get()