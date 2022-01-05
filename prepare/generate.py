#!/usr/bin/env python3

import sqlite3, re, json, os
from collections import defaultdict
import logging
from time import time
import ruamel.yaml
from itertools import chain
import unicodedata
import variant

logging.basicConfig(format='%(message)s', level=logging.INFO)
start = time()
start0 = start

def timeit():
  global start
  end = time()
  passed = end - start
  start = end
  return passed

d=defaultdict(list)

def log(s, l=d, f=None):
  if not f: f = timeit()
  if l:
    logging.info(f"({len(l):5d}) {f:6.3f} {s}")

def hex2chr(uni):
    "把unicode轉換成漢字"
    if uni.startswith("U+"): uni = uni[2:]
    return chr(int(uni, 16))

def ishz(c):
  c = c.strip()
  if len(c) != 1: return False
  n = ord(c)
  return 0x3400<=n<0xA000 or n in (0x25A1, 0x3007) or 0xF900<=n<0xFB00 or 0x20000<=n<0x31350

HEADS = [
  ('hz', '漢字', '漢字', '#9D261D', '漢字音典在線版', 'https://mcpdict.sourceforge.io/cgi-bin/search.py?hz=%s', "<br>　　本程序源自“<a href=https://github.com/MaigoAkisame/MCPDict>漢字古今中外讀音查詢</a>”，收錄了更多語言、更多讀音，錯誤也更多，可去<a href=https://github.com/osfans/MCPDict>主頁</a>或<a href=mqqopensdkapi://bizAgent/qm/qr?url=http%3A%2F%2Fqm.qq.com%2Fcgi-bin%2Fqm%2Fqr%3Ffrom%3Dapp%26p%3Dandroid%26jump_from%3Dwebapi%26k%3D-hNzAQCgZQL-uIlhFrxWJ56umCexsmBi>QQ群</a>提出意見与建議、提供同音字表請求收錄。<br>　　本程序將多種語言的漢字讀音集成於本地數據庫，默認用國際音標注音，可用於比較各語言讀音的異同，也能給學習本程序所收的語言提供有限的幫助。方言分片以《中國語言地圖集》（第一版）为主。<br>　　本程序收錄了統一碼14.0全部漢字（包含“鿽鿾鿿𪛞𪛟𫜵𫜶𫜷𫜸”，不包含部首及兼容區漢字）、〇（同“星”或“零”）、□（有音無字、本字不明）。支持形音義等多種查詢方式，可輸入𰻞（漢字）、30EDE（統一碼）、biang2（普通話拼音，音節末尾的“?”可匹配任何聲調）、43（總筆畫數）、辵39（部首餘筆），均可查到“𰻞”字，也可以選擇兩分、五筆畫等輸入形碼進行查詢，還可以選擇說文解字、康熙字典、漢語大字典等通過釋義中出現的詞語搜索到相應的漢字。",None),
  ('lf', '兩分', '兩分', '#1E90FF', None, None, "<br>來源：<a href=http://yedict.com/zslf.htm>兩分查字</a><br>說明：可以輸入“雲龍”或“yunlong”查到“𱁬”",None),
  ('wbh', '五筆畫', '五筆畫', '#1E90FF', None, None, "<br>來源：<a href=https://github.com/CNMan/UnicodeCJK-WuBi>五筆字型Unicode CJK超大字符集編碼數據庫</a><br>說明：12345分別代表橫豎撇捺折，可以輸入“12345”查到“札”。也可以輸入五筆字型的編碼查詢漢字，比如輸入“snn”查詢“扎”。",None),
  ('sw', '說文解字', '說文', '#1E90FF', "說文解字線上搜索", "http://www.shuowen.org/?kaishu=%s", "<br>來源：<a href=https://github.com/shuowenjiezi/shuowen/>說文解字網站數據</a>",None),
  ('kx', '康熙字典', '康熙', '#1E90FF', "康熙字典網上版", "https://kangxizidian.com/kxhans/%s", "<br>來源：<a href=https://github.com/7468696e6b/kangxiDictText/>康熙字典 Kangxi Dictionary TXT</a>",None),
  ('hd', '漢語大字典', '漢大', '#1E90FF', None, None, "<br>來源：<a href=https://github.com/zi-phoenicia/hydzd/>GitHub</a>",None),
  ('och_sg', '上古（鄭張尚芳）', '鄭張', '#4D4D4D', '韻典網（上古音系）', 'https://ytenx.org/dciangx/dzih/%s',"<br>來源：<a href=https://ytenx.org/dciangx/>韻典網上古音鄭張尚芳擬音</a><br>說明：在擬音後面的括號中注明了《上古音系》中的反切、聲符、韻部。",None),
  ('och_ba', '上古（白一平沙加爾）', '白沙2015', '#4D4D4D', None, None, "更新：2015-10-13<br>來源：<a href=http://ocbaxtersagart.lsait.lsa.umich.edu/>上古音白一平沙加爾2015年擬音</a>",None),
  ('ltc_mc', '廣韻', '廣韻', '#4D4D4D', '韻典網', "http://ytenx.org/zim?kyonh=1&dzih=%s", "<br>來源：<a href=https://ytenx.org/kyonh/>韻典網</a><br>說明：括號中注明了《廣韻》中的聲母、韻攝、韻目、等、呼、聲調，以及《平水韻》中的韻部。對於“支脂祭真仙宵侵鹽”八個有重紐的韻，僅在聲母爲脣牙喉音時標註A、B類。廣韻韻目中缺少冬系上聲、臻系上聲、臻系去聲和痕系入聲，“韻典網”上把它們補全了，分別作“湩”、“𧤛”、“櫬”、“麧”。由於“𧤛”字不易顯示，故以同韻目的“齔”字代替。"," 1 1 平 ꜀, 3 2 上 ꜂, 5 3 去 ꜄, 7 4 入 ꜆"),
  ('ltc_yt', '韻圖', '韻圖', '#4D4D4D', None, None, "<br>來源：QQ共享文檔<a href=https://docs.qq.com/sheet/DYk9aeldWYXpLZENj>韻圖音系同音字表</a>"," 1 1 平 ꜀, 3 2 上 ꜂, 5 3 去 ꜄, 7 4 入 ꜆"),
  ('ltc_zy', '中原音韻', '中原音韻', '#4D4D4D', '韻典網（中原音韻）', 'https://ytenx.org/trngyan/dzih/%s', "<br>來源：<a href=https://ytenx.org/trngyan/>韻典網</a><br>說明：平聲分陰陽，入聲派三聲。下標“入”表示古入聲字","33 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,214 3 2 上 ꜂,51 5 3 去 ꜄"),
  ('ltc_lgy', '老國音', '老國音', '#4D4D4D', None, None, "<br>來源：<a href=https://github.com/jacob-us/lau_guoq_in/>老國音輸入灋方案</a>、<a href=https://zhuanlan.zhihu.com/p/21674298>老國音輸入方案簡介</a><br>說明：老國音，前民國教育部討論頒行的全國統一語音規範。 與現行普通話/國語相比，增加微疑兩母以及入聲，聲韻配合與些許字音也有不同。 本方案爲基於《校改國音字典》的老國音輸入灋，元書中發現有紕漏乃至錯誤之處一併糾正。","33 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,214 3 2 上 ꜂,51 5 3 去 ꜄,5 7 4 入 ꜆"),
  ('cmn_', '普通話', '普通話', '#FF0000', '字海', 'http://yedict.com/zscontent.asp?uni=%2$s', "更新：2021-08-23<br>來源：漢語大字典、<a href=https://www.zdic.net/>漢典</a>、<a href=http://yedict.com/>字海</a>、<a href=https://www.moedict.tw/>萌典</a><br>說明：灰色讀音來自<a href=https://www.moedict.tw/>萌典</a>。可使用漢語拼音、注音符號查詢漢字。在輸入漢語拼音時，可以用數字1、2、3、4代表聲調，放在音節末尾，“?”可代表任何聲調；字母ü可用v代替。例如查詢普通話讀lüè的字時可輸入lve4。在輸入注音符號時，聲調一般放在音節末尾，但表示輕聲的點（˙）既可以放在音節開頭，也可以放在音節末尾，例如“的”字的讀音可拼作“˙ㄉㄜ”或“ㄉㄜ˙”。","55 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,214 3 2 上 ꜂,51 5 3 去 ꜄"),
  ('cmn_zho_xa', '西安話', '西安', '#FF00C7', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-11-12<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=A","21 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,53 3 2 上 ꜂,,44 5 3 去 ꜄"),
  ('cmn_zho_ccwz','澄城王莊話', '澄城王莊', '#FF00C7', None, None, "更新：2021-11-01<br>來源：<u>清竮塵</u>整理自卜曉梅《陝西澄城（王莊鎮）方言同音字彙集》","21 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,53 3 2 上 ꜂,,44 5 3 去 ꜄"),
  ('cmn_zho_qagj','秦安郭嘉話', '秦安郭嘉', '#FF00C7', None, None, "版本：1.1 (2021-11-07)<br>來源：<u>清竮塵</u>整理自李小潔《甘肅秦安縣郭嘉方言語音研究》","113 1 1 平 ꜀,,53 3 2 上 ꜂,,44 5 3 去 ꜄"),
  ('cmn_zho_xz','徐州話', '徐州', '#FF00C7', None, None, "更新：2021-11-11<br>來源：<u>慕禃</u>整理自《江蘇省志·方言志》","213 1 1a 陰平 ꜀,45 2 1b 陽平 ꜁,35 3 2 上 ꜂,42 5 3 去 ꜄"),
  ('cmn_jil_jn', '濟南話', '濟南', '#FF0072', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-11-12<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=B","213 1 1a 陰平 ꜀,42 2 1b 陽平 ꜁,55 3 2 上 ꜂,,21 5 3 去 ꜄"),
  ('cjy_bz_ty', '太原話', '太原', '#00008B', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-11-12<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=E","11 1 1 平 ꜀,,53 3 2 上 ꜂,,45 5 3 去 ꜄,,2 7 4a 陰入 ꜆,54 8 4b 陽入 ꜇"),
  ('cjy_zh_yyhsy','陽原化稍營話', '陽原化稍營', '#00008B', None, None, "更新：2021-10-13<br>來源：<u>osfans</u>整理自趙小陽《河北陽原（化稍營）方言同音字彙》","42 1 1 平 ꜀,,55 3 2 上 ꜂,,213 5 3 去 ꜄,,32 7 4 入 ꜆"),
  ('cmn_xn_hg_wh', '武漢話', '武漢', '#C600FF', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-11-12<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=C","55 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,42 3 2 上 ꜂,,35 5 3 去 ꜄"),
  ('cmn_xn_yzll', '永州零陵話', '零陵', '#C600FF', None, None, "更新：2021-07-15<br>來源：<a href=https://github.com/shinzoqchiuq/yongzhou-homophony-syllabary>永州官話同音字表</a>、《湖南省志·方言志》<br>說明：本同音字表描寫的是屬於山北片區的永州零陵區口音，整理自《湖南省志·方言志》，有脣齒擦音 /f/，無全濁塞擦音 /dz/ 和 /dʒ/，「彎」「汪」不同韻，區分陰去和陽去","13 1 1a 陰平 ꜀,33 2 1b 陽平 ꜁,55 3 2 上 ꜂,24 5 3a 陰去 ꜄,324 6 3b 陰去 ꜅"),
  ('cmn_xn_xzzp','象州中平話', '象州中平', '#C600FF', None, None, "版本：1.1 (2021-10-14)<br>來源：<u>清竮塵</u>整理自唐七元、仇浩揚《廣西象州中平官話同音字彙》","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,54 3 2 上 ꜂,,35 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅"),
  ('cmn_xn_xznl','象州羅秀納祿話', '象州納祿', '#C600FF', None, None, "版本：1.1 (2021-10-14)<br>來源：<u>清竮塵</u>整理自段昊《廣西象州縣羅秀鎮納祿村官話研究》","44 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,52 3 2 上 ꜂,,35 5 3a 陰去 ꜄,112 6 3b 陽去 ꜅"),
  ('cmn_xn_wmgh','武鳴官話', '武鳴官話', '#C600FF,#FFAD00', None, None, "更新：2021-10-14<br>來源：<u>清竮塵</u>整理自陸淼焱《武鳴縣城官話調查報告》","33 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,55 3 2 上 ꜂,,24 5 3 去 ꜄,,55 7a 4a 高入 ꜆,21 7b 4b 低入 ꜀,35   借入調 "),
  ('cmn_xn_gshh','浪平高山漢話', '浪平高山漢話', '#C600FF,#8B0000', None, None, "更新：2021-10-06<br>來源：<u>清竮塵</u>整理自梁豔芝《一個西南官話方言島——浪平高山漢話研究》","334 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,53 3 2 上 ꜂,,35 5 3 去 ꜄"),
  ('cmn_hy_hc_fdgc', '肥東古城話', '肥東古城', '#800080', None, None, "更新：2021-07-12<br>來源：安徽肥東古城方言同音字彙","31 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,213 3 2 上 ꜂,,53 5 3 去 ꜄,,44 7 4 入 ꜆"),
  ('cmn_hy_hc_lj', '南京話', '南京', '#800080', None,None, "更新：2021-08-04<br>來源：<a href=https://github.com/uliloewi/lang2jin1>南京話拼音输入法</a>", "31 1 1a 陰平 ꜀,13 2 1b 陽平 ꜁,212 3 2 上 ꜂,44 5 3 去 ꜄,5 7 4 入 ꜆"),
  ('cmn_hy_hc_yz', '揚州話', '揚州', '#800080', None,None, "版本：V2.0 (2021-11-12)<br>來源：<u>慕禃</u>", "21 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,42 3 2 上 ꜂,,55 5 3 去 ꜄,,4 7 4 入 ꜆,2 8 4b 陽入 ꜇"),
  ('cmn_hy_hc_hz', '海州話', '海州', '#800080', None, None, "版本：V1.1 (2021-10-24)<br>來源：<u>清竮塵</u>整理自蘇曉青《海州方言同音字彙》","214 1 1a 陰平 ꜀,324 2 1b 陽平 ꜁,41 3 2 上 ꜂,,55 5 3 去 ꜄,,24 7 4 入 ꜆"),
  ('cmn_hy_hc_fn', '阜寧話', '阜寧', '#800080', None, None, "版本：V3.2 (2021-11-07)<br>來源：<u>清竮塵</u>整理自《濱海縣志》","52 1 1a 陰平 ꜀,25 2 1b 陽平 ꜁,211 3 2 上 ꜂,,334 5 3 去 ꜄,,4 7 4 入 ꜆"),
  ('cmn_hy_hc_yc', '鹽城話', '鹽城', '#800080', '淮語字典', "https://huae.sourceforge.io/query.php?table=類音字彙&字=%s", "更新：2021-09-17<br>來源：osfans整理自<a href=http://huae.nguyoeh.com/>《類音字彙》</a>、《鹽城縣志》","31 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,55 3 2 上 ꜂,,35 5 3 去 ꜄,,5 7 4 入 ꜆"),
  ('cmn_hy_hc_ycbf', '鹽城步鳳話', '鹽城步鳳', '#800080', None, None, "更新：2021-10-08<br>來源：osfans整理自蔡華祥《鹽城方言研究》（步鳳）","31 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,33 3 2 上 ꜂,,35 5 3 去 ꜄,,5 7 4 入 ꜆"),
  ('cmn_hy_tt_xh', '興化話', '興化', '#800080', None, None, "更新：2021-07-15<br>來源：osfans整理自顧黔《江蘇興化方言音系》、張丙釗《興化方言詞典》","324 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,213 3 2 上 ꜂,,53 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,4 7 4a 陰入 ꜆,5 8 4b 陽入 ꜇"),
  ('cmn_hy_tt_tr', '泰如方言', '泰如', '#800080', '泰如小字典', "http://taerv.nguyoeh.com/query.php?table=泰如字典&簡體=%s", "更新：2021-08-01<br>來源：<a href=http://taerv.nguyoeh.com/>泰如小字典</a>","21 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,213 3 2 上 ꜂,,44 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,4 7 4a 陰入 ꜆,35 8 4b 陽入 ꜇"),
  ('cmn_hy_tt_nt', '南通話', '南通', '#800080', '南通方言網', "http://nantonghua.net/search/index.php?hanzi=%s", "更新：2018-01-08<br>來源：<a href=http://nantonghua.net/archives/5127/南通话字音查询/>南通方言網</a>","21 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,55 3 2 上 ꜂,,42 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅,42 7 4a 陰入 ꜆,55 8 4b 陽入 ꜇"),
  ('cmn_hy_hx_wxhq','武穴花橋話', '武穴花橋', '#800080', None, None, "更新：2021-10-31<br>來源：<u>清竮塵</u>整理自陳姍姍《湖北省武穴市花橋話語音研究》","445 1 1a 陰平 ꜀,54 2 1b 陽平 ꜁,33 3 2 上 ꜂,,35 5 3a 陰去 ꜄,31 6 3b 陽去 ꜅,51 7 4 入 ꜆"),
  ('cmn_fyd_qmjh','祁門軍話', '祁門軍話', '#FF0000,#800080', None, None, "更新：2021-10-05<br>來源：<u>清竮塵</u>整理自鄧楠《祁門軍話語音研究》","22 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,35 3 2 上 ꜂,,212 5 3 去 ꜄,,42 7 4 入 ꜆"),
  ('cmn_fyd_xfgh','信豐官話', '信豐官話', '#FF0000,#008000', None, None, "更新：2021-10-11<br>來源：<u>清竮塵</u>整理自鍾永超《贛南官話語音及其系屬考察》","33 1 1a 陰平 ꜀,52 2 1b 陽平 ꜁,31 3 2 上 ꜂,,412 5 3 去 ꜄,,54 7 4 入 ꜆"),
  ('cmn_fyd_gzgh','贛州官話', '贛州官話', '#FF0000,#008000', None, None, "更新：2021-10-11<br>來源：<u>清竮塵</u>整理自鍾永超《贛南官話語音及其系屬考察》","33 1 1a 陰平 ꜀,42 2 1b 陽平 ꜁,452 3 2 上 ꜂,,212 5 3 去 ꜄,,5 7 4 入 ꜆"),
  ('cmn_fyd_hlzh', '華樓正話', '華樓正話', '#FF0000,#FFAD00', None, None, "版本：V1.1 (2021-10-24)<br>來源：<u>清竮塵</u>整理自陳雲龍《廣東電白舊時正話》","33 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,31 3 2 上 ꜂,,55 5 3 去 ꜄,,5 7a 4a 短入 ꜆,214 7b 4b 長入 ꜀"),
  ('cmn_fyd_npgh', '南平官話', '南平官話', '#FF0000,#FF6600', None, None, "更新：2021-10-04<br>來源：<u>清竮塵</u>整理自蘇華《福建南平方言同音字彙》","44 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,353 3 2 上 ꜂,,35 5 3 去 ꜄,,2 7 4 入 ꜆"),
  ('wuu_th_pl_td', '包場正餘餘東話', '包場-餘東', '#0000FF', None, None, "更新：2021-11-12<br>來源：<u>正心修身</u>基於呂四方言研究及海門縣方言志修改整理擴充而成<br>說明：本文所紀錄的通東（包場-餘東）屬於太湖吳語的毗陵小片，是帶有吳淮邊界特徵的特殊吳方言，以通東地區的中間地帶的包場鎮餘東鎮爲代表。通東地區（古通州東鄉）的方言具有高度的一致性。不同鄉鎮之間方言區別，主要體現在聲調歸派以及調值與連讀變調上，部分點直接音韻也有細微差別，內部大致可分爲三路口音：以呂四（呂泗）爲代表的東路口音，以包場餘東爲代表的中路口音，以四甲爲代表的西路口音，以及位於如皋境內的南場話。呂四以及四甲擁有現成字表，餘東-包場是由正心修身綜合整理該兩字表資料，並根據田調重新記音考訂本字整合而成。<br>以下講述 包場-餘東 呂四 四甲 三地音系差別<br>包場-餘東音系無獨立ɚ韻，凡呂四字表中ɚ韻字一律併入ɛ。<br>包場-餘東音大部分幫組麻韻讀如ɤᵚ韻，如馬ʔmɤᵚ③ 區別於四甲mo③<br>包場-餘東音次濁平一律入陰去 區別於呂四（沿iɪ̃②!=宴iɪ̃⑤），四甲（次濁平一律讀陽平）<br>包場-餘東音有獨立次濁入調⑧B 4ˀ 區別於四甲讀入陽入調⑧5ˀ，呂四讀入陰入調⑦34ˀ。<br>（注：四甲 陰入⑦34ˀ 陽入⑧4ˀ 呂四 陰入⑦34ˀ 陽入⑧23ˀ 餘東-包場 陰入⑦34ˀ 陽入⑧A 23ˀ 次濁入⑧B 5ˀ）<br>以上爲主要音系差別<br>原字表材料均僅有29個聲母<br>p pʰ b m f v t tʰ d n l ts tsʰ dz s z tɕ tɕʰ dʑ ɕ ʑ k kʰ ɡ ŋ x ɣ 0<br>正心修身根據實際發音將接撮口tɕ組聲母單獨列出記爲tʃ，舌面細音在接撮口呼時具有強烈的舌葉色彩，與原接齊齒呼的tɕ組聽感上存在較大差異，新派的齊齒呼tɕ組發生女國音現象併入ts組，如 今讀如tsiŋ乃至tsəŋ 先憲讀如siɪ̃，接撮口呼的tɕ組音則舌葉色彩加劇，如虛讀如ʃʯ，新派的iⱼ韻有兩個演變方向一爲併入ɿ導致雞=資=tsɿ，二爲舌葉化讀如ʅ 雞tʃʅ!=資tsɿ，因爲影響到韻的分合，字表採用了較爲老派的發音tɕiⱼ，並未將iⱼ韻tɕ組併入tʃ或是ts，又正心修身將陽調零聲母單獨列出記作ɦ（通東陽調零聲母與上海陽調匣母性質相同），故聲母總數爲36個，比前字表記音多出tʃ tʃʰ dʒ ʃ ʒ ɲ ɦ幾個聲母。其他韻母也根據實際發音進行了記音調整，使用者可以通過記音對比自行發現。<br>另注：通東話的a韻字在不同聲母後有不同變體在軟齶音後爲a，在雙脣音及舌尖音後爲aɐ̥（帶有強烈的央後元音色彩）,在接i介音時實際發音爲iä，字表記音中一律記作a，並沒有根據實際發音單列，需要注意。","44 1 1a 陰平 ꜀,113 2 1b 陽平 ꜁,51 3 2a 陰上 ꜂,231 4 2b 陽上 ꜃,334 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅,34 7 4a 陰入 ꜆,23 8a 4b 陽入 ꜇,5 8b 4c 次濁入 ꜁"),
  ('wuu_th_pl_jj', '靖江話', '靖江', '#0000FF', None, None, "更新：2021-09-25<br>來源：江蘇靖江方言同音字彙，有一定修改，轉錄者<u>落橙</u>","433 1 1a 陰平 ꜀,223 2 1b 陽平 ꜁,334 3 2 上 ꜂,,51 5 3a 陰去 ꜄,31 6 3b 陽去 ꜅,55 7 4a 陰入 ꜆,34 8a 4b 陽入 ꜇"),
  ('wuu_th_pl_jt', '金壇話', '金壇', '#0000FF', None, None, "更新：2021-10-30<br>來源：金壇縣志，轉錄者<u>正心修身</u>","434 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,44 3 2a 陰上 ꜂,21 4 2b 陽上 ꜃,55 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅,4 7 4a 陰入 ꜆,2 8a 4b 陽入 ꜇"),
  ('wuu_th_shj_sz', '蘇州話', '蘇州', '#0000FF', '吳語學堂（蘇州）', "https://www.wugniu.com/search?table=suzhou_zi&char=%s", "版本：墳派4.1 (2021-11-07)、翹舌2.6<br>來源：<a href=https://github.com/NGLI/rime-wugniu_soutseu>蘇州吳語拼音輸入方案</a>、一百年前的蘇州話、鄉音字類<br>說明：灰色的爲老派翹舌音，是樛木整理自《一百年前的蘇州話》、《鄉音字類》，加*的漢字表示[ʐ][dʐ]歸屬、陽上陽去歸屬缺乏直接資料，以區分這兩者的蘇州行政區劃內的方吳語爲基準。對於《一百年前的蘇州話》有而《鄉音字類》中沒有的字，因《一百年前的蘇州話》記音不含聲調，則其聲調以今音爲準。","44 1 1a 陰平 ꜀,223 2 1b 陽平 ꜁,51 3 2 上 ꜂,31 4 2b 陽上 ꜃,523 5 3a 陰去 ꜄,231 6 3b 陽去 ꜅,4 7 4a 陰入 ꜆,23 8 4b 陽入 ꜇"),
  ('wuu_th_shj_csd', '常熟東鄉話', '常熟東', '#0000FF', None, None, "更新：2021-11-12<br>來源：<u>鶩高赭紗匕</u>","53 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,44 3 2a 陰上 ꜂,31 4 2b 陽上 ꜃,423 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,23 8 4b 陽入 ꜇"),
  ('wuu_th_shj_tclh', '太倉鹿河話', '太倉鹿河', '#0000FF', None, None, "更新：2021-11-12<br>來源：<u>鶩高赭紗匕</u>","53 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,44 3 2a 陰上 ꜂,31 4 2b 陽上 ꜃,423 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,23 8 4b 陽入 ꜇"),
  ('wuu_th_shj_shjz', '上海江鎮話', '上海江鎮', '#0000FF', None, None, "更新：2021-11-12<br>來源：<u>鶩高赭紗匕</u>","53 1 1a 陰平 ꜀,22 2 1b 陽平 ꜁,44 3 2a 陰上 ꜂,213 4 2b 陽上 ꜃,35 5 3a 陰去 ꜄,13 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,23 8 4b 陽入 ꜇"),
  ('wuu_th_shj_sh', '上海話', '上海', '#0000FF', '吳音小字典（上海）', "http://www.wu-chinese.com/minidict/search.php?searchlang=zaonhe&searchkey=%s", "<br>來源：《上海市區方言志》（1988年版），蔡子文錄入<br>說明：該書記錄的是中派上海話音系（使用者多出生於20世紀40至70年代），與<a href=http://www.wu-chinese.com/minidict/>吳音小字典</a>記錄的音系並不完全相同。","53 1 1 平 ꜀,,,,34 5 3a 陰去 ꜄,23 6 3b 陽去 ꜅,55 7 4a 陰入 ꜆,12 8 4b 陽入 ꜇"),
  ('wuu_th_hz', '湖州話', '湖州', '#0000FF', None, None, "更新：2021-10-09<br>來源：<u>Vô Danh</u>","44 1 1a 陰平 ꜀,12 2 1b 陽平 ꜁,42 3 2a 陰上 ꜂,31 4 2b 陽上 ꜃,35 5 3a 陰去 ꜄,24 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,23 8 4b 陽入 ꜇"),
  ('wuu_th_ls_fydzg', '富陽東梓關話', '富陽東梓關', '#0000FF', None, None, "更新：2021-11-05<br>來源：<u>Biaz Imia</u>整理自盛益民、徐愷遠（2021）《吳語富陽（東梓關）方言音系》","53 1 1a 陰平 ꜀,223 2 1b 陽平 ꜁,55 3 2 上 ꜂,,335 5 3a 陰去 ꜄,313 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('wuu_hz', '杭州話', '杭州', '#0000FF', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-11-12<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=M","33 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,53 3 2 上 ꜂,,445 5 3a 陰去 ꜄,13 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('wuu_jy', '縉雲話', '縉雲', '#0000FF', None, None, "更新：2021-08-26<br>來源：由東甌組<u>老虎</u>、<u>林奈安</u>提供","334 1 1a 陰平 ꜀,231 2 1b 陽平 ꜁,53 3 2a 陰上 ꜂,31 4 2b 陽上 ꜃,554 5 3a 陰去 ꜄,213 6 3b 陽去 ꜅,423 7 4a 陰入 ꜆,35 8 4b 陽入 ꜇"),
  ('wuu_tz_lh', '臨海話', '臨海', '#0000FF', None, None, "更新：2021-08-25<br>來源：<u>落橙</u>","33 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,42 3 2 上 ꜂,,55 5 3a 陰去 ꜄,13 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('wuu_tz_xj', '仙居話', '仙居', '#0000FF', None, None, "更新：2021-08-25<br>來源：<u>落橙</u>","334 1 1a 陰平 ꜀,312 2 1b 陽平 ꜁,423 3 2 上 ꜂,,55 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('wuu_jq_wy', '武義話', '武義', '#0000FF', None, None, "更新：2021-11-07<br>來源：<u>一三</u>","24 1 1a 陰平 ꜀,423 2 1b 陽平 ꜁,445 3 2a 陰上 ꜂,334 4 2b 陽上 ꜃,53 5 3a 陰去 ꜄,31 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,3 8 4b 陽入 ꜇"),
  ('wuu_sl_sc', '遂昌話', '遂昌', '#0000FF', None, None, "更新：2021-09-22<br>來源：<u>落橙</u>、<u>阿纓</u>","55 1 1a 陰平 ꜀,221 2 1b 陽平 ꜁,52 3 2a 陰上 ꜂,13 4 2b 陽上 ꜃,334 5 3a 陰去 ꜄,212 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,23 8 4b 陽入 ꜇"),
  ('wuu_sl_yh', '雲和話', '雲和', '#0000FF', None, None, "更新：2021-08-17<br>來源：<u>落橙</u>、<u>阿纓</u>","324 1 1a 陰平 ꜀,423 2 1b 陽平 ꜁,53 3 2a 陰上 ꜂,21 4 2b 陽上 ꜃,55 5 3a 陰去 ꜄,223 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,24 8 4b 陽入 ꜇"),
  ('wuu_sl_tsly', '泰順羅陽話', '泰順羅陽', '#0000FF', None, None, "更新：2021-08-13<br>來源：<u>落橙</u>、<u>阿纓</u>","224 1 1a 陰平 ꜀,42 2 1b 陽平 ꜁,51 3 2a 陰上 ꜂,21 4 2b 陽上 ꜃,35 5 3a 陰去 ꜄,11 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,1 8 4b 陽入 ꜇,33 0 0 小稱 0"),
  ('wuu_sl_sy', '松陽話', '松陽', '#0000FF', None, None, "更新：2021-09-11<br>來源：<u>落橙</u>","51 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,214 3 2a 陰上 ꜂,22 4 2b 陽上 ꜃,35 5 3a 陰去 ꜄,13 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('wuu_oj_yqyc', '樂清樂成話', '樂清樂成', '#0000FF', None, None, "更新：2021-10-13<br>來源：由東甌組<u>落橙</u>、<u>老虎</u>、<u>阿纓</u>提供","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,34 4 2b 陽上 ꜃,52 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,323 7 4a 陰入 ꜆,212 8 4b 陽入 ꜇"),
  ('wuu_oj_yj', '永嘉話', '永嘉', '#0000FF', None, None, "更新：2021-10-18<br>來源：《永嘉縣志》轉錄人落橙","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,45 3 2a 陰上 ꜂,34 4 2b 陽上 ꜃,52 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,323 7 4a 陰入 ꜆,212 8 4b 陽入 ꜇"),
  ('wuu_oj_wzyq', '永強話', '永強', '#0000FF', None, None, "更新：2021-10-03<br>來源：摘自甌語音系(沈克誠)，轉錄者落橙","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,45 3 2a 陰上 ꜂,34 4 2b 陽上 ꜃,42 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,323 7 4a 陰入 ꜆,212 8 4b 陽入 ꜇"),
  ('wuu_oj_wz_ltc', '清末溫州話', '清末溫州', '#0000FF,#4D4D4D', None, None, "版本：V2.1 (2021-10-21)<br>來源：<u>阿纓</u>轉錄<br>參考文獻：1.《清末溫州方言音系研究》，張雪，2015；2.《溫州方言入門》，P.H.S.蒙哥馬利,1893","44 1 1a 陰平 ꜀,331 2 1b 陽平 ꜁,45 3 2a 陰上 ꜂,34 4 2b 陽上 ꜃,42 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,223 7 4a 陰入 ꜆,112 8 4b 陽入 ꜇"),
  ('wuu_oj_wz', '溫州話', '溫州', '#0000FF', None, None, "版本：V2.0 (2021-09-10)<br>來源：<u>阿纓</u>整理自《溫州話音檔》","33 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,35 4 2b 陽上 ꜃,52 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,213 7 4a 陰入 ꜆,213 8 4b 陽入 ꜇"),
  ('wuu_oj_rads', '瑞安東山話', '瑞安東山', '#0000FF', None, None, "更新：2021-10-23<br>來源：由東甌組<u>落橙</u>、<u>老虎</u>提供","55 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,13 4 2b 陽上 ꜃,52 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,322 7 4a 陰入 ꜆,322 8 4b 陽入 ꜇"),
  ('wuu_oj_ra', '瑞安話', '瑞安', '#0000FF', None, None, "更新：2021-09-17<br>說明：主要參考《瑞安話語音研究（陳海芳）》，有一定的修改，轉錄者<u>落橙</u>","55 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,52 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,434 7 4a 陰入 ꜆,323 8 4b 陽入 ꜇"),
  ('wuu_oj_rats', '瑞安陶山話', '瑞安陶山', '#0000FF', None, None, "更新：2021-09-30<br>來源：浙南甌語(顏逸明)，有一定的修改，轉錄者落橙","55 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,52 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,323 7 4a 陰入 ꜆,212 8 4b 陽入 ꜇"),
  ('wuu_oj_rahl', '瑞安湖嶺話', '瑞安湖嶺', '#0000FF', None, None, "更新：2021-10-13<br>來源：《瑞安湖嶺方言音系（太田斋）》，轉錄者落橙，校對者阿纓","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,13 4 2b 陽上 ꜃,53 5 3a 陰去 ꜄,212 6 3b 陽去 ꜅,424 7 4a 陰入 ꜆,323 8 4b 陽入 ꜇"),
  ('wuu_oj_py', '平陽話', '平陽', '#0000FF', None, None, "更新：2021-10-13<br>來源：平陽方言記略，轉錄者<u>落橙</u>","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,54 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,32 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,35 7 4a 陰入 ꜆,213 8 4b 陽入 ꜇"),
  ('wuu_oj_lg', '龍港話', '龍港', '#0000FF', None, None, "更新：2021-09-25<br>來源：《蒼南方言志》中的龍港字表，其成書時龍港尚未脫離蒼南，轉錄人落橙，龍港：太保人","44 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,54 3 2a 陰上 ꜂,45 4 2b 陽上 ꜃,42 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,24 7 4a 陰入 ꜆,213 8 4b 陽入 ꜇"),
  ('wuu_oj_cnys', '蒼南宜山話', '蒼南宜山', '#0000FF', None, None, "更新：2021-10-19<br>來源：《甌語音系》轉錄人落橙","44 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,54 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,42 5 3a 陰去 ꜄,11 6 3b 陽去 ꜅,34 7 4a 陰入 ꜆,213 8 4b 陽入 ꜇"),
  ('wuu_oj_wc', '文成話', '文成', '#0000FF', None, None, "更新：2021-10-15<br>來源：《文成縣誌》，轉錄者落橙","55 1 1a 陰平 ꜀,11 2 1b 陽平 ꜁,54 3 2a 陰上 ꜂,33 4 2b 陽上 ꜃,435 5 3a 陰去 ꜄,312 6 3b 陽去 ꜅,35 7 4a 陰入 ꜆,213 8 4b 陽入 ꜇"),
  ('wuu_oj_cnpm', '蒼南蒲門甌語方言島', '蒼南蒲門', '#0000FF', None, None, "版本：V2.0 (2021-10-19)<br>來源：鄭張尚芳調查資料、陳玉燕《浙南蒲門甌語方言島語音研究》附錄同音字彙，轉錄者<u>落橙</u>、<u>阿纓</u>","44 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,45 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,42 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,323 7 4a 陰入 ꜆,212 8 4b 陽入 ꜇"),
  ('czh_qw_fljc', '浮梁舊城話', '浮梁舊城', '#1E90FF', None, None, "更新：2021-10-17<br>來源：Pekkhak（啵啵）整理自謝留文《江西浮樑（舊城村）方言同音字彙》","55 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,21 3 2 上 ꜂,,213 5 3a 陰去 ꜄,33 6 3b 陽去 ꜅"),
  ('czh_yz_cacc', '淳安淳城話', '淳安淳城', '#1E90FF', None, None, "更新：2021-09-22<br>來源：<u>清竮塵</u>整理自曹志耘《徽語嚴州方言研究》","224 1 1a 陰平 ꜀,445 2 1b 陽平 ꜁,55 3 2 上 ꜂,,,22 6 3 去 ꜄,5 7 4a 陰入 ꜆,13 8 4b 陽入 ꜇"),
  ('czh_yz_jdmc', '建德梅城話', '建德梅城', '#1E90FF', None, None, "更新：2021-10-14<br>來源：<u>清竮塵</u>整理自曹志耘《徽語嚴州方言研究》<br>說明：文白讀調值不同","423 1 1a 陰平 ꜀,334 2 1b 陽平 ꜁,213 3 2 上 ꜂,,,55 6 3 去 ꜄,5 7 4a 陰入 ꜆,12 8 4b 陽入 ꜇,,,334 1b 1c 陰平 ꜀,211 2b 1d 陽平 ꜁,55 3b 2b 上 ꜂,,,213 6b 3b 去 ꜄"),
  ('czh_yz_jdsc', '建德壽昌話', '建德壽昌', '#1E90FF', None, None, "更新：2021-10-14<br>來源：<u>清竮塵</u>整理自曹志耘《徽語嚴州方言研究》<br>說明：文白讀調值不同","112 1 1a 陰平 ꜀,52 2 1b 陽平 ꜁,324 3 2a 陰上 ꜂,53 4 2b 陽上 ꜃,334 5 3 去 ꜄,,55 7a 4a 上陰入 ꜆,12 8a 4c 陽入 ꜇,3 7b 4b 下陰入 ꜀,,334 1b 1c 陰平 ꜀,112 2b 1d 陽平 ꜁,55 3b 2b 上 ꜂,,,324 6 3b 去 ꜄,5 7c 4d 陰入 ꜆,13 8b 4e 陽入 ꜇"),
  ('czh_yz_sasc', '遂安獅城話', '遂安獅城', '#1E90FF', None, None, "更新：2021-09-24<br>來源：<u>清竮塵</u>整理自曹志耘《徽語嚴州方言研究》","534 1 1a 陰平 ꜀,33 2 1b 陽平 ꜁,213 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,,52 6 3 去 ꜄,24 7 4 入 ꜆"),
  ('czh_yz_lxcsh', '蘭溪船上話', '蘭溪船上話', '#1E90FF', None, None, "更新：2021-10-06<br>來源：<u>清竮塵</u>整理自劉倩《九姓漁民方言研究》","53 1 1a 陰平 ꜀,33 2 1b 陽平 ꜁,214 3 2 上 ꜂,,44 5 3 去 ꜄,,55 7a 4a 上陰入 ꜆,12 8 4c 陽入 ꜇,5 7b 4b 下陰入 ꜀,,53 1b 1a 連讀降調 ꜀,,24 3b 2c 連讀升調 ꜂,,44 5b 3b 連讀高調 ꜄,,,12 8b 4d 連讀低調 ꜇"),
  ('czh_txcsh', '屯溪船上話', '屯溪船上話', '#1E90FF', None, None, "更新：2021-10-04<br>來源：<u>清竮塵</u>整理自黄曉東《皖南九姓漁民方言音系》","53 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,21 3 2 上 ꜂,,22 5 3a 陰去 ꜄,324 6 3b 陽去 ꜅,,,,,53 1b 1a 連讀高降調 ꜀,55 2b 1c 連讀高平調 ꜁,21 3b 2b 連讀低降調 ꜂,,22 5b 3c 連讀低平調 ꜄,324 6b 3d 連讀曲折調 ꜅"),
  ('gan_nc', '南昌話', '南昌', '#20B2AA', None, None, "<br>來源：<u>澀口的茶</u>","42 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,213 3 2 上 ꜂,,45 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,21 8 4b 陽入 ꜇"),
  ('gan_ygyt', '餘干玉亭話', '餘干玉亭', '#20B2AA', None, None, "更新：2021-10-24<br>來源：由Pekkhak（啵啵）整理自陳昌儀《餘干方言同音字彙》及陳昌儀《贛方言概要》<br>說明：餘干方言入聲韻在發了塞音尾之後，經過短暫的休止，又有一個同部位的鼻音，且入聲韻的兩個部分都有自己的調值。","33 1 1a 陰平 ꜀,25 2 1b 陽平 ꜁,213 3 2 上 ꜂,,45 5 3a 陰去 ꜄,23 6 3b 陽去 ꜅,104 7 4a 陰入 ꜆,101 8 4b 陽入 ꜇"),
  ('gan_lcsdd', '臨川上頓渡話', '臨川上頓渡', '#20B2AA', None, None, "更新：2021-11-10<br>來源：Pekkhak（啵啵）整理自《撫州方言研究》<br>說明：這份資料記錄是臨川上頓渡口音，並非老城區口音，其與老城區口音最大的區別在於陰平和陽去尚未合流","11 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,35 3 2 上 ꜂,,42 5 3a 陰去 ꜄,33 6 3b 陽去 ꜅,2 7 4a 陰入 ꜆,5 8 4b 陽入 ꜇"),
  ('gan_gayx', '高安楊墟話', '高安楊墟', '#20B2AA', None, None, "更新：2021-10-21<br>來源：Pekkhak（啵啵）整理自顏森《高安（老屋周家）方言的语音系统》<br>說明：這份資料記錄的並非高安市區方言，其面貌與高安市區方言存在一定的差異","55 1 1a 陰平 ꜀,24 2 1b 陽平 ꜁,42 3 2 上 ꜂,,33 5 3a 陰去 ꜄,11 6 3b 陽去 ꜅,3 7 4a 陰入 ꜆,1 8 4b 陽入 ꜇"),
  ('hak_whhb', '五華橫陂客家話', '五華橫陂', '#008000', None, None,"更新：2021-09-27<br>來源：<u>阿缨</u>整理自魏宇文《五華方言同音字彙》","44 1 1a 陰平 ꜀,13 2 1b 陽平 ꜁,31 3 2 上 ꜂,,53 5 3 去 ꜄,,1 7 4a 陰入 ꜆,5 8 4b 陽入 ꜇"),
  ('hak_whsz', '五華水寨客家話', '五華水寨', '#008000', None, None,"更新：2021-09-27<br>來源：<u>阿缨</u>整理自《廣東五華客家話比較研究》，徐汎平，2010","44 1 1a 陰平 ꜀,13 2 1b 陽平 ꜁,31 3 2 上 ꜂,,53 5 3 去 ꜄,,2 7 4a 陰入 ꜆,4 8 4b 陽入 ꜇"),
  ('hak_hl', '客家話海陸腔', '海陸客語', '#008000', '客語萌典', "https://www.moedict.tw/:%s", "<br>來源：<a href=https://www.moedict.tw/>客語萌典</a>","53 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,24 3 2 上 ꜂,,11 5 3a 陰去 ꜄,33 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('hak_sx', '客家話四縣腔', '四縣客語', '#008000', '客語萌典', "https://www.moedict.tw/:%s", "<br>來源：<a href=https://www.moedict.tw/>客語萌典</a>","24 1 1a 陰平 ꜀,11 2 1b 陽平 ꜁,31 3 2 上 ꜂,,55 5 3 去 ꜄,,2 7 4a 陰入 ꜆,5 8 4b 陽入 ꜇"),
  ('hsn_cs', '長沙話', '長沙', '#FF69B4', None, None, "版本：1.1.2 (2021-11-11)<br>來源：《湘音檢字》正音館<br>記音指導：UntPhesoca","334 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,41 3 2 上 ꜂,,45 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,14 7 4 入 ꜆"),
  ('hsn_xt', '湘潭話', '湘潭', '#FF69B4', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-11-12<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=G","33 1 1a 陰平 ꜀,12 2 1b 陽平 ꜁,42 3 2 上 ꜂,,55 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,24 7 4 入 ꜆"),
  ('hsn_nshu', '女書', '女書', '#FF69B4', None, None, "更新：2021-08-27<br>來源：<a href=https://nushuscript.org/>在線女書字典</a><br>說明：女書，又名江永女書，是一種獨特的漢語書寫系統。它是一種專門由女性使用的文字，起源於中國湖南省南部永州的江永縣。其一般被用來書寫屬於湘語永全片的江永城關方言。以前在江永縣及其毗鄰的道縣、江華瑤族自治縣的大瑤山、以及廣西部分地區的婦女之間流行、傳承。<br>注明女書寫法的來自趙麗明、徐焰編纂的《女書規範字書法字帖》，注明女書編號的來自宮哲兵、唐功暐編纂的《女書標準字字典》，兩者音系不完全相同。","44 1 1a 陰平 ꜀,42 2 1b 陽平 ꜁,35 3 2a 陰上 ꜂,13 4 2b 陽上 ꜃,21 5 3a 陰去 ꜄,33 6 3b 陽去 ꜅,5 7 4 入 ꜆"),
  ('yue_hk', '香港粵語', '香港', '#FFAD00', '粵語審音配詞字庫', "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-can/search.php?q=%3$s", "<br>來源：<a href=http://humanum.arts.cuhk.edu.hk/Lexis/lexi-can/>粵語審音配詞字庫</a>、<a href=http://www.unicode.org/charts/unihan.html>Unihan</a><br>說明：括號中的爲異讀讀音","55 1 1a 陰平 ꜀,35 3 2a 陰上 ꜂,33 5 3a 陰去 ꜄,11 2 1b 陽平 ꜁,23 4 2b 陽上 ꜃,22 6 3b 陽去 ꜅,55 7a 4a 上陰入 ꜆,33 7b 4b 下陰入 ꜀,22 8 4c 陽入 ꜇"),
  ('yue_yl', '鬱林話', '鬱林', '#FFAD00', None, None, "更新：2021-09-15<br>來源：<u>赤鬚夜蜂虎</u>","54 1 1a 陰平 ꜀,33 3 2a 陰上 ꜂,52 5 3a 陰去 ꜄,32 2 1b 陽平 ꜁,13 4 2b 陽上 ꜃,21 6 3b 陽去 ꜅,5 7a 4a 上陰入 ꜆,3 7b 4b 下陰入 ꜀,2 8a 4c 上陽入 ꜇,1 8b 4d 下陽入 ꜁,44 0 0 上陰小 0,45 0 0 下陰小 0,24 0 0 陽小 0"),
  ('yue_nnbh', '南寧白話', '南寧白話', '#FFAD00', None, None, "更新：2021-07-13<br>來源：<a href=https://github.com/leimaau/naamning_jyutping>南寧話輸入方案</a><br>說明：心母字讀 sl[ɬ]（清齒齦邊擦音），效咸山攝二等字讀 -eu[-ɛu]、-em[-ɛm]/-ep[-ɛp]、-en[-ɛn]/-et[-ɛt]<br>老派的師韻（止開三精莊組）字讀 zy[tsɿ]、cy[tsʰɿ]、sy[sɿ]，津韻（臻合三舌齒音、部份臻開三）字讀 -yun[-yn]/-yut[-yt]<br>(白)白讀；(文)文讀；(老派)老派音；(習)習讀；(常)常讀；(又)又讀；(罕)罕讀；(訓)訓讀；(舊)舊讀；(語)口語音；(書)書面音；(外)外來語音譯；(名)名詞；(動)動詞；(量)量詞","55 1 1a 陰平 ꜀,35 3 2a 陰上 ꜂,33 5 3a 陰去 ꜄,21 2 1b 陽平 ꜁,24 4 2b 陽上 ꜃,22 6 3b 陽去 ꜅,55 7a 4a 上陰入 ꜆,33 7b 4b 下陰入 ꜀,22 8 4c 陽入 ꜇"),
  ('csp_nntz', '南寧亭子平話', '南寧亭子', '#FF9900', None, None, "更新：2021-07-13<br>來源：<a href=https://github.com/leimaau/naamning_jyutping>南寧話輸入方案</a><br>說明：<br>心母字讀 sl[ɬ]（清齒齦邊擦音），日母和疑母細音字讀 nj[ȵ]（齦齶音）<br>老派的疑母模韻字讀 ngu[ŋu]，微母遇攝臻攝字讀 fu[fu]、fat[fɐt]、fan[fɐn]，遇合一讀o[o]，果合一讀u[u]<br> (白)白讀；(文)文讀；(老派)老派音；(習)習讀；(常)常讀；(又)又讀；(罕)罕讀；(訓)訓讀；(舊)舊讀；(語)口語音；(書)書面音；(外)外來語音譯；(名)名詞；(動)動詞；(量)量詞","53 1 1a 陰平 ꜀,33 3 2a 陰上 ꜂,55 5 3a 陰去 ꜄,21 2 1b 陽平 ꜁,24 4 2b 陽上 ꜃,22 6 3b 陽去 ꜅,55 7a 4a 上陰入 ꜆,33 7b 4b 下陰入 ꜀,24 8a 4c 上陽入 ꜇,22 8b 4d 下陽入 ꜁"),
  ('nan_tw', '臺灣閩南語', '臺灣', '#FF6600', '臺灣閩南語常用詞辭典', "http://twblg.dict.edu.tw/holodict_new/result.jsp?querytarget=1&radiobutton=0&limit=20&sample=%s", "更新：2020-05-17<br>來源：<a href=https://github.com/tauhu-tw/tauhu-taigi>豆腐台語詞庫</a>、<a href=https://twblg.dict.edu.tw/holodict_new/>臺灣閩南語常用詞辭典</a><br>說明：下標“俗”表示“俗讀音”，“替”表示“替代字”，指的是某個字的讀音其實來自另一個字，比如“人”字的lang5音其實來自“儂”字。有些字會有用斜線分隔的兩個讀音（如“人”字的jin5/lin5），前者爲高雄音（第一優勢腔），後者爲臺北音（第二優勢腔）。","55 1 1a 陰平 ꜀,51 3 2 上 ꜂,31 5 3a 陰去 ꜄,3 7 4a 陰入 ꜆,24 2 1b 陽平 ꜁,,33 6 3b 陽去 ꜅,5 8 4b 陽入 ꜇"),
  ('nan_lz_lz', '雷州黎話', '雷州', '#FF6600', None, None, "版本：V2.2 (2021-11-10)<br>來源：<u>Kiattan</u>","24 1 1a 陰平 ꜀,22 2 1b 陽平 ꜁,41 3 2a 陰上 ꜂,33 4 2b 陽上 ꜃,21 5 3a 陰去 ꜄,453 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('nan_lz_wcls', '吳川蘭石東話', '吳川蘭石', '#FF6600', None, None, "版本：V2.2 (2021-11-10)<br>來源：<u>Kiattan</u>","33 1 1a 陰平 ꜀,22 2 1b 陽平 ꜁,31 3 2a 陰上 ꜂,42 4 2b 陽上 ꜃,44 5 3a 陰去 ꜄,453 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('nan_lz_dbls', '電白龍山海話', '電白龍山', '#FF6600', None, None, "版本：V2.2 (2021-11-10)<br>來源：<u>Kiattan</u>","33 1 1a 陰平 ꜀,22 2 1b 陽平 ꜁,31 3 2a 陰上 ꜂,42 4 2b 陽上 ꜃,44 5 3a 陰去 ꜄,453 6 3b 陽去 ꜅,53 6b 3c 陽去b ꜃,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('nan_lz_ldzz', '羅定漳州話', '羅定漳州', '#FF6600', None, None, "版本：V2.2 (2021-11-10)<br>來源：<u>Kiattan</u>","45 1a 1a 陰平a ꜀,55 1b 1b 陰平b ꜆,24 2a 1c 陽平a ꜁,22 2b 1d 陽平b ꜇,21 2c 1e 陽平c ꜇,451 3 2a 陰上 ꜂,443 4 2b 陽上 ꜃,31 5 3 去 ꜄,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('nan_cs_cz', '潮州話', '潮州', '#FF6600', None, None, "版本：V1.4 (2021-11-05)<br>來源：<u>Kiattan</u>","33 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,52 3 2a 陰上 ꜂,25 4 2b 陽上 ꜃,213 5 3a 陰去 ꜄,11 6 3b 陽去 ꜅,2 7 4a 陰入 ꜆,54 8 4b 陽入 ꜇"),
  ('nan_cs_st', '汕頭話', '汕頭', '#FF6600', None, None, "版本：V2.9 (2021-11-05)<br>來源：<u>Kiattan</u><br>說明：<br>1.字表注“文”或“白”的读法相比其他读音一般为少用的读法，相对的，未注明者则为使用较多的读音。<br>2.舌尖聲母ts,tsʰ,s,在接細音i時，會發生顎化，常有舌面變體且舌面讀法較多，但兩者不對立且可以同時存在同個人口音中，如“心”sim/ɕim。<br>3.零聲母前常帶有喉塞聲母ʔ，如“影”多讀 ʔia ̃，但喉塞聲母與零聲母不對立。<br>4.另市區口音的韻母因個人祖籍而異，部分人有部分字丟失閉口韻現象，如“入”讀成dzik等。<br>5.表中列出的是汕頭播音腔，即一般常見的主流口音，市區還有部分人韻母有所差異，如oinn讀為ainn（間），及urng讀成ing（斤）。<br><br>拼音IPA转换说明:<br>阴平1:˧˧ 阴上3:˥˨ 阴去5:˨˩˨ 阴入7:˨ 阳平2:˥˥ 阳上4:˧˥ 阳去6:˧˩ 阳入8:˥˦","33 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,52 3 2a 陰上 ꜂,35 4 2b 陽上 ꜃,212 5 3a 陰去 ꜄,31 6 3b 陽去 ꜅,2 7 4a 陰入 ꜆,54 8 4b 陽入 ꜇"),
  ('nan_cs_pn', '普寧話', '普寧', '#FF6600', None, None, "版本：V2.2 (2021-10-12)<br>來源：<u>阿纓</u><br>說明：本文所記錄的普寧方言屬於潮汕話，是閩方言的一種，以普寧市區流沙東街道爲代表。原屬於流沙鎮的流沙東、西、南、北街道及占隴鎮發音具有較高的一致性，內部差別主要體現在個別調值不同。大多數粵東閩方言有18個聲母，分別爲：p、pʰ、b、m、t、tʰ、n、l、ts、tsʰ、dz、s、k、kʰ、g、h、ʔ，其中普寧方言p、pʰ、b、m逢今讀合口呼絕大部分字，變爲脣齒音，記爲pf、pfʰ、bv、ɱ等脣齒聲母。實際上不單聲母發音部位發生了變化，就是介音也從u變成ʋ，如“配”的實際音值爲pfʰʋe，“霧”的實際音值爲bvʋu或者bvʋ̍，爲簡化音系，仍記爲pfʰue、bvu等，因此本表普寧方言記錄22個聲母，而韻母數量不發生變化。<br>  部分聲母存在變體，如：h-聲母逢合口呼今部分字聲母爲ɸ-，逢齊齒呼少部分字新派讀ɕ-聲母，如“現”讀ɕiaŋ，均屬於自由變體，讀音暫不作記錄。還有一些聲母變體僅在連讀詞中出現，而單字音不存在，如：“好”在“有好”（得以的意思）的語流中讀音ɦuo，如“有好食”（有東西喫）。","223 1 1a 陰平 ꜀,44 2 1b 陽平 ꜁,53 3 2a 陰上 ꜂,213 4 2b 陽上 ꜃,21 5 3a 陰去 ꜄,311 6 3b 陽去 ꜅,32 7 4a 陰入 ꜆,54 8 4b 陽入 ꜇"),
  ('nan_cs_rp', '饒平話', '饒平', '#FF6600', None, None, "版本：V2.4 (2021-11-12)<br>來源：<u>四方麻東</u>","33 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,51 3 2a 陰上 ꜂,25 4 2b 陽上 ꜃,212 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,2 7 4a 陰入 ꜆,54 8 4b 陽入 ꜇"),
  ('nan_cs_rpxf', '饒平新豐話', '饒平新豐', '#FF6600', None, None, "版本：V1.4 (2021-11-12)<br>來源：<u>四方麻東</u>","34 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,52 3 2a 陰上 ꜂,25 4 2b 陽上 ꜃,212 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,32 7 4a 陰入 ꜆,54 8 4b 陽入 ꜇"),
  ('nan_cs_hllj', '惠來隆江話', '惠來隆江', '#FF6600', None, None, "版本：V1.04 (2021-10-19)<br>來源：<u>空白</u>","35 1 1a 陰平 ꜀,44 2 1b 陽平 ꜁,53 3 2a 陰上 ꜂,11 4 2b 陽上 ꜃,41 5 3 去 ꜄,,2 7 4a 陰入 ꜆,5 8 4b 陽入 ꜇"),
  ('nan_cs_cy', '潮陽話', '潮陽', '#FF6600', None, None, "版本：V1.0 (2021-10-23)<br>來源：<u>與子偕老</u>","21 1 1a 陰平 ꜀,55 3 2a 陰上 ꜂,51 5 3a 陰去 ꜄,32 7 4a 陰入 ꜆,33 2 1b 陽平 ꜁,51 4 2b 陽上 ꜃,331 6 3b 陽去 ꜅,5 8 4b 陽入 ꜇"),
  ('cdo_nd', '寧德話', '寧德', '#DB7093', None, None, "更新：2021-08-12<br>來源：<u>落橙</u>、<u>阿纓</u>","44 1 1a 陰平 ꜀,22 2 1b 陽平 ꜁,42 3 2 上 ꜂,,35 5 3a 陰去 ꜄,332 6 3b 陽去 ꜅,2 7 4a 陰入 ꜆,5 8 4b 陽入 ꜇"),
  ('cdo_cnqk', '蒼南錢庫蠻話', '蒼南錢庫', '#DB7093,#0000FF', None, None, "更新：2021-10-14<br>來源：<u>阿纓</u>","44 1 1a 陰平 ꜀,213 2 1b 陽平 ꜁,45 3 2 上 ꜂,,41 5 3a 陰去 ꜄,22 6 3b 陽去 ꜅,4 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"),
  ('mnp_jo', '建甌話', '建甌', '#DB7093', "漢語多功能字庫", "http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialect.php?word=%s", "更新：2021-10-19<br>來源：http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/dialectIndex.php?point=Q","54 1 1 平 ꜀,,21 3 2 上 ꜂,,33 5 3a 陰去 ꜄,44 6 3b 陽去 ꜅,24 7 4a 陰入 ꜆,42 8 4b 陽入 ꜇"),
  ('xxx_glps', '桂林平山土話', '桂林平山', '#000000', None, None, "更新：2021-08-27<br>來源：清竮塵整理自蘇彥湄《桂林平山土話語音研究》","51 1 1a 陰平 ꜀,33 2 1b 陽平 ꜁,43 3 2a 陰上 ꜂,24 4 2b 陽上 ꜃,35 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,5 7 4 入 ꜆"),
  ('vi_', '越南語', '越南', '#8B0000', '漢越辭典摘引', "http://www.vanlangsj.org/hanviet/hv_timchu.php?unichar=%s", "<br>來源：<a href=http://www.vanlangsj.org/hanviet/>漢越辭典摘引</a>","33 1 1a 陰平 ꜀,21 2 1b 陽平 ꜁,313 3 2a 陰上 ꜂,35 4 2b 陽上 ꜃,35 5 3a 陰去 ꜄,21 6 3b 陽去 ꜅,35 7 4a 陰入 ꜆,21 8 4b 陽入 ꜇"),
  ('ko_okm', '中世紀朝鮮語', '中世朝鮮', '#8B0000,#4D4D4D', None, None, "<br>來源：<a href=https://github.com/nk2028/sino-korean-readings>韓國漢字音歷史層次研究</a>",None),
  ('ko_kor', '朝鮮語', '朝鮮', '#8B0000', 'Naver漢字辭典', "http://hanja.naver.com/hanja?q=%s", "<br>來源：<a href=http://hanja.naver.com/>Naver漢字辭典</a><br>說明：括號前的讀音爲漢字本來的讀音，也是朝鮮的標準音，而括號內的讀音爲韓國應用<a href=http://zh.wikipedia.org/wiki/%E9%A0%AD%E9%9F%B3%E6%B3%95%E5%89%87>頭音法則</a>之後的讀音。",None),
  ('ja_go', '日語吳音', '日語吳音', '#8B0000', None, None, "<br>來源：《漢字源》改訂第五版<br>說明：《漢字源》區分了漢字的吳音、漢音、唐音與慣用音，並提供了“歷史假名遣”寫法。該辭典曾經有<a href=http://ocn.study.goo.ne.jp/online/contents/kanjigen/>在線版本</a>，但已於2014年1月底終止服務。<br>　　日語每個漢字一般具有吳音、漢音兩種讀音，個別漢字還具有唐音和慣用音。這四種讀音分別用“日吳”、“日漢”、“日唐”、“日慣”表示。另外，對於一些生僻字，《漢字源》中沒有註明讀音的種類，也沒有提供“歷史假名遣”寫法，這一類“其他”讀音用“日他”表示。<br>　　 有的讀音會帶有括號，括號前的讀音爲“現代假名遣”寫法，括號內的讀音爲對應的“歷史假名遣”寫法。<br>　　 讀音的顏色和粗細代表讀音的常用程度。<b>黑色粗體</b>爲“常用漢字表”內的讀音；黑色細體爲《漢字源》中列第一位，但不在“常用漢字表”中的讀音；<span class=dim>灰色細體</span>爲既不在“常用漢字表”中，也不在《漢字源》中列第一位的讀音。",None),
  ('ja_kan', '日語漢音', '日語漢音', '#8B0000', None, None, "<br>來源：《漢字源》改訂第五版<br>說明：《漢字源》區分了漢字的吳音、漢音、唐音與慣用音，並提供了“歷史假名遣”寫法。該辭典曾經有<a href=http://ocn.study.goo.ne.jp/online/contents/kanjigen/>在線版本</a>，但已於2014年1月底終止服務。<br>　　日語每個漢字一般具有吳音、漢音兩種讀音，個別漢字還具有唐音和慣用音。這四種讀音分別用“日吳”、“日漢”、“日唐”、“日慣”表示。另外，對於一些生僻字，《漢字源》中沒有註明讀音的種類，也沒有提供“歷史假名遣”寫法，這一類“其他”讀音用“日他”表示。<br>　　 有的讀音會帶有括號，括號前的讀音爲“現代假名遣”寫法，括號內的讀音爲對應的“歷史假名遣”寫法。<br>　　 讀音的顏色和粗細代表讀音的常用程度。<b>黑色粗體</b>爲“常用漢字表”內的讀音；黑色細體爲《漢字源》中列第一位，但不在“常用漢字表”中的讀音；<span class=dim>灰色細體</span>爲既不在“常用漢字表”中，也不在《漢字源》中列第一位的讀音。",None),
  ('ja_tou', '日語唐音', '日語唐音', '#8B0000', None, None, "<br>來源：《漢字源》改訂第五版<br>說明：《漢字源》區分了漢字的吳音、漢音、唐音與慣用音，並提供了“歷史假名遣”寫法。該辭典曾經有<a href=http://ocn.study.goo.ne.jp/online/contents/kanjigen/>在線版本</a>，但已於2014年1月底終止服務。<br>　　日語每個漢字一般具有吳音、漢音兩種讀音，個別漢字還具有唐音和慣用音。這四種讀音分別用“日吳”、“日漢”、“日唐”、“日慣”表示。另外，對於一些生僻字，《漢字源》中沒有註明讀音的種類，也沒有提供“歷史假名遣”寫法，這一類“其他”讀音用“日他”表示。<br>　　 有的讀音會帶有括號，括號前的讀音爲“現代假名遣”寫法，括號內的讀音爲對應的“歷史假名遣”寫法。<br>　　 讀音的顏色和粗細代表讀音的常用程度。<b>黑色粗體</b>爲“常用漢字表”內的讀音；黑色細體爲《漢字源》中列第一位，但不在“常用漢字表”中的讀音；<span class=dim>灰色細體</span>爲既不在“常用漢字表”中，也不在《漢字源》中列第一位的讀音。",None),
  ('ja_kwan', '日語慣用音', '日語慣用', '#8B0000', None, None, None,None),
  ('ja_other', '日語其他讀音', '日語其他', '#8B0000', None, None, None,None),
  ('bh', '總筆畫數', '總筆畫數', '#808080', None, None, None,None),
  ('bs', '部首餘筆', '部首餘筆', '#808080', None, None, None,None),
  ('cj3', '倉頡三代', '倉三', '#808080', None, None, None,None),
  ('cj5', '倉頡五代', '倉五', '#808080', None, None, None,None),
  ('cj6', '倉頡六代', '倉六', '#808080', None, None, None,None),
  ('wb86', '五筆86版', '五筆86', '#808080', None, None, None,None),
  ('wb98', '五筆98版', '五筆98', '#808080', None, None, None,None),
  ('wb06', '五筆06版', '五筆06', '#808080', None, None, None,None),
  ('va', '異體字', '異體', '#808080', None, None, None,None),
  ('fl', '分類', '分類', '#808080', None, None, None,None),
]
ZHEADS = list(zip(*HEADS))
KEYS = ZHEADS[0]
FIELDS = ", ".join(["%s "%i for i in KEYS])
COUNT = len(KEYS)
INSERT = 'INSERT INTO mcpdict VALUES (%s)'%(','.join('?'*COUNT))

#ST
stVariants = dict()
for line in open("STCharacters.txt"):
  line = line.strip()
  if "\t" not in line: continue
  fs = line.split("\t")
  if " " not in fs[1]:
    stVariants[fs[0]] = fs[1]

#db
unicodes=defaultdict(dict)
conn = sqlite3.connect('mcpdict.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
for r in c.execute('SELECT * FROM mcpdict'):
  i = chr(int(r["unicode"],16))
  row = dict(r)
  del row["pu"]
  row["hz"] = i
  del row["mc"]
  row["wuu_th_shj_sh"] = row.pop("sh")
  row["yue_hk"] = row.pop("ct")
  row["nan_tw"] = row.pop("mn")
  row["vi_"] = row.pop("vn")
  row["ko_kor"] = row.pop("kr")
  row["ja_go"] = row.pop("jp_go")
  row["ja_kan"] = row.pop("jp_kan")
  row["ja_tou"] = row.pop("jp_tou")
  row["ja_kwan"] = row.pop("jp_kwan")
  row["ja_other"] = row.pop("jp_other")
  unicodes[i] = row
conn.close()
for i in stVariants:
  if i in unicodes:
    unicodes.pop(i)
log("加載", None)

kCompatibilityVariants = dict()

def update(k, d):
  global kCompatibilityVariants
  for i,v in d.items():
    i = kCompatibilityVariants.get(i, i)
    if "_" in k and "ltc_" not in k:
      i = stVariants.get(i, i)
    if i not in unicodes:
      unicodes[i] = {"hz": i, "unicode": "%04X"%ord(i)}
    if unicodes[i].get(k, None): continue
    sep = "\n" if k in ("och_sg", "ltc_mc") else ","
    vs = sep.join(v)
    vs = vs.replace("~", "～").replace("Ǿ", "Ǿ")
    if k.startswith("wuu_") or k.startswith("nan_cs_"):
      vs = vs.replace("g", "ɡ")
    unicodes[i][k] = vs

#kCompatibilityVariant
for line in open("../app/src/main/res/raw/orthography_hz_compatibility.txt"):
    han, val = line.rstrip()
    kCompatibilityVariants[han] = val
log("兼容字", None)

#mc
d.clear()
pq = dict()
for line in open("PrengQim.txt"):
    line = line.strip()
    fs = line.split(" ")
    pq[fs[0]] = fs[1].replace("'", "0")
last = ""
for line in open("Dzih.txt"):
  line = line.strip()
  fs = line.split(" ")
  if len(fs[0]) == 1:
    hz = fs[0]
    js = fs[3]
    if "上同" in js: js = js.replace("上同", "同" + last)
    else: last = hz
    js = "%s`%s`"%(pq[fs[1]], js)
    d[hz].append(js)
update("ltc_mc", d)
log("廣韻")

#yt
import yt
ytd = yt.get_dict()
update("ltc_yt", ytd)
log("韻圖")

#sg
#https://github.com/BYVoid/ytenx/blob/master/ytenx/sync/dciangx/DrienghTriang.txt
d.clear()
for line in open("DrienghTriang.txt"):
  line = line.strip('\n')
  if line.startswith('#'): continue
  fs = line.split(' ')
  hz = fs[0]
  if len(hz) != 1: continue
  zs = fs[16]
  if zs: zs = "`%s`" % zs
  js = ("%s (%s%s切 %s聲 %s%s)%s"%(fs[12], fs[7],fs[8],fs[9],fs[10],fs[11],zs))
  if js not in d[hz]:
    d[hz].append(js)
update("och_sg", d)
log("鄭張")

#ba
#http://ocbaxtersagart.lsait.lsa.umich.edu/BaxterSagartOC2015-10-13.xlsx
d.clear()
for line in open("BaxterSagartOC2015-10-13.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz = fs[0]
  js = fs[4]
  if len(hz) == 1:
    if js not in d[hz]:
      d[hz].append(js)
update("och_ba", d)
log("白沙")

#zy
#https://github.com/BYVoid/ytenx/blob/master/ytenx/sync/trngyan
d.clear()

def getIPA(name):
  yms = dict()
  for line in open(name):
    line = line.strip('\n')
    if line.startswith('#'): continue
    fs = line.split(' ')
    ym, ipa = fs
    yms[ym] = ipa
  return yms
sms = getIPA("CjengMuxNgixQim.txt")
yms = getIPA("YonhMuxNgixQim.txt")
sds = {'去': '4', '入平': '2', '入去': '4', '入上': '3', '上': '3','陽平': '2', '陰平': '1'}

for line in open("TriungNgyanQimYonh.txt"):
  line = line.strip()
  if line.startswith('#'): continue
  fs = line.split(' ')
  hzs = fs[1]
  sd = fs[2]
  py = sms[fs[4]]+yms[fs[5]]+sds[sd]
  if "ɿ" in py:
    py = re.sub("([ʂɽ].*?)ɿ", "\\1ʅ", py)
  if sd.startswith("入"):
    py = "%s`入`"%py
  for hz in hzs:
    if py not in d[hz]:
      d[hz].append(py)
update("ltc_zy", d)
log("中原音韻")

#lgy
d.clear()
for line in open("lau_guoq_in.dict.yaml"):
  line = line.strip()
  if '\t' not in line: continue
  fs = line.split('\t')
  hz = fs[0]
  py = fs[1]
  py = re.sub("(^|[^iy])eq$", "\\1ə5", py)
  py = re.sub("q$", "5", py)
  py = py.replace("ng", "ŋ")
  py = re.sub("^n([iy])", "ȵ\\1", py)
  py = py.replace("iu","iou").replace("ou", "əu").replace("ui", "uei").replace("er", "ɚ").replace("rw", "rʅ").replace("w", "ɿ")
  py = py.replace("p", "pʰ").replace("b", "p")
  py = py.replace("t", "tʰ").replace("d", "t")
  py = py.replace("j", "ʨ").replace("q", "ʨʰ").replace("x", "ɕ")
  py = py.replace("k", "kʰ").replace("g", "k").replace("h", "x")
  py = py.replace("zr", "tʂ").replace("cr", "tʂʰ").replace("sr", "ʂ").replace("r", "ɻ")
  py = py.replace("z", "ts").replace("c", "tsʰ")
  py = py.replace("yŋ", "iuŋ").replace("un","uen").replace("en","ən").replace("eŋ","əŋ")
  if py not in d[hz]:
    d[hz].append(py)
update("ltc_lgy", d)
log("老國音")

#ccwz
d.clear()
for line in open("澄城王庄同音字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("Ø", "")
    if len(fs) < 2: continue
    for sd,hzs,n in re.findall("\[(\d)\](.*?)((?=\[)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '/':
            p = "书"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_zho_ccwz", d)
log("澄城王莊")

#qagj
d.clear()
for line in open("秦安郭嘉同音字表1.1.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("Ø", "")
    if len(fs) < 2: continue
    for sd,hzs,n in re.findall("\[(\d)\](.*?)((?=\[)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '/':
            p = "书"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_zho_qagj", d)
log("秦安郭嘉")

#xz
d.clear()
sms=set()
for line in open("徐州同音字彙.tsv"):
  line = line.strip()
  if not line: continue
  if line.startswith("#"):
    ym = line[1:]
  else:
    sm = re.findall("^.*?[①②③④]", line)[0].rstrip("ø①②③④")
    sms.add(sm)
    for sd,hzs in re.findall("([①②③④])([^①②③④]+)", line):
      sd = ord(sd) - ord('①') + 1
      py = sm + ym + str(sd)
      for hz, m in re.findall("(.)(（.*?）)?", hzs):
        m = m.strip("（）")
        if m:
          m = "`%s`" % m
        p = py + m
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_zho_xz", d)
log("徐州")

#yzll
d.clear()
for line in open("永州官話同音字表.tsv"):
  line = line.strip("\n")
  fs = line.split("\t")
  hz,jt,py,bz = fs
  if len(hz)!=1: continue
  sd = py[-1]
  py = py[:-1]
  py = py.replace("w","u").replace("uu", "u")
  py = re.sub("^(ts|tsh|s|z)i", "\\1ɿ", py)
  py = re.sub("^y(?=[^u])", "i", py).replace("ii","i")
  py = re.sub("^(c|ch|sh|zh)u", "\\1yu", py)
  py = py.replace("iu", "iou").replace("ui", "uei").replace("yun", "yn").replace("un", "uen")
  ipa = py.replace("ou", "əu").replace("ao", "au").replace("ang", "ã").replace("an", "ẽ").replace("yu", "y")
  ipa = re.sub("^h", "x", ipa).replace("gh", "ɣ").replace("sh", "ɕ").replace("zh", "ʑ").replace("h", "ʰ")\
      .replace("ts", "ts").replace("c", "tɕ").replace("ng", "ŋ")
  ipa = ipa + sd
  if bz:
    ipa += "`%s`"%bz
  d[hz].append(ipa)
update("cmn_xn_yzll", d)
log("零陵")

#np
d.clear()
for line in open("南平官话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_fyd_npgh", d)
log("南平官話")

#hlzh
d.clear()
for line in open("华楼正话同音字表1.1.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+[ab]?)\]([^\[\]]+)", fs[1]):
      if sd == "7a": sd = "7"
      elif sd == "7b": sd = "8"
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_fyd_hlzh", d)
log("華樓正話")

#qmjh
d.clear()
for line in open("祁门军话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_fyd_qmjh", d)
log("祁門軍話")

#gshh
d.clear()
for line in open("高山汉话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_xn_gshh", d)
log("高山漢話")

#wxhq
d.clear()
for line in open("武穴花桥同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?([-=])?(\{.*?\})?", hzs)
      for hz, c, m in hzm:
        m = m.strip("{}")
        p = ""
        if c and c in '-=':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_hy_hx_wxhq", d)
log("武穴花橋")

#wmgh
d.clear()
for line in open("武鸣官话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      if sd == "7a": sd = "7"
      elif sd == "7b": sd = "8"
      py = sm + ym + sd
      hzm = re.findall("(.)\d?([-=])?(\{.*?\})?", hzs)
      for hz, c, m in hzm:
        m = m.strip("{}")
        p = ""
        if c and c in '-=':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_xn_wmgh", d)
log("武鳴官話")

#xfgh
d.clear()
for line in open("信丰官话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_fyd_xfgh", d)
log("信豐官話")

#gzgh
d.clear()
for line in open("赣州官话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?([$&])?(\{.*?\})?", hzs)
      for hz, c, m in hzm:
        m = m.strip("{}")
        if c:
          if c == '$':
            c = "单字调"
          elif c == '&':
            c = "连读前字调"
          if m:
            m = "%s %s" % (c, m)
          else:
            m = c
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_fyd_gzgh", d)
log("贛州官話")

#xzzp
d.clear()
for line in open("象州中平同音字表1.1.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+[ab]?)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_xn_xzzp", d)
log("象州中平")

#xznl
d.clear()
for line in open("象州纳禄同音字表1.1.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+[ab]?)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("cmn_xn_xznl", d)
log("象州納祿")

#hz
d.clear()
for line in open("海州同音字表1.1.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("Ø", "")
    if len(fs) < 2: continue
    for sd,hzs,n in re.findall("\[(\d)\](.*?)((?=\[)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '/':
            p = "书"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_hy_hc_hz", d)
log("海州")

#fn
d.clear()
for line in open("阜寧同音字表3.2.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("Ø", "")
    if len(fs) != 2: continue
    for sd,hzs,n in re.findall("\[(\d)\](.*?)((?=\[)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '/':
            p = "书"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_hy_hc_fn", d)
log("阜寧")

#nt
#http://nantonghua.net
d.clear()
for line in open("nt.txt"):
  fs = line.strip().split(',')
  if fs[1]=='"hanzi"': continue
  hz = fs[1].strip('"')[0]
  py = fs[-6].strip('"') + fs[-4]
  if '白读' in line:
    py = "%s`白`" % py
  elif '文读' in line:
    py = "%s`文`" % py
  elif '又读' in line:
    py = "%s`又`" % py
  if py not in d[hz]:
    d[hz].append(py)
update("cmn_hy_tt_nt", d)
log("南通")

#tr
#http://taerv.nguyoeh.com/
d.clear()
trsm = {'g': 'k', 'd': 't', '': '', 'sh': 'ʂ', 'c': 'tsʰ', 'b': 'p', 'l': 'l', 'h': 'x', 'r': 'ɻ', 'zh': 'tʂ', 't': 'tʰ', 'v': 'ʋ', 'ng': 'ŋ', 'q': 'tɕʰ', 'z': 'ts', 'j': 'tɕ', 'f': 'f', 'ch': 'tʂʰ', 'k': 'kʰ', 'n': 'n', 'x': 'ɕ', 'm': 'm', 's': 's', 'p': 'pʰ'}
trym = {'ae': 'ɛ', 'ieh': 'iəʔ', 'ii': 'iɪ', 'r': 'ʅ', 'eh': 'əʔ', 'io': 'iɔ', 'ieu': 'iəʊ', 'u': 'ʊ', 'v': 'ʋ', 'en': 'əŋ', 'a': 'a', 'on': 'ɔŋ', 'ei': 'əi', 'an': 'aŋ', 'oh': 'ɔʔ', 'i': 'i', 'ien': 'iŋ', 'ion': 'iɔŋ', 'ah': 'aʔ', 'ih': 'ɪʔ', 'y': 'y', 'uei': 'uəi', 'uae': 'uɛ', 'aeh': 'ɛʔ', 'in': 'ɪ̃', 'ia': 'ia', 'z': 'ɿ', 'uh': 'ʊʔ', 'aen': 'ɛ̃', 'er': 'ɚ', 'eu': 'əʊ', 'iah': 'iaʔ', 'ueh': 'uəʔ', 'iae': 'iɛ', 'iuh': 'iʊʔ', 'yen': 'yəŋ', 'ian': 'iaŋ', 'iun': 'iʊ̃', 'un': 'ʊ̃', 'o': 'ɔ', 'uan': 'uaŋ', 'ua': 'ua', 'uen': 'uəŋ', 'ioh': 'iɔʔ', 'iaen': 'iɛ̃', 'uaen': 'uɛ̃', 'uaeh': 'uɛʔ', 'iaeh': 'iɛʔ', 'uah': 'uaʔ', 'yeh': 'yəʔ', 'ya': 'ya'}
for line in open("cz6din3.csv"):
  fs = line.strip().split(',')
  if fs[0]=='"id"': continue
  hz = fs[1].replace('"','')
  if not hz: continue
  fs[3] = fs[3].strip('"')
  fs[4] = fs[4].strip('"')
  fs[5] = fs[5].strip('"')
  c = fs[6]
  if fs[3] == fs[4] == 'v': fs[3] = ''
  py = trsm[fs[3]]+trym[fs[4]]+fs[5]
  if '白' in c or '口' in c or '常' in c or '古' in c or '舊' in c or '未' in c:
    py = "%s`白`" % py
  elif '正' in c or '本' in c:
    py = "%s`本音`" % py
  elif '異' in c or '訓' in c or '避' in c or '又' in c:
    py = "%s`又`" % py
  elif '文' in c or '新' in c or '齶化' in c:
    py = "%s`文`" % py
  
  if py not in d[hz]:
    d[hz].append(py)
update("cmn_hy_tt_tr", d)
log("泰如")

#xh
d.clear()
for line in open("興化同音字表.tsv"):
  line = line.strip()
  if line.startswith("#"):
    ym = line[1:]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("0", "")
    for sd,hzs,n in re.findall("［(\d)］(.*?)((?=［)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '/':
            p = "书"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_hy_tt_xh", d)
log("興化")

#yc
d.clear()
icsm = {'g': 'k', 'd': 't', '': '', 'c': 'tsʰ', 'b': 'p', 'l': 'l', 'h': 'x', 't': 'tʰ', 'q': 'tɕʰ', 'z': 'ts', 'j': 'tɕ', 'f': 'f', 'k': 'kʰ', 'n': 'n', 'x': 'ɕ', 'm': 'm', 's': 's', 'p': 'pʰ', 'ng': 'ŋ'}
icym = {'ae': 'ɛ', 'ieh': 'iəʔ', 'ii': 'iɪ', 'eh': 'əʔ', 'io': 'iɔ', 'ieu': 'iɤɯ', 'u': 'ʊ', 'v': 'u', 'en': 'ən', 'a': 'a', 'on': 'ɔŋ', 'an': 'ã', 'oh': 'ɔʔ', 'i': 'i', 'ien': 'in', 'ion': 'iɔŋ', 'ah': 'aʔ', 'ih': 'iʔ', 'y': 'y', 'ui': 'uɪ', 'uae': 'uɛ', 'aeh': 'ɛʔ', 'in': 'ĩ', 'ia': 'ia', 'z': 'ɿ', 'uh': 'ʊʔ', 'aen': 'ɛ̃', 'eu': 'ɤɯ', 'iah': 'iaʔ', 'ueh': 'uəʔ', 'iae': 'iɛ', 'iuh': 'yʊʔ', 'yen': 'yn', 'ian': 'iã', 'iun': 'yʊ̃', 'un': 'ʊ̃', 'o': 'ɔ', 'uan': 'uã', 'ua': 'ua', 'uen': 'uən', 'ioh': 'iɔʔ', 'iaen': 'iɛ̃', 'uaen': 'uɛ̃', 'uaeh': 'uɛʔ', 'iaeh': 'iɛʔ', 'uah': 'uaʔ', 'yeh': 'yəʔ', 'ya': 'ya', '': ''}
for line in open("鹽城同音字表.tsv"):
  line = line.strip()
  if not line: continue
  fs = line.split('\t')
  py,hzs = fs
  sm = re.findall("^[^aeiouvy]?g?", py)[0]
  sd = py[-1]
  if sd not in "12357": sd = ""
  ym = py[len(sm):len(py)-len(sd)]
  py = icsm[sm]+icym[ym]+sd
  hzs = re.findall("(.)([+-=*?]?)(\{.*?\})?", hzs)
  for hz, c, m in hzs:
    p = ""
    m = m.strip("{}")
    if c and c in '-+=*?':
      if c == '-':
        p = "白"
      elif c == '+':
        p = "又"
      elif c == '=':
        p = "文"
      elif c == '*':
        p = "俗"
      elif c == '?':
        p = "待考"
    if p and m:
        p = "%s：%s" % (p, m)
    else:
        p = p + m
    if p:
      p = "`%s`" % p
    p = py + p
    if p not in d[hz]:
      if c == '-':
        d[hz].insert(0, p)
      else:
        d[hz].append(p)
update("cmn_hy_hc_yc", d)
log("鹽城")

#ycbf
d.clear()
for line in open("鹽城方言研究-步鳳.tsv"):
  line = line.strip().replace('"','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    if len(fs) != 2: continue
    sm = fs[0]
    for sd,hzs,n in re.findall("\[(\d+)\](.*?)((?=\[)|$)", fs[1]):
      py = sm + ym +sd
      py = py.replace("0", "")
      hzs = re.findall("(.)([+-=\*?]?)(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        if "}" in m: print(m)
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cmn_hy_hc_ycbf", d)
log("鹽城步鳳")

#fdgc
d.clear()
for line in open("肥東古城同音字表.tsv"):
  line = line.strip()
  if line.startswith("#"): continue
  ipa,hzs = line.split("\t")
  ipa = ipa.rstrip("0")
  hzs = re.findall("(.)(\d)?\*?(\(.*?\))?", hzs)
  for hz,index,m in hzs:
    p = ipa
    if m:
      m = m.strip("()")
      p = "%s`%s`" % (p, m)
    if index == "1":
      d[hz].insert(0, p)
    else:
      d[hz].append(p)    
update("cmn_hy_hc_fdgc", d)
log("肥東古城")

#lj
#https://github.com/uliloewi/lang2jin1/blob/master/langjin.dict.yaml
ljsm = {'g': 'k', 'd': 't', '': '', 'sh': 'ʂ', 'c': 'tsʰ', 'b': 'p', 'l': 'l', 'h': 'x', 'r': 'ʐ', 'zh': 'ʈʂ', 't': 'tʰ', 'v': 'v', 'ng': 'ŋ', 'q': 'tɕʰ', 'z': 'ts', 'j': 'tɕ', 'f': 'f', 'ch': 'ʈʂʰ', 'k': 'kʰ', 'n': 'n', 'x': 'ɕ', 'm': 'm', 's': 's', 'p': 'pʰ'}
def lj2ipa(py):
  py = re.sub("r([1-5])$", "ʅ\\1", py)
  if py.startswith("ʅ"): py = "r" + py
  #fs = re.findall("^([^aäüeiouyʅ1-9]+)?(.*)(\d)?$", py)
  sm = py[:2]
  if sm not in ljsm: sm = py[0]
  if sm not in ljsm: sm = ""
  sd = py[-1]
  ym = py[len(sm):-1]
  if not sd.isdigit():
    ym = ym + sd
    sd = ""
  sm = ljsm[sm]
  ym = ym.replace("y", "ɿ").replace("ü", "y").replace("än", "ẽ").replace("ä", "ɛ")\
    .replace("ao", "ɔ").replace("ei", "əi").replace("ou", "əɯ")\
    .replace("en", "ə̃").replace("er", "ɚ").replace("ng", "̃").replace("n", "̃")
  return sm + ym + sd
d.clear()
for line in open("langjin.dict.yaml"):
  line = line.strip()
  fs = line.split('\t')
  if len(fs) < 2: continue
  hz, py = fs[:2]
  if len(hz)!=1 or py in "vw": continue
  js = lj2ipa(py)
  if js not in d[hz]:
    d[hz].append(js)
update("cmn_hy_hc_lj", d)
log("南京")

#yz
d.clear()
for line in open("揚州同音字表2.tsv"):
  line = line.strip("\n").replace('"', '').replace("##","#").replace('“','')
  py,hzs = line.split("\t")
  for c,hz,m in re.findall("([？#\+])?(.)(（[^）]*?（.*?）.*）|（.*?）)?", hzs):
    p = ""
    if c == '+':
      p = "書"
    elif c == '#':
      p = "俗"
    elif c == '？':
      p = "存疑"
    if m:
      p += " " + m.strip("（）")
    p = p.strip()
    if p:
      p = "`%s`" % p
    p = py + p
    if p not in d[hz]:
      d[hz].append(p)
update("cmn_hy_hc_yz", d)
log("揚州")

#yyhsy
d.clear()
for line in open("河北阳原（化稍营）方言同音字汇.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("0", "")
    for sd,hzs,n in re.findall("［(\d)］(.*?)((?=［)|$)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("cjy_zh_yyhsy", d)
log("陽原化稍營")

#td
d.clear()
for line in open("通東（包場正餘餘東）談話  字表11.12.tsv"):
  line = line.strip('\n')
  fs = [i.strip(' "') for i in line.split('\t')]
  hz, jt, ipat, ipa, py, tone, js = fs[:7]
  if ipat == "IPA" or len(hz) != 1: continue
  sd = py[-1]
  if sd == "0": sd = ""
  elif sd == "¹": sd = "8"
  elif sd == "²": sd = "9"
  if sd: ipa += sd
  if js: js = "%s`%s`"%(ipa,js)
  else: js = ipa
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_th_pl_td", d)
log("通東")

#wuu_th_pl_jj
d.clear()
for line in open("靖江方言同音字汇.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_th_pl_jj", d)
log("靖江")

#jt
d.clear()
for line in open("金壇話.tsv"):
  line = line.strip().replace('"','').replace(' ','').rstrip()
  if '\t' not in line: continue
  fs = line.split("\t")
  sy = fs[0]
  for sd,hzs in re.findall("([①②③④⑤⑥⑦⑧])([^①②③④⑤⑥⑦⑧]+)", fs[1]):
    sd = ord(sd) - ord('①') + 1
    py = sy + str(sd)
    hzs = re.findall("(.)(\*)?(［\\d］)?(（.*?）)?", hzs)
    for hz, s, c, m in hzs:
      m = m.replace("（", "`").replace("）", "`")
      p = py + m
      if p not in d[hz]:
        d[hz].append(p)
update("wuu_th_pl_jt", d)
log("金壇")

#lh
d.clear()
tones = {'33':1,'31':2,'42':3,'55':5,'13':6,'5':7,'2':8}
for line in open("临海方言字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,sd,zs = fs[:5]
  if not yb or len(hz)!=1: continue
  sd = str(tones[sd])
  js = yb + sd
  if zs: js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_tz_lh", d)
log("临海")

#xj
d.clear()
tones = {'334':1,'312':2,'423':3,'55':5,'22':6,'5':7,'2':8}
for line in open("仙居方言字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,sd,zs = fs[:5]
  if not yb or len(hz)!=1: continue
  sd = str(tones[sd])
  js = yb + sd
  if zs: js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_tz_xj", d)
log("仙居")

#wy
d.clear()
for line in open("武義字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  jt,hz,py,yb,zs = fs[:5]
  if not yb or len(hz)!=1: continue
  sd = py[-1]
  js = yb.rstrip("12345") + sd
  if zs: js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_jq_wy", d)
log("武義")

#sz
#https://github.com/NGLI/rime-wugniu_soutseu/blob/master/wugniu_soutseu.dict.yaml
def sz2ipa(s):
  tone = s[-1]
  if tone.isdigit():
    s = s[:-1]
  else:
    tone = ""
  s = re.sub("y$", "ɿ", s)
  s = re.sub("^yu$", "ghiu", s)
  s = re.sub("yu$", "ʮ", s)
  s = re.sub("q$", "h", s)
  s = s.replace("y", "ghi").replace("w", "ghu").replace("ii", "i").replace("uu", "u")
  s = re.sub("iu$", "yⱼ", s)
  s = s.replace("au", "æ").replace("ieu", "y").replace("eu", "øʏ").replace("oe", "ø")\
          .replace("an", "ã").replace("aon", "ɑ̃").replace("en", "ən")\
          .replace("iuh", "yəʔ").replace("iu", "y").replace("ou", "əu").replace("aeh", "aʔ").replace("ah", "ɑʔ").replace("ih", "iəʔ").replace("eh", "əʔ").replace("on", "oŋ")
  s = re.sub("h$", "ʔ", s)
  s = re.sub("er$", "əl", s)
  s = s.replace("ph", "pʰ").replace("th", "tʰ").replace("kh", "kʰ").replace("tsh", "tsʰ")\
          .replace("ch", "tɕʰ").replace("c", "tɕ").replace("sh", "ɕ").replace("j", "dʑ").replace("zh", "ʑ")\
          .replace("gh", "ɦ").replace("ng", "ŋ").replace("gn", "ȵ").replace("g", "ɡ")
  s = re.sub("i$", "iⱼ", s)
  s = re.sub("ie$", "i", s)
  s = re.sub("e$", "ᴇ", s)
  s = s + tone
  return s
d.clear()
firstline = False
for filename in ("苏州话翘舌音字表2.6.tsv", "与今音有区别的坟派读音字表(苏州话)4.1.tsv"):
  firstline = False
  for line in open(filename):
    line = line.replace('"', '').strip()
    fs = line.split("\t")
    if fs[0] == '#ən' or fs[0] == "#ɛ":
      firstline = True
    if firstline:
      if len(fs) == 1:
        ym = fs[0][1:]
      else:
        sm = fs[0][1:]
        if "原" in sm:
          sm = re.sub("^.+?\(原(.+?)\)", "\\1", sm)
        for sd,hzs,n in re.findall("\[(\d)\](.*?)((?= )|$)", fs[1]):
          py = sm + ym +sd
          hzl = re.findall("(.)([-=*]?)(\{.*?\})?", hzs)
          for hz, c, m in hzl:
            if hz in '、()': continue
            p = ''
            if c == '=':
              p = "書"
            elif c == '-':
              p = "白"
            elif c == '*':
              p = "＊"
            m = m.strip('{}')
            if m:
              p += " " + m
            p = p.strip()
            if p:
              p = "`%s`" % p
            p = "|%s%s|" % (py,p)
            d[hz].append(p)
for line in open("wugniu_soutseu.dict.yaml"):
  line = line.strip()
  fs = line.split('\t')
  if len(fs) != 2: continue
  hz, py = fs
  if len(hz) == 1:
    py = sz2ipa(py)
    if py not in d[hz]:
      d[hz].append(py)
update("wuu_th_shj_sz", d)
log("蘇州")

#cmn
d.clear()
for line in open("cmn.tsv"):
  line = line.strip()
  if not line or line.startswith("#"):
    continue
  hzs,py = line.split("\t")[:2]
  for hz in hzs:
    d[hz] = py.split(",")
update("cmn_",d)
log("普通話")

#gz
#https://github.com/rime/rime-cantonese/blob/master/jyut6ping3.dict.yaml
d.clear()
for line in open("jyut6ping3.dict.yaml"):
  line = line.strip()
  fs = line.split('\t')
  if len(fs) < 2: continue
  hz, py = fs[:2]
  if len(hz) == 1:
    if py not in d[hz]:
      d[hz].append(py)
for line in open("/usr/share/unicode/Unihan_Readings.txt"):
  line = line.strip()
  if not line.startswith("U"): continue
  fields = line.strip().split("\t", 2)
  han, typ, yin = fields
  if typ == "kCantonese":
    yin = yin.strip().split(" ")
    han = hex2chr(han)
    for y in yin:
      if y not in d[han]:
        d[han].append(y)
update("yue_hk", d)
log("香港")

#yl
ipas={'b∅': 'p', 'p∅': 'pʰ', 'bb∅': 'ɓ', 'm∅': 'm', 'f∅': 'f', 'd∅': 't', 't∅': 'tʰ', 'dd∅': 'ɗ', 'n∅': 'n', 'l∅': 'l', 'sl∅': 'ɬ', 'g∅': 'k', 'k∅': 'kʰ', 'gw∅': 'kʷ', 'kw∅': 'kʷʰ', 'h∅': 'h', 'ng∅': 'ŋ', 'z∅': 'tʃ', 'c∅': 'tʃʰ', 's∅': 'ʃ', 'nj∅': 'ȵ', 'j∅': 'j', 'w∅': 'w', '∅': '', 'aa': 'a', 'ai': 'ai', 'au': 'au', 'an': 'an', 'ah': 'aʔ', 'am': 'am', 'ang': 'aŋ', 'at': 'at', 'ap': 'ap', 'ak': 'ak', 'o': 'ɔ', 'oi': 'ɔi', 'ou': 'ɔu', 'on': 'ɔn', 'om': 'ɔm', 'ong': 'ɔŋ', 'ot': 'ɔt', 'op': 'ɔp', 'ok': 'ɔk', 'oe': 'œ', 'oen': 'œn', 'yng': 'œŋ', 'yet': 'œt', 'yk': 'œk', 'oek': 'œk', 'oep': 'œp', 'e': 'ɛ', 'een': 'ɛn', 'ing': 'eŋ', 'ik': 'ek', 'eo': 'o', 'eou': 'əu', 'eat': 'ət', 'eu': 'ɛu', 'ei': 'ei', 'en': 'ɛn', 'em': 'ɛm', 'eng': 'ɛŋ', 'et': 'ɛt', 'ep': 'ɛp', 'ek': 'ɛk', 'i': 'i', 'iu': 'iu', 'in': 'in', 'im': 'im', 'it': 'it', 'ip': 'ip', 'iik': 'ik', 'u': 'u', 'ui': 'ui', 'un': 'un', 'ung': 'oŋ', 'ut': 'ut', 'uk': 'ok', 'yu': 'y', 'yun': 'yn', 'yut': 'yt', 'm': 'm̩', 'ng': 'ŋ̍', '': ''}
d.clear()
for line in open("鬱林話字表-粵拼版-21年9月15日.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  if len(fs) < 12: continue
  hz = fs[0]
  if len(hz) > 1: continue
  sm,ym,sd,zs = fs[8:12]
  sm = sm.replace("0", "") + "∅"
  yb = (ipas[sm] if sm in ipas else sm.rstrip("∅"))+ipas[ym]
  js = yb + sd + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("yue_yl", d)
log("鬱林")

#nnbh
d.clear()
xlit="PmfTnNlKhHsʃjwWɐAEɛIɪɔOœɵUʊYː]|pmftnŋlkhʰsʃjwʷɐaeɛiɪɔoœɵuʊyː̚"
xlits = list(zip(*xlit.split("|")))
def nnbhipa(py):
  py = re.sub("([ptk])1", "\g<1>7", py)
  py = re.sub("([ptk])3", "\g<1>8", py)
  py = re.sub("([ptk])6", "\g<1>9", py)
  py = re.sub("^(m)+$", "\\1̩", py)
  py = re.sub("^(ng)+$", "\\1̍", py)
  py = re.sub("^q", "ʔ", py)
  py = re.sub("^([jy])u(ng)","jʊŋ", py)
  py = re.sub("^(jy|[jy])u([t])", "jYː\\2]", py)
  py = re.sub("([dtlgkhzcsj])yu([t])", "\\1Yː\\2]", py)
  py = re.sub("sl", "ɬ", py)
  py = re.sub("^([jy])u([k])","jʊ\\2]", py)
  py = re.sub("^(jy)u", "jYː", py)
  py = re.sub("yu", "Yː", py)
  py = re.sub("y([aeior])", "j\\1", py)
  py = re.sub("(aa|r)([i])", "AːI", py)
  py = re.sub("(aa|r)([u])", "AːU", py)
  py = py.replace("ai", "ɐI").replace("au", "ɐU")
  py = re.sub("(aa|r)([ptk])", "Aː\\2]", py)
  py = re.sub("a([ptk])", "ɐ\\1]", py)
  py = re.sub("(aa|r)", "Aː", py)
  py = re.sub("^b", "P", py)
  py = re.sub("c", "T͡ʃH", py)
  py = re.sub("^d", "T", py)
  py = re.sub("eu", "ɛːU", py)
  py = re.sub("(eo|oe)i", "ɵY", py)
  py = re.sub("(eo|oe)([pk])", "œː\\2]", py)
  py = re.sub("(eo|oe)(ng)", "œː\\2", py)
  py = re.sub("(eo|oe)(t)", "ɵ\\2]", py)
  py = re.sub("(eo|oe)(n)", "ɵ\\2", py)
  py = py.replace("oe", "œː").replace("oi", "ɔːI")
  py = re.sub("ou", "OU", py)
  py = re.sub("u([k])", "ʊ\\1]", py)
  py = re.sub("ui", "UːI", py)
  py = re.sub("iu", "IːU", py)
  py = re.sub("i(ng)", "EN", py)
  py = re.sub("ik", "EK]", py)
  py = re.sub("i([pt])", "Iː\\1]", py)
  py = py.replace("eo", "ɵ").replace("a", "ɐ").replace("ei", "EI").replace("i", "Iː")
  py = re.sub("e([ptk])", "ɛː\\1]", py)
  py = re.sub("e", "ɛː", py)
  py = re.sub("o([ptk])", "ɔː\\1]", py)
  py = re.sub("u([pt])", "Uː\\1]", py)
  py = re.sub("u(ng)", "ʊN", py)
  py = re.sub("o", "ɔː", py)
  py = re.sub("u", "Uː", py)
  py = re.sub("em", "ɛːm", py)
  py = re.sub("en", "ɛːn", py)
  py = py.replace("ng", "N").replace("kw", "KWH").replace("gw", "KW").replace("g", "K")
  py = re.sub("^([ptk])", "\\1H", py)
  py = re.sub("s", "ʃ", py)
  py = re.sub("z", "T͡ʃ", py)
  py = re.sub("T͡ʃy", "T͡sɿ", py)
  py = re.sub("T͡ʃHy", "T͡sHɿ", py)
  py = re.sub("ʃy", "sɿ", py)
  py = re.sub("T͡ʃT͡ʃ", "T͡sɿ", py)
  py = re.sub("T͡ʃHT͡ʃ", "T͡sHɿ", py)
  py = re.sub("ʃT͡ʃ", "sɿ", py)
  py = re.sub("T͡ʃIːIː", "T͡sɿ", py)
  py = re.sub("T͡ʃHIːIː", "T͡sHɿ", py)
  py = re.sub("ʃIːIː", "sɿ", py)
  py = re.sub("nj", "ȵ", py)
  for a,b in xlits:
    py = py.replace(a, b)
  return py
for line in open("naamning_baakwaa.dict.yaml"):
  line = line.strip()
  if '\t' not in line: continue
  fs = line.split('\t')
  hz = fs[0]
  js = fs[1]
  if len(hz) > 1: continue
  c,py,zs = re.findall("(\(.*?\))?([a-z0-9]+)(「.*?」)?", js)[0]
  zs = zs.strip('「」')
  if not zs: c = c.strip("()")
  js = c + zs
  py = nnbhipa(py)
  if js: js = "%s`%s`" % (py, js)
  else: js = py
  if js not in d[hz]:
    d[hz].append(js)
update("yue_nnbh", d)
log("南寧白話")

#nntz
d.clear()
xlit="PmfTnNlKhHsʃjwWɐAEɛIɪɔOœɵUʊYː]|pmftnŋlkhʰsʃjwʷɐaeɛiɪɔoœɵuʊyː̚"
xlits = list(zip(*xlit.split("|")))
def nntzipa(py):
  py = re.sub("([ptk])3", "\g<1>7", py)
  py = re.sub("([ptk])2", "\g<1>8", py)
  py = re.sub("([ptk])5", "\g<1>9", py)
  py = re.sub("([ptk])6", "\g<1>10", py)
  py = re.sub("^(m)+$", "\\1̩", py)
  py = re.sub("^(ng)+$", "\\1̍", py)
  py = re.sub("^q", "ʔ", py)
  py = re.sub("^(jy|[jy])u([t])", "jYː\\2]", py)
  py = re.sub("([dtlgkhzcsj])yu([t])", "\\1Yː\\2]", py)
  py = re.sub("sl", "ɬ", py)
  py = re.sub("^(jy)u", "jYː", py)
  py = re.sub("yu", "Yː", py)
  py = re.sub("y([aeior])", "j\\1", py)
  py = re.sub("(aa|r)([i])", "AːI", py)
  py = re.sub("(aa|r)([u])", "AːU", py)
  py = re.sub("a([i])", "ɐI", py)
  py = re.sub("a([u])", "ɐU", py)
  py = re.sub("(aa|r)([ptk])", "Aː\\2]", py)
  py = re.sub("a([ptk])", "ɐ\\1]", py)
  py = re.sub("(aa|r)", "Aː", py)
  py = re.sub("^b", "P", py)
  py = re.sub("c", "T͡ʃH", py)
  py = re.sub("^d", "T", py)
  py = re.sub("eu", "ɛːU", py)
  py = re.sub("oe([ptk])", "œː\\1]", py)
  py = re.sub("oe(ng)", "œː\\1", py)
  py = re.sub("oe", "œː", py)
  py = re.sub("eo(ng)", "œːŋ", py)
  py = re.sub("eo([k])", "œː\\1]", py)
  py = re.sub("ou", "OU", py)
  py = re.sub("u([k])", "O\\1]", py)
  py = re.sub("ui", "UːI", py)
  py = re.sub("iu", "IːU", py)
  py = re.sub("i(ng)", "EN", py)
  py = re.sub("ik", "EK]", py)
  py = re.sub("i([pt])", "Iː\\1]", py)
  py = re.sub("a", "ɐ", py)
  py = re.sub("ei", "EI", py)
  py = re.sub("i", "Iː", py)
  py = re.sub("e([ptk])", "ɛː\\1]", py)
  py = re.sub("e", "ɛː", py)
  py = re.sub("Iːɐ", "Iɐ", py)
  py = re.sub("Iːɐk", "Iɐk]", py)
  py = re.sub("Iːɐng", "IɐN", py)
  py = re.sub("o([ptk])", "O\\1]", py)
  py = re.sub("u([pt])", "Uː\\1]", py)
  py = re.sub("u(ng)", "ON", py)
  py = re.sub("o", "O", py)
  py = re.sub("u", "Uː", py)
  py = re.sub("ng", "N", py)
  py = re.sub("kw", "KWH", py)
  py = re.sub("gw", "KW", py)
  py = re.sub("g", "K", py)
  py = re.sub("^([ptk])", "\\1H", py)
  py = re.sub("s", "ʃ", py)
  py = re.sub("z", "T͡ʃ", py)
  py = re.sub("em", "ɛːm", py)
  py = re.sub("en", "ɛːn", py)
  py = re.sub("nj", "ȵ", py)
  for a,b in xlits:
    py = py.replace(a, b)
  return py
for line in open("naamning_bingwaa.dict.yaml"):
  line = line.strip()
  if '\t' not in line: continue
  fs = line.split('\t')
  hz = fs[0]
  js = fs[1]
  if len(hz) > 1: continue
  c,py,zs = re.findall("(\(.*?\))?([a-z0-9]+)(「.*?」)?", js)[0]
  zs = zs.strip('「」')
  if not zs: c = c.strip("()")
  js = c + zs
  py = nntzipa(py)
  if js: js = "%s`%s`" % (py, js)
  else: js = py
  if js not in d[hz]:
    d[hz].append(js)
update("csp_nntz", d)
log("南寧亭子")

#sh
def sh2ipa(s):
  tag = s[0]
  isTag = tag == "|"
  if isTag:
    s = s[1:-1]
  b = s
  tone = s[-1]
  if tone.isdigit():
    s = s[:-1]
  else:
    tone = ""
  s = re.sub("y$", "ɿ", s)
  s = s.replace("y", "ghi").replace("w", "ghu").replace("ii", "i").replace("uu", "u")
  s = re.sub("^(c|ch|j|sh|zh)u", "\\1iu", s)
  s = s.replace("au", "ɔ").replace("eu", "ɤ").replace("oe", "ø")\
          .replace("an", "ã").replace("aon", "ɑ̃").replace("en", "ən")\
          .replace("iuh", "yiʔ").replace("iu", "y").replace("eh", "əʔ").replace("on", "oŋ")
  s = re.sub("h$", "ʔ", s)
  s = re.sub("r$", "əl", s)
  s = s.replace("ph", "pʰ").replace("th", "tʰ").replace("kh", "kʰ").replace("tsh", "tsʰ")\
          .replace("ch", "tɕʰ").replace("c", "tɕ").replace("sh", "ɕ").replace("j", "dʑ").replace("zh", "ʑ")\
          .replace("gh", "ɦ").replace("ng", "ŋ").replace("g", "ɡ")
  s = re.sub("e$", "ᴇ", s)
  s = s + tone
  if isTag:
    s = "%s`白`" % s
  return s

for i in unicodes.keys():
  if "wuu_th_shj_sh" in unicodes[i]:
    sh = unicodes[i]["wuu_th_shj_sh"]
    if sh:
      fs = sh.split(",")
      fs = map(sh2ipa, fs)
      sh = ",".join(fs)
      unicodes[i]["wuu_th_shj_sh"] = sh
log("上海")

#csd
d.clear()
for line in open("常熟东字表20211112.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,py,bz,sd = fs[:6]
  if not yb or len(hz)!=1: continue
  yb = yb.rstrip("012345678")
  js = yb + sd
  if bz:
    js += "`%s`" % (bz.rstrip('。'))
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_th_shj_csd", d)
log("常熟東")

#jz
d.clear()
for line in open("江镇字表20211112.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,py,bz,sd = fs[:6]
  if not yb or len(hz)!=1: continue
  yb = yb.rstrip("012345678")
  js = yb + sd
  if bz:
    js += "`%s`" % (bz.rstrip('。'))
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_th_shj_shjz", d)
log("江鎮")

#tclh
d.clear()
for line in open("太仓鹿河字表20211112.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,py,bz,sd = fs[:6]
  if not yb or len(hz)!=1: continue
  yb = yb.rstrip("012345678")
  js = yb + sd
  if bz:
    js += "`%s`" % (bz.rstrip('。'))
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_th_shj_tclh", d)
log("太仓鹿河")

#hz
d.clear()
for line in open("湖州话字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,py,bz = fs[:5]
  if not yb or len(hz)!=1: continue
  sd = py[-1]
  if not sd.isdigit(): sd = ""
  yb = yb.rstrip("¹²³⁴⁵")
  js = yb + sd
  if hz == "？": hz = "□"
  if bz:
    js += "`%s`" % bz
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_th_hz", d)
log("湖州")

#fydzg
d.clear()
for line in open("东梓关字表20211105.tsv"):
  line = line.strip('\n').replace('�','□')
  fs = [i.strip(' "') for i in line.split('\t')]
  jt, hz, js, ipa, py = fs[:5]
  if ipa == "IPA": continue
  sd = py[-1]
  ipa = ipa.rstrip("¹²³⁴⁵")
  if sd == "0": sd = ""
  if sd: ipa += sd
  if js: js = "%s`%s`"%(ipa,js)
  else: js = ipa
  if len(hz) == 1:
    if js not in d[hz]:
      d[hz].append(js)
update("wuu_th_ls_fydzg", d)
log("富陽東梓關")

#sy
d.clear()
tones = {'51':1,'31':2,'214':3,'22':4,'35':5,'13':6,'5':7,'2':8}
for line in open("松阳方言字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,sd = fs[:4]
  if not yb or len(hz)!=1: continue
  sd = str(tones[sd])
  js = yb + sd
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_sl_sy", d)
log("松陽")

#sc
d.clear()
tones = {'55':1,'221':2,'52':3,'13':4,'334':5,'212':6,'5':7,'23':8}
for line in open("吴语遂昌话字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,yb,sd,zs = fs[:4]
  if not yb or len(hz)!=1: continue
  if sd == "0": sd = ""
  else: sd = str(tones[sd])
  js = yb + sd
  if zs: js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_sl_sc", d)
log("遂昌")

#yh
d.clear()
tones = {'324':1,'423':2,'53':3,'21':4,'55':5,'223':6,'5':7,'24':8}
for line in open("云和方言同音字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,sd,zs = fs[:5]
  if not yb or len(hz)!=1: continue
  if sd == "0": sd = ""
  else: sd = str(tones[sd])
  js = yb + sd
  if zs: js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_sl_yh", d)
log("雲和")

#tsly
d.clear()
tones = {'224':1,'42':2,'51':3,'21':4,'35':5,'11':6,'5':7,'1':8, '33':9}
for line in open("泰顺罗阳同音字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,sd,zs = fs[:5]
  if not yb or len(hz)!=1: continue
  if sd == "0": sd = ""
  else: sd = str(tones[sd])
  js = yb + sd
  if zs: js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_sl_tsly", d)
log("泰順羅陽")

#ra
d.clear()
for line in open("瑞安话语音研究（陈海芳）-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      if sd == "0": sd = ""
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_ra", d)
log("瑞安")

#rads
d.clear()
for line in open("瑞安東山-方言调查字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,zs = fs[:4]
  if not yb or len(hz) != 1: continue
  yb = yb.rstrip("0")
  js = yb + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_oj_rads", d)
log("瑞安東山")

#rahl
d.clear()
for line in open("瑞安湖岭方言音系（太田斋）-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_rahl", d)
log("瑞安湖嶺")

#rats
d.clear()
for line in open("浙南瓯语(颜逸明)-瑞安陶山-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_rats", d)
log("瑞安陶山")

#yqyc
d.clear()
for line in open("乐清乐成字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb = fs[:3]
  if not yb: continue
  if len(hz) == 1:
    js = yb.rstrip("0")
    if js not in d[hz]:
      d[hz].append(js)
update("wuu_oj_yqyc", d)
log("樂清樂成")

#wzyq
d.clear()
for line in open("瓯语音系-永强-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_wzyq", d)
log("永強")

#wz_ltc
d.clear()
for line in open("清末温州2.1.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  if len(fs) < 7: continue
  order,hz,yb,sm,ym,sd,zs = fs[:7]
  if len(hz) != 1: continue
  js = yb
  if zs:
    js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_oj_wz_ltc", d)
log("清末溫州")

#wz
d.clear()
tones = {'阳入':8,'阴上':3,'阳平':2,'阴入':7,'阳去':6,'阴平':1,'阴去':5,'阳上':4}
for line in open("温州方言同音字表2.0.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  order,hz,jt,yb,sm,ym,sd,zs = fs[:8]
  if not yb or len(hz) != 1: continue
  sd = str(tones[sd])
  js = yb + sd
  if zs:
    js += "`%s`"%zs
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_oj_wz", d)
log("溫州")

#cnpm
d.clear()
tones = {'44':1,'31':2,'45':3,'24':4,'42':5,'22':6,'323':7,'212':8}
for line in open("苍南蒲门瓯语方言岛2.0.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,yb,sd = fs[:3]
  if not yb or len(hz)!=1: continue
  sd = str(tones[sd])
  js = yb + sd
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_oj_cnpm", d)
log("蒼南蒲門")

#wuu_oj_py
d.clear()
for line in open("平阳方言记略(陈承融)-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_py", d)
log("平陽")

#wuu_oj_lg
d.clear()
for line in open("苍南方言志-龙港-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_lg", d)
log("龍港")

#wuu_oj_cnys
d.clear()
for line in open("苍南宜山字表.tsv"):
  line = line.rstrip("\n").replace('"','').replace(' ','')
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  sm,ym,sd,hz,zs = fs[:5]
  if sm == "声母" or len(hz) != 1: continue
  sd = sd.strip("[]")
  zs = zs.strip("{}")
  js = sm + ym + sd + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_oj_cnys", d)
log("蒼南宜山")

#wuu_oj_wc
d.clear()
for line in open("文成县志-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_wc", d)
log("文成")

#yj
d.clear()
for line in open("永嘉县志-字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0]
    for sd,hzs in re.findall("\[(\d)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzs = re.findall("(.)(\{.*?\})?", hzs)
      for hz, m in hzs:
        m = m.replace("{", "`").replace("}", "`")
        p = py + m
        if p not in d[hz]:
          d[hz].append(p)
update("wuu_oj_yj", d)
log("永嘉")

#jy
tones = {'阳入':8,'阴上':3,'阳平':2,'阴入':7,'阳去':6,'阴平':1,'阴去':5,'阳上':4}
d.clear()
for line in open("缙云字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,sd,zs,yb = fs[0],fs[1],fs[4],fs[5],fs[7]
  if not yb or len(hz) != 1: continue
  yb = yb.rstrip("˩˨˧˦˥0") + str(tones[sd])
  js = yb + ("`%s`"% zs if zs and not zs.isdigit() else "")
  if js not in d[hz]:
    d[hz].append(js)
update("wuu_jy", d)
log("縉雲")

#nan
d.clear()
for line in open("豆腐台語詞庫.csv"):
  fs = line.strip().split(',')
  hz = fs[0]
  if len(hz) == 1:
    for py in fs[1:]:
      if py not in d[hz]:
        d[hz].append(py)
update("nan_tw", d)
for i in unicodes.keys():
  if "nan_tw" in unicodes[i]:
    py = unicodes[i]["nan_tw"]
    if py:
      py = re.sub("\|(.*?)\|", "\\1`白`", py)
      py = re.sub("\*(.*?)\*", "\\1`文`", py)
      py = re.sub("\((.*?)\)", "\\1`俗`", py)
      py = re.sub("\[(.*?)\]", "\\1`替`", py)
      unicodes[i]["nan_tw"] = py
log("閩南")

#nan_lz
lzs = ["dbls", "ldzz", "lz", "wcls"]
tones = [
  {'33':1,'22':2,'31':3,'42':4,'44':5,'53':6,'453':7,'5':8,'2':9},
  {'45':1,'55':2,'24':3,'22':4,'21':5,'451':6,'443':7,'31':8,'5':9,'2':10},
  {'24':1,'22':2,'41':3,'33':4,'21':5,'453':6,'5':7,'2':8},
  {'33':1,'22':2,'31':3,'42':4,'44':5,'453':6,'5':7,'2':8},
]
for index,lz in enumerate(lzs):
  d.clear()
  for line in open("粤西闽语方言字表2.2（繁体）.tsv"):
    fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
    if len(fs) < 6: continue
    hz = fs[0]
    ybs = fs[2 + index]
    if not ybs or ybs.startswith("—") or hz == "例字": continue
    zs = "`%s`"%hz[1:] if len(hz)>1 else ""
    hz = hz[0]
    for yb in ybs.split("/"):
      yb = yb.strip()
      sd = re.findall("\d+", yb)[0]
      if sd not in tones[index]: continue
      js = yb.replace(sd, str(tones[index][sd])) + zs
      js = re.sub("[（）]", "`", js)
      if js not in d[hz]:
        d[hz].append(js)
  update("nan_lz_" + lz, d)
log("粤西閩語")

#pn
d.clear()
tones = {'54':8,'53':3,'44':2,'32':7,'311':6,'223':1,'21':5,'213':4}
for line in open("普宁2.2.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,yb,zs,sm,ym,sd = fs[:6]
  if not yb or len(hz) != 1: continue
  if sd: sd = str(tones[sd])
  if hz in "?？": hz = "□"
  yb = sm + ym + sd
  js = yb + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("nan_cs_pn", d)
log("普寧")

#cz
d.clear()
for line in open("方言调查字表 1.4（潮州）(3600字).tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  if len(fs) < 4: continue
  hz,py,yb,zs = fs[:4]
  yb = yb.replace(' ', '')
  if not yb: continue
  sd = py[-1]
  if not sd.isdigit():
    sd = ""
  if len(hz) == 1:
    yb = yb.rstrip("˩˨˧˦˥0") + sd
    js = yb + ("`%s`"% zs if zs else "")
    if js not in d[hz]:
      d[hz].append(js)
update("nan_cs_cz", d)
log("潮州")

#nan_st
d.clear()
for line in open("方言调查字表2.9 （汕头）(3600字).tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  if len(fs) < 4: continue
  hz,py,yb,zs = fs[:4]
  yb = yb.replace(' ', '')
  if not yb: continue
  sd = py[-1]
  if not sd.isdigit():
    sd = ""
  if len(hz) == 1:
    yb = yb.rstrip("˩˨˧˦˥0") + sd
    js = yb + ("`%s`"% zs if zs else "")
    if js not in d[hz]:
      d[hz].append(js)
update("nan_cs_st", d)
log("汕頭")

#nan_cs_rp
d.clear()
for line in open("方言调查字表（闽-饶平）2.4.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,py,yb,zs = fs[:4]
  if not yb: continue
  sd = py[-1]
  if not sd.isdigit():
    sd = ""
  if len(hz) == 1:
    yb = yb.rstrip("˩˨˧˦˥0") + sd
    js = yb + ("`%s`"% zs if zs else "")
    if js not in d[hz]:
      d[hz].append(js)
update("nan_cs_rp", d)
log("饒平")

#nan_cs_rpxf
d.clear()
for line in open("方言调查字表（闽-饶平新丰）1.4.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,py,yb,zs = fs[:4]
  if not yb: continue
  sd = py[-1]
  if not sd.isdigit():
    sd = ""
  if len(hz) == 1:
    yb = yb.rstrip("˩˨˧˦˥0") + sd
    js = yb + ("`%s`"% zs if zs else "")
    if js not in d[hz]:
      d[hz].append(js)
update("nan_cs_rpxf", d)
log("饒平新豐")

#nan_cs_hllj
tones = {'阳入':8,'阴上':3,'阳平':2,'阴入':7,'阴平':1,'去声':5,'阳上':4}
d.clear()
for line in open("惠来隆江字表1.04.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  order,hz,jt,yb,zs = fs[:5]
  if not yb or len(hz) != 1: continue
  for i in tones:
      if i in yb:
          yb = yb.replace(i, str(tones[i]))
          break
  js = yb + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("nan_cs_hllj", d)
log("惠來隆江")

#cy
d.clear()
sms = {'p':'p',
'ph':'pʰ',
'b':'b',
'm':'m',
'pf':'pf',
'pfh':'pfʰ',
'bv':'bv',
't':'t',
'th':'tʰ',
'l':'l',
'n':'n',
'ts':'ts',
'tsh':'tsʰ',
'dz':'dz',
's':'s',
'k':'k',
'kh':'kʰ',
'g':'g',
'ng':'ŋ',
'h':'h',
'':''
}
yms = {
'i':'i',
'u':'u',
'a':'a',
'ia':'ia',
'ua':'ua',
'o':'o',
'io':'io',
'e':'e',
'ue':'ue',
'ui':'ui',
'ai':'ai',
'uai':'uai',
'oi':'oi',
'iu':'iu',
'au':'au',
'iau':'iau',
'ou':'ou',
'im':'im',
'am':'am',
'iam':'iam',
'uam':'uam',
'om':'om',
'ing':'iŋ',
'ung':'uŋ',
'ang':'aŋ',
'iang':'iaŋ',
'uang':'uaŋ',
'ong':'oŋ',
'iong':'ioŋ',
'eng':'eŋ',
'ueng':'ueŋ',
'ip':'ip',
'ap':'ap',
'iap':'iap',
'uap':'uap',
'op':'op',
'ik':'ik',
'uk':'uk',
'ak':'ak',
'iak':'iak',
'uak':'uak',
'ok':'ok',
'iok':'iok',
'ek':'ek',
'uek':'uek',
'inn':'ĩ',
'ann':'ã',
'iann':'iã',
'uann':'uã',
'onn':'õ',
'ionn':'iõ',
'enn':'ẽ',
'uenn':'uẽ',
'uinn':'uĩ',
'ainn':'aĩ',
'uainn':'uaĩ',
'oinn':'oĩ',
'iunn':'iũ',
'aunn':'aũ',
'iaunn':'iaũ',
'ounn':'oũ',
'ih':'iʔ',
'uh':'uʔ',
'ah':'aʔ',
'iah':'iaʔ',
'uah':'uaʔ',
'oh':'oʔ',
'ioh':'ioʔ',
'eh':'eʔ',
'ueh':'ueʔ',
'oih':'oiʔ',
'iuh':'iuʔ',
'auh':'auʔ',
'iauh':'iauʔ',
'annh':'ãʔ',
'uannh':'uãʔ',
'iaunnh':'iaũʔ',
'ɿ':'ɿ',
'm':'m',
'ng':'ŋ',
'ək':'ək',
'aannp':'ãːp',
'annp':'ãp',
'uei':'uei',
'':''
}
for line in open("潮阳话字表1.0.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  order,hz,zs,yb,sm,ym,sd = fs[:7]
  if len(hz) != 1: continue
  ym = ym.rstrip("12345678")
  sd = sd.strip()
  yb = sms[sm] + yms[ym] + sd
  js = yb + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("nan_cs_cy", d)
log("潮陽")

#cdo_nd
tones = {'陽入':8,'上':3,'陽平':2,'陰入':7,'陽去':6,'陰平':1,'陰去':5}
d.clear()
for line in open("闽东宁德方言字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,jt,yb,sd,zs = fs
  if not yb or len(hz) != 1: continue
  yb = yb + str(tones[sd.split("|")[1]])
  js = yb + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("cdo_nd", d)
log("寧德")

#cdo_cnqk
d.clear()
for line in open("钱库蛮话.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  sm,ym,sd,hz,zs = fs[:5]
  if sm == "声母" or len(hz) != 1: continue
  if sm == "零": sm = ""
  yb = sm + ym + sd
  js = yb + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("cdo_cnqk", d)
log("蒼南錢庫")

#hak
#https://github.com/syndict/hakka/blob/master/hakka.dict.yaml
hktones = {"⁴⁴":"1", "³³": "1", "¹¹":"2", "³¹":"3", "¹³":"4", "⁵²":"5", "⁵³":"5", "²¹":"6", "¹":"7", "⁵":"8", "³":"8"}
sxtones = {"²⁴":"1", "¹¹": "2", "³¹":"3", "⁵³":"3", "⁵⁵":"5", "²":"7", "⁵":"8"}
hltones = {"⁵³":"1", "⁵⁵": "2", "²⁴":"3", "¹¹":"5", "³³":"6", "⁵":"7", "²":"8"}
def hk2ipa(s, tones):
  c = s[-1]
  if c in "文白":
    s = s[:-1]
  else:
    c = ""
  s = s.replace("er","ə").replace("ae","æ").replace("ii", "ɿ").replace("e", "ɛ").replace("o", "ɔ")
  s = s.replace("sl", "ɬ").replace("nj", "ɲ").replace("t", "tʰ").replace("zh", "tʃ").replace("ch", "tʃʰ").replace("sh", "ʃ").replace("p", "pʰ").replace("k", "kʰ").replace("z", "ts").replace("c", "tsʰ").replace("j", "tɕ").replace("q", "tɕʰ").replace("x", "ɕ").replace("rh", "ʒ").replace("r", "ʒ").replace("ng", "ŋ").replace("?", "ʔ").replace("b", "p").replace("d", "t").replace("g", "k")
  tone = re.findall("[¹²³⁴⁵\d]+$", s)
  if tone:
    tone = tone[0]
    s = s.replace(tone, tones[tone])
  if c == "文" or c == "白":
    s = "%s`%s`"%(s,c)
  return s

#https://github.com/g0v/moedict-data-hakka/blob/master/dict-hakka.json
tk = json.load(open("dict-hakka.json"))
d.clear()
for line in tk:
    hz = line["title"]
    heteronyms = line["heteronyms"]
    if len(hz) == 1:
      for i in heteronyms:
        pys = i["pinyin"]
        py = re.findall("海⃞(.+?)\\b", pys)
        if py:
          d[hz].append(hk2ipa(py[0], hltones))
update("hak_hl", d)
d.clear()
for line in tk:
    hz = line["title"]
    heteronyms = line["heteronyms"]
    if len(hz) == 1:
      for i in heteronyms:
        pys = i["pinyin"]
        py = re.findall("四⃞(.+?)\\b", pys)
        if py:
          d[hz].append(hk2ipa(py[0], sxtones))
update("hak_sx", d)
log("客家")

#hak_whhb
d.clear()
tones = {'44':1,'13':2,'31':3,'53':5,'1':7,'5':8}
for line in open("五华横陂客家方言字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  hz,yb,sd,zs = fs[:4]
  if not yb or len(hz) != 1: continue
  sd = str(tones.get(sd))
  js = yb + sd + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("hak_whhb", d)
log("五華橫陂")

#hak_whsz
d.clear()
tones = {'44':1,'13':2,'31':3,'53':5,'2':7,'4':8}
for line in open("五华水寨客家话字表.tsv"):
  fs = [i.strip('" ') for i in line.strip('\n').split('\t')]
  yb,hz,zs = fs[:3]
  if not yb or len(hz) != 1: continue
  dz = re.findall("\d+$", yb)[0]
  yb = yb[:-len(dz)]
  sd = str(tones.get(dz))
  js = yb + sd + ("`%s`"% zs if zs else "")
  if js not in d[hz]:
    d[hz].append(js)
update("hak_whsz", d)
log("五華水寨")

#nc
readings = "白文又"
d.clear()
def get_readings(index):
  if not index: return ''
  return "`%s`"%readings[int(index)-1]
def readorder(py):
  index = readings.index(py[-2])+1 if py.endswith('`') else 0
  return "%d%s"%(index,py)
def sub(m):
  ret = ''
  for i in m.group(1):
    if i in "12345":continue
    ret += i + m.group(2)
  return ret
for line in open("nc"):
  line = line.strip().replace(" ", "").replace("(", "（").replace(")","）")
  if line.startswith("#") or not line: continue
  line = re.sub('（(.*?)）(\d)', sub, line)
  fs = re.findall("^([^\u3400-\U0003134f]+ ?)(.*)$", line)[0]
  py, hzs = fs
  if not hzs: continue
  for hz,r in re.findall("(.)(\d?)", hzs):
    item = py+get_readings(r)
    if item not in d[hz]:
      d[hz].append(item)
    if py.endswith('k7') or py.endswith('k8'):
      item = re.sub('k([78])', 'ʔ\\1', py)+get_readings('3')
      if item not in d[hz]:
        d[hz].append(item)
for hz in d:
  d[hz] = sorted(d[hz], key=readorder)
update("gan_nc", d)
log("南昌")

#lc
d.clear()
for line in open("臨川上頓渡同音字彙.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if line.startswith("#"):
    ym = line[1:].strip()
  else:
    fs = line.split("\t")
    sm = fs[0].replace("Ø", "")
    for sd,hzs,n in re.findall("［(\d)］(.*?)((?=［)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)([+-=*/?]?)(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("gan_lcsdd", d)
log("臨川上頓渡")

#gayx
d.clear()
for line in open("高安楊墟同音字彙.tsv"):
  line = line.strip().replace('"','')
  if line.startswith("#"):
    ym = line[1:].strip()
  else:
    fs = line.split("\t")
    sm = fs[0].replace("∅", "")
    for sd,hzs,n in re.findall("［(\d)］(.*?)((?=［)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)([+-=*/?]?)(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("gan_gayx", d)
log("高安楊墟")

#ygyt
d.clear()
for line in open("餘干玉亭同音字彙.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  if line.startswith("#"):
    ym = line[1:].strip()
  else:
    fs = line.split("\t")
    sm = fs[0].replace("∅", "")
    for sd,hzs,n in re.findall("［(\d)］(.*?)((?=［)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)([+-=*/?]?)(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("gan_ygyt", d)
log("餘干玉亭")

#cs
d.clear()
for line in open("長沙話字表 1.1.2.tsv"):
  line = line.strip('\n').replace('"','')
  fs = line.split("\t")
  yb, sd, hz, zs = fs[5:]
  hz = hz.strip()
  if len(hz) != 1: continue
  py = yb + str(ord(sd) - ord('①') + 1)
  if zs:
    py = "%s`%s`" % (py, zs)
  if py not in d[hz]:
    d[hz].append(py)  
update("hsn_cs", d)
log("長沙")

#nshu
d.clear()
tones = ['44','42','35','13','21','33','5']
for line in open("unicode_nushu_data.csv"):
  line = line.strip()
  fs = line.split(",")
  ns = fs[0]
  if len(ns) != 1: continue
  hzs = fs[2]
  py = fs[3]
  py = re.sub("^h", "x", py)
  py = py.replace("nj", "ȵ").replace('ng', 'ŋ').replace("c", "ɕ").replace('h', 'ʰ')
  py = py.replace("oe", "ø").replace('e', 'ə').replace('iə', 'ie').replace('w', 'ɯ')
  tone = re.findall('\d+', py)[0]
  tonetype = str(tones.index(tone)+1)
  py = py.replace(tone, tonetype)
  for hz in hzs:
    d[hz].append("%s%s"%(py,ns))
tones = ['33','42','35','13','21','xx','5']
for line in open("nsbzzzd.csv"):
  line = line.strip()
  fs = line.split(",")
  ns = fs[0]
  if not ns.isdigit(): continue
  hzs = fs[2]
  py = fs[1]
  tone = re.findall('\d+', py)[0]
  tonetype = str(tones.index(tone)+1)
  py = py.replace(tone, tonetype)
  py = py.replace("yueng", "yun").replace("yiong", "ing")
  py = re.sub("^y([^iu])", "i\\1", py)
  py = py.replace('yu', 'y').replace('yiu', 'yu').replace('yi', 'i')
  py = re.sub('([jqx])u', '\\1y', py)
  py = re.sub('([jqx])iu', '\\1yu', py)
  py = re.sub('([jqx])ou', '\\1iou', py)
  py = py.replace("nj", "ȵ").replace('ng', 'ŋ')
  py = py.replace("p", "pʰ").replace('b', 'p')
  py = py.replace("t", "tʰ").replace('d', 't')
  py = py.replace("k", "kʰ").replace('g', 'k')
  py = py.replace("c", "tsʰ").replace('z', 'ts')
  py = py.replace("q", "tɕʰ").replace('j', 'tɕ').replace('x', 'ɕ').replace('h', 'x').replace('w', 'v')
  py = py.replace('ao', 'au').replace('e', 'ə').replace('iə', 'ie')
  py = re.sub('o(\d)', 'ø\\1', py)
  py += "`%s`"%ns
  for hz in hzs:
    d[hz].append(py)
update("hsn_nshu", d)
log("女書")

#jo
d.clear()
tones = {"平聲54": 1, "上聲21": 3, "陰去33": 5, "陽去44": 6, "陰入24": 7, "陽入42": 8}
for line in open("建甌同音字彙.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[:3]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("mnp_jo", d)
log("建甌")

#hz
d.clear()
tones = {"陰平33": 1, "陽平213": 2, "陰上53": 3, "陰去445": 5, "陽去13": 6, "陰入5": 7, "陽入2": 8}
for line in open("杭州.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[1:4]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("wuu_hz", d)
log("杭州")

#jn
d.clear()
tones = {"陰平213": 1, "陽平42": 2, "上聲55": 3, "去聲21": 5, "輕聲": ''}
for line in open("濟南.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[1:4]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("cmn_jil_jn", d)
log("濟南")

#xa
d.clear()
tones = {"陰平21": 1, "陽平24": 2, "上聲53": 3, "去聲44": 5}
for line in open("西安.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[1:4]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("cmn_zho_xa", d)
log("西安")

#xt
d.clear()
tones = {"陰平33": 1, "陽平12": 2, "上聲42": 3, "陰去55": 5, "陽去21": 6, "入聲24": 7}
for line in open("湘潭.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[1:4]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("hsn_xt", d)
log("湘潭")

#wh
d.clear()
tones = {"陰平55": 1, "陽平213": 2, "上聲42": 3, "去聲35": 5}
for line in open("武漢.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[1:4]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("cmn_xn_hg_wh", d)
log("武漢")

#ty
d.clear()
tones = {"平聲11": 1, "上聲53": 3, "去聲45": 5, "陰入2": 7, "陽入54": 8}
for line in open("太原.tsv"):
  line = line.strip('\n').replace('"','').replace(' ','')
  fs = line.split("\t")
  sy, sd, zy = fs[1:4]
  if zy == "字元": continue
  py = sy + str(tones[sd])
  for hz in zy.split(","):
    if not hz: continue
    if py not in d[hz]:
      d[hz].append(py)  
update("cjy_bz_ty", d)
log("太原")

#glps
d.clear()
for line in open("桂林平山土话同音字表.tsv"):
  line = line.strip().replace('"','').replace(' ','')
  if not line: continue
  if line.startswith("#"):
    ym = line[1:].split()[0]
  else:
    fs = line.split("\t")
    sm = fs[0].replace("Ø", "")
    if len(fs) < 2: continue
    for sd,hzs,n in re.findall("\[(\d)\](.*?)((?=\[)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)\d?([+-=*/?]?)\d?(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '+':
            p = "又"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '/':
            p = "书"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + "：" + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("xxx_glps", d)
log("桂林平山")

#czh_qw_fljc
d.clear()
for line in open("浮梁舊城同音字彙.tsv"):
  line = line.strip('\n').replace('"','')
  if line.startswith("#"):
    ym = line[1:].strip()
  else:
    fs = line.split("\t")
    sm = fs[0].replace("∅", "")
    for sd,hzs,n in re.findall("［(\d)］(.*?)((?=［)|$)", fs[1]):
      py = sm + ym +sd
      hzs = re.findall("(.)([+-=*/?]?)(\{.*?\})?", hzs)
      for hz, c, m in hzs:
        m = m.strip("{}")
        p = ""
        if c and c in '-+=*?':
          if c == '-':
            p = "白"
          elif c == '=':
            p = "文"
          elif c == '*':
            p = "俗"
          elif c == '?':
            p = "待考"
        if p and m:
          p = p + " " + m
        else:
          p = p + m
        if p:
          p = "`%s`" % p
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
update("czh_qw_fljc", d)
log("浮梁舊城")

#cacc
d.clear()
for line in open("淳安淳城同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym +sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("czh_yz_cacc", d)
log("淳安淳城")

#jdmc
d.clear()
for line in open("建德梅城白读1.1.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym +sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          if c == '-':
            d[hz].insert(0, p)
          else:
            d[hz].append(p)
for line in open("建德梅城文读.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      if sd in "1236": sd = "1" + sd
      py = sm + ym +sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`文读。%s`" % m
        else:
          p = "`文`"
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("czh_yz_jdmc", d)
log("建德梅城")

#jdsc
d.clear()
for line in open("建德寿昌白读1.1.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+[ab]?)\]([^\[\]]+)", fs[1]):
      if sd == "7a": sd = "7"
      elif sd == "7b": sd = "9"
      elif sd == "0": sd = ""
      py = sm + ym +sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
for line in open("建德寿昌文读.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      if sd.isdigit(): sd = "1" + sd
      py = sm + ym +sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`文读。%s`" % m
        else:
          p = "`文`"
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("czh_yz_jdsc", d)
log("建德壽昌")

#sasc
d.clear()
for line in open("遂安狮城同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) != 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+)\]([^\[\]]+)", fs[1]):
      py = sm + ym + sd
      hzm = re.findall("(.)\d?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("czh_yz_sasc", d)
log("遂安獅城")

#lxcsh
d.clear()
tones = {"1b": "11", "3b": "13", "5b":"15", "8b":"18", "7a":"7", "7b":"9"}
for line in open("兰溪船上话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+[ab]?)\]([^\[\]]+)", fs[1]):
      py = sm + ym + tones.get(sd, sd)
      hzm = re.findall("(.)\d?=?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("czh_yz_lxcsh", d)
log("蘭溪船上話")

#txcsh
d.clear()
tones = {"1b": "11", "2b": "12", "3b": "13", "5b":"15", "6b":"16"}
for line in open("屯溪船上话同音字表.tsv"):
  line = line.strip('\n')
  fs = [i.strip('" ') for i in line.split('\t')]
  if not fs: continue
  if fs[0].startswith("#"):
    ym = fs[0][1:]
  else:
    if len(fs) < 2: continue
    sm = fs[0].replace("Ø", "")
    for sd,hzs in re.findall("\[(\d+[ab]?)\]([^\[\]]+)", fs[1]):
      py = sm + ym + tones.get(sd, sd)
      hzm = re.findall("(.)\d?=?(\{.*?\})?", hzs)
      for hz, m in hzm:
        m = m.strip("{}")
        p = ""
        if m:
          p = "`%s`" % m
        p = py + p
        if p not in d[hz]:
          d[hz].append(p)
update("czh_txcsh", d)
log("屯溪船上話")

#ko
#https://github.com/nk2028/sino-korean-readings/blob/main/woosun-sin.csv
d.clear()
for line in open("woosun-sin.csv"):
  fs = line.strip().split(',')
  hz = fs[0]
  if len(hz) == 1:
    py = "".join(fs[1:4])
    if py not in d[hz]:
      d[hz].append(py)
update("ko_okm", d)
log("中世朝鮮")

#patch
patch = ruamel.yaml.load(open("patch.yaml"), Loader=ruamel.yaml.Loader)
for lang in patch:
  for hz in patch[lang]:
    for i in hz:
      if i not in unicodes:
        unicodes[i]["hz"] = i
      unicodes[i][lang] = patch[lang][hz]
log("修正", None)

#sw
d.clear()
for line in open("shuowen.tsv"):
  fs = line.strip().split('\t', 1)
  hz = fs[0]
  js = fs[1].replace("\t", "\n").strip()
  d[hz].append(js)
update("sw", d)
log("說文解字")

#kx
d.clear()
for line in open("kangxizidian-v3f.txt"):
  fs = line.strip().split('\t\t')
  hz = fs[0]
  if len(hz) == 1:
    js = fs[1].replace("", "\n").strip()[6:]
    js = re.sub("頁(\d+)第(\d+)\n", lambda x: "%04d.%d"%(int(x[1]),int(x[2])), js)
    d[hz].append(js)
update("kx", d)
log("康熙字典")

#hd
d.clear()
hd=defaultdict(dict)
numbers="❶❷❸❹❺❻❼❽❾❿⓫⓬⓭⓮⓯⓰⓱⓲⓳⓴㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
pages = dict()
for line in open("handa.txt"):
  line = line.strip('\n')
  fs = line.split('\t')
  if len(fs[0]) == 1:
    hz,py,js,page = fs[:4]
    if hz in kCompatibilityVariants and js.startswith("同"): continue
    pages[hz] = page
    if py == "None":
        py = ""
    if py in hd[hz]:
      hd[hz][py].append(js)
    else:
      hd[hz][py] = [js]
for hz in hd:
  for py in hd[hz]:
    if len(hd[hz][py])!=1:
      hd[hz][py] = [numbers[count]+js for count,js in enumerate(hd[hz][py])]
for hz in hd:
  js = "\n\n".join(["%s\n%s" % (py, "\n".join(hd[hz][py])) for py in hd[hz]])
  js = re.sub("=(.)", "“\\1”", js).strip()
  d[hz] = ["%s\n%s"%(pages[hz], js)]
update("hd", d)
log("漢語大字典")

#bh
d.clear()
for line in open("/usr/share/unicode/Unihan_IRGSources.txt"):
    if not line.startswith("U"): continue
    fields = line.strip().split("\t", 2)
    han, typ, val = fields
    if typ == "kTotalStrokes":
      han = hex2chr(han)
      d[han].append(val)
update("bh", d)
log("總畫數")

#bs
bs = dict()
for line in open("/usr/share/unicode/CJKRadicals.txt"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    fields = line.split("; ", 2)
    order, radical, han = fields
    han = hex2chr(han)
    bs[order] = han
d.clear()
for line in open("/usr/share/unicode/Unihan_IRGSources.txt"):
    if not line.startswith("U"): continue
    fields = line.strip().split("\t", 2)
    han, typ, vals = fields
    if typ != "kRSUnicode": continue
    han = hex2chr(han)
    for val in vals.split(" "):
      fs = val.split(".")
      order, left = fs
      left = left.replace('-', 'f')
      d[han].append(bs[order]+left)
update("bs", d)
log("部首檢字")

#variant
variants = variant.get()
for i in list(unicodes.keys()):
  vad = unicodes[i]
  if i in variants:
    vad["va"] = " ".join(variants.get(i, i))
log("異體字")

#cj
d.clear()
for line in open("cj3.txt"):
  line = line.strip()
  if not line or " " not in line or "=" in line: continue
  fs = line.split(" ")
  cj = fs[0]
  hz = fs[-1]
  if ishz(hz):
    d[hz].append(cj)
update("cj3", d)

d.clear()
for line in open("Cangjie5.txt"):
  line = line.strip()
  if not line or "\t" not in line: continue
  fs = line.split("\t")
  cj = fs[1]
  hz = fs[0]
  if ishz(hz):
    d[hz].append(cj)
update("cj5", d)

d.clear()
for line in open("cangjie6.dict.yaml"):
  line = line.strip()
  if not line or "\t" not in line: continue
  fs = line.split("\t")
  cj = fs[1]
  hz = fs[0]
  if ishz(hz):
    d[hz].append(cj)
update("cj6", d)
log("仓頡")

#wb
d.clear()
for line in open("wb.csv"):
  line = line.strip()
  fs = line.split(",")
  hz = fs[1]
  wb = fs[2]
  if ishz(hz):
    d[hz].append(wb)
update("wb86", d)

d.clear()
for line in open("wb.csv"):
  line = line.strip()
  fs = line.split(",")
  hz = fs[1]
  wb = fs[3]
  if ishz(hz):
    d[hz].append(wb)
update("wb98", d)

d.clear()
for line in open("wb.csv"):
  line = line.strip()
  fs = line.split(",")
  hz = fs[1]
  wb = fs[4]
  if ishz(hz):
    d[hz].append(wb)
update("wb06", d)

d.clear()
for line in open("wb.csv"):
  line = line.strip()
  fs = line.split(",")
  hz = fs[1]
  wb = fs[5]
  if ishz(hz):
    d[hz].append(wb)
update("wbh", d)
log("五筆")

#lf
d.clear()
for line in open("liangfen.dict.yaml"):
  line = line.strip()
  if not line or "\t" not in line: continue
  fs = line.split("\t")
  lf = fs[1]
  hz = fs[0]
  if ishz(hz):
    d[hz].append(lf)
for line in open("lfzy.tsv"):
  line = line.strip()
  fs = line.split("\t")
  lf = fs[1]
  hz = fs[0]
  if ishz(hz):
    if "(" in lf:
      if " " in lf:
        a,b=lf.split(" ")
        for i in a.strip(")").split("("):
          for j in b.strip(")").split("("):
            d[hz].append(i+j)
      else:
        for j in b.strip(")").split("("):
          d[hz].append(j)
    else:
      lf = lf.replace(" ", "")
      d[hz].append(lf)
update("lf", d)
log("兩分")

#fl
d.clear()
for line in open("/usr/share/unicode/Unihan_OtherMappings.txt"):
  if not line.startswith("U"): continue
  han, typ, val = line.strip().split("\t", 2)
  han = hex2chr(han)
  if typ == "kTGH":
    order = int(val.split(":")[1])
    if order <= 3500: level = 1
    elif order <= 6500: level = 2
    else: level = 3
    d[han].append("%s%d"%(typ, level))
  elif typ in ("kGB0", "kBigFive"):
    d[han].append(typ)
for line in open("/usr/share/unicode/Unihan_DictionaryLikeData.txt"):
  if not line.startswith("U"): continue
  han, typ, val = line.strip().split("\t", 2)
  if typ == "kHKGlyph":
    han = hex2chr(han)
    d[han].append(typ)
for line in open("/usr/share/unicode/Unihan_IRGSources.txt"):
  if not line.startswith("U"): continue
  han, typ, val = line.strip().split("\t", 2)
  if typ == "kIRG_TSource" and val.startswith("T1-"):
    han = hex2chr(han)
    d[han].append("T1")
for line in open("方言調查字表"):
  han = line.strip()
  if han:
    d[han].append("FD")
update("fl", d)
log("分類")

#filter
for i in sorted(unicodes.keys()):
  n = ord(i)
  if not(ishz(i)):
    print(i, unicodes[i])
    unicodes.pop(i)

#stat
counts = dict()
dialects = 0
for lang in KEYS:
  count = 0
  if "_" in lang: dialects += 1
  for i in unicodes:
    if unicodes[i].get(lang, None): count+=1
    elif lang == "ja_tou": #所有日語音
      if unicodes[i].get("ja_go", None)\
          or unicodes[i].get("ja_kan", None)\
          or unicodes[i].get("ja_kwan", None)\
          or unicodes[i].get("ja_other", None):
          count+=1
  counts[lang] = count
ZHEADS[6] = list(ZHEADS[6])
for i,lang in enumerate(KEYS):
    desc = ZHEADS[6][i]
    ZHEADS[6][i]="收字：%d個<br>%s"%(counts[lang], desc if desc else "")
    if i == 0:
      ZHEADS[6][i]= "語言：%d個<br>%s"%(dialects,ZHEADS[6][i])

#all hz readings
def cjkorder(s):
  n = ord(s)
  return n + 0x10000 if n < 0x4E00 else n

NAME='../app/src/main/assets/databases/mcpdict.db'
os.remove(NAME)
conn = sqlite3.connect(NAME)
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS mcpdict")
c.execute("CREATE VIRTUAL TABLE mcpdict USING fts3 (%s)"%FIELDS)
c.executemany(INSERT, ZHEADS[1:])

for i in sorted(unicodes.keys(), key=cjkorder):
  d = unicodes[i]
  v = list(map(d.get, KEYS))
  c.execute(INSERT, v)

conn.commit()
conn.close()
log("保存", None)
log("耗時", unicodes, time() - start0)
