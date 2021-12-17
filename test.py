#!/usr/bin/env python
import re
import run
import json
import csv
import xlsxwriter
import requests


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


def test():
    with open("./output/template.txt", 'r', encoding="utf-8") as inf, open("./output/test_result.txt", 'w+', encoding="utf-8") as outf:
        flag = False
        lines = []
        for line in inf:
            if line.startswith('--'):
                flag = not flag
                continue
            if flag:
                lines.append(line)
            else:
                l = len(lines)
                for i, ln in enumerate(lines[l//2+1:]):
                    obj = run.ede(lines[i])
                    if not obj:
                        continue
                    outf.write(lines[i])
                    entities_sent = obj["entities_sent"]
                    match_result = obj["match_result"]
                    labels_used = obj["labels_used"]
                    labels_unused = obj["labels_unused"]
                    labels_used_count = obj["labels_used_count"]
                    labels_unused_count = obj["labels_unused_count"]
                    outf.write("entities_sent: " + entities_sent+'\n')
                    outf.write("structs: \n")
                    outf.write(json.dumps(
                        match_result, ensure_ascii=False, indent=4))
                    outf.write('\n')
                    outf.write("labels_used: [\n")
                    for lu in labels_used:
                        outf.write('\t')
                        outf.write(str(lu) + '\n')
                    outf.write("]\n")

                    outf.write("labels_unused: [\n")
                    for lu in labels_unused:
                        outf.write('\t')
                        outf.write(str(lu) + '\n')
                    outf.write("]\n")

                    outf.write("labels_used_count: " +
                               str(labels_used_count) + '\n')
                    outf.write("labels_unused_count: " +
                               str(labels_unused_count) + '\n')
                    outf.write("\n\n")
                lines.clear()

def test1():
    with open("./input/sample.csv", 'r') as inf:
        wb = xlsxwriter.Workbook("./output/test_result.xlsx")
        sh1 = wb.add_worksheet()
        sh2 = wb.add_worksheet()
        str_format = wb.add_format({'align': 'center','valign': 'vcenter'})
        reader = csv.reader(inf)
        next(reader)
        sh1.write_row(0,0,['news_id','title','valid_sentence','ner_entities','struct','unused'], str_format)
        sh2.write_row(0,0,['news_id','title','valid_sentence','ner_entities', 'rule_index', 'struct', 'is_valid'], str_format)
        sh1_row_cnt = 1
        sh2_row_cnt = 1
        # cnt = 1
        unuse_labels_count = 0
        total_labels_count = 0
        for i, row in enumerate(reader,1):
            # if cnt > 20:
            #     break
            
            title = row[0]
            sents = row[1].split("\n---------- \n")
            for sent in sents:
                
                # cnt += 1
                # if cnt > 16:
                #     break
                
                obj = run.ede(sent)
                if not obj:
                    continue
                
                data = []
                data.append(i)
                data.append(title)
                data.append(sent)
                data.append("\n".join([str(i) for i in obj["labels_value"]]))
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
                    data.append(json.dumps(mr["struct"], ensure_ascii=False, indent=4))
                    sh2.write_row(sh2_row_cnt, 0, data, str_format)
                    sh2_row_cnt += 1
        print("total_labels_count: ", total_labels_count)
        print("unuse_labels_count: ", unuse_labels_count)
        wb.close()


if __name__ == "__main__":
    # test()
    test1()
