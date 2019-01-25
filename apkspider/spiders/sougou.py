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


import pycurl

class Proxy(object):
    def __init__(self, apkid, downloadproxy):
        self.curl = pycurl.Curl();
        self.curl.setopt(pycurl.URL,downloadproxy);
        self.curl.setopt(pycurl.HEADERFUNCTION,self.process_header);
        self.downloadlink = '';

    def get_downloadaddress(self):
        self.curl.perform();
        return self.downloadlink;

    def process_header(self, buf):
        result = '';
        l = buf.strip();
        if l.startswith('Location'):
            print(l);
            l = l[l.find(':')+1:];
            result = l.strip();
            self.downloadlink = result;

class SougouSpider(scrapy.Spider):
    name = 'sougou'
    allowed_domains = ['zhushou.sogou.com']
    start_urls = ['http://zhushou.sogou.com/apps/']
    
    json_url = '%s?act=getapp&page=%d';
    download_url = 'http://zhushou.sogou.com/apps/download.html?appid=%d';

    def __init__(self, checkpoint=None, *a, **kw):
        super(SougouSpider, self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity = 10000000);
        self.checkpoint = checkpoint;
        self.apkbf = BloomFilter(capacity = 100000000);
        if not checkpoint == None:
            fd = open(checkpoint,'r');
            while True:
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
                url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter=True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        catesoup = soup.select('.catelist')[0];
        categorypattern = re.compile(ur'[0-9]+-0');
        for aitem in catesoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            if categorypattern.search(href) == None:
                continue;
            yield Request(
                url = self.json_url%(href, 1),
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta={'href':href, 'page':1},
                callback=self.parse_json
            );


    def parse_json(self, response):
        json_response = json.loads(response.body_as_unicode());
        if not json_response.has_key('data'):
            return;
        datalist = json_response['data'];
        if len(datalist) == 0:
            return;
        for appentity in datalist:
            if not appentity['type'] == 'app':
                continue;
            appid = appentity['app_id'];
            commonname = appentity['name'];
            packagename = appentity['packagename'];
            version = appentity['version'];
            url = appentity['url'];
            updatetime = appentity['date_modified'];
            size = appentity['size'];
            yield Request(
                url = url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = { 'appid' : appid, 'commonname' : commonname, 'packagename': packagename, 'version': version, 'updatetime':updatetime, 'size' : size},
                callback=self.parse_detail
            );


    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        appid = response.meta['appid'];
        commonname = response.meta['commonname'];
        packagename = response.meta['packagename'];
        version = response.meta['version'];
        size = response.meta['size'];
        updatetime = response.meta['updatetime'];
        infosoup = soup.select('.info')[0];
        developer = infosoup.select('td')[5].get_text();
        developer = developer[developer.find(ur'：')+1:].strip();
        category = infosoup.select('td')[6].get_text();
        category = category[category.find(ur'：')+1:].strip();
        yield Request(
            url = self.download_url%int(appid),
            headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
            meta = {'appid' : appid, 'commonname' : commonname, 'packagename': packagename, 'version': version, 'updatetime':updatetime, 'size' : size ,
                'developer':developer, 'category':category , 'url':response.url},
            callback=self.parse_download
        );

    def parse_download(self, response):
        json_response = json.loads(response.body_as_unicode());
        if not json_response['errno'] == 0:
            return;
        downloadurl = json_response['data']['file_url'];
        proxy = Proxy(0,downloadurl);
        downloadurl = proxy.get_downloadaddress();
        if response.meta['appid'] in self.apkbf:
            return;
        self.apkbf.add(response.meta['appid']);
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',response.meta['commonname']);
        item.add_value('apkplaform',self.name);
        item.add_value('apkid_specifiedbyplaform',response.meta['appid']);
        item.add_value('category',response.meta['category']);
        item.add_value('developer',response.meta['developer']);
        item.add_value('packagename',response.meta['packagename']);
        item.add_value('updatetime',response.meta['updatetime']);
        item.add_value('size',response.meta['size']);
        item.add_value('version',response.meta['version']);
        item.add_value('urllink',downloadurl);
        item.add_value('file_urls',downloadurl);
        item.add_value('checkpoint', self.checkpoint);
        yield item.load_item();
