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



class AppchinaSpider(scrapy.Spider):
    name = 'appchina'
    allowed_domains = ['appchina.com']
    start_urls = ['http://www.appchina.com/']
    
    base_url = 'http://www.appchina.com';

    def __init__(self, checkpoint=None, *a, **kw):
        super(AppchinaSpider, self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity=10000000);
        self.apkbf = BloomFilter(capacity=10000000);
        self.checkpoint = checkpoint;
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
            self.bf.add(url);
            yield Request(
                url = url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter = True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            if href.find('category') == -1:
                continue;
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_category
            );

    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        pagesoup = soup.select('.discuss_fangye')[0];
        appsoup = soup.select('.app-list')[0];
        for aitem in pagesoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_category
            );
        for aitem in appsoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_detail
            );



    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        print(response.url);
        urllinkpattern = re.compile(ur'\'.*\'');
        urllink = soup.select('.download_app')[0];
        if not urllink.has_attr('onclick') or urllink['onclick'] == 'return false;':
            return;
        urllink = urllink['onclick'];
        urllink = urllinkpattern.search(urllink).group()[1:-1];
        commonname = soup.select('.app-name')[0].get_text();
        detaillist = soup.select('.art-content');
        size = detaillist[2].get_text();
        size = size[size.find(u'：')+1:];
        version = detaillist[3].get_text();
        version = version[version.find(u'：')+1:];
        category = detaillist[6].get_text();
        category = category[category.find(u'：')+1:];
        packagename = response.url[response.url.rfind('/')+1:];
        permissionlist = list();
        permissions = soup.select('.permissions-list')[0].find_all('li');
        for perm in permissions:
            permissionlist.append(perm.get_text());
        if packagename in self.apkbf:
            return;
        self.apkbf.add(packagename);
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('apkid_specifiedbyplaform',packagename);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',self.name);
        item.add_value('category',category);
        item.add_value('packagename',packagename);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('permission',permissionlist);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        item.add_value('checkpoint',self.checkpoint);
        yield item.load_item();
            
