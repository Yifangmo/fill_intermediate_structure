#!/usr/bin/env python
'''
{
    "deal_type": "",
    "financing_company": {
        "full_name": "",
        "primary_name": "",
        "english_name": ""
    },
    "disclosed_date": "",
    "occurrence_date": "",
    "investors":[
        {
            "full_name": "",
            "primary_name": "",
            "english_name": "",
            "is_leading_investor":True
        },
        ...
    ], [[{},{}],[{},{}],[{},{}],[{},{}]]
    "finacial_advisers": [""],
    "deal_size": "",
    "business_profile": "",
    "purpose_of_raised_funds": "",
    
    "cumulative_amount_of_financing": "",
    "pre_money_valuation": "",
    "post_money_valuation": ""
}
'''
from typing import Hashable, Iterable, List, Callable, Dict
import copy

'''
必须相同: '', 0, 0.0, ()
不断叠加: {}, [], set({})
需要递归处理: {}, []
'''

class Merge(object):
    seperator = '.'
    def __init__(self):
        # self.type_dict = {str: "", int: 0, float: 0.0, None: None, dict: {}, list: []}
        self.simple_type = {str, int, float, bool}
        self.default_filter = lambda i:sorted(i, reverse=True)[0]
    
    def handle(self, arg, keys: Iterable[str], filters_dict: dict):
        res = None
        for k in keys:
            if not isinstance(k, str):
                raise TypeError("key's type must be str: {}".format(k))
        keys = set(keys)
        if isinstance(arg, list):
            res = self.handle_list(arg, keys, filters_dict, None)
        else:
            res = self.handle_list([arg], keys, filters_dict, None)
        return res

    def handle_list(self, arg: list, keys: Iterable[str], filters_dict: dict, current_field: str):
        """递归处理合并列表操作

        Args:
            arg (list): 待合并的列表
            filters_dict ([type]): 一个字段名到筛选器函数的字典，当非键字段出现多值时需调用筛选器函数
            keys (Iterable[str]): 指明哪些字段为键，这些字段不需要筛选
            current_field (str): 当前处理的字段的key，用于获取相应的filter，若无字段名则填None

        Raises:
            TypeError: 列表中的元素类型不支持
        """
        
        element_type = None
        current_keys = None
        if current_field:
            current_keys = {i for i in keys if i.startswith(current_field+Merge.seperator)}
        else:
            current_keys = {i for i in keys if Merge.seperator not in i}
        for i in arg:
            if not element_type:
                element_type = type(i)
            elif element_type != type(i):
                raise TypeError("list element's type is not unified: {}, {}".format(element_type, type(i)))
        if element_type in self.simple_type:
            tmp = set(arg)
            if len(tmp) > 1:
                if current_field in filters_dict:
                    tmp = filters_dict[current_field](tmp)
                else:
                    tmp = self.default_filter(tmp)
            else:
                tmp = arg.pop()
            res = tmp
        elif element_type == list:
            lst = []
            isHashable = True
            for li in arg:
                for i in li:
                    if not isinstance(i, Hashable):
                        isHashable = False
                lst += li
            res = list(set(lst)) if isHashable else self.handle_list(lst, keys, filters_dict, current_field)
            pass
        elif element_type == dict:
            res = []
            key_dict = {}
            for i in arg:
                for k in i:
                    if not isinstance(k, str):
                        raise TypeError("dict key's type must be str: {}".format(k))
                    if k.find(Merge.seperator) != -1:
                        raise ValueError('dict key can not contain dot: {}'.format(k))
                keys_values = []
                for k in current_keys:
                    k = k.replace(current_field+Merge.seperator, '', 1) if current_field else k
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
                tmp = {}
                for obj in objlist:
                    for k, v in obj.items():
                        if k not in tmp:
                            tmp[k] = [v]
                        else:
                            tmp[k].append(v)
                for k, v in tmp.items():
                    field = Merge.seperator.join([current_field, k]) if current_field else k
                    tmp[k] = self.handle_list(v, keys, filters_dict, field)
                res.append(tmp)
            res = res if len(res) != 1 else res[0]
        else:
            raise TypeError("type is not supported: {}".format(element_type))
        return res

