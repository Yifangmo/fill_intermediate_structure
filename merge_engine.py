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
        
        if not isinstance(arg, list):
            return arg
        
        if len(arg) == 0:
            return None
        
        if isinstance(keys, list):
            for k in keys:
                if not isinstance(k, str):
                    raise TypeError("key's type must be str: {}".format(type(k)))
        elif isinstance(keys, dict):
            for key, wrapper in keys.items():
                pass
        else:
            raise TypeError("the type of keys must be dict or list: {}".format(type(keys)))
        keys = set(keys)
        res = None
        if isinstance(arg, list):
            res = self.handle(arg, keys, filters_dict, None)
        else:
            res = self.handle([arg], keys, filters_dict, None)
        return res

    def handle(self, arg: list, keys: List[str], filters_dict: dict, current_field: str):
        element_type = None
        current_keys = None
        if current_field:
            current_keys = {i for i in keys if i.startswith(current_field+self.seperator)}
        else:
            current_keys = {i for i in keys if self.seperator not in i}
        for i in arg:
            if not element_type:
                element_type = type(i)
            elif element_type != type(i):
                raise TypeError("list element's type is not unified: {}, {}".format(element_type, type(i)))
        if element_type in self.simple_type:
            tmp_set = set({})
            new_arg = []
            for i in arg:
                if i not in tmp_set:
                    new_arg.append(i)
                    tmp_set.add(i)
            if len(tmp_set) > 1:
                if current_field in filters_dict:
                    tmp_set = filters_dict[current_field](new_arg)
                else:
                    tmp_set = self.default_filter(new_arg)
            else:
                tmp_set = arg.pop()
            res = tmp_set
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
            key_dict = {}
            for i in arg:
                for k in i:
                    if not isinstance(k, str):
                        raise TypeError("dict key's type must be str: {}".format(k))
                    if k.find(self.seperator) != -1:
                        raise ValueError('dict key can not contain dot: {}'.format(k))
                keys_values = []
                for k in current_keys:
                    k = k.replace(current_field+self.seperator, '', 1) if current_field else k
                    if k in i:
                        if isinstance(i[k], Hashable):
                            keys_values.append(i[k])
                        else:
                            raise TypeError("key's value must be hashable: {}".format(k))
                    else:
                        keys_values.append(None)
                keys_values_tup = tuple(keys_values)
                if keys_values_tup not in key_dict:
                    key_dict[keys_values_tup] = [i]
                else:
                    key_dict[keys_values_tup].append(i)
            for keys_values, objlist in key_dict.items():
                tmp_set = {}
                for obj in objlist:
                    for k, v in obj.items():
                        if k not in tmp_set:
                            tmp_set[k] = [v]
                        else:
                            tmp_set[k].append(v)
                for k, v in tmp_set.items():
                    field = self.seperator.join([current_field, k]) if current_field else k
                    tmp_set[k] = self.handle(v, keys, filters_dict, field)
                res.append(tmp_set)
            res = res if len(res) != 1 else res[0]
        else:
            raise TypeError("type is not supported: {}".format(element_type))
        return res
