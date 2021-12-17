#!/usr/bin/env python
import openpyxl
import csv
import re,json,requests

FLAG_NONE_TAG = -1
FLAG_UNIQUE_TAG = 0
FLAG_HAS_TAG = 1
FLAG_MULTI_TAG = 2
FLAG_MULTI_ER = 3
FLAG_NONE_ER = 4
FLAG_UNIQUE_ER = 5

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

def cutconlumn():
    wb = openpyxl.load_workbook("./input/sample.xlsx", read_only=True)
    with open("./input/sample.csv", "w+") as f:
        s = wb.worksheets[0]
        columnIdx = [0, 1, 5]
        writer = csv.writer(f)
        for row in s.rows:
            writer.writerow(c.value for i, c in enumerate(row)
                            if i in columnIdx)
    wb.close()


def tag_statistic(tag: str):
    headers = [tag, "次数"]
    countSet = {}
    p = r"\['(?P<" + tag + ">.*?)', '" + tag + "'\]"
    reobj = re.compile(p)
    with open("./input/sample.csv", 'r') as inf:
        with open("./output/标签次数统计/" + tag + ".csv", 'w+') as outf:
            reader = csv.DictReader(inf)
            writer = csv.writer(outf)
            writer.writerow(headers)
            for row in reader:
                labels = row[reader.fieldnames[2]]
                res = reobj.finditer(labels)
                for r in res:
                    k = r.group(tag)
                    if k in countSet:
                        countSet[k] += 1
                    else:
                        countSet[k] = 1
            writer.writerows(
                sorted(countSet.items(), key=lambda kv: (kv[1], kv[0]), reverse=True))


def get_detail(tag: str, tag_content: str):
    with open("./output/" + "各类" + tag + "详情" + "/"+tag_content + ".csv", "w+") as outf:
        with open("./input/sample.csv", "r") as inf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            p = "\['"+tag_content+"', '"+tag+"'\]"
            writer.writerows(get_detail_common(tag, p, inf))


def get_multag_detail(tag: str):
    with open("./output/单句重复标签/" + tag + ".csv", "w+") as outf:
        with open("./input/sample.csv", "r") as inf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            writer.writerows(get_detail_common(tag, inf, FLAG_MULTI_TAG))


def get_nonetag_detail(tag: str):
    with open("./output/单句无标签/" + tag + ".csv", "w+") as outf:
        with open("./input/sample.csv", "r") as inf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            p = "\['.*?', '" + tag + "'\]"
            writer.writerows(get_detail_common(tag, p, inf, FLAG_NONE_TAG))


def get_uniquetag_detail(tag: str):
    with open("./output/单句唯一标签/" + tag + ".csv", "w+") as outf:
        with open("./input/sample.csv", "r") as inf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            p = "\['.*?', '" + tag + "'\]"
            writer.writerows(get_detail_common(tag, p, inf, FLAG_UNIQUE_TAG))


def get_detail_common(tag: str, p: str, inf, flag=FLAG_HAS_TAG):
    reader = csv.DictReader(inf)
    fn = reader.fieldnames
    reobj = re.compile(p)
    res = []
    for i, row in enumerate(reader):
        ss = row[fn[1]].split("\n---------- \n")
        tags = row[fn[2]].split("\n--------")
        selectedS = []
        selectedT = []
        for j, s in enumerate(ss):
            l = len(reobj.findall(tags[j]))
            if (flag == FLAG_HAS_TAG and l >= 1 or
                flag == FLAG_NONE_TAG and l == 0 or
                flag == FLAG_UNIQUE_TAG and l == 1 or
                    flag == FLAG_MULTI_TAG and l > 1):
                selectedS.append(s)
                selectedT.append(tags[j])
        if len(selectedS) != 0:
            res.append(
                [i, row[fn[0]], "\n---------- \n".join(selectedS), "\n--------".join(selectedT)])
    return res


def get_multiER_before_DT(tag: str):
    with open("output/单句唯一标签/" + tag + ".csv", "r") as inf:
        with open("output/单句唯一标签/多关联方/" + tag + ".csv", "w+") as outf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            writer.writerows(classify_ER(inf, FLAG_MULTI_ER))


