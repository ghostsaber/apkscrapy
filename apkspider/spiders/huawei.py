# -*- coding: utf-8 -*-
import scrapy

from scrapy.http import Request

import bs4
from pybloom_live import BloomFilter

import re
import json

from scrapy.loader import ItemLoader
from apkspider.items import ApkspiderItem

import time

class HuaweiSpider(scrapy.Spider):
    name = 'huawei'
    allowed_domains = ['app.hicloud.com']
    start_urls = ['http://app.hicloud.com/game/list','http://app.hicloud.com/soft/list']
    base_url = 'http://app.hicloud.com';
    custom_settings = {"CONCURRENT_REQUESTS": 3};

    def __init__(self, checkpoint=None ,*a, **kw):
        super(HuaweiSpider, self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity = 10000000);
        self.checkpoint = checkpoint;
        self.apkbf = BloomFilter(capacity=100000000);
        if not checkpoint == None:
            fd = open(checkpoint, 'r');
            while(True):
                line = fd.readline();
                if not line:
                    break;
                line = line.strip();
                self.apkbf.add(line);
            fd.close();
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter = True
            )

    def next_page(self, url):
        prefixpage = url[:url.rfind('_') + 1];
        postfixpage = url[url.rfind('_') + 1:];
        return prefixpage + str((int(postfixpage) + 1));

    def parse(self, response):
        categorypattern = re.compile(ur'list_.*');
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            if categorypattern.search(href) == None:
                continue;
            yield Request(
                url = href + "_2_1",
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback=self.parse_category
            );

    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        info = soup.find_all('div',class_='unit-main')[0];
        apppatern = re.compile(ur'app/.*');
        pagepattern = re.compile(ur'list_[0-9]+_[0-9]+_[0-9]+');
        #print(info);
        num = 0;
        category = soup.select('span.key-select.txt-sml')[0].get_text();
        for aitem in info.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            if not apppatern.search(href) == None:
                num += 1;
                yield Request(
                    url = href,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    meta = {"category":category},
                    callback = self.parse_detail
                );
        print("%s %d %s"%(response.url,num,self.next_page(response.url)));
        if not num == 0:
            print("%s %d %s"%(response.url,num,self.next_page(response.url)));
            yield Request(
                url = self.next_page(response.url),
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback=self.parse_category
            );
            
    
    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        info = soup.select('div.app-info.flt')[0];
        commonname = info.select('.title')[0].get_text();
        category = response.meta['category'];
        platform = self.name;
        detailinfos = info.select('li.ul-li-detail');
        if not len(detailinfos) == 4:
            return;
        size = detailinfos[0].select('span')[0].get_text();
        updatetime = detailinfos[1].select('span')[0].get_text();
        developer= detailinfos[2].select('span')[0].get_text();
        version= detailinfos[3].select('span')[0].get_text();
        permissionlist = list();
        permissions = soup.select('.hidepermission')[0].select('li');
        for p in permissions:
            if p.get_text().startswith(u'·'):
                permissionlist.append(p.get_text());
        urllink = soup.select('a.mkapp-btn.mab-download')[0];
        apkid = "";
        if not urllink.has_attr("onclick"):
            return;
        urllink = urllink['onclick'].split('\'');
        apkid = urllink[1];
        urllink = urllink[11];
        urllink = urllink[:urllink.find('?sign')];
        print(urllink);
        packagename = urllink[urllink.rfind('/')+1:];
        print(packagename);
        if apkid in self.apkbf:
            return;
        self.apkbf.add(apkid);
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',platform);
        item.add_value('apkid_specifiedbyplaform',apkid);
        item.add_value('category',category);
        item.add_value('developer',developer);
        item.add_value('packagename',packagename);
        item.add_value('updatetime',updatetime);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('permission',permissionlist);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        item.add_value('checkpoint', self.checkpoint);
        yield item.load_item();

