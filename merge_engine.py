#!/usr/bin/env python
from typing import Hashable, List, TypeVar

MAX_FILTER = lambda i:sorted(i, reverse=True)[0]
MIN_FILTER = lambda i:sorted(i)[0]
MAX_LENGTH_FILTER = lambda s : sorted(s, key=lambda i:len(i), reverse=True)[0]
MIN_LENGTH_FILTER = lambda s : sorted(s, key=lambda i:len(i))[0]
SAVE_ALL_FILTER = lambda s : list(s)
FILED_SEPERATOR = "."

KT = TypeVar('KT', List[str], dict)

class MergeEngine(object):
    def __init__(self):
        self.simple_type = {str, int, float, bool}
        self.default_filter = MAX_FILTER
        self.seperator = FILED_SEPERATOR
    
    def __call__(self, arg, keys: KT, filters_dict: dict):
        
        """递归处理合并列表操作
        Args:
            arg (list): 待合并的列表
            keys (List[str], dict): 指明哪些字段为键，这些字段不需要筛选
            filters_dict ([type]): 一个字段名到筛选器函数的字典，当非键字段出现多值时需调用筛选器函数，若指定字段的筛选器为None，则用默认的筛选器
        Raises:
            TypeError: 列表中的元素类型不支持
        """     
        if not arg:
            return None
        
        if isinstance(keys, list):
            for k in keys:
                if not isinstance(k, str):
                    raise TypeError("key's type must be str: {}".format(type(k)))
            keys = {k:None for k in keys}
        elif isinstance(keys, dict):
            for key, wrapper in keys.items():
                if not isinstance(key, str):
                    raise TypeError("key's type must be str: {}".format(type(key)))
                if wrapper and not isinstance(wrapper(None), Hashable):
                    raise TypeError("The key's wrapper should be Hashable: {}".format(key))
        else:
            raise TypeError("the type of keys must be dict or list: {}".format(type(keys)))
        res = None
        if isinstance(arg, list):
            res = self.handle(arg, keys, filters_dict, None)
        else:
            res = self.handle([arg], keys, filters_dict, None)
        return res

    def handle(self, arg: list, keys: List[str], filters_dict: dict, current_field: str):
        if len(arg) == 0:
            return None
        element_type = None
        current_keys = None
        if current_field:
            current_keys = {k:k.replace(current_field+self.seperator, '', 1) for k in keys if k.startswith(current_field+self.seperator)}
        else:
            current_keys = {k:k for k in keys if self.seperator not in k}
        for ele in arg:
            if not element_type:
                element_type = type(ele)
            elif element_type != type(ele):
                raise TypeError("list element's type is not unified: {}, {}".format(element_type, type(ele)))
        if element_type in self.simple_type:
            res_dict = set({})
            eles = []
            for ele in arg:
                if ele not in res_dict:
                    eles.append(ele)
                    res_dict.add(ele)
            if len(res_dict) > 1:
                if current_field in keys and keys[current_field]:
                    res = sorted([keys[current_field](ele) for ele in eles])[0].value
                elif current_field in filters_dict:
                    res = filters_dict[current_field](eles)
                else:
                    res = self.default_filter(eles)
            else:
                res = eles[0]
                
        elif element_type == list:
            lst = []
            isHashable = True
            for li in arg:
                for i in li:
                    if not isinstance(i, Hashable):
                        isHashable = False
                lst += li
            res = list(set(lst)) if isHashable else self.handle(lst, keys, filters_dict, current_field)
            pass
        elif element_type == dict:
            res = []
            kvalues2elements = {}
            # 根据各个ele中的当前多个关键字的值的有序数列来对ele分类
            for ele in arg:
                # 检查dict每个键的类型
                for k in ele:
                    if not isinstance(k, str):
                        raise TypeError("dict key's type must be str: {}".format(k))
                    if k.find(self.seperator) != -1:
                        raise ValueError('dict key can not contain dot: {}'.format(k))
                kvalues = []
                # 遍历当前需要处理的关键字，ck是无前缀的关键字
                for k, ck in current_keys.items():
                    if ck in ele:
                        # 如果当前关键字的值是可哈希的或者有可hash的包装类，就加入到关键字值有序数列中
                        k_wrapper = keys[k]
                        if isinstance(ele[ck], Hashable) or k_wrapper:
                            kvalue = k_wrapper(ele[ck]) if k_wrapper else ele[ck]
                            kvalues.append(kvalue)
                        else:
                            raise TypeError("key's value must be hashable or have hashable wrapper: {}".format(k))
                    else:
                        kvalues.append(None)
                kvalues_tup = tuple(kvalues)
                # 根据关键字值有序数列分组
                if kvalues_tup not in kvalues2elements:
                    kvalues2elements[kvalues_tup] = [ele]
                else:
                    kvalues2elements[kvalues_tup].append(ele)
            # 对分好组的eles融合
            for kvalues, elements in kvalues2elements.items():
                res_dict = {}
                # 遍历组内ele
                for ele in elements:
                    for k, v in ele.items():
                        if k not in res_dict:
                            res_dict[k] = [v]
                        else:
                            res_dict[k].append(v)
                for k, v in res_dict.items():
                    field = self.seperator.join([current_field, k]) if current_field else k
                    res_dict[k] = self.handle(v, keys, filters_dict, field)
                res.append(res_dict)
            res = res if len(res) != 1 else res[0]
        else:
            raise TypeError("type is not supported: {}".format(element_type))
        return res

class KeyWrapper(str):
    def __init__(self, value) -> None:
        self.value = value
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, __x: object) -> bool:
        return self.value == __x.value
    
    def __hash__(self) -> int:
        return super().__hash__()
    
    def __lt__(self, __x: str) -> bool:
        return super().__lt__(__x)