def f(inputs):
    return sorted(inputs)[0]

arg = [
    {
        "financing_company": {
            "full_name": "万声音乐1",
            "primary_name": "万声音乐",
        },
        "deal_size": "6000万美元",
        "deal_type": "B1轮融资"
    },
    {
        "financing_company": {
            "full_name": "万声音乐2",
            "primary_name": "万声音乐",
        },
        "deal_type": "B1轮融资"
    },
    {
        "investors": [
            {
                "full_name": "招银国际",
                "primary_name": "招银国际",
                "is_leading_investor": True
            },
            {
                "primary_name": "OPPO",
                "english_name": "OPPO",
                "is_leading_investor": True
            }
        ],
        "deal_type": "B1轮融资"
    },
    {
        "financing_company": {
            "full_name": "万声音乐",
            "primary_name": "万声音乐",
        },
        "deal_size": "6000万美元",
        "deal_type": "B1轮融资",
        "disclosed_date": "8月24日"
    },
    {
        "deal_type": "B1轮融资",
        "investors": [
            {
                "full_name": "招银国际",
                "primary_name": "招银国际",
                "is_leading_investor": True
            },
            {
                "primary_name": "oppo",
                "english_name": "oppo",
                "is_leading_investor": True
            }
        ]
    },
    {
        "investors": [
            {
                "full_name": "小米",
                "primary_name": "小米",
                "is_leading_investor": False
            },
            {
                "full_name": "惠友资本",
                "primary_name": "惠友资本",
                "is_leading_investor": False
            }
        ],
        "deal_type": "B1轮融资"
    },
    {
        "finacial_advisers": [
            "光源资本"
        ],
        "deal_type": "B1轮融资"
    }
]

print(Merge().handle(arg, ['deal_type', 'investors.primary_name', 'financing_company.primary_name'], {'financing_company.full_name': f}))

'''
处理交易类型：
输入：存放一篇新闻中所有以句为单位的基础结构体的list
[
    {
        'sent': 'Element Finance完成440万美元融资a16z和Placeholder领投',
        'labels_value': [
            ['Element Finance', '关联方'],
            ['440万美元', '金额'],
            ['融资', '交易类型'],
            ['a16z', '关联方'],
            ['Placeholder', '关联方']
        ],
        'entities_sent': '<关联方>完成<金额><交易类型><关联方>和<关联方>领投',
        'deal_types': {
            '融资': (11, 17)
        },
        'match_result': [{
            'struct': {
                'financing_company': {},
                'deal_size': '440万美元',
                'deal_type': '融资'
            },
            'from_rule': 'Rule1'
        }]
    }
]

1. 以篇为单位将所有交易类型划分([交易类型] -> [实际交易类型] + [指代交易类型]):
    (1) 用正则匹配指代交易类型
    (2) 剩余为实际交易类型

2. 融合实际交易类型中相同的部分(如 "B+轮战略融资" 和 "B+轮投资")：
    (1) 先识别这一情况，有字母的匹配字母，没有的视情况而定
    (2) 再筛选或融合为一个，主要选字符串长的

3. 替换指代交易类型：
    (1) 若实际交易类型只有一个就直接替换
    (2) 若有多个则需筛选，筛选规则视情况而定

4. 最后相同交易类型的基础结构体放在一个容器中待下一步处理

输出：一个或多个存放基础结构体的list，某个list中的基础结构体交易类型相同，且所有交易类型不是指代交易类型
'''

'''
原则：同一交易类型的融资方一定相同
{
    'deal_type': '',
    'financing_company_names': set({'full_name1', 'primary_name1', 'english_name1'}), 
    'investor_names': set({'full_name1', 'primary_name1', 'english_name1'}),
    'financing_company': {
        'full_name': '',
        'primary_name': '',
        'english_name': ''
    },
    'investors':[
        {
            'full_name': '',
            'primary_name': '',
            'english_name': '',
            'is_leading_investor':True
        },
        ...
    ],
    'finacial_advisers': set({}),
    'deal_size': set({}),
    'business_profile': set({}),
    'pre_money_valuation': set({}),
    'post_money_valuation': set({}),
    'cumulative_amount_of_financing': set({})
}
'''

