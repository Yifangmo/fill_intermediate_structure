#!/usr/bin/env python
from extrator import ede
from merger import Merger
import rules
from typing import *

def test_rule(rule, result):
    entities_sent = result["entities_sent"]
    r = rule()
    tr = r.reobj.search(entities_sent)
    print("r.reobj: ", r.reobj)
    print(rule.__name__, "test result:", tr)

def test_merge():
    merger = Merger()
    sents = [
        "美国大学生金融援助平台CampusLogic完成1.2亿美元融资",
        "鲸媒体讯（文/吱吱）日前，美国大学生金融援助平台CampusLogic获得1.2亿美元融资，投资方为Dragoneer投资集团。",
        "据悉，这是CampusLogic自2011年成立以来获得的最大一笔融资。",
        "截至目前，CampusLogic的融资总额达到1.928亿美元。",
    ]
    strus = []
    for s in sents:
        obj = ede(s)
        # print(obj)
        for mr in obj["match_result"]:
            strus.append(mr["struct"])
    merged = merger(strus)
    print(merged)
    pass

def test_gen():
    obj = ede("genapsys Inc.（genapsys），今天宣布已在D轮股权融资中筹集7000万美元。")
    # print("original_index2entities: ", obj["original_index2entities"])
    # print()
    # del obj["original_index2entities"]
    print(obj)
    test_rule(rules.Rule4, obj)
    pass

KT = TypeVar('KT', List[str], dict)

class wrapper(str):
    def __init__(self, value: str):
        self.value = value
        
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
    
    def __str__(self) -> str:
        return self.value

def test1():
    w1 = wrapper("IDG资本")
    w2 = wrapper("idg资本")
    s = {}
    s[w1] = 1
    s[w2] = 2
    for k in s:
        print(k)

def test2(k: KT):
    if isinstance(k, (List, int)):
        print(True)
    pass

class A:
    def __eq__(self, __o: object) -> bool:
        pass
    def __hash__(self) -> int:
        return 0
    pass

if __name__ == "__main__":
    # test_gen()
    # test_merge()
    # test1()
    a = A()
    # b = {a:1}
    print(isinstance(A, Hashable))
    pass
    
    # 多分句共用关联方
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
    # obj = ede("36氪获悉，饭乎于近期连续完成两轮融资，包括昕先资本（洽洽家族基金）投资的千万元级天使轮融资，以及联想之星领投和拙朴投资跟投的数千万元级A轮融资。")
