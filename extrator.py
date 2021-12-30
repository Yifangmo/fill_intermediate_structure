#!/usr/bin/env python
from re import I
from merge_engine import MergeEngine
import requests
import json
import re
import rules
import inspect

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

def get_field_value(sent: str, entities_index2original: dict, span):
    res = None
    if isinstance(span, list):
        res = []
        for sp in span:
            # if sp not in entities_index2original:
            #     print("get_field_values 实体索引映射错误：({},{})".format(sp[0], sp[1]))
            #     continue
            sent_idx_span = entities_index2original[sp]
            res.append(sent[sent_idx_span[0]:sent_idx_span[1]])
    else:
        sent_idx_span = entities_index2original[span]
        res = sent[sent_idx_span[0]: sent_idx_span[1]]
    return res

def get_classified_alias(alias: set):
    invalid_reobj = re.compile(r"\d{3,}")
    alias = {i for i in alias if not invalid_reobj.search(i)}
    en_reobj = re.compile(r"([A-Za-z\d]{3,}(?:\s[A-Za-z\d]+)*)")
    english_names = {n for n in alias if en_reobj.fullmatch(n)}
    full_names = {n for n in alias if n.endswith(("公司","集团","基金"))}
    primary_names = alias - english_names - full_names
    if len(primary_names) == 0:
        primary_names = full_names
    if len(primary_names) == 0:
        primary_names = english_names
    names = {}
    if len(primary_names) > 0:
        names["primary_name"] = sorted(primary_names, key=lambda n: (len(n), n))[0]
    if len(english_names) > 0:
        names["english_name"] = sorted(english_names, key=lambda n: (len(n), n), reverse=True)[0]
    if len(full_names) > 0:
        names["full_name"] = sorted(full_names, key=lambda n: (len(n), n), reverse=True)[0]
    return names

# 获取某个子句的位置
def get_clause_span(sent: str, token_low_index: int, token_high_index: int, unique_sep:str = None, *additional_seps: str):
    separators = ["；", "，", "。", "】", "【"]
    if unique_sep:
        separators = [unique_sep]
    elif additional_seps:
        separators += additional_seps 
    l = len(sent)
    begin = None
    end = None
    for i in range(token_low_index, -1, -1):
        if sent[i] in separators:
            begin = i+1
            break
    for i in range(token_high_index, l, 1):
        if sent[i] in separators:
            end = i
            break
    begin = begin if begin else 0
    end = end if end else l
    return begin, end

# 为出现交易类型的子句划分索引范围，子句间的分隔符是标点符号。返回的是某个子句在整个句子中的索引范围到该子句所含交易类型的映射。
def divide_real_dts_span(sent: str, idxspan2real_dts: dict, real_dt2label_dts: dict, separators: list):
    if len(separators) == 0:
        return idxspan2real_dts
    separator = separators.pop(0)
    new_idxspan2real_dts = {}
    for span, real_dts in idxspan2real_dts.items():
        if len(real_dts) == 1:
            new_idxspan2real_dts[span] = real_dts
            continue
        for real_dt in real_dts:
            label_dts = real_dt2label_dts[real_dt]
            new_span = get_clause_span(sent, label_dts[0][0], label_dts[0][1], separator)
            if new_span not in new_idxspan2real_dts:
                new_idxspan2real_dts[new_span] = [real_dt]
            else:
                new_idxspan2real_dts[new_span].append(real_dt)

    return divide_real_dts_span(sent, new_idxspan2real_dts, real_dt2label_dts, separators)

# 去除无关紧要的空白字符、引号等；将英文标点转换为中文标点；将标签指示符转为书名号
def normalize_sentence(sent: str):
    def repl(m):
        dic = {1: "", 2: "，", 3: "；", 4: "：", 5: "（", 6: "）", 7: "《", 8: "》"}
        for i in range(1, 7):
            if m.group(i):
                return dic[i]
    # 处理标题的空格
    # if not sent.endswith("。") or sent.endswith(("？", "！")):
        # sent = re.sub(r"(?<![A-Za-z])\s(?![A-Za-z])", "，", sent)
        # pass
    return re.sub(r"((?<![A-Za-z])\s|\s(?![A-Za-z])|“|”|「|」|‘|’)|(,)|(;)|(:)|(\()|(\))|(<)|(>)", repl, sent)


