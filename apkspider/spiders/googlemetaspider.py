# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import time;

class GooglemetaspiderSpider(CrawlSpider):
    name = 'googlemetaspider'
    allowed_domains = ['play.google.com/store/apps']
    start_urls = ['https://play.google.com/store/apps/category/FOOD_AND_DRINK']

    '''custom_settings = { 
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': '5688_log_%s.txt' % time.time(),
        "DEFAULT_REQUEST_HEADERS": 
            { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36' }
    };'''

    rules = (
        Rule(LinkExtractor(allow='https://play.google.com/store/apps/category/FOOD_AND_DRINK'), callback='parse_main', follow=True),
    )


    def parse_main(self, response):
        i = {}
        #i['domain_id'] = response.xpath('//input[@id="sid"]/@value').extract()
        #i['name'] = response.xpath('//div[@id="name"]').extract()
        #i['description'] = response.xpath('//div[@id="description"]').extract()
        print(123);
        print(response.url);
        return i
