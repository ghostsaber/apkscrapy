# -*- coding: utf-8 -*-
import scrapy


class LenovonSpider(scrapy.Spider):
    name = 'lenovon'
    allowed_domains = ['lenovomm.com']
    start_urls = ['http://lenovomm.com/']

    def parse(self, response):
        pass
