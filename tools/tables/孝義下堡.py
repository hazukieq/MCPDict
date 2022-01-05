#!/usr/bin/env python3

from tables._縣志 import 字表 as 表

class 字表(表):
	key = "cjy_ll_xyxb"
	_file = "孝义下堡*.tsv"
	note = "版本：2021-12-31<br>來源：管文慧 2018《孝義下堡方言語音研究》Hynuza 整理"
	tones = "324 1 1a 陰平 ꜀,22 2 1b 陽平 ꜁,312 3 2 上 ꜂,,53 5 3 去 ꜄,,2 7 4a 陰入 ꜆,312 8 4b 陽入 ꜇"
	simplified = 2