class EntitiesDictExtrator(object):
    def __init__(self, *rules):
        self.label_related_party = "关联方"
        self.label_related_amount = "金额"
        self.label_related_attr_nount = "属性名词"
        self.label_related_occ_date = "发生时间"
        self.label_related_dcs_date = "披露时间"
        self.label_related_deal_type = "交易类型"
        self.label_related_business_prof = "融资方标签"
        self.label_str_map = {
            "关联方": "<关联方>",
            "金额": "<金额>",
            "属性名词": "<属性名词>",
            "发生时间": "<发生时间>",
            "披露时间": "<披露时间>",
            "交易类型": "<交易类型>",
            "融资方标签": "<融资方标签>"
        }
        self.validate_deal_type_reobj = re.compile(
            (
                r"(((pre-)?[A-H]\d?(\++|＋+|plus)?)|天使|种子|战略|新一|IPO)(轮|系列轮|系列(?!轮))((?![融投]资|投融资)|([融投]资|投融资)(?!人|者|方|机构))|"
                r"(上一?|首|两|三|四|五)轮((?![融投]资|投融资)|(([融投]资|投融资)(?!人|者|方|机构)))|"
                r"(天使|种子|战略|风险|IPO|股权|新一|上一|(新一|上一?|首|两|三|四|五)次)([融投]资|投融资)(?!人|者|方|机构)|"
                r"(本|此|该)(轮|次)([融投]资|投融资)|"
                r"[融投]资(?!人|者|方|机构)"
            ), re.I
        )
        self.repl_deal_type_reobj = re.compile(r"(轮|次|笔|轮战略|系列轮?)?(投资|融资)|投融资")
        self.date_reobj = re.compile(r"\d{1,2}月\d{1,2}日|年\d{1,2}月")
        self.verb_reobj = re.compile(r"获|完成")
        self.rules = rules
        
    # 返回clause_idx_span到实际交易事件和时间的映射
    def get_span_dict(self, sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        label_dt2repl_dt = {}
        repl_dt2real_dt = {}
        amount_dt_pair = {}
        print("labels_indexes: ", labels_indexes)
        for i, li in enumerate(labels_indexes):
            label_content = sent[li[0]:li[1]]
            if li[2] == "交易类型":
                repl_dt = self.repl_deal_type_reobj.sub("", label_content)
                # 此类交易类型实体只用于匹配模板来获取融资方信息，不作为实际交易事件，也不为之划分span
                if re.search(r"两|三|四|五|(?<![a-zA-Z])\d", repl_dt):
                    continue
                # 励销云宣布完成新一轮2000万美元B轮融资
                if i > 1 and labels_indexes[i-1][2]=="金额" and labels_indexes[i-2][2]=="交易类型":
                    pre_label_dt_content = sent[labels_indexes[i-2][0]:labels_indexes[i-2][1]]
                    pre_li_span = (labels_indexes[i-2][0], labels_indexes[i-2][1])
                    if pre_li_span in label_dt2repl_dt:
                        pre_repl_dt = label_dt2repl_dt[pre_li_span]
                        # 新一轮2000万美元B轮融资
                        if re.search(r"[A-Za-z]", repl_dt):
                            # 将原有的 新一 替换为 B
                            label_dt2repl_dt[(li[0],li[1])] = repl_dt
                            label_dt2repl_dt[pre_li_span] = repl_dt
                            # 删除原有的repl_dt，避免同一交易事件（real_dt）有多个repl_dt
                            del repl_dt2real_dt[pre_repl_dt]
                            # 将实际交易类型由新一轮替换为B轮融资
                            if label_content.endswith("融资") or not pre_label_dt_content.endswith("融资"):
                                repl_dt2real_dt[repl_dt] = label_content
                        # B轮2000万美元新融资 | B轮2000万美元融资
                        else:
                            label_dt2repl_dt[(li[0],li[1])] = pre_repl_dt
                            # 将实际交易类型由B轮替换为B轮融资
                            if label_content.endswith("融资") and not pre_label_dt_content.endswith("融资"):
                                repl_dt2real_dt[pre_repl_dt] = pre_label_dt_content + label_content
                        continue
                # "B+轮战略融资" 和 "B+轮投资"
                if repl_dt in repl_dt2real_dt:
                    label_dt2repl_dt[(li[0], li[1])] = repl_dt
                    pre_real_dt = repl_dt2real_dt[repl_dt]
                    ult_real_dt = label_content
                    # 优先取融资结尾的，再取长度更长的
                    if pre_real_dt.endswith("融资"):
                        ult_real_dt = pre_real_dt
                    if pre_real_dt != label_content:
                        if label_content.endswith("融资") and len(pre_real_dt) < len(label_content):
                            ult_real_dt = label_content
                    else:
                        if len(pre_real_dt) >= len(label_content):
                            ult_real_dt = pre_real_dt
                    if ult_real_dt != pre_real_dt:
                        repl_dt2real_dt[repl_dt] = ult_real_dt
                    continue
                
                if i > 0 and labels_indexes[i-1][2]=="金额" and li[0] - labels_indexes[i-1][1] < 2:
                    amount_dt_pair[(li[0],li[1])] = (labels_indexes[i-1][0],labels_indexes[i-1][1])
                
                label_dt2repl_dt[(li[0], li[1])] = repl_dt
                repl_dt2real_dt[repl_dt] = label_content

        real_dt2label_dts = {}
        print("label_dt2repl_dt: ", label_dt2repl_dt)
        print("repl_dt2real_dt: ", repl_dt2real_dt)
        for label_dt, repl_dt in label_dt2repl_dt.items():
            real_dt = repl_dt2real_dt[repl_dt]
            if real_dt not in real_dt2label_dts:
                real_dt2label_dts[real_dt] = [label_dt]
            else:
                real_dt2label_dts[real_dt].append(label_dt)
        idxspan2real_dts = {(0, len(sent)): list(real_dt2label_dts.keys())}
        
        if len(real_dt2label_dts) > 0:
            print("sent: ", sent)
            print("real_dt2label_dts: ", real_dt2label_dts)
            separators = ["；", "，", "、"]
            # 划分span为尽可能小单位，以尽可能使得每个span最多只有一个real_dt，最小的单位为"、"分割的短句的span
            idxspan2real_dts = divide_real_dts_span(sent, idxspan2real_dts, real_dt2label_dts, separators)
        
        # 使前面的未被span覆盖的时间标签被其后面的dt_span覆盖，因为前面的时间很大可能是其后real_dt相关的时间
        for i, li in enumerate(labels_indexes):
            if li[2] == "披露时间" or li[2] == "发生时间":
                label_content = sent[li[0]:li[1]]
                time_span = get_clause_span(sent, li[0], li[1])
                spans = sorted(idxspan2real_dts.keys())
                for j, span in enumerate(spans):
                    real_dts = idxspan2real_dts[span]
                    if span[0] <= time_span[0] and time_span[1] <= span[1]:
                        break
                    if j == 0 and span[0] > time_span[1] or \
                        j > 0 and spans[j-1][1] < time_span[0] and span[0] > time_span[1]:
                        del idxspan2real_dts[span]
                        idxspan2real_dts[(time_span[0], span[1])] = real_dts
                        break
        
        # 向后扩展span，使所有span邻接，合并以"、"分割但无金额的span
        spans = sorted(idxspan2real_dts.keys())
        for i, span in enumerate(spans):
            real_dts = idxspan2real_dts[span]
            if i == len(spans)-1:
                del idxspan2real_dts[span]
                idxspan2real_dts[(span[0], len(sent))] = real_dts
                break
            if span[1] != spans[i+1][0] - 1:
                del idxspan2real_dts[span]
                idxspan2real_dts[(span[0], spans[i+1][0] - 1)] = real_dts
                continue
            if i > 0 and span[0] == spans[i-1][1] + 1 and sent[spans[i-1][1]] == "、":
                has_amount = False
                for real_dt in real_dts:
                    if real_dt2label_dts[real_dt][0] in amount_dt_pair:
                        has_amount = True
                        break
                if not has_amount:
                    pre_real_dts = idxspan2real_dts[spans[i-1]]
                    del idxspan2real_dts[span]
                    del idxspan2real_dts[spans[i-1]]
                    idxspan2real_dts[(spans[i-1][0], span[1])] = real_dts + pre_real_dts
        
        # 生成span到date的映射，优先更准确的时间
        idxspan2dates = {}
        for i, li in enumerate(labels_indexes):
            if li[2] == "披露时间":
                label_content = sent[li[0]:li[1]]
                for span in idxspan2real_dts:
                    if li[0] >= span[0] and li[1] <= span[1]:
                        if span not in idxspan2dates:
                            idxspan2dates[span] = {}
                        if "disclosed_dates" not in idxspan2dates[span]:
                            idxspan2dates[span]["disclosed_dates"] = [(li[0],li[1])]
                        else:
                            pre_span = idxspan2dates[span]["disclosed_dates"][0]
                            pre = sent[pre_span[0]:pre_span[1]]
                            if not self.date_reobj.search(pre):
                                idxspan2dates[span]["disclosed_dates"][0] = (li[0],li[1])
                            elif self.date_reobj.search(label_content):
                                idxspan2dates[span]["disclosed_dates"].append((li[0],li[1]))
            if li[2] == "发生时间":
                label_content = sent[li[0]:li[1]]
                for span in idxspan2real_dts:
                    if li[0] >= span[0] and li[1] <= span[1]:
                        if span not in idxspan2dates:
                            idxspan2dates[span] = {}
                        if "occurrence_dates" not in idxspan2dates[span]:
                            idxspan2dates[span]["occurrence_dates"] = [(li[0],li[1])]
                        else:
                            pre_span = idxspan2dates[span]["occurrence_dates"][0]
                            pre = sent[pre_span[0]:pre_span[1]]
                            if not self.date_reobj.search(pre):
                                idxspan2dates[span]["occurrence_dates"][0] = (li[0],li[1])
                            elif self.date_reobj.search(label_content):
                                idxspan2dates[span]["occurrence_dates"].append((li[0],li[1]))
        
        # 若无则对其加指代交易类型
        spans = idxspan2real_dts.keys()
        for span in spans:
            real_dts = idxspan2real_dts[span]
            if len(real_dts) == 0:
                matches = self.validate_deal_type_reobj.finditer(sent, span[0], span[1])
                for m in matches:
                    mspan = m.span()
                    is_valid = True
                    for li in labels_indexes:
                        # "维港投资"中的"投资"不是交易类型
                        if li[2] == "关联方" and mspan[0] >= li[0] and mspan[1] <= li[1]:
                            is_valid = False
                            break
                        if li[0] > mspan[1]:
                            break
                    if is_valid:
                        idxspan2real_dts[span] = [m.group()]
                        break
                
        # 根据span排序重新生成dict
        idxspan2real_dts = {i[0]:i[1] for i in sorted(idxspan2real_dts.items())}
        
        return idxspan2real_dts, idxspan2dates, real_dt2label_dts
               
    def validate_deal_type(self, sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        new_labels_indexes = []
        labels_unused = []
        
        for i, li in enumerate(labels_indexes):
            label_content = sent[li[0]:li[1]]
            if li[2] != "交易类型":
                new_labels_indexes.append(li)
                continue
                
            if not self.validate_deal_type_reobj.search(re.sub(r"\s","", label_content)):
                labels_unused.append([label_content, li[2]])
                continue
            
            # 该公司成立以来获得的第三次融资(无用)
            if label_content.startswith("第"):
                labels_unused.append([label_content, li[2]])
                continue
            
            # 此轮本来只打算融资6000-8000万美元
            if re.match(r"融资|投资", label_content) and i+1 < len(labels_indexes) and labels_indexes[i+1][0] == li[1] and labels_indexes[i+1][2] == "金额":
                labels_unused.append([label_content, li[2]])
                continue
            
            clause_pos_span = get_clause_span(sent, li[0], li[1])
            # 本轮融资由深圳高新投战略投资(无用)
            if label_content.endswith("投资") and not self.verb_reobj.search(sent, clause_pos_span[0], li[0]):
                labels_unused.append([label_content, li[2]])
                continue
            
            # 继2018年完成2.4亿A轮、2019年3月完成20亿人民币B轮、2020年8月和10月分别完成25亿人民币C轮和战略融资后(有用)
            # 这是继去年Pre-A轮以及今年4月A轮之后(无用)
            if "继" in sent[clause_pos_span[0]:li[0]] and "后" in sent[li[1]:clause_pos_span[1]]:
                isunuse = True
                for j in range(i, -1, -1):
                    if labels_indexes[j][0] < clause_pos_span[0]:
                        break
                    if labels_indexes[j][2] == "金额":
                        isunuse = False
                        break
                if isunuse:
                    labels_unused.append([label_content, li[2]])
                continue
            
            new_labels_indexes.append(li)
        print("deal_type_labels_unused: ", labels_unused)
        return new_labels_indexes, labels_unused

    def get_entities_sent(self, sentence_struct_info: dict):
        sent = sentence_struct_info["sent"]
        labels_indexes = sentence_struct_info["labels_indexes"]
        idxspan2real_dts = sentence_struct_info["idxspan2real_dts"]
        idxspan2dates = sentence_struct_info["idxspan2dates"]
        
        entities_sent, entities_index2original, alias, attr_noun_dict, original_index2entities = "", {}, {}, {}, {}
        # 标签替换前后首索引差值
        replaced_list = []
        idx_diff = 0
        start = 0
        
        # 将sent的span转为entities_sent的span
        ori_spans = list(idxspan2real_dts.keys())
        new_spans = []
        ori_spans_idx = 0
        span_start_diff = 0
        span_start = ori_spans[ori_spans_idx][0]
        span_end = ori_spans[ori_spans_idx][1]
        
        for i, label in enumerate(labels_indexes):
            label_content = sent[label[0]:label[1]]
            replaced_list.append(sent[start:label[0]])
            
            # 将sent的span转为entities_sent的span
            while label[0] >= span_end:
                new_span_start = span_start + span_start_diff
                new_span_end = span_end + idx_diff
                new_spans.append((new_span_start, new_span_end))
                ori_spans_idx += 1
                if ori_spans_idx == len(ori_spans):
                    break
                span_start = ori_spans[ori_spans_idx][0]
                span_end = ori_spans[ori_spans_idx][1]
                pass
            if label[1] >= span_start and i > 0 and labels_indexes[i - 1][1] < span_start:
                span_start_diff = idx_diff
            # 生成标签索引映射
            label_start_idx = label[0]+idx_diff
            label_length = len(self.label_str_map[label[2]])
            entities_index2original[(label_start_idx, label_start_idx + label_length)] = (label[0], label[1])
            original_index2entities[(label[0], label[1])] = (label_start_idx, label_start_idx + label_length)
            idx_diff += (label_length - (label[1] - label[0]))
            # 替换为标签
            replaced_list.append(self.label_str_map[label[2]])
            start = label[1]
            
            # 生成属性名词span到origin str的dict
            if label[2] == "属性名词":
                attr_noun_dict[(label_start_idx, label_start_idx + label_length)] = label_content
                continue
            # 使融资方标签和关联方标签邻近
            if label[2] == "融资方标签" and (i + 1) < len(labels_indexes) and labels_indexes[i + 1][2] == "关联方":
                idx_diff -= (labels_indexes[i + 1][0] - start)
                start = labels_indexes[i + 1][0]
                continue
            if label[2] == "关联方":
                er = sent[label[0]:label[1]]
                # 处理括号内别名
                alias[er] = {er}
                if start < len(sent) and sent[start] == "（":
                    end = sent.find("）", start)
                    # 排除一些情况，包括括号内有实体的情况
                    if end == -1 or re.search("隶属|领投|估值|股票代码", sent[start+1:end]) or\
                        (i + 1) < len(labels_indexes) and labels_indexes[i+1][1] <= end:
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
        new_span_start = span_start + span_start_diff
        new_span_end = span_end + idx_diff
        new_spans.append((new_span_start, new_span_end))
        new_idxspan2real_dts = {i[1]: idxspan2real_dts[i[0]] for i in zip(ori_spans, new_spans)}
        new_idxspan2dates = {i[1]: idxspan2dates[i[0]] for i in zip(ori_spans, new_spans) if i[0] in idxspan2dates}
        sentence_struct_info["idxspan2real_dts"] = new_idxspan2real_dts
        sentence_struct_info["idxspan2dates"] = new_idxspan2dates
        
        entities_sent = "".join(replaced_list)
        return entities_index2original, entities_sent, alias, attr_noun_dict, original_index2entities

    # 填充deal_type，对dates分类，处理关联方别名，统计标签使用情况
    def adjust_field(self, sentence_struct_info):
        sent = sentence_struct_info["sent"]
        entities_sent = sentence_struct_info["entities_sent"]
        idxspan2real_dts = sentence_struct_info["idxspan2real_dts"]
        idxspan2dates = sentence_struct_info["idxspan2dates"]
        real_dt2label_dts = sentence_struct_info["real_dt2label_dts"]
        match_result = sentence_struct_info["match_result"]
        entities_index2original = sentence_struct_info["entities_index2original"]
        original_index2entities = sentence_struct_info["original_index2entities"]
        alias = sentence_struct_info["alias"]
        total_labels = set(entities_index2original.keys())
        total_labels_used = set({})
        new_match_result = []
        
        # 从所有的match_result中获取fc信息
        financing_company_info = {}
        i = 0
        while i < len(match_result):
            mr_struct = match_result[i]["struct"]
            if "financing_company" in mr_struct:
                fc_span = mr_struct["financing_company"]
                del mr_struct["financing_company"]
                total_labels_used.add(fc_span)
                fc_name = get_field_value(sent, entities_index2original, fc_span)
                fc_names = get_classified_alias(alias[fc_name])
                fc = {}
                for k, v in fc_names.items():
                    fc[k] = v
                bp = None
                if "business_profile" in mr_struct:
                    bp_span = mr_struct["business_profile"]
                    del mr_struct["business_profile"]
                    total_labels_used.add(bp_span)
                    bp = get_field_value(sent, entities_index2original, bp_span)
                if fc_name not in financing_company_info or fc_name in financing_company_info and bp:
                    financing_company_info[fc_name] = {"business_profile": bp, "financing_company": fc} if bp else {"financing_company": fc}
            i += 1

        print("==========================================")
        print("financing_company_info: ", financing_company_info)
        print("entities_sent: ", entities_sent)
        print("idxspan2real_dts: ", idxspan2real_dts)
        print("idxspan2dates: ", idxspan2dates)
        print("==========================================")
        print()
        
        # 根据匹配的span对应的实际交易事件不同作不同处理，并将结构体的span字段值替换为实际值
        for mr in match_result:
            mr_struct = mr["struct"]
            mr_span = mr["match_span"]
            for span, real_dts in idxspan2real_dts.items():
                if span[0] <= mr_span[0] and mr_span[1] <= span[1]:
                    # TODO if len(real_dts) == 0 的情况
                    for real_dt in real_dts:
                        if len(financing_company_info)==0 and len(real_dts) > 1:
                            break
                        nmr_struct = {}
                        nmr = {"struct": nmr_struct,"from_rule": mr["from_rule"]}
                        # 添加使用过的deal_type和date标签以及填充date
                        if real_dt in real_dt2label_dts:
                            for label_dt in real_dt2label_dts[real_dt]:
                                total_labels_used.add(original_index2entities[label_dt])
                        if span in idxspan2dates:
                            for field_name, date_spans in idxspan2dates[span].items():
                                date_span = date_spans[0]
                                nmr_struct[field_name] = sent[date_span[0]:date_span[1]]
                                total_labels_used.add(original_index2entities[date_span])
                        nmr_struct["deal_type"] = real_dt
                        
                        # 如果有融资方信息就填充
                        if len(financing_company_info)!=0:
                            for k, v in financing_company_info[list(financing_company_info.keys())[0]].items():
                                nmr_struct[k] = v
                                
                        # 如果只有一个real_deal_type就填充非共用部分
                        if len(real_dts) == 1:
                            for k, v in mr_struct.items():
                                if isinstance(v, tuple):
                                    total_labels_used.add(v)
                                    # 跳过属性名词不填
                                    if k != "attr_noun":
                                        nmr_struct[k] = get_field_value(sent, entities_index2original, v)
                                # 填充投资方信息（多个）
                                elif k == "investors":
                                    total_labels_used.update(v)
                                    investors = []
                                    is_leading_investor = mr_struct["is_leading_investor"] if "is_leading_investor" in mr_struct else False
                                    i_names = get_field_value(sent, entities_index2original, v)
                                    for i_name in i_names:
                                        investor = {}
                                        names = get_classified_alias(alias[i_name])
                                        for k, v in names.items():
                                            investor[k] = v
                                        investor["is_leading_investor"] = is_leading_investor
                                        investors.append(investor)
                                    nmr_struct["investors"] = investors
                                elif k == "finacial_advisers":
                                    total_labels_used.update(v)
                                    finacial_advisers = get_field_value(sent, entities_index2original, v)
                                    nmr_struct["finacial_advisers"] = finacial_advisers
                        new_match_result.append(nmr)
                        
        total_labels_unused = total_labels - total_labels_used
        labels_unused = []
        for i in sorted(total_labels_unused):
            try:
                sent_index = entities_index2original[i]
                labels_unused.append([entities_sent[i[0]+1:i[1]-1], sent[sent_index[0]:sent_index[1]]])
            except KeyError:
                print("实体索引映射错误：({},{})".format(i[0], i[1]))
            pass
        sentence_struct_info["labels_unused"]=labels_unused
        sentence_struct_info["labels_unused_count"] = len(labels_unused)
        sentence_struct_info["match_result"] = new_match_result
        
        del sentence_struct_info["entities_index2original"]
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
            "match_result": [],
            "sent": sent,
            "labels_indexes": labels_indexes,
        }
        labels_value = [[sent[li[0]:li[1]], li[2]] for li in labels_indexes]
        sentence_struct_info["labels_value"] = labels_value
        sentence_struct_info["labels_indexes"], sentence_struct_info["labels_unused"] = self.validate_deal_type(sentence_struct_info)
        sentence_struct_info["idxspan2real_dts"], sentence_struct_info["idxspan2dates"], sentence_struct_info["real_dt2label_dts"] = self.get_span_dict(sentence_struct_info)
        sentence_struct_info["entities_index2original"], sentence_struct_info["entities_sent"],sentence_struct_info["alias"], sentence_struct_info["attr_noun_dict"], sentence_struct_info["original_index2entities"] = self.get_entities_sent(sentence_struct_info)
        entities_sent = sentence_struct_info["entities_sent"]
        attr_noun_dict = sentence_struct_info["attr_noun_dict"]

        match_result = []
        for func in self.rules:
            match_result += func(entities_sent, attr_noun_dict)
        sentence_struct_info["match_result"] = match_result
        print("match_result: ", match_result)
        self.adjust_field(sentence_struct_info)
        return sentence_struct_info

EDE = EntitiesDictExtrator(*[i[1]() for i in inspect.getmembers(rules, inspect.isclass) if i[0].startswith("Rule")])