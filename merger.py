from merge_engine import MergeEngine, MAX_LENGTH_FILTER, SAVE_ALL_FILTER, KeyWrapper
import re

class Merger():
    def __init__(self):
        self.repl_deal_type_reobj = re.compile(r"(轮|次|笔|轮战略|系列轮?)?(投资|融资)|投融资")
        self.refer_deal_type_reobj = re.compile(r"(本|此|该)")
        self.keys = {
            'deal_type': None, 
            'investors.primary_name': PrimaryNameWrapper, 
            'financing_company.primary_name': PrimaryNameWrapper
        }
        self.is_leading_investor_filter = lambda s : True in s
        self.full_name_filter = MAX_LENGTH_FILTER
        self.deal_size = SAVE_ALL_FILTER
        self.business_profile = SAVE_ALL_FILTER
        self.filters_dict={
            'investors.is_leading_investor': self.is_leading_investor_filter,
            'financing_company.full_name': self.full_name_filter,
            'investors.full_name': self.full_name_filter,
            'business_profile': self.business_profile,
            'deal_size': self.deal_size
        }
        self.mergeengine = MergeEngine()
        pass
    
    def __call__(self, match_result: list):
        match_result = self.merge_deal_type(match_result)
        merge_result = self.mergeengine(match_result, self.keys, self.filters_dict)
        return merge_result

    def merge_deal_type(self, match_result: list):
        deal_type2match_result = {}
        refer_deal_type2match_result = {}
        repl_dt_map = {}
        for mr in match_result:
            if "deal_type" not in mr:
                if None in refer_deal_type2match_result:
                    refer_deal_type2match_result[None].append(mr)
                else:
                    refer_deal_type2match_result[None] = [mr]
            dt = mr["deal_type"]
            if dt in deal_type2match_result:
                deal_type2match_result[dt].append(mr)
            elif dt in refer_deal_type2match_result:
                refer_deal_type2match_result[dt].append(mr)
            else:
                if self.refer_deal_type_reobj.search(dt):
                    refer_deal_type2match_result[dt] = [mr]
                else:
                    repl_dt = self.repl_deal_type_reobj.sub("",dt)
                    if repl_dt in repl_dt_map:
                        pre_dt = repl_dt_map[repl_dt]
                        ult_dt = None
                        if len(pre_dt) > len(dt):
                            ult_dt = pre_dt
                        elif len(pre_dt) < len(dt):
                            ult_dt = dt
                        else:
                            if dt.endswith("融资"):
                                ult_dt = dt
                            else:
                                ult_dt = pre_dt
                        if ult_dt == pre_dt:
                            mr["deal_type"] = ult_dt
                            deal_type2match_result[ult_dt].append(mr)
                        else:
                            pre_mr = deal_type2match_result[pre_dt]
                            del deal_type2match_result[pre_dt]
                            for mr in pre_mr:
                                mr["deal_type"] = ult_dt
                            pre_mr.append(mr)
                            deal_type2match_result[ult_dt] = pre_mr
                            repl_dt_map[repl_dt] = ult_dt
                    else:
                        repl_dt_map[repl_dt] = dt
                        deal_type2match_result[dt] = [mr]
        
        # 尝试将引用交易类型转为实际交易类型
        for dt, mrs in refer_deal_type2match_result.items():
            for mr in mrs:
                tmp_dt = None
                if len(deal_type2match_result) == 1:
                    tmp_dt = list(deal_type2match_result.keys())[0]
                # 找出与之最近的并且在前面的real_dt
                else:
                    try:
                        mpos = match_result.index(mr)
                    except:
                        continue
                    else:
                        pos_diff = 100
                        for dt, omr in deal_type2match_result.items():
                            try:
                                mpos = match_result.index(mr)
                            except:
                                continue
                            else:
                                opos = match_result.index(omr[0])
                                pd = (mpos - opos)
                                if pd <= pos_diff and pd >= 0:
                                    pos_diff = pd
                                    tmp_dt = dt
                mr["deal_type"] = tmp_dt
                deal_type2match_result[tmp_dt].append(mr)
        res = []
        for dt, mr in deal_type2match_result.items():
            res += mr
        return res

class PrimaryNameWrapper(KeyWrapper):
    def __init__(self, value: str):
        super().__init__(value)
        
    def __eq__(self, __o: object):
        if self.value == __o.value:
            return True
        v1 = self.value.upper()
        v2 = __o.value.upper()
        if v1.find(v2) != -1 or v2.find(v1) != -1:
            return True
        return False
    
    def __hash__(self) -> int:
        return 0
    
    
    def __lt__(self, __x: str) -> bool:
        sv = self.value
        xv = __x.value
        if len(sv) < len(xv):
            return False
        elif len(sv) > len(xv):
            return True
        else:
            if sv.isupper():
                return True
            if xv.isupper():
                return False
        return True
