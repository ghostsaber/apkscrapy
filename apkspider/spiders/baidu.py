# -*- coding: utf-8 -*-
import scrapy

from scrapy.http import Request

import bs4
from pybloom_live import BloomFilter

import re

from scrapy.loader import ItemLoader
from apkspider.items import ApkspiderItem

class BaiduSpider(scrapy.Spider):
    name = 'baidu';
    allowed_domains = ['shouji.baidu.com'];
    start_urls = ['https://shouji.baidu.com/software','https://shouji.baidu.com/game'];
    custom_settings = {"CONCURRENT_REQUESTS": 3};

    def __init__(self,*a,**kw):
        super(BaiduSpider,self).__init__(*a,**kw);
        self.categorybf = BloomFilter(capacity=100000000);

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter = True
            );

    def parse(self, response):
        base_url = 'https://shouji.baidu.com';
        soup = bs4.BeautifulSoup(response.text,"html.parser");
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if not href.find('board') == -1 and not href in self.categorybf:
                self.categorybf.add(href);
                yield Request(
                    url = base_url + href,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_category
                );

    def parse_category(self,response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        pattern = re.compile(ur'https://shouji.baidu.com/.*/[0-9]+\.html');
        base_url = 'https://shouji.baidu.com';
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if href in self.categorybf:
                continue;
            self.categorybf.add(href);
            if not href.find('list')  == -1:
                yield Request(
                    url = base_url + href,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_category
                );
                #print(href);
            elif not pattern.match(base_url+href) == None:
                yield Request(
                    url = base_url + href,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_detail
                );
        
    def parse_detail(self,response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        platform = self.name;
        commonname = soup.find_all("h1", class_='app-name')[0].find('span').get_text();
        detailinfo = soup.find_all("div", class_='detail')[0];
        size = detailinfo.find_all("span",class_='size')[0].get_text();
        version = detailinfo.find_all("span", class_='version')[0].get_text();
        sizepattern = re.compile(ur'[0-9\.]+.*');
        versionpattern = re.compile(ur'[0-9\.]+');
        idpattern = re.compile(ur'[0-9]+');
        size = sizepattern.search(size).group();
        version = versionpattern.search(version).group();
        packagename = commonname;
        platformid = idpattern.search(response.url).group();
        urllink = soup.find_all("a", class_='apk')[0]['href'];
        category = soup.find_all("a", attrs={'target':'_self'})[2].get_text();
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',platform);
        item.add_value('apkid_specifiedbyplaform',platformid);
        item.add_value('category',category);
        item.add_value('packagename',packagename);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        yield item.load_item();
