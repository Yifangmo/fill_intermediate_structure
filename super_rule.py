import re
from typing import Callable

class SuperRule(object):
    def __init__(self):
        self.financing_company_pattern = (r"(?:(?P<bp><融资方标签>)?(?P<fc><关联方>))", "bp", "fc")
        self.full_financing_company_pattern = (r"(?:(?P<bp><融资方标签>)(?P<fc><关联方>))", "bp", "fc")
        self.investors_pattern = (r"(?P<i>(?:(?:<属性名词>的?)?(?:<关联方>)(?:（<属性名词>）)?(?:、|和|以?及)?)+)等?(?:机构|基金|则?(?:以|作为)?(?:<属性名词>))?", "i")
        self.may_be_deal_size_pattern = (r"(?P<ds><金额>)?", "ds")
        self.single_rp_pattern = (r"(?P<rp><关联方>)?", "rp")
        self.deal_size_pattern = (r"(?P<ds><金额>)", "ds")
        self.may_be_deal_type_pattern = r"(?:<交易类型>)?"
        self.deal_type_pattern = r"<交易类型>"
        self.date_pattern = r"(?:<发生时间>|<披露时间>)?"
        self.attr_noun_pattern = (r"(?P<attr><属性名词>)", "attr")
        self.anychar_pattern = r"[^，；]*?"
        self.anychar_notag_pattern = r"[^，；<>]*?"
    
    def construct(self, entities_sent: str, is_leading_investor: bool = False, attr_handler: Callable = None):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        if attr_handler:
            for m in matches:
                struct = {}
                res = attr_handler(m)
                for r in res:
                    if r[1]:
                        sp = m.span(self.field_name2tag_name[r[0]])
                        if sp != (-1,-1):
                            if r[0] == "investors":
                                struct["investors"] = get_multi_value_idx_spans(entities_sent, sp, "<关联方>")
                                struct["is_leading_investor"] = is_leading_investor
                                continue
                            if r[0]== "finacial_advisers":
                                struct["finacial_advisers"] = get_multi_value_idx_spans(entities_sent, sp, "<关联方>")
                                continue
                            struct[r[0]] = sp
                    else:
                        break
                if len(struct) > 0:
                    mr = {"struct": struct}
                    mr["match_span"] = m.span()
                    mr["from_rule"] = self.__class__.__name__
                    match_result.append(mr)
        else:
            for m in matches:
                struct = {}
                for field_name, tag_name in self.field_name2tag_name.items():
                    sp = m.span(tag_name)
                    if sp == (-1, -1):
                        continue
                    if field_name == "investors":
                        primary_names = get_multi_value_idx_spans(entities_sent, sp, "<关联方>")
                        struct["investors"] = primary_names
                        struct["is_leading_investor"] = is_leading_investor
                        continue
                    struct[field_name] = sp
                if len(struct) > 0:
                    mr = {"struct": struct}
                    mr["match_span"] = m.span()
                    mr["from_rule"] = self.__class__.__name__
                    match_result.append(mr)
        return match_result

def get_multi_value_idx_spans(entities_sent: str, pos_span: tuple, match_for: str):
    res = []
    list_reobj = re.compile(match_for)
    matches = list_reobj.finditer(entities_sent, pos_span[0], pos_span[1])
    for m in matches:
        res.append(m.span())
    return res