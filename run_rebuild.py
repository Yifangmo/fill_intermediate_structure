#!/usr/bin/env python
from re import I
import requests
import json
import re

LABEL_ER = ('(<关联方>)', 5)
LABEL_AM = ('(<金额>)', 4)
LABEL_ATTR = ('(<属性名词>)', 6)
LABEL_OT = ('(<发生时间>)', 6)
LABEL_PT = ('(<披露时间>)', 6)
LABEL_DT = ('(<交易类型>)', 6)
LABEL_FL = ('(<融资方标签>)', 7)

WILDCARD = '[^，]*'

LABEL_STR_MAP = {
    "关联方": LABEL_ER,
    "金额": LABEL_AM,
    "属性名词": LABEL_ATTR,
    "发生时间": LABEL_OT,
    "披露时间": LABEL_PT,
    "交易类型": LABEL_DT,
    "融资方标签": LABEL_FL
}


class MyJSONEncoder(json.JSONEncoder):
    
  def iterencode(self, o, _one_shot=False):
    list_lvl = 0
    for s in super(MyJSONEncoder, self).iterencode(o, _one_shot=_one_shot):
      if s.startswith('['):
        list_lvl += 1
        s = s.replace('\n', '').rstrip()
      elif 0 < list_lvl:
        s = s.replace('\n', '').rstrip()
        if s and s[-1] == ',':
          s = s[:-1] + self.item_separator
        elif s and s[-1] == ':':
          s = s[:-1] + self.key_separator
      if s.endswith(']'):
        list_lvl -= 1
      yield s

def get_ner_predict(sent):
    """
    Args:
        sent: str, 要打标的句子
    """
    data = json.dumps({"sent": sent, "use_ner": 0})
    r = requests.post(
        "http://192.168.88.204:6004/run_ner_predict", data=data.encode("utf-8"))
    res = json.loads(r.text)
    return res

