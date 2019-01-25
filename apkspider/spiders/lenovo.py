# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request

import bs4
from pybloom_live import BloomFilter

import urlparse

import re
import json

from scrapy.loader import ItemLoader
from apkspider.items import ApkspiderItem

class LenovoSpider(scrapy.Spider):
    name = 'lenovo'
    allowed_domains = ['lenovomm.com']
    start_urls = ['https://www.lenovomm.com/apps/1038/0?type=1', 'https://www.lenovomm.com/apps/2397/0?type=2']

    custom_settings = {"CONCURRENT_REQUESTS": 3}
    base_url = 'https://www.lenovomm.com';

    def __init__(self, checkpoint = None, *a,**kw):
        super(LenovoSpider,self).__init__(*a,**kw);
        self.bf = BloomFilter(capacity=10000000);
        self.checkpoint = checkpoint;
        self.apkbf = BloomFilter(capacity=1000000000);
        if not checkpoint == None:
            fd = open(checkpoint,'r');
            while(True):
                line = fd.readline();
                if not line:
                    break;
                line = line.strip();
                self.apkbf.add(line);
            fd.close();
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter=True
            );

    def parse(self, response):
        pagepattern = re.compile(ur'p=[0-9]+');
        categorypattern = re.compile(ur'apps/[0-9]+/0');
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if not pagepattern.search(href) == None:
                continue;
            if categorypattern.search(href) == None:
                continue;
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_category
            );
        
    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        applist = soup.select('.list-wrapper')[0];
        category = soup.select('.active')[0].get_text();
        for aitem in applist.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href.find('appdetail') == -1:
                continue;
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {'category': category},
                callback = self.parse_detail
            );
        pagelist = soup.select('.page-wrapper')[0];
        for page in pagelist.find_all('a'):
            if page.get_text() == u'下一页':
                pagehref = self.base_url + page['href'];
                if pagehref in self.bf:
                    continue;
                self.bf.add(pagehref);
                yield Request(
                    url = pagehref,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback = self.parse_category
                );
            
            

    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        idpattern = re.compile(ur'[0-9]+');
        appinfo = soup.select('.app-info')[0];
        apknamepattern = re.compile(ur'appdetail/.*?/');
        commonname = appinfo.select('.title')[0].get_text();
        category = response.meta['category'];
        platform = self.name;
        sv = appinfo.select('.dec')[0].get_text().split('|');
        size = sv[0];
        version = sv[1];
        print(response.url);
        apkid = idpattern.search(response.url).group();
        print(apkid);
        packagename = apknamepattern.search(response.url).group()[10:-1];
        urllink = soup.select('.download')[0]['href'];
        if apkid in self.apkbf:
            return;
        self.apkbf.add(apkid);
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('apkid_specifiedbyplaform',apkid);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',platform);
        item.add_value('category',category);
        item.add_value('packagename',packagename);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        item.add_value('checkpoint',self.checkpoint);
        yield item.load_item();

