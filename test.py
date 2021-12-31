#!/usr/bin/env python
def f1(dict_: dict):
    dict_["a"] = [[(1,2)],2]
    return

def f2():
    dict_ = {"b": 1}
    f1(dict_)
    print(dict_)
    
f2()