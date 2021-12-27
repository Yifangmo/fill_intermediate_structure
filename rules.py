from super_rule import SuperRule, get_multi_value_idx_spans
import re

class Rule1(SuperRule):
    def __init__(self):
        super().__init__()
        # 36氪获悉，<关联方>于<发生时间>连续完成<交易类型>，包括<关联方>投资的<金额><交易类型>，以及<关联方>领投和<关联方>跟投的<金额><交易类型>
        # self.pattern = r"((?P<bp><融资方标签>)?(?P<fc><关联方>))?[^，；<>]*(?:<发生时间>|<披露时间>)?[^，；<>]*(?:完成|获)[^，；]*(?P<ds><金额>)?[^，；<>]*<交易类型>"
        self.pattern = "".join([self.financing_company_pattern[0], "?", self.anychar_notag_pattern, self.date_pattern, 
                                self.anychar_notag_pattern, r"(?:完成|获)", self.anychar_pattern, self.may_be_deal_size_pattern[0], 
                                self.anychar_notag_pattern, self.deal_type_pattern])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "business_profile": self.financing_company_pattern[1], 
            "financing_company": self.financing_company_pattern[2], 
            "deal_size": self.deal_size_pattern[1]
        }

    def __call__(self, entities_sent, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule2(SuperRule):
    def __init__(self):
        super().__init__()
        # self.pattern = r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:机构|基金|(<属性名词>))?(?:联合|重仓加码|共同|独家)?(?:领投|牵头)"
        self.pattern = "".join([self.investors_pattern[0], "(?:联合|重仓加码|共同|独家)?(?:领投|牵头)"])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "investors": self.investors_pattern[1], 
        }

    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent, True)

class Rule3(SuperRule):
    def __init__(self):
        super().__init__()
        # 其中，红杉中国作为老股东继续增持，华平投资则是本轮新进入的领投方。
        # self.pattern = r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:机构|基金|则?(以|作为)?(?:<属性名词>)?)?也?(?:联合|共同|继续|同轮|独家|超额)?(?:参与到?|追加)?了?(?:战略)?(?:(?:本轮|本次)(?:投资|融资)|融资|投资|跟投|加持|增持|参投)"
        self.pattern = "".join([self.investors_pattern[0], "也?(?:联合|共同|继续|同轮|独家|超额|持续)?(?:参与到?|追加)?了?(?:战略)?(?:(?:本轮|本次)(?:投资|融资)|融资|投资|跟投|加持|增持|参投|参与)"])
        # self.pattern = "".join([self.investors_pattern[0], "持续参投"])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "investors": self.investors_pattern[1], 
        }

    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule4(SuperRule):
    def __init__(self):
        super().__init__()
        # <融资方标签><关联方>连续完成<属性名词><金额>的<交易类型>与<交易类型>
        self.patterns_for_attr_noun = [r"(?:总|整体|累计)?融资(?:总?金?额|规模|累计金?额)|规模", r"投前估值", r"后估值", r"估值",
                                       r"投资方|投资人|投资者|投资机构|参投方?", r"领投方?|领投机构", r"财务顾问|融资顾问"]
        self.patterns_for_sentence = [
            (r"(<属性名词>)(?:已|将)?(?:达到?|为)?了?(<金额>)",
             self.patterns_for_attr_noun[:4], (1, 2)),
            (r"(<属性名词>)还?(?:主要)?(?:为|是|有|囊括|包括|涉及|包?含)((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)",
             self.patterns_for_attr_noun[4:], (1, 2)),
            (r"(<属性名词>)的?((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)",
             self.patterns_for_attr_noun[5:], (1, 2)),
            (r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:作为|在内的|等|则是|则以|(?:继续)?担?任)(<属性名词>)",
             self.patterns_for_attr_noun[4:], (2, 1))
        ]
        self.patterns_with_multi_value_list_idx = {1, 2, 3}
        self.field_name_with_multi_value = {
            "investors", "leading_investors", "finacial_advisers"}
        self.reobjs = [(re.compile(i[0]), [re.compile(j)
                        for j in i[1]], i[2]) for i in self.patterns_for_sentence]
        self.attr_noun_pattern_to_field_name = {
            self.patterns_for_attr_noun[0]: "deal_size",
            self.patterns_for_attr_noun[1]: "pre_money_valuation",
            self.patterns_for_attr_noun[2]: "post_money_valuation",
            self.patterns_for_attr_noun[3]: "valuation",
            self.patterns_for_attr_noun[4]: "investors",
            self.patterns_for_attr_noun[5]: "leading_investors",
            self.patterns_for_attr_noun[6]: "finacial_advisers"
        }

    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        match_result = []
        for i, reobj in enumerate(self.reobjs):
            matches = reobj[0].finditer(entities_sent)
            attr_noun_content_reobjs = list(reobj[1])
            attr_noun_group_id = reobj[2][0]
            field_value_group_id = reobj[2][1]
            for match in matches:
                struct = {}
                attr_noun_idx_span = match.span(attr_noun_group_id)
                field_value_idx_spans = [match.span(field_value_group_id)]
                if i in self.patterns_with_multi_value_list_idx:
                    field_value_idx_spans = get_multi_value_idx_spans(
                        entities_sent, field_value_idx_spans[0], "<关联方>")
                attr_noun_origin_str =attr_noun_dict[attr_noun_idx_span]
                
                for ro in attr_noun_content_reobjs:
                    m = ro.search(attr_noun_origin_str)
                    if m:
                        field_name = self.attr_noun_pattern_to_field_name[m.re.pattern]
                        if field_name == "investors":
                            struct["investors"] = field_value_idx_spans
                            struct["is_leading_investor"] = False
                        elif field_name == "leading_investors":
                            struct["investors"] = field_value_idx_spans
                            struct["is_leading_investor"] = True
                        elif field_name == "finacial_advisers":
                            struct["finacial_advisers"] = field_value_idx_spans
                        else:
                            struct[field_name] = field_value_idx_spans[0]
                        struct["attr_noun"] = attr_noun_idx_span
                if len(struct) > 0:
                    mr = {"struct": struct}
                    mr["match_span"] = match.span()
                    mr["from_rule"] = "Rule4"
                    match_result.append(mr)
        return match_result

class Rule5(SuperRule):
    def __init__(self):
        super().__init__()
        # self.pattern = r"(?P<fc><关联方>)[^，；<>]*签署<交易类型>协议"
        self.pattern = "".join([self.financing_company_pattern[0], self.anychar_notag_pattern, r"签署<交易类型>协议"])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {"business_profile": self.financing_company_pattern[1], "financing_company": self.financing_company_pattern[2]}
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

    
class Rule6(SuperRule):
    def __init__(self):
        super().__init__()
        # 中俄投资基金进行战略性股权投资
        # self.investors_pattern = r"(?P<i>(?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?"
        self.pattern = self.investors_pattern[0] + r"进行<交易类型>"
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {"investors": self.investors_pattern[1]}
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule7(SuperRule):
    def __init__(self):
        super().__init__()        
        # 作为<属性名词>，<关联方>这次选择了直接投资<关联方>。
        # 此前，<关联方>、<关联方>、<关联方>、<关联方>、<关联方>、<关联方>等<属性名词>以<金额>投资「<关联方>」是中国农业科技领域历史上最大的一笔商业融资。
        # self.pattern = r"(?:<属性名词>)?(<关联方>)投资(关联方)"
        self.pattern = "".join([self.investors_pattern[0], "以", self.may_be_deal_size_pattern[0], self.anychar_notag_pattern, r"投资", self.financing_company_pattern[0]])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "investors": self.investors_pattern[1], 
            "deal_size": self.may_be_deal_size_pattern[1], 
            "business_profile": self.financing_company_pattern[1], 
            "financing_company": self.financing_company_pattern[2]
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule8(SuperRule):
    def __init__(self):
        super().__init__()
        # 专注于人工智能的农业技术初创公司Intello Labs在由Avaana Capital牵头的一轮融资中筹集了500万美元
        self.pattern = r"(?P<bp><融资方标签>)?(?P<fc><关联方>)在[^，；]*<交易类型>[^，；<>]*筹集[^，；<>]*(?P<ds><金额>)"
        self.pattern = "".join([self.financing_company_pattern[0], r"在", self.anychar_pattern, self.deal_type_pattern, self.anychar_notag_pattern, r"筹集", self.anychar_notag_pattern, self.deal_size_pattern[0]])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "business_profile": self.financing_company_pattern[1], 
            "financing_company": self.financing_company_pattern[2], 
            "deal_size": self.deal_size_pattern[1]
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule9(SuperRule):
    def __init__(self):
        super().__init__()
        # 此次注资，是高瓴创投对去年11月极飞科技12亿元人民币融资的追加投资。
        # "此次注资，是<关联方>对<发生时间><关联方><金额><交易类型>的追加投资。"
        self.pattern = "".join([self.investors_pattern[0], r"对",self.date_pattern, self.financing_company_pattern[0], self.may_be_deal_size_pattern[0], self.may_be_deal_type_pattern, self.anychar_notag_pattern, r"投资"])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "investors": self.investors_pattern[1], 
            "business_profile": self.financing_company_pattern[1], 
            "financing_company": self.financing_company_pattern[2], 
            "deal_size": self.may_be_deal_size_pattern[1]
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule10(SuperRule):
    def __init__(self):
        super().__init__()
        # Stripe估值达到950亿美元
        self.pattern = "".join([self.financing_company_pattern[0], r"估值达到?(?P<pmv><金额>)"])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "financing_company": self.financing_company_pattern[1],
            "post_money_valuation": "pmv"
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule11(SuperRule):
    def __init__(self):
        super().__init__()
        # 本轮投资来自险峰长青。
        self.deal_type_pattern = r"((?:(?:(?:Pre-|pre-)?[A-H]\d?|天使|种子|新一|上一?|本|此|该|两|首)(?:\+)?(?:轮|次)(?:融资|投资)?)|天使投资)"
        self.pattern = "".join([self.deal_type_pattern, r"来自", self.investors_pattern[0]])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {"investors": self.investors_pattern[1]}
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)

class Rule12(SuperRule):
    def __init__(self):
        super().__init__()
        self.pattern = "".join([self.deal_size_pattern[0], "的?", self.deal_type_pattern])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {"deal_size": self.deal_size_pattern[1]}
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)
    
class Rule13(SuperRule):
    def __init__(self):
        super().__init__()
        self.pattern = "".join([r"(?:完成|获得?)", self.investors_pattern[0], self.anychar_notag_pattern, self.may_be_deal_size_pattern[0], self.deal_type_pattern])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "investors": self.investors_pattern[1],
            "deal_size": self.may_be_deal_size_pattern[1],
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)
        
class Rule14(SuperRule):
    def __init__(self):
        super().__init__()
        self.pattern = "".join([self.full_financing_company_pattern[0], self.anychar_notag_pattern, "，"])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "business_profile": self.financing_company_pattern[1], 
            "financing_company": self.financing_company_pattern[2], 
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)
    
class Rule15(SuperRule):
    def __init__(self):
        super().__init__()
        self.pattern = "".join([self.financing_company_pattern[0], self.anychar_notag_pattern, r"宣布|获|完成", 
                                self.anychar_notag_pattern, r"[，；]", self.anychar_notag_pattern, self.deal_type_pattern])
        self.reobj = re.compile(self.pattern)
        self.field_name2tag_name = {
            "business_profile": self.financing_company_pattern[1], 
            "financing_company": self.financing_company_pattern[2], 
        }
        
    def __call__(self, entities_sent: str, attr_noun_dict: dict):
        return self.construct(entities_sent)