def get_noneER_before_DT(tag: str):
    with open("output/单句唯一标签/" + tag + ".csv", "r") as inf:
        with open("output/单句唯一标签/无关联方/" + tag + ".csv", "w+") as outf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            writer.writerows(classify_ER(inf, FLAG_NONE_ER))


def get_uniqueER_before_DT(tag: str):
    with open("output/单句唯一标签/" + tag + ".csv", "r") as inf:
        with open("output/单句唯一标签/唯一关联方/" + tag + ".csv", "w+") as outf:
            writer = csv.writer(outf)
            writer.writerow(["row", "title", "valid_sentences", "tags"])
            writer.writerows(classify_ER(inf, FLAG_UNIQUE_ER))


def classify_ER(inf, flag=FLAG_MULTI_ER):
    reader = csv.DictReader(inf)
    fn = reader.fieldnames
    # tagreobj = re.compile("\['(?P<tag_value>.*?)', '(?P<tag>.*?)'\]")
    reobj1 = re.compile(", '(关联方)'\]")
    reobj2 = re.compile(", '(交易类型)'\]")
    res = []
    for row in reader:
        ss = row[fn[2]].split("\n---------- \n")
        tags = row[fn[3]].split("\n--------")
        selectedS = []
        selectedT = []
        for j, s in enumerate(ss):
            ms = list(reobj1.finditer(tags[j]))
            firstERidx = -1
            secondERidx = -1
            DTidx = -1
            if len(ms) > 0:
                firstERidx = ms[0].start(1)
                if len(ms) > 1:
                    secondERidx = ms[1].start(1)
            m = reobj2.search(tags[j])
            if m:
                DTidx = m.start(1)
            if ((firstERidx == -1 or firstERidx > DTidx) and flag == FLAG_NONE_ER or
                secondERidx != -1 and secondERidx < DTidx and flag == FLAG_MULTI_ER or
                    firstERidx != -1 and secondERidx == -1 and firstERidx < DTidx and flag == FLAG_UNIQUE_ER):
                selectedS.append(s)
                selectedT.append(tags[j])
        if len(selectedS) != 0:
            res.append(
                [row[fn[0]], row[fn[1]], "\n---------- \n".join(selectedS), "\n--------".join(selectedT)])
    return res

def normalize_sentence(sent: str):
    def repl(m):
        dic = {1: "", 2: "，", 3: "；", 4: "：", 5: "（", 6: "）", 7: "《", 8: "》"}
        for i in range(1, 7):
            if m.group(i):
                return dic[i]
    if not sent.endswith("。"):
        return sent
    return re.sub(r'((?<![A-Za-z])\s|\s(?![A-Za-z])|“|”|「|」)|(,)|(;)|(:)|(\()|(\))|(<)|(>)', repl, sent)

def get_invalid_deal_type():
    with open("./input/sample.csv", 'r') as inf, open("output/标签次数统计/invalid_er.txt", 'w+') as outf, \
        open("output/标签次数统计/valid_er.txt", 'w') as outf1:
        validate_deal_type_pattern = r".{2,}"
        reobj = re.compile(validate_deal_type_pattern, re.I)
        reader = csv.reader(inf)
        next(reader)
        for row in reader:
            sents = row[1].split("\n---------- \n")
            for sent in sents:
                resp = get_ner_predict(sent)
                if resp["error_message"] or not "labels_indexes" in resp["response"]:
                    print(resp["error_message"], ": ", sent)
                    continue
                labels_indexes = resp["response"]["labels_indexes"]
                for li in labels_indexes:
                    if li[2] == "关联方":
                        er = re.sub(r'\s', '', sent[li[0]:li[1]])
                        if not reobj.search(er):
                            outf.write(sent + '\n')
                            outf.write(er+ '\n\n')
                        else:
                            outf1.write(er+'\n')


if __name__ == "__main__":
    # tag_statistic("交易类型")
    # tag_statistic("属性名词")
    get_invalid_deal_type()
