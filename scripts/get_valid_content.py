#!/usr/bin/env python3
from os import altsep, write
import re
import csv
from typing import Iterable

p = (
    r"领投|"
    "跟投|"
    "继续加持|"
    "由[^，,]*?([^联]合投|牵头)|"
    "(担任|本轮|作?为)[^，,]*?(财务顾问|FA|独家顾问|融资顾问)|"
    "筹集[^，,]*?(轮资金|融资)|"
    "融资由[^，,]*?(构成|投资)|"
    "投资(方|者|人|机构)(有|是|为|还?包括)|"
    "(美元|美金|[^多]元|人民币|亿|万)[^，,：:；;)）（(]*?[投融]资|"
    "估值[^，,：:；;)）（(]*?(美元|美金|元|人民币|亿|万)|"
    "(美元|美金|元|人民币|亿|万)[^，,：:；;)）（(]*?估值|"
    "(((Pre)?(A|B|C|D|E|F|种子|天使|本)轮)|等)投资(方|者|人|机构)|"
    "(?<!累计)([投融]资[金总]?额|融资|筹集)[^，,：:；;)）（(]*?(美元|美金|元|人民币|亿|万)|"
    "((累计|总共|连续)(获|完成)|(获得?|完成)两轮|公布|开启)[^，,：:；;)）（(]*?((美元|美金|元|人民币|亿|万)[^，,：:；;)）（(]*?|轮|略)[融投]资|"
    "([公宣]布|取得|启动|完成|迎来|获得?|筹集|开启)[^，,：:；;)）（(]*?(美元|美金|元|人民币|亿|万)[^，,：:；;)）（(]*?[融投]资(后|之后)|"
    "(?<!累计|总共|连续)(?<!共)([公宣]布(?!连续)|取得|启动|完成|迎来|获得?|筹集)(?!本轮|两轮|后续|的)[^，,：:；;)）（(]*?([融投]资(?!人|者|方|机构|之后|后)|投资(人|者|方|机构)[^，,]*[融投]资)"
)
p_purpose = (
    "(资金|融资)[\u4e00-\u9fa5，,]{0,10}((?<!应)(用(于|途[为，,]))|支持)|"
    "投资[\u4e00-\u9fa5，,]{0,4}((?<!应)用(于|途[为，]))"
)
p_exclude = "([\d]+|[亿万千百十两])起|(完成|经历|发生|获得?|进行)[^,，]*?(?<!第)[\d]+(笔|例|次融资)|[共达][^,，]*[\d][家种]"

separator = "\n\n"

reObj = re.compile(p, re.I)
re_purpose_obj = re.compile(p_purpose, re.I)
re_exclude_obj = re.compile(p_exclude, re.I)

def get_valid_contents():
    with open("input/news.csv") as f, \
        open("output/valid_sentences.csv", mode="w+") as nopf:
        reader = csv.reader(f)
        writer = csv.writer(nopf)
        writer.writerow(["title", "valid_sentences"])
        next(reader)
        # i = 0
        for row in reader:
            # if i > 0:
            #     break
            # print(row)
            # i += 1
            title = row[0]
            content = row[1]
            if re_exclude_obj.search(title):
                continue
            valid_sentences = []
            if reObj.search(title):
                valid_sentences.append(title)
            for seg in re.split("\n\n", content):
                if seg == "":
                    continue
                for sen in re.split("。", seg):
                    vsen = validate_sentence(sen)
                    for s in vsen:
                        if re_exclude_obj.search(s):
                                continue
                        if reObj.search(s):
                            valid_sentences.append(s + "。")
            res = separator.join(valid_sentences)
            writer.writerow([title, res])
            
def separate_long_sentence(sen: str):
    sen = sen.strip(',')
    sen = sen.strip('，')
    invalid_sen_li = [sen]
    valid_sen_li = []
    while len(invalid_sen_li) != 0:
        s = invalid_sen_li.pop()
        comma_matches = list(re.finditer("[,，]",s))
        comma_count = len(comma_matches)
        if comma_count == 0:
            continue
        sen_separate_idx = comma_matches[comma_count // 2].start()
        first = s[:sen_separate_idx]
        second = s[sen_separate_idx+1:]
        if len(first) > 256:
            invalid_sen_li.append(first)
        else:
            valid_sen_li.append(first)
        if len(second) > 256:
            invalid_sen_li.append(second)
        else:
            valid_sen_li.append(second)
    return valid_sen_li
    
def validate_sentence(sen: str):
    if len(sen) > 256:
        return separate_long_sentence(sen)
    else:
        return [sen]

if __name__ == "__main__":
    get_valid_contents()
    pass