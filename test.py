#!/usr/bin/env python
import re
import run_rebuild
import json
import csv
import xlsxwriter
import requests
import traceback

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
                    s = s[:-1].strip() + self.item_separator.strip()
                elif s and s[-1] == ':':
                    s = s[:-1].strip() + self.key_separator.strip()
                s = s.strip()
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

def test1():
    with open("./input/sample.csv", 'r') as inf , open("./output/err.log", 'w+') as errf:
        wb = xlsxwriter.Workbook("./output/test_result1.xlsx")
        sh1 = wb.add_worksheet()
        sh2 = wb.add_worksheet()
        sh3 = wb.add_worksheet()
        sh1.set_column(0, 0, 8)
        sh1.set_column(1, 1, 25)
        sh1.set_column(2, 3, 35)
        sh1.set_column(4, 4, 50)
        sh1.set_column(5, 5, 35)
        sh2.set_column(0, 0, 8)
        sh2.set_column(1, 1, 25)
        sh2.set_column(2, 2, 40)
        sh2.set_column(3, 3, 35)
        sh2.set_column(4, 4, 10)
        sh2.set_column(5, 5, 50)
        sh2.set_column(6, 6, 8)
        sh3.set_column(0, 0, 8)
        sh3.set_column(1, 1, 25)
        sh3.set_column(2, 3, 35)
        sh3.set_column(4, 4, 50)
        str_format = wb.add_format({'align': 'center','valign': 'vcenter', 'text_wrap': True})
        reader = csv.reader(inf)
        next(reader)
        sh1.write_row(0,0,['news_id','title','valid_sentence','ner_entities','struct','unused'], str_format)
        sh2.write_row(0,0,['news_id','title','valid_sentence','ner_entities', 'rule_index', 'struct', 'is_valid'], str_format)
        sh3.write_row(0,0,['news_id','title','valid_sentences','ner_entities','struct'], str_format)
        sh1_row_cnt = 1
        sh2_row_cnt = 1
        # cnt = 1
        unuse_labels_count = 0
        total_labels_count = 0
        
        reader = list(reader)[::-1]
        for i, row in enumerate(reader,1):
            # if cnt > 1000:
            #     break
            
            title = row[0]
            sents = row[1].split("\n---------- \n")
            valid_sentences = row[1]
            news_structs = []
            labels_values = []
            for sent in sents:
                
                # cnt += 1
                # if cnt > 1000:
                #     break
                
                obj = None
                try:
                    obj = run_rebuild.ede(sent)
                except BaseException as e:
                    errf.write(traceback.format_exc()+'\n'+sent+'\n')
                if not obj:
                    continue
                
                data = []
                data.append(i)
                data.append(title)
                data.append(sent)
                lv_str = "\n".join([str(i) for i in obj["labels_value"]])
                data.append(lv_str)
                labels_values.append(lv_str)
                match_result = obj["match_result"]
                try:
                    data.append("\n--------\n".join([json.dumps(mr["struct"], ensure_ascii=False, indent=4) for mr in match_result]))
                except:
                    print(sent)
                    print(match_result)
                data.append("\n".join([str(i) for i in obj["labels_unused"]]))
                unuse_labels_count += len(obj["labels_unused"])
                total_labels_count += len(obj["labels_value"])
                sh1.write_row(sh1_row_cnt, 0, data, str_format)
                sh1_row_cnt += 1
                for mr in match_result:
                    from_rule = mr["from_rule"]
                    data = []
                    data.append(i)
                    data.append(title)
                    data.append(sent)
                    data.append("\n".join([str(i) for i in obj["labels_value"]]))
                    data.append(from_rule)
                    stru = mr["struct"]
                    data.append(json.dumps(stru, ensure_ascii=False, indent=4))
                    news_structs.append(stru)
                    sh2.write_row(sh2_row_cnt, 0, data, str_format)
                    sh2_row_cnt += 1
            merged_result = None
            try: 
                merged_result = run_rebuild.mergenews.merge(news_structs)
            except:
                errf.write(traceback.format_exc()+valid_sentences+'\n\n')
            else:
                if isinstance(merged_result, dict):
                    merged_result = json.dumps(merged_result, ensure_ascii=False, indent=4)
                elif merged_result:
                    merged_result = "\n--------\n".join([json.dumps(i, ensure_ascii=False, indent=4) for i in merged_result])
                else:
                    merged_result = ""
                data = []
                data.append(i)
                data.append(title)
                data.append(valid_sentences)
                data.append("\n--------\n".join(labels_values))
                data.append(merged_result)
                sh3.write_row(i+1, 0, data, str_format)
        print("total_labels_count: ", total_labels_count)
        print("unuse_labels_count: ", unuse_labels_count)
        wb.close()

def refine_news():
    with open("./input/纯融资_news.csv", 'r+') as inf, open("./input/news.csv", 'w+') as outf:
        reader = csv.reader(inf)
        writer = csv.writer(outf)
        writer.writerow(["title", "content"])
        next(reader)
        titles = set({})
        for row in reader:
            title = row[0]
            content = row[1]
            if title not in titles:
                titles.add(title)
                writer.writerow([title, content])
        pass
    pass

