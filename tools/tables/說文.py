#!/usr/bin/env python3

from tables._表 import 表

class 字表(表):
	key = "sw"
	_lang = "說文解字"
	site = "說文解字線上搜索"
	url = "http://www.shuowen.org/?kaishu=%s"
	note = "來源：<a href=https://github.com/shuowenjiezi/shuowen/>說文解字網站數據</a>"
	ybTrimSpace = False
	
	def parse(self, fs):
		return fs[0], "\t".join(fs[1:])
