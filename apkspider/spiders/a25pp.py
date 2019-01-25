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

class A25ppSpider(scrapy.Spider):
    name = '25pp'
    allowed_domains = ['25pp.com']
    start_urls = ['https://www.25pp.com/android/','https://www.25pp.com/android/game/'];
    base_url = 'https://www.25pp.com';

    def __init__(self, checkpoint=None, *a, **kw):
        super(A25ppSpider,self).__init__(*a,**kw);
        self.bf = BloomFilter(capacity = 10000000);
        self.apkbf = BloomFilter(capacity = 100000000);
        self.checkpoint = checkpoint;
        if not checkpoint == None:
            fd = open(checkpoint, 'r');
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
        categorypattern = re.compile(ur'fenlei/[0-9]+');
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
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
        print(response.url);
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        category = soup.select('.active')[2].get_text();
        print(category);
        applist = soup.select('.app-list')[0];
        pagelist = soup.select('.page-wrap')[0];
        for aitem in applist.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {'category':category},
                callback = self.parse_detail
            );
        for aitem in pagelist.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href in self.bf:
                continue;
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_category
            );


    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        appinfo = soup.select('.app-info')[0];
        commonname = appinfo.select('.app-title')[0].get_text();
        pls = soup.select('.permission-list');
        permissionlist = list();
        if not len(pls) == 0:
            for perm in pls[0].select('.clearfix')[0].find_all('li'):
                permissionlist.append(perm.get_text());
        category = response.meta['category'];
        detail_info = soup.select('.app-detail-info')[0].select('strong');
        size = detail_info[1].get_text();
        updatetime = detail_info[0].get_text();
        version = detail_info[2].get_text();
        urllink = soup.select('.btn-install')[0]['appdownurl'];
        platform = self.name;
        detailpattern = re.compile(ur'detail_[0-9]+');
        idpattern = re.compile(ur'[0-9]+');
        detailstring = detailpattern.search(response.url).group();
        apkid = idpattern.search(detailstring).group();
        packagename = commonname;
        if apkid in self.apkbf:
            return;
        print("apkid%s"%apkid);
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',commonname);
        item.add_value('apkid_specifiedbyplaform',apkid);
        item.add_value('apkplaform',platform);
        item.add_value('category',category);
        item.add_value('packagename',packagename);
        item.add_value('updatetime',updatetime);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('permission',permissionlist);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        item.add_value('checkpoint', self.checkpoint);
        yield item.load_item();