def get_deal_type():
    with open("./output/valid_sentences.csv", 'r+') as inf:
        refer_dt_reobj = re.compile(r"(?:(?:Pre-|pre-)?[A-H]\d?|天使|种子|新一|上一?|本|此|该|两|首)(?:\+)?(?:轮|次)(?:融资|投资)?", re.I)
        validate_deal_type_reobj = re.compile(r"(((Pre-)?[A-H]\d?|天使|种子|战略|IPO|新一|上一?|本|此|该|两|首)(\++|＋+|plus)?(系列)?(轮|次)(融资|投资|投融资)?|(天使|种子|战略|风险|IPO|股权)(融资|投资|投融资)|融资|投资)", re.I)
        wb = xlsxwriter.Workbook("./output/deal_type1.xlsx")
        ws = wb.add_worksheet()
        ws.set_row(0, 30)
        ws.set_column(0, 0, 40)
        ws.set_column(1, 1, 90)
        ws.set_column(2, 2, 20)
        ws.set_column(3, 3, 20)
        str_format = wb.add_format({'align': 'center','valign': 'vcenter','text_wrap': True})
        red_format = wb.add_format({'color': 'red'})
        purple_format = wb.add_format({'color': 'purple'})
        ws.write_row(0,0,["title", "valid_sentences", "deal_types", "refer_deal_type"], str_format)
        reader = csv.reader(inf)
        next(reader)
        rowidx = 1
        separator = "\n--------\n"
        for row in reader:
            
            # if rowidx > 10:
            #     break
            
            title = row[0]
            valid_sentences = row[1]
            vs = valid_sentences.split("\n\n")
            sent_dt = {}
            sent_dt_set = {}
            dt_set = set({})
            refer_dt_set = set({})
            for s in vs:
                s = run_rebuild.normalize_sentence(s)
                resp = get_ner_predict(s)
                if resp["error_message"] or not "labels_indexes" in resp["response"]:
                    print(resp["error_message"], ": ", s)
                    continue
                labels_indexes = resp["response"]["labels_indexes"]
                for li in labels_indexes:
                    
                    dt = s[li[0]:li[1]]
                    if li[2] == "交易类型" and validate_deal_type_reobj.search(dt):
                        dt_set.add(li[0])
                        dt_set.add(li[1])
                        if s not in sent_dt_set:
                            sent_dt_set[s] = {dt}
                        else:
                            sent_dt_set[s].add(dt)
                        if s not in sent_dt:
                            sent_dt[s] = [(li[0], li[1], True)]
                        else:
                            sent_dt[s].append((li[0], li[1], True))
            if len(dt_set) <= 2:
                continue
            
            for s, dts in sent_dt_set.items():
                if len(dts) != 1:
                    ms = refer_dt_reobj.finditer(s)
                    for m in ms:
                        rdt = m.span()
                        if rdt[0] not in dt_set and rdt[1] not in dt_set:
                            refer_dt_set.add(s[rdt[0]:rdt[1]])
                            if s not in sent_dt:
                                sent_dt[s] = [m.span() + (False,)]
                            else:
                                sent_dt[s].append(m.span()+ (False,))
            dt_set.clear()
            formated_strs = []
            for s, dt_idxs in sent_dt.items():
                if len(dt_idxs) <= 1:
                    continue
                if len(formated_strs) != 0:
                    formated_strs.append(separator)
                dt_idxs.sort()
                start = 0
                for dti in dt_idxs:
                    color = purple_format
                    if dti[2]:
                        dt_set.add(s[dti[0]:dti[1]])
                        color = red_format
                    tmp = s[start:dti[0]]
                    if tmp != "":
                        formated_strs.append(tmp)
                    formated_strs.append(color)
                    formated_strs.append(s[dti[0]:dti[1]])
                    start = dti[1]
                tmp = s[start:]
                if tmp != "":
                    formated_strs.append(tmp)
            if len(formated_strs) == 0:
                continue
            ws.write_string(rowidx, 0, title, str_format)
            formated_strs.append(str_format)
            ws.write_rich_string(rowidx, 1, *formated_strs)
            ws.write_string(rowidx, 2, "\n".join(dt_set), str_format)
            ws.write_string(rowidx, 3, "\n".join(refer_dt_set), str_format)
            rowidx += 1
        wb.close()
        
    
    
def get_valid_content(title:str, content:str):
    req = json.dumps({"content": content, "snapshot": {"title": title}})
    resp = requests.post("http://192.168.88.203:5689/get_valid_content", req)
    res = json.loads(resp.text)
    if res["error_message"] == "":
        res = res["response"]["valid_content"]
    else:
        res = None
    return res

def test_get_valid_content():
    title = "智达万应获得1000万元天使轮融资"
    content = "智达万应是一家专注于“大数据+交通”的企业，在国内首创“CPR交通大数据综合应用平台”，为行业用户提供整体解决方案以及运营模式，致力于让道路更畅通，确保公众出行安全。日前获得天使轮1000万元融资，正进行工商信息变更。该公司创始人王博在受访时称，在获得本轮融资后，将主要用于解决公司流动资金及智慧交通“黑科技”硬件产品研发。年内将根据公司战略发展需要，开启“天使轮+”融资，希望引入新的战略股东，力争用3-5年时间把智达万应培育称四川乃至中国西部智慧交通领域的领军型科创企业。"
    res = get_valid_content(title, content)
    if res:
        for r in res:
            for s in r["sentences"]:
                print(s)

if __name__ == "__main__":
    # test()
    test1()
    # refine_news()
    # get_deal_type()
