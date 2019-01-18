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


class LiquSpider(scrapy.Spider):
    name = 'liqu'
    allowed_domains = ['liqucn.com']
    start_urls = ['https://www.liqucn.com/rj/', 'https://www.liqucn.com/yx/'];
    TRY_NUM = 3;

    def __init__(self, *a, **kw):
        super(LiquSpider, self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity=10000000);

    def start_requests(self):
        for url in self.start_urls:
            self.bf.add(url);
            yield Request(
                url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter=True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser').select('.sift')[0];
        catepattern = re.compile(ur'/c/[0-9]+');
        print(response.url);
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if catepattern.search(href) == None:
                continue;
            if href in self.bf:
                continue;
            self.bf.add(href);
            if href.find(response.url) == -1:
                continue;
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {'category': href},
                callback = self.parse_category
            );


    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        pagesoup = soup.select('.page')[0];
        appsoup = soup.select('.tip_blist')[0];
        androidpattern = re.compile(ur'android');
        for aitem in pagesoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = response.meta['category'] + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {'category': response.meta['category']},
                callback = self.parse_category
            );
        for aitem in appsoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            if androidpattern.search(href) == None:
                continue;
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_detail
            );
        
    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        infosoup = soup.select('.info_box')[0];
        versionpattern = re.compile(ur'[0-9\.]+');
        packagenamepattern = re.compile(ur'/[^/]*.apk');
        commonname = infosoup.select('h1')[0].get_text();
        version = versionpattern.search(commonname).group();
        metainfolist = infosoup.select('em');
        category = metainfolist[0].get_text();
        updatetime = metainfolist[1].get_text();
        size = metainfolist[3].get_text();
        developer = metainfolist[4].get_text();
        urllink = soup.select('.btn_android')[0]['href'];
        for i in range(0, self.TRY_NUM):
            if not urllink.find('.apk') == -1:
                break;
            proxy = Proxy(0,urllink);
            urllink = proxy.get_downloadaddress();
        idpattern = re.compile(ur'[0-9]+');
        apkid = idpattern.search(response.url).group();
        packagename = packagenamepattern.search(urllink).group()[1:-4];
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',self.name);
        item.add_value('apkid_specifiedbyplaform',apkid);
        item.add_value('category',category);
        item.add_value('developer',developer);
        item.add_value('packagename',packagename);
        item.add_value('updatetime',updatetime);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        yield item.load_item();