class Rule1(object):
    def __init__(self):
        self.pattern = r"(<披露时间>|<发生时间>)?[^，<>]*(<融资方标签>)?(<关联方>)?[^，<>]*(<披露时间>|<发生时间>)?[^，<>]*(?:完成|获)[^，<>]*(?:((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)?等?(领投|牵头)?)?[^，<>]*(?:(<交易类型>)?|(?:<属性名词>)?)(<金额>)?[^，<>]*(<交易类型>)"
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["date", "business_profile", "financing_company",
                                     "date", "investors", "is_leading_investor", "deal_type", "deal_size", "deal_type"]

    def __call__(self, entities_sent, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            dates = []
            deal_type = ""
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                if sp == (-1, -1):
                    continue
                if field_name == "investors":
                    spans = get_multi_value_idx_spans(
                        entities_sent, sp, "<关联方>")
                    primary_names = get_field_values(
                        sent, entities_index_dict, spans)
                    struct["investors"] = primary_names
                    struct["is_leading_investor"] = False
                    labels_used.update(spans)
                else:
                    if field_name == "is_leading_investor":
                        struct["is_leading_investor"] = True
                    else:
                        field_value = get_field_value(
                            sent, entities_index_dict, sp)
                        labels_used.add(sp)
                        if field_name == "date":
                            dates.append(field_value)
                        elif field_name == "deal_type":
                            deal_type += field_value
                        else:
                            struct[field_name] = field_value
            if len(dates) > 0:
                struct["dates"] = dates
                pass
            if deal_type != "":
                struct["deal_type"] = deal_type
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["labels_used"] = labels_used
                mr["from_rule"] = "Rule1"
                match_result.append(mr)
        return match_result


class Rule2(object):
    def __init__(self):
        # self.pattern = r"(?:((?:本|该|此)轮(?:战略)?(?:融资|投资)|<交易类型>)?由|由|^|(?<=，|>)|(?<=[^>]、))((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:机构|基金|(<属性名词>))?(?:联合|重仓加码|共同|独家)?领投"
        self.pattern = r"((?:本|该|此)轮(?:战略)?(?:融资|投资)|<交易类型>)?[^，<>]*((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:机构|基金|(<属性名词>))?(?:联合|重仓加码|共同|独家)?领投"
        self.reobj = re.compile(self.pattern)
        self.deal_type_group_id = 1
        self.investors_group_id = 2
        self.attr_noun_group_id = 3
        self.pattern_mapping = {1: "deal_type", 2: "investors"}

    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            labels_used = set({})
            if m.span(self.deal_type_group_id) != (-1, -1):
                sp = m.span(self.deal_type_group_id)
                deal_type = get_field_value(sent, entities_index_dict, sp)
                if deal_type:
                    struct["deal_type"] = deal_type
                    labels_used.add(sp)
                else:
                    struct["deal_type"] = m.group(self.deal_type_group_id)
            investors_idx_span = m.span(self.investors_group_id)
            investor_idx_spans = get_multi_value_idx_spans(
                entities_sent, investors_idx_span, "<关联方>")
            primary_names = get_field_values(
                sent, entities_index_dict, investor_idx_spans)
            if len(primary_names) > 0:
                struct["investors"] = primary_names
                struct["is_leading_investor"] = True
                labels_used.update(investor_idx_spans)
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["labels_used"] = labels_used
                mr["from_rule"] = "Rule2"
                match_result.append(mr)
        return match_result


class Rule3(object):
    def __init__(self):
        # 其中，红杉中国作为老股东继续增持，华平投资则是本轮新进入的领投方。
        self.pattern = r"(?:((?:本|该|此)轮(?:战略)?(?:融资|投资)|<交易类型>)?由|由|^|(?<=，|>|\w)|(?<=[^>]、)|(?<=<属性名词>))((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:机构|基金|则?(以|作为)?(?:<属性名词>)?)?也?(?:联合|共同|继续|同轮|独家|超额)?(?:参与到?|追加)?了?(?:战略)?(?:((?:本轮|本次)(?:投资|融资))|融资|投资|跟投|加持|增持|参投)"
        self.reobj = re.compile(self.pattern)
        self.deal_type1_group_id = 1
        self.investors_group_id = 2
        self.attr_noun_group_id = 3
        self.deal_type2_group_id = 4

    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            labels_used = set({})
            deal_type = None
            if m.span(self.deal_type1_group_id) != (-1, -1):
                sp = m.span(self.deal_type1_group_id)
                deal_type = get_field_value(sent, entities_index_dict, sp)
                if deal_type:
                    struct["deal_type"] = deal_type
                    labels_used.add(sp)
                else:
                    struct["deal_type"] = m.group(self.deal_type1_group_id)
            investors_idx_span = m.span(self.investors_group_id)
            investor_idx_spans = get_multi_value_idx_spans(
                entities_sent, investors_idx_span, "<关联方>")
            primary_names = get_field_values(
                sent, entities_index_dict, investor_idx_spans)
            if len(primary_names) > 0:
                struct["investors"] = primary_names
                struct["is_leading_investor"] = False
                labels_used.update(investor_idx_spans)
            if not deal_type:
                deal_type = m.group(self.deal_type2_group_id)
            if deal_type:
                struct["deal_type"] = deal_type
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["labels_used"] = labels_used
                mr["from_rule"] = "Rule3"
                match_result.append(mr)
        return match_result


class Rule4(object):
    def __init__(self):
        # <融资方标签><关联方>连续完成<属性名词><金额>的<交易类型>与<交易类型>
        self.patterns_for_attr_noun = [r'(?:总|整体|累计)?融资(?:总?金?额|规模|累计金?额)|规模', r'投前估值', r'后估值', r'估值',
                                       r'投资方|投资人|投资者|投资机构|参投方?', r'领投方?|领投机构', r'财务顾问|融资顾问']
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
        self.deal_type_pattern = r'((?:本次|本轮)?(?:(?:(?:Pre-|pre-)?[A-H]\d?|天使|种子|战略|新一|上一?|本|此|该|两|首)(?:\+)?(?:轮|次)(?:融资)?)|天使投资)'
        self.deal_type_group_id = 1
        self.deal_type_reobj = re.compile(self.deal_type_pattern)
        self.patterns_with_multi_value_list_idx = {1, 2, 3}
        self.field_name_with_multi_value = {
            'investors', 'leading_investors', 'finacial_advisers'}
        self.reobjs = [(re.compile(i[0]), [re.compile(j)
                        for j in i[1]], i[2]) for i in self.patterns_for_sentence]
        self.attr_noun_pattern_to_field_name = {
            self.deal_type_pattern: 'deal_type',
            self.patterns_for_attr_noun[0]: 'deal_size',
            self.patterns_for_attr_noun[1]: 'pre_money_valuation',
            self.patterns_for_attr_noun[2]: 'post_money_valuation',
            self.patterns_for_attr_noun[3]: 'valuation',
            self.patterns_for_attr_noun[4]: 'investors',
            self.patterns_for_attr_noun[5]: 'leading_investors',
            self.patterns_for_attr_noun[6]: 'finacial_advisers'
        }

    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        match_result = []
        for i, reobj in enumerate(self.reobjs):
            matches = reobj[0].finditer(entities_sent)
            attr_noun_content_reobjs = list(reobj[1])
            attr_noun_group_id = reobj[2][0]
            field_value_group_id = reobj[2][1]
            for match in matches:
                struct = {}
                labels_used = set({})
                attr_noun_idx_span = match.span(attr_noun_group_id)
                field_value_idx_spans = [match.span(field_value_group_id)]
                if i in self.patterns_with_multi_value_list_idx:
                    field_value_idx_spans = get_multi_value_idx_spans(
                        entities_sent, field_value_idx_spans[0], "<关联方>")
                attr_noun_origin_str = get_field_value(
                    sent, entities_index_dict, attr_noun_idx_span)
                field_values = get_field_values(
                    sent, entities_index_dict, field_value_idx_spans)
                m = self.deal_type_reobj.search(attr_noun_origin_str)
                if m:
                    struct["deal_type"] = m.group(self.deal_type_group_id)
                
                for ro in attr_noun_content_reobjs:
                    m = ro.search(attr_noun_origin_str)
                    if m:
                        field_name = self.attr_noun_pattern_to_field_name[m.re.pattern]
                        if field_name == "investors":
                            struct["investors"] = field_values
                            struct["is_leading_investor"] = False
                        elif field_name == "leading_investors":
                            struct["investors"] = field_values
                            struct["is_leading_investor"] = True
                        elif field_name == "finacial_advisers":
                            struct["finacial_advisers"] = field_values
                        else:
                            struct[field_name] = field_values[0]
                        labels_used.add(attr_noun_idx_span)
                        labels_used.update(field_value_idx_spans)
                if len(struct) > 0:
                    mr = {"struct": struct}
                    mr["labels_used"] = labels_used
                    mr["from_rule"] = "Rule4"
                    match_result.append(mr)

        return match_result

class Rule5(object):
    def __init__(self):
        self.pattern = r"(<关联方>)[^，]*签署(<交易类型>)协议"
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["financing_company", "deal_type"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                struct[field_name] = get_field_value(sent, entities_index_dict, sp)
                labels_used.add(sp)
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule5"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result
    
class Rule6(object):
    def __init__(self):
        # 中俄投资基金进行战略性股权投资
        self.investors_pattern = r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?"
        self.pattern = self.investors_pattern + r"进行(<交易类型>)"
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["investors", "deal_type"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                if field_name == "investors":
                    spans = get_multi_value_idx_spans(
                        entities_sent, sp, "<关联方>")
                    primary_names = get_field_values(
                        sent, entities_index_dict, spans)
                    struct["investors"] = primary_names
                    struct["is_leading_investor"] = False
                    labels_used.update(spans)
                    continue
                struct[field_name] = get_field_value(sent, entities_index_dict, sp)
                labels_used.add(sp)
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule6"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result
   
class Rule7(object):
    def __init__(self):
        # 作为多家知名创投身后的母基金，元和资本这次选择了直接投资玻色量子。
        # 此前，百度资本、软银愿景基金、创新工场、成为资本、越秀产业基金、广州新兴基金等机构以12亿人民币投资「极飞科技」是中国农业科技领域历史上最大的一笔商业融资。
        # 作为<属性名词>，<关联方>这次选择了直接投资<关联方>。
        # 此前，<关联方>、<关联方>、<关联方>、<关联方>、<关联方>、<关联方>等<属性名词>以<金额>投资「<关联方>」是中国农业科技领域历史上最大的一笔商业融资。
        investors_pattern = r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?"
        financing_company_pattern = r"(<融资方标签>)?(<关联方>)"
        date_pattern = r"(<披露时间>|<发生时间>)?[^，<>]*"
        attr_pattern = r"(?:<属性名词>)?"
        # self.pattern = r"(?:<属性名词>)?(<关联方>)投资(关联方)"
        self.pattern = "".join([date_pattern, investors_pattern, attr_pattern, date_pattern, \
            r"(<金额>)?[^，<>]*", r"投资", financing_company_pattern ])
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["date", "investors", "date", "deal_size", "business_profile", "financing_company"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            dates = []
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                if sp == (-1, -1):
                    continue
                if field_name == "investors":
                    spans = get_multi_value_idx_spans(
                        entities_sent, sp, "<关联方>")
                    primary_names = get_field_values(
                        sent, entities_index_dict, spans)
                    struct["investors"] = primary_names
                    struct["is_leading_investor"] = False
                    labels_used.update(spans)
                else:
                    field_value = get_field_value(
                        sent, entities_index_dict, sp)
                    labels_used.add(sp)
                    if field_name == "date":
                        dates.append(field_value)
                    else:
                        struct[field_name] = field_value
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule7"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result

class Rule8(object):
    def __init__(self):
        # 专注于人工智能的农业技术初创公司Intello Labs在由Avaana Capital牵头的一轮融资中筹集了500万美元
        self.pattern = r"(<披露时间>|<发生时间>)?[^，<>]*(<融资方标签>)?(<关联方>)[^，<>]*(<披露时间>|<发生时间>)?[^，<>]*由((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?(?:领投|牵头)[^，<>]*(<交易类型>)[^，<>]*(<金额>)"
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["date", "business_profile", "financing_company", "date", "investors", "deal_type", "deal_size"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            dates = []
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                if sp == (-1, -1):
                    continue
                if field_name == "investors":
                    spans = get_multi_value_idx_spans(
                        entities_sent, sp, "<关联方>")
                    primary_names = get_field_values(
                        sent, entities_index_dict, spans)
                    struct["investors"] = primary_names
                    struct["is_leading_investor"] = True
                    labels_used.update(spans)
                else:
                    field_value = get_field_value(
                        sent, entities_index_dict, sp)
                    labels_used.add(sp)
                    if field_name == "date":
                        dates.append(field_value)
                    else:
                        struct[field_name] = field_value

            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule8"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result

class Rule9(object):
    def __init__(self):
        # 此次注资，是高瓴创投对去年11月极飞科技12亿元人民币融资的追加投资。
        # '此次注资，是<关联方>对<发生时间><关联方><金额><交易类型>的追加投资。'
        investors_pattern = r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?"
        financing_company_pattern = r"(<融资方标签>)?(<关联方>)"
        date_pattern = r"(<披露时间>|<发生时间>)?[^，<>]*"
        self.pattern = "".join([date_pattern, investors_pattern, date_pattern, r"对", date_pattern, \
            financing_company_pattern, date_pattern, r"(<金额>)?[^，<>]*", r"(<交易类型>)?[^，<>]*", r"投资"])
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["date", "investors", "date", "date", "business_profile", "financing_company", \
            "date", "deal_size", "deal_type"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            dates = []
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                if sp == (-1, -1):
                    continue
                if field_name == "investors":
                    spans = get_multi_value_idx_spans(
                        entities_sent, sp, "<关联方>")
                    primary_names = get_field_values(
                        sent, entities_index_dict, spans)
                    struct["investors"] = primary_names
                    struct["is_leading_investor"] = False
                    labels_used.update(spans)
                else:
                    field_value = get_field_value(
                        sent, entities_index_dict, sp)
                    labels_used.add(sp)
                    if field_name == "date":
                        dates.append(field_value)
                    else:
                        struct[field_name] = field_value
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule9"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result

class Rule10(object):
    def __init__(self):
        # Stripe估值达到950亿美元
        self.pattern = r"(<关联方>)估值达到?(<金额>)"
        self.reobj = re.compile(self.pattern)
        self.field_names_in_order = ["financing_company", "post_money_valuation"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                sp = m.span(group_id)
                struct[field_name] = get_field_value(sent, entities_index_dict, sp)
                labels_used.add(sp)
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule10"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result

class Rule11(object):
    def __init__(self):
        # 本轮投资来自险峰长青。
        self.deal_type_pattern = r"((?:(?:(?:Pre-|pre-)?[A-H]\d?|天使|种子|新一|上一?|本|此|该|两|首)(?:\+)?(?:轮|次)(?:融资|投资)?)|天使投资)"
        self.investors_pattern = r"((?:(?:<属性名词>的?)?(?:<关联方>)(?:、|和|以?及)?)+)等?"
        self.pattern = "".join([self.deal_type_pattern, r"来自", self.investors_pattern])
        self.reobj = re.compile(self.pattern)
        self.deal_type_group_id = 1
        self.field_names_in_order = ["deal_type", "investors"]
        
    def __call__(self, entities_sent: str, sent: str, entities_index_dict: dict):
        matches = self.reobj.finditer(entities_sent)
        match_result = []
        for m in matches:
            struct = {}
            labels_used = set({})
            for group_id, field_name in enumerate(self.field_names_in_order, 1):
                if group_id == self.deal_type_group_id:
                    struct[field_name] = m.group(group_id)
                if field_name == "investors":
                    spans = get_multi_value_idx_spans(
                        entities_sent, m.span(group_id), "<关联方>")
                    primary_names = get_field_values(
                        sent, entities_index_dict, spans)
                    struct["investors"] = primary_names
                    struct["is_leading_investor"] = False
                    labels_used.update(spans)
            if len(struct) > 0:
                mr = {"struct": struct}
                mr["from_rule"] = "Rule11"
                mr["labels_used"] = labels_used
                match_result.append(mr)
        return match_result

def get_multi_value_idx_spans(entities_sent: str, pos_span: tuple, count_for: str):
    res = []
    list_reobj = re.compile(count_for)
    matches = list_reobj.finditer(entities_sent, pos_span[0], pos_span[1])
    for m in matches:
        res.append(m.span())
    return res

def get_field_value(sent: str, entities_index_dict: dict, span: tuple):
    if span not in entities_index_dict:
        print("get_field_value 实体索引映射错误：({},{})".format(span[0], span[1]))
        return
    sent_idx_span = entities_index_dict[span]
    return sent[sent_idx_span[0]: sent_idx_span[1]]

def get_field_values(sent: str, entities_index_dict: dict, spans: list):
    res = []
    for sp in spans:
        if sp not in entities_index_dict:
            print("get_field_values 实体索引映射错误：({},{})".format(sp[0], sp[1]))
            continue
        sent_idx_span = entities_index_dict[sp]
        res.append(sent[sent_idx_span[0]:sent_idx_span[1]])
    return res

def get_classified_alias(alias: set):
    english_names = {n for n in alias if re.fullmatch(
        r"([A-Za-z\d]{3,}(?:\s[A-Za-z\d]+)*)", n)}
    full_names = {n for n in alias if n.endswith(('公司','集团','基金'))}
    primary_names = alias - english_names - full_names
    if len(primary_names) == 0:
        primary_names = full_names
    if len(primary_names) == 0:
        primary_names = english_names
    names = {}
    if len(primary_names) > 0:
        names["primary_name"] = sorted(primary_names, key=lambda n: (len(n), n), reverse=True)[0]
    if len(english_names) > 0:
        names["english_name"] = sorted(english_names, key=lambda n: (len(n), n), reverse=True)[0]
    if len(full_names) > 0:
        names["full_name"] = sorted(full_names, key=lambda n: (len(n), n), reverse=True)[0]
    return names

# 获取某个分句的位置
def get_clause_pos(sent: str, token: str):
    sent.rfind()
    pass

# 去除无关紧要的空白字符、引号等；将英文标点转换为中文标点；将标签指示符转为书名号
def normalize_sentence(sent: str):
    def repl(m):
        dic = {1: "", 2: "，", 3: "；", 4: "：", 5: "（", 6: "）", 7: "《", 8: "》"}
        for i in range(1, 7):
            if m.group(i):
                return dic[i]
    # 处理标题的空格
    if not sent.endswith("。") or sent.endswith("？"):
        # sent = re.sub(r'(?<![A-Za-z])\s(?![A-Za-z])', '，', sent)
        pass
    return re.sub(r'((?<![A-Za-z])\s|\s(?![A-Za-z])|“|”|「|」|‘|’)|(,)|(;)|(:)|(\()|(\))|(<)|(>)', repl, sent)


class EntitiesDictExtrator(object):
    def __init__(self, funcs: list):
        self.validate_deal_type_reobj = re.compile(r"(((Pre-)?[A-H]\d?|天使|种子|战略|IPO|新一|上一?|本|此|该|两|首)(\++|＋+|plus)?(系列)?(轮|次)(融资|投资|投融资)?|(天使|种子|战略|风险|IPO|股权)(融资|投资|投融资)|融资|投资)", re.I)
        self.validate_attr_noun_reobj = re.compile(r'(?:总|整体|累计)?融资(?:总?金?额|规模|累计金?额)|投前估值|后估值|估值|投资方|投资人|投资者|投资机构|领投方|领投机构|财务顾问|融资顾问')
        self.repl_deal_type_reobj = re.compile(r'(轮|次|笔|轮战略)?(投资|融资)|投融资')
        self.date_reobj = re.compile(r'\d{1,2}月\d{1,2}日|年\d{1,2}月')
        self.verb_reobj = re.compile(r"获|完成")
        self.func_a = funcs
        
    # 返回交易类型实体到实际交易事件的映射
    def get_deal_type_dict(self,  sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        # 交易类型替换后的值到交易类型标签的映射，每个替换后的值代表一个实际交易事件
        repl_dt_dict = {}
        # 交易类型实体到实际交易事件的映射
        deal_type_entity_dict = {}
        # 实际交易事件
        real_deal_types = []
        for i, li in enumerate(labels_indexes):
            label_content = sent[li[0]:li[1]]
            if li[2] == "交易类型":
                repl_dt = self.repl_deal_type_reobj.sub("", label_content)
                pre_comma_pos = sent.rfind('，', None, li[0])
                post_comma_pos = sent.find('，', li[1], None)
                if repl_dt != "":
                    # 无效交易类型实体
                    if label_content.endswith("投资") and not self.verb_reobj.search(sent, pre_comma_pos, li[0]) \
                        or re.search(r"第|两|三|四|五|又一|(?<![a-zA-Z])\d", repl_dt):
                        deal_type_entity_dict[label_content] = None
                    else:
                        if repl_dt in repl_dt_dict:
                            pre = repl_dt_dict[repl_dt]
                            # TODO
                            real_dt = pre if len(pre) > len(label_content) else label_content
                            deal_type_entity_dict[pre][2] = real_dt
                            deal_type_entity_dict[label_content] = [pre_comma_pos, post_comma_pos, real_dt]
                        else:
                            repl_dt_dict[repl_dt] = label_content
                            deal_type_entity_dict[label_content] = [pre_comma_pos, post_comma_pos, label_content]
                elif re.match(r'融资|投资', label_content):
                    if  i > 1 and labels_indexes[i-1][2] == "金额" and labels_indexes[i-2][2] == "交易类型":
                        pre_dt_label = deal_type_entity_dict[repl_dt_dict[pre_dt]][2]
                        if not pre_dt_label.endswith(('投资', '融资')):
                            deal_type_entity_dict[repl_dt_dict[pre_dt]][2] += label_content
        if len(repl_dt_dict) == 1:
            for k, v in deal_type_entity_dict.items():
                v[0] = 0
                v[1] = len(sent)
        return deal_type_entity_dict

        # dt_reobj = re.compile(
        #     r"(?:(?:(?:Pre-)?[A-H]\d?|天使|种子|新一|上一?|本|此|该|两|首)(?:\+)?(?:轮|次)(?:融资)?)|天使投资", re.I)

    def get_date_dict(self, sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        occurrence_dates = {}
        disclosed_dates = {}
        accurate_occurrence_dates = []
        accurate_disclosed_dates = []
        first_comma_pos = sent.find('，')
        for li in labels_indexes:
            label_content = sent[li[0]:li[1]]
            pre_comma_pos = sent.rfind('，', None, li[0])
            post_comma_pos = sent.rfind('，', None, li[1])   
            match = self.date_reobj.search(label_content)
            if li[2] == "披露时间":
                if match:
                    accurate_disclosed_dates.append((li[0], li[1]))
                if not match and li[0] > first_comma_pos:
                    disclosed_dates[label_content] = [pre_comma_pos, post_comma_pos, accurate_disclosed_dates[0]] if len(accurate_disclosed_dates)>0 else [pre_comma_pos, post_comma_pos, None]
                else:
                    disclosed_dates[label_content] = [0, len(sent), label_content] if match else [0, len(sent), None]
            elif li[2] == "发生时间":
                if match:
                    accurate_occurrence_dates.append((li[0], li[1]))
                if not match and li[0] > first_comma_pos:
                    occurrence_dates[label_content] = [pre_comma_pos, post_comma_pos, accurate_occurrence_dates[0]] if len(accurate_occurrence_dates)>0 else [pre_comma_pos, post_comma_pos, None]
                else:
                    occurrence_dates[label_content] = [0, len(sent), label_content] if match else [0, len(sent), None]
        for k, v in disclosed_dates.items():
            if v[2]:
                continue
            v[2] = sent[accurate_disclosed_dates[0][0]:accurate_disclosed_dates[0][1]] if len(accurate_disclosed_dates)>0 else k
        for k, v in occurrence_dates.items():
            if v[2]:
                continue
            v[2] = sent[accurate_occurrence_dates[0][0]:accurate_occurrence_dates[0][1]] if len(accurate_occurrence_dates)>0 else k

        return occurrence_dates, disclosed_dates
            
    def validate_deal_type(self, sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        labels_unused = []
        
        new_labels_indexes = []
        for li in labels_indexes:
            label_content = sent[li[0]:li[1]]
            if li[2] != '交易类型' or li[2] == '交易类型' and self.validate_deal_type_reobj.search(re.sub(r"\s",'', label_content)):
                new_labels_indexes.append(li)
            else:
                labels_unused.append([label_content, li[2]])
        del labels_indexes

        return new_labels_indexes, labels_unused

    def get_entities_sent(self, sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        entities_sent, entities_index_dict, labels_value, alias = "", {}, [], {}
        # 标签替换前后首索引差值
        replaced_list = []
        idx_diff = 0
        start = 0
        for i, label in enumerate(labels_indexes):
            label_content = sent[label[0]:label[1]]
            replaced_list.append(sent[start:label[0]])
            # 转为标签名和值
            labels_value.append([label_content, label[2]])
            # 生成标签索引映射
            label_start_idx = label[0]+idx_diff
            label_length = LABEL_STR_MAP[label[2]][1]
            entities_index_dict[(
                label_start_idx, label_start_idx + label_length)] = (label[0], label[1])
            idx_diff += (label_length - (label[1] - label[0]))
            # 替换为标签
            replaced_list.append("<"+label[2]+">")
            start = label[1]
            # 使融资方标签和关联方标签邻近
            if label[2] == '融资方标签' and (i + 1) < len(labels_indexes) and labels_indexes[i + 1][2] == "关联方":
                idx_diff -= (labels_indexes[i + 1][0] - start)
                start = labels_indexes[i + 1][0]
                
            if label[2] == '关联方':
                er = sent[label[0]:label[1]]
                # 处理括号内别名
                alias[er] = {er}
                if start < len(sent) and sent[start] == '（':
                    end = sent.find('）', start)
                    # 排除一些情况，包括有标签<>的
                    if end == -1 or re.search('<|隶属|领投|估值|股票代码', sent[start+1:end]):
                        continue
                    alias_reobj = re.compile(r"(?:简称|英文名|下称)：?")
                    m = alias_reobj.search(sent, start+1, end)
                    # “简称|英文名：”后是别名，若无则默认括号内都是别名
                    s = m.end() if m else start+1
                    als = {sent[s:end]}
                    # 处理简称前可能有英文名的情况
                    english_name_reobj = re.compile(
                        r"([A-Za-z\d]{3,}(?:\s[A-Za-z\d]+)*)")
                    e = m.start() if m else end
                    m = english_name_reobj.search(sent, start+1, e)
                    if m:
                        als.add(sent[m.start():m.end()])
                    alias[er] |= als
                    # 移除括号及其内容，方便后续模板设计
                    idx_diff -= (end + 1 - start)
                    start = end + 1
        
        replaced_list.append(sent[start:])
        entities_sent = "".join(replaced_list)
        return labels_value, entities_index_dict, entities_sent, alias

    # 填充deal_type，对dates分类，处理关联方别名，统计标签使用情况
    def adjust_field(self, sentence_struct_info):
        sent = sentence_struct_info["sent"]
        entities_sent = sentence_struct_info["entities_sent"]
        deal_type_dict = sentence_struct_info["deal_type_dict"]
        occurrence_dates = sentence_struct_info["occurrence_dates"]
        disclosed_dates = sentence_struct_info["disclosed_dates"]
        match_result = sentence_struct_info["match_result"]
        entities_index_dict = sentence_struct_info["entities_index_dict"]
        total_labels = set(entities_index_dict.keys())
        total_labels_used = set({})
        alias = sentence_struct_info["alias"]
        invalid_mr = []
        for mr in match_result:
            mr_struct = mr["struct"]
            total_labels_used |= mr["labels_used"]
            dt_set = {i[2] for i in deal_type_dict.values() if i}
            # 有交易类型
            if "deal_type" in mr_struct:
                mr_deal_type = mr_struct["deal_type"]
                # 指代交易类型
                if mr_deal_type not in deal_type_dict:
                    if len(dt_set) == 1:
                        mr_struct["deal_type"] = dt_set.__iter__().__next__()
                    elif len(dt_set) == 0:
                        continue
                # 无效交易类型
                elif not deal_type_dict[mr_deal_type]:
                    del mr_struct["deal_type"]
                # 有效交易类型
                else:
                    mr_struct["deal_type"] = deal_type_dict[mr_deal_type][2]
            # 无交易类型
            else:
                if len(dt_set) == 1:
                    mr_struct["deal_type"] = dt_set.__iter__().__next__()
                else:
                    pass
            
            if "dates" in mr_struct:
                mr_dates = mr_struct["dates"]
                for date in mr_dates:
                    if date in occurrence_dates:
                        mr_struct["occurrence_date"] = occurrence_dates[date][2]
                    elif date in disclosed_dates:
                        mr_struct["disclosed_date"] = disclosed_dates[date][2]
            else:
                if len(occurrence_dates) == 1:
                    for k, v in occurrence_dates.items():
                        mr_struct["occurrence_date"] = v[2]
                if len(disclosed_dates) == 1:
                    for k, v in disclosed_dates.items():
                        mr_struct["disclosed_date"] = v[2]

            if "financing_company" in mr_struct:
                fc_name = mr_struct["financing_company"]
                fc = {}
                names = get_classified_alias(alias[fc_name])
                for k, v in names.items():
                    fc[k] = v
                mr_struct["financing_company"] = fc
            if "investors" in mr_struct:
                is_leading_investor = mr_struct.pop("is_leading_investor", False)
                investors = []
                for i_name in mr_struct["investors"]:
                    investor = {}
                    names = get_classified_alias(alias[i_name])
                    for k, v in names.items():
                        investor[k] = v
                    investor["is_leading_investor"] = is_leading_investor
                    investors.append(investor)
                mr_struct["investors"] = investors
            del mr["labels_used"]
        for imr in invalid_mr:
            match_result.remove(imr)
        total_labels_unused = total_labels - total_labels_used
        labels_unused = []
        for i in sorted(total_labels_unused):
            try:
                sent_index = entities_index_dict[i]
                labels_unused.append([entities_sent[i[0]+1:i[1]-1], sent[sent_index[0]:sent_index[1]]])
            except KeyError:
                print("实体索引映射错误：({},{})".format(i[0], i[1]))
            pass
        sentence_struct_info["labels_unused"]+=labels_unused
        sentence_struct_info["labels_unused_count"] = len(sentence_struct_info["labels_unused"])
        del sentence_struct_info["entities_index_dict"]
        return

    def __call__(self, sent):
        # print("sentence before normalize: " + sent)
        sent = normalize_sentence(sent)
        # print("sentence after normalize: " + sent)
        resp = get_ner_predict(sent)
        if resp["error_message"] or not "labels_indexes" in resp["response"]:
            print(resp["error_message"], ": ", sent)
            return
        labels_indexes = resp["response"]["labels_indexes"]
        sentence_struct_info = {
            "sent": sent,
            "labels_indexes": labels_indexes,
        }
        sentence_struct_info["labels_indexes"], sentence_struct_info["labels_unused"] = self.validate_deal_type(sentence_struct_info)
        sentence_struct_info["deal_type_dict"] = self.get_deal_type_dict(sentence_struct_info)
        sentence_struct_info["occurrence_dates"], sentence_struct_info["disclosed_dates"] = self.get_date_dict(sentence_struct_info)
        sentence_struct_info["labels_value"],sentence_struct_info["entities_index_dict"], sentence_struct_info["entities_sent"],sentence_struct_info["alias"] = self.get_entities_sent(sentence_struct_info)
        entities_sent = sentence_struct_info["entities_sent"]
        entities_index_dict = sentence_struct_info["entities_index_dict"]

        match_result = []
        for func in self.func_a:
            match_result += func(entities_sent, sent, entities_index_dict)
        sentence_struct_info["match_result"] = match_result
        
        print("match_result： ", sentence_struct_info["match_result"])
        print()

        self.adjust_field(sentence_struct_info)
        return sentence_struct_info

ede = EntitiesDictExtrator([Rule1(), Rule2(), Rule3(), Rule4(), Rule5(), Rule6(), Rule7() ,Rule8(), Rule9(), Rule10(), Rule11()])
def call(sent):
    return ede(sent)

if __name__ == "__main__":
    # 多分句共用关联方
    obj = call("苏宁易购出让23%股份，获深国际、鲲鹏资本148.17亿元战略投资")
    # obj = call("9月1日消息，近日，教育机器人及STEAM玩教具公司LANDZO蓝宙科技宣布，公司已于6月完成A轮1.89亿元融资，投资方为至临资本、文化产业上市资方、中视金桥、南京市政府基金，庚辛资本担任长期独家财务顾问。")
    # obj = call("投资界（ID：pedaily2012）5月11日消息，近期，上海九穗农业科技有限公司（以下简称：米小芽），再次获得数千万A轮融资，由老股东新梅资本领投。")
    # obj = call("业内人士分析，在目前市场偏于谨慎的投资环境下，金智维逆势完成融资，再获逾2亿元资本加持")
    
    # 属性名词问题
    # obj = call("还有市场消息称，L catterton、淡马锡跟投，此外高榕、龙湖等多位老股东也继续跟投，本轮投后元气森林估值达60亿美元，短短一年之内大涨约三倍。")

    # 标题空格
    # obj = call("高精度工业机器人制造商“若贝特”获数千万人民币A+轮融资")
    
    # 新增模板
    # obj = call("投资方为贝塔斯曼亚洲投资基金（领投）。")
    # obj = call("本轮融资由钟鼎资本领投、厦门建发新兴投资、三奕资本联合参投，君联资本和德宁资本等老股东超额跟投。")
    
    # 战略投资是名词还是动词
    # obj = call("证券时报e公司讯，追觅科技宣布完成36亿元C轮融资，由华兴新经济基金等领投，碧桂园创投战略投资，老股东小米集团等追加投资。")

    # obj = call("36氪了解到，“简爱酸奶”于近日完成总计8亿元人民币B轮融资，老股东经纬中国、黑蚁资本、中信农业基金、麦星资本继续加码，新进股东为红杉中国、云锋基金、璞瑞投资基金、德弘资本，本轮融资将全部用于现代化牧场建设，持续发力供应链。")
    # obj = call("猎云网近日获悉，浙江正泰安能电力系统工程有限公司（以下简称“正泰安能”）宣布完成人民币10亿元战略融资，长期战略合作伙伴--鋆（yún）昊资本(Cloudview Capital)作为领投方投资人民币2.4亿元，")
    # obj = call("公开资料显示，2011年初咕咚获得盛大集团天使轮数千万元投资，随后的2014年3月，咕咚获得深创投领投、中信资本跟投的1000万美元A轮融资；同年11月，咕咚又获得由SIG和软银共同投资的3000万美元B轮融资。")
    # obj = call("8月31日晚间，外媒 The Information 报道，知情人士透露，亚洲初创公司极兔速递（J&T Express ）正在与腾讯及其他投资者进行融资洽谈，融资金额逾10亿美元，投前估值200亿美元。")
    # obj = call("8月25日，极客网了解到，劢微机器人获得数千万人民币A+轮融资，信天创投领投，plug and play、梅花创投参投。")
    # obj = call("据悉，乐播投屏此前曾于2015年获得赛马资本的天使轮融资，2016年获得金沙江联合资本的A轮融资，2017年11月获前海母基金，暴龙资本领投，博将资本、易合资本联合参投的A+轮融资。")
    # obj = call("业内人士分析，在目前市场偏于谨慎的投资环境下，金智维逆势完成融资，再获逾2亿元资本加持，证明其强大的自主研发能力、以用户为本的产品理念、金融行业的高渗透率以及可持续发展的商业模式，得到广泛的验证和认可。")
    # obj = call("去年5月，该公司在由Saama Capital领投的A轮融资中筹集了590万美元。")
    # obj = call("华米科技240万美元领投neuro42 A轮融资")
    # obj = call("投资界7月28日消息，中国本土原浆啤酒品牌泰山啤酒完成新一轮融资，由中信系投资平台信金资本独家战略加持。")
    # obj = call("日前网通社获悉，威马汽车控股有限公司宣布，威马汽车预计将获得超过3亿美元的D1轮融资，本轮融资由电讯盈科有限公司（“电讯盈科”）和信德集团有限公司（“信德集团”）领投，参投方包括广发信德投资管理有限公司旗下美元投资机构等。")
    # obj = call("据威马汽车官方介绍，本次获得的D1轮融资贷款，将用于威马汽车无人驾驶技术与其他智能化技术和产品研发，另外资金还将用于销售及服务渠道拓展等，另外锦沄资本和光源资本则以财务顾问身份参与本轮融资。")

    # obj = call("根据CVSource投中数据，煲仔皇曾于2015年获0331创投百万级天使轮融资，2016年获真格基金、老鹰基金、星瀚资本千万级PreA轮融资，2017年获弘毅投资旗下百福控股数千万A轮融资。")
    # obj = call("2021开年，B1轮融资发布不过4个月，奇点云再迎喜讯：于近日完成8000万元B2轮融资，字节跳动独家领投，老股东IDG资本跟投。")
    obj = call("36氪获悉，饭乎于近期连续完成两轮融资，包括昕先资本（洽洽家族基金）投资的千万元级天使轮融资，以及联想之星领投和拙朴投资跟投的数千万元级A轮融资。")

    print(obj)