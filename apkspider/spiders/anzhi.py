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


class AnzhiSpider(scrapy.Spider):
    name = 'anzhi'
    allowed_domains = ['anzhi.com']
    start_urls = ['http://www.anzhi.com/widgetcatetag_1.html','http://www.anzhi.com/widgetcatetag_2.html'];
    custom_settings = {"CONCURRENT_REQUESTS": 3}
    base_url = 'http://www.anzhi.com';
    downloadgate = 'http://www.anzhi.com/dl_app.php?s=%d';

    def __init__(self, *a, **kw):
        super(AnzhiSpider, self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity = 10000000);
        self.downloadlink = dict();

    def start_requests(self):
        for url in self.start_urls:
            self.bf.add(url);
            yield Request(url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter=True
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
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_category
            );

    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        pagesoup = soup.select('.pagebars')[0];
        appsoup = soup.select('.app_list')[0].select('ul')[0];
        appitempattern = re.compile(ur'pkg');
        for aitem in pagesoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            #yield Request(
            #    url = href,
            #    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
            #    callback = self.parse_category
            #);
        for aitem in appsoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if appitempattern.search(href) == None:
                continue;
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_detail
            );
    

    def parse_detail(self, response):
        print(response.url);
        numpattern = re.compile(ur'[0-9]+');
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        appdetail = soup.select('.app_detail')[0];
        commonname = appdetail.select('.detail_line')[0].select('h3')[0].get_text();
        version = appdetail.select('.app_detail_version')[0].get_text();
        appdetail = appdetail.select('#detail_line_ul')[0].select('li');
        category = appdetail[0].get_text();
        category = category[category.find(u'：')+1:];
        updatetime = appdetail[2].get_text();
        updatetime = updatetime[updatetime.find(u'：')+1:];
        size = appdetail[3].get_text();
        size = size[size.find(u'：')+1:];
        developer = appdetail[6].get_text();
        developer = developer[developer.find(u'：')+1:];
        apkid = numpattern.search(soup.select('.detail_down')[0].select('a')[0]['onclick']).group();
        dlg = self.downloadgate%int(apkid);
        proxy = Proxy(apkid, dlg);
        urllink = proxy.get_downloadaddress();
        packagenamepattern = re.compile(ur'/[^/]*\.html');
        packagename = packagenamepattern.search(response.url).group()[1:-5];
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

