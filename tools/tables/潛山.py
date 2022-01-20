#!/usr/bin/env python3

from tables._縣志 import 字表 as 表

class 字表(表):
	key = "gan_hy_qs"
	note = "來源：《安徽潛山梅城方言語音研究》，“空島。”整理修改"
	tones = "42 1 1a 陰平 ꜀,35 2 1b 陽平 ꜁,324 3 2 上 ꜂,,54 5 3a 陰去 ꜄,33 6 3b 陽去 ꜅"
	_file = "安徽省潜山方言同音字表*.tsv"
	simplified = 2

	def format(self, line):
		line = line.replace("*", "□")
		return line
