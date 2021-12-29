#!/usr/bin/env python
import re

def test_pattern(reobj, testfile, teststr:str=None):
    if teststr:
        res = reobj.search(teststr)
        print(res)
        return
    err_simples = []
    for row in testfile:
        row = row.strip("\n")
        input = row.split(" ")
        simple, should_match = input[0], input[1]
        m = reobj.search(simple)
        if m and m.group() != should_match or not m and should_match != "":
            actual = m.group() if m else ""
            err_simples.append((simple, should_match, actual))
    if len(err_simples) == 0:
        print("Congratulations, the pattern test pass!")
    else:
        print("The following simples encounter problems!")
        print("simple\tshould_match\tactual")
        for es in err_simples:
            print("{}\t{}\t{}\n".format(*es))
    pass

reobj = re.compile(
    (
        r"(((pre-)?[A-H]\d?(\++|＋+|plus)?)|天使|种子|战略|新一|IPO)(轮|系列轮|系列(?!轮))((?![融投]资|投融资)|([融投]资|投融资)(?!人|者|方|机构))|"
        r"(上一?|首|两|三|四|五)轮((?![融投]资|投融资)|(([融投]资|投融资)(?!人|者|方|机构)))|"
        r"(天使|种子|战略|风险|IPO|股权|新一|上一|(新一|上一?|首|两|三|四|五)次)([融投]资|投融资)(?!人|者|方|机构)|"
        r"(本|此|该)(轮|次)([融投]资|投融资)|"
        r"[融投]资(?!人|者|方|机构)"
    ), re.I
)

with open("./deal_type_test_simple") as inf:
    test_pattern(reobj, inf)
    # test_pattern(reobj, None, teststr="A系列轮")
