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


class A360Spider(scrapy.Spider):
    name = '360'
    allowed_domains = ['zhushou.360.cn']
    start_urls = ['http://zhushou.360.cn/list/index/cid/1/','http://zhushou.360.cn/list/index/cid/2/']
    base_url = 'http://zhushou.360.cn';
    custom_settings = {"CONCURRENT_REQUESTS": 3};

    def __init__(self, *a, **kw):
        super(A360Spider,self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity = 10000000);

    def start_requests(self):
        for url in self.start_urls:
            self.bf.add(url);
            yield Request(
                url = url,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter = True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text,"html.parser");
        categorypattern = re.compile(ur'cid/[0-9]+/$');
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
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {"category_url":href,'category':aitem.get_text() },
                callback = self.parse_category
            );

    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        appinfo = soup.select('div .icon_box')[0];
        pagepattern = re.compile(ur'pageCount\s*=\s*[0-9]+');
        numpattern = re.compile(ur'[0-9]+');
        for aitem in appinfo.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.base_url + aitem['href'];
            if href.find('detail') == -1:
                continue;
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {'category':response.meta['category']},
                callback = self.parse_detail
            );
        pageinfo = soup.select('script')[7];
        pagenum = numpattern.search(pagepattern.search(pageinfo.text).group()).group()
        print(response.url);
        print(pagenum);
        for np in range(2,int(pagenum)):
            yield Request(
                url = response.meta['category_url'] + '?page=%d'%np,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {"category_url": response.meta['category_url'],'category':response.meta['category'] },
                callback = self.parse_category
            );


    def parse_detail(self, response):
        urlpattern = re.compile(ur'url=.*');
        apkidpattern = re.compile(ur'soft_id/[0-9]+');
        numpattern = re.compile(ur'[0-9]+');
        packagenamepattern = re.compile(ur'/[^/]*\.apk');
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        print(response.url);
        commonname = soup.select('#app-name')[0].get_text();
        size = soup.select('.s-3')[1].get_text();
        urllink = urlpattern.search(soup.select('.js-downLog.dbtn')[0]['href']).group()[4:];
        packagename = packagenamepattern.search(urllink).group()[1:-4];
        apkid = numpattern.search(apkidpattern.search(response.url).group()).group();
        metainfo = soup.select('.base-info')[0];
        metainfo = metainfo.select('td');
        developer = metainfo[0].get_text();
        developer = developer[developer.find(u'：')+1:];
        version = metainfo[2].get_text();
        version = version[version.find(u'：')+1:];
        updatetime = metainfo[1].get_text();
        updatetime = updatetime[updatetime.find(u'：')+1:];
        permissionlist = list();
        permission = soup.select('#authority-panel')[0].select('p')[0].get_text().split('\n');
        category = response.meta['category'];   
        for perm in permission:
            if perm.strip().startswith(u'-'):
                permissionlist.append(perm.strip());
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
        item.add_value('permission',permissionlist);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        yield item.load_item();

