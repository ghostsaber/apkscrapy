# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request

import bs4
from pybloom_live import BloomFilter

import urlparse
import re

from scrapy.loader import ItemLoader
from apkspider.items import ApkspiderItem

class PconlineSpider(scrapy.Spider):
    name = 'pconline'
    allowed_domains = ['dl.pconline.com.cn']
    start_urls = ['https://dl.pconline.com.cn/sort/1402.html', 'https://dl.pconline.com.cn/sort/1403.html'];

    httpprotocol = 'https:';
    def __init__(self, *a, **kw):
        super(PconlineSpider,self).__init__(*a,**kw);
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
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        categorylist = soup.select('.sort-links')[0];
        for aitem in categorylist.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.httpprotocol + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback=self.parse_category
            );


    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        pagesoup = soup.select('.page')[0];
        appsoup = soup.select('.list-wrap')[0];
        category = soup.select('.sort-links')[0].select('.current')[0].get_text();
        for aitem in pagesoup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = self.httpprotocol + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_category
            );
        for titem in appsoup.select('.title'):
            aitem=titem.find('a');
            if not aitem.has_attr('href'):
                continue;
            href = self.httpprotocol + aitem['href'];
            if href in self.bf:
                continue;
            self.bf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = {'category':category},
                callback = self.parse_detail
            );

    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, 'html.parser');
        idpattern = re.compile(ur'[0-9]+');
        versionpattern = re.compile(ur'[0-9.]+');
        commonname = soup.select('dt.clearfix')[0].get_text().strip();
        version = versionpattern.search(commonname).group();
        category = response.meta['category'];
        msgsoup = soup.select('.msg-list')[0];
        msglist = msgsoup.select('li');
        size = msglist[0].get_text();
        size = size[size.find(u'：')+1:].strip();
        developer = msglist[1].get_text();
        developer = developer[developer.find(u'：')+1:].strip();
        updatetime = msglist[5].get_text();
        updatetime = updatetime[updatetime.find(u'：')+1:].strip();
        print(response.url);
        apkid = idpattern.search(response.url).group();
        urllink = self.httpprotocol + soup.select('.dl-btn')[0]['tempurl'];
        print(urllink);
        packagename;
