# -*- coding: utf-8 -*-
import scrapy

from scrapy.http import Request

import bs4
from pybloom_live import BloomFilter

import re
import json

from scrapy.loader import ItemLoader
from apkspider.items import ApkspiderItem



class QqSpider(scrapy.Spider):
    name = 'qq'
    allowed_domains = ['sj.qq.com'];
    start_urls = ['https://sj.qq.com/myapp/index.htm'];
    custom_settings = {"CONCURRENT_REQUESTS": 3};
    base_cate_url = "https://sj.qq.com/myapp/cate/appList.htm?orgame=1&categoryId=%d&pageSize=20&pageContext=%d";

    def __init__(self, *a, **kw):
        super(QqSpider,self).__init__(*a,**kw);
        self.step = 20;
        self.begin_step = 0;
        self.categorybf = BloomFilter(capacity = 100000000);

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter = True
            );


    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        pattern = re.compile(ur'categoryId=-?[0-9]+');
        idpattern = re.compile(ur'-?[0-9]+');
        for aitem in soup.find_all('a'):
            href = aitem['href'];
            if not href.find('categoryId') == -1 and href not in self.categorybf:
                self.categorybf.add(href);
                categoryid = pattern.search(href).group();
                categoryid = idpattern.search(categoryid).group();
                url = self.base_cate_url%(int(categoryid),self.begin_step);
                #print(url);
                yield Request(
                    url,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_json
                );
    

    def parse_json(self, response):
        categorypattern = re.compile(ur'categoryId=-?[0-9]+');
        pagecontext = re.compile(ur'pageContext=-?[0-9]+');
        idpattern = re.compile(ur'-?[0-9]+');
        catestring = categorypattern.search(response.url).group();
        pagestring = pagecontext.search(response.url).group();
        cateid = idpattern.search(catestring).group();
        pageid = idpattern.search(pagestring).group();
        json_response = json.loads(response.body_as_unicode());
        count = 0;
        if json_response.has_key('count'):
            count = int(json_response['count']);
        else:
            return;
        print(response.url);
        print(count);
        if count <= 0:
            return;
        objs = "";
        if json_response.has_key('obj'):
            objs = json_response['obj'];
        else:
            return;
        apkplaform = 'qq';
        for obj in objs:
            if obj['apkUrl'] in self.categorybf:
                continue;
            self.categorybf.add(obj['apkUrl']);
            item = ItemLoader(item=ApkspiderItem(), response=response);
            item.add_value("commonname",obj['appName']);
            item.add_value('apkplaform',apkplaform);
            item.add_value('apkid_specifiedbyplaform',obj['appId']);
            item.add_value('category',obj['categoryName']);
            item.add_value('developer',obj['authorName']);
            item.add_value('packagename',obj['pkgName']);
            item.add_value('updatetime',obj['apkPublishTime']);
            item.add_value('version',obj['versionName']);
            item.add_value('urllink',obj['apkUrl']);
            item.add_value('file_urls',obj['apkUrl']);
            yield item.load_item();

        url = self.base_cate_url%(int(cateid),int(pageid)+self.step);
        yield Request(
            url,
            headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
            callback=self.parse_json
        );

