#!/usr/bin/env python3

import re, json
from collections import defaultdict
from tables._表 import 表

toneValues = {"⁵³":"1", "⁵⁵": "2", "²⁴":"3", "¹¹":"5", "³³":"6", "⁵":"7", "²":"8"}
def py2yb(s, tones):
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
	if c == "文":
		s+="="
	elif c == "白":
		s += "-"
	return s
  
class 字表(表):
	key = "hak_hl"
	_lang = "海陸腔客語"
	#https://github.com/g0v/moedict-data-hakka/blob/master/dict-hakka.json
	_file = "dict-hakka.json"
	note = "來源：<a href=https://www.moedict.tw/>客語萌典</a>"
	site = "客語萌典"
	url = "https://www.moedict.tw/:%s"
	tones = "53 1 1a 陰平 ꜀,55 2 1b 陽平 ꜁,24 3 2 上 ꜂,,11 5 3a 陰去 ꜄,33 6 3b 陽去 ꜅,5 7 4a 陰入 ꜆,2 8 4b 陽入 ꜇"

	def update(self):
		d = defaultdict(list)
		tk = json.load(open(self.spath))
		for line in tk:
				hz = line["title"]
				heteronyms = line["heteronyms"]
				if len(hz) != 1: continue
				for i in heteronyms:
					pys = i["pinyin"]
					py = re.findall("海⃞(.+?)\\b", pys)
					if py and py[0]:
						yb = py2yb(py[0], toneValues).strip()
						if yb: d[hz].append(yb)
		self.write(d)

