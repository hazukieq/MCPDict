#!/usr/bin/env python3

from tables._希 import 字表 as 表

class 字表(表):
	key = "cmn_xn_xs_mc_qjgn"
	note = "來源：由播州東條希整理自《綦江方言音系調查研究》 2011 黃雅婷 及《永川等六区县方言语音调查研究》2018 萬霞，並有所增補"
	tones = "35 1 1a 陰平 ꜀,31 2 1b 陽平 ꜁,42 3 2 上 ꜂,,112 5 3 去 ꜄,,3 7 4 入 ꜆"
	_file = "*溱州新韻*.tsv"
	toneValues = {"˧˥": 1, "˧˩": 2, "˦˨": 3, "˩˩˨": 5, "˧": 7, "": ""}

