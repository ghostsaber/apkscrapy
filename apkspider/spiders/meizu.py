# -*- coding: utf-8 -*-
import scrapy

from scrapy.http import Request

import bs4
from pybloom_live import BloomFilter

import re
import json

from scrapy.loader import ItemLoader
from apkspider.items import ApkspiderItem

class MeizuSpider(scrapy.Spider):
    name = 'meizu'
    allowed_domains = ['app.meizu.com','app.flyme.cn']
    start_urls = ['http://app.meizu.com/','http://app.flyme.cn/games/public/index']
    custom_settings = {"CONCURRENT_REQUESTS": 3};
    download_url = 'http://app.flyme.cn/%s/public/download.json?app_id=%d';

    def __init__(self, checkpoint = None, *a, **kw):
        super(MeizuSpider,self).__init__(*a, **kw);
        self.bf = BloomFilter(capacity=10000000);
        self.checkpoint = checkpoint;
        self.apkbf = BloomFilter(capacity=100000000);
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
            metainfo = {'type':'apps'};
            if not url.find('games') == -1:
                metainfo = {'type':'games'};
            yield Request(url,
                headers = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = metainfo,
                dont_filter = True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        category_url = 'http://app.flyme.cn/%s/public/category/%d/all/feed/index/0/18';
        categorylist = soup.select("#categoryList");
        if not len(categorylist) == 1:
            return;
        categorylist = categorylist[0];
        dataparam = categorylist.select("li");
        for dp in dataparam:
            if dp.has_attr('data-param'):
                yield Request(
                    url = category_url%(response.meta['type'],int(dp['data-param'])),
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    meta = response.meta,
                    callback=self.parse_category
                );

    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        applist = soup.select('#app');
        base_url = 'http://app.flyme.cn';
        if len(applist) == 0:
            return;
        applist = applist[0].find_all('a');
        for app in applist:
            if not app.has_attr('href'):
                continue;
            if base_url + app['href'] in self.bf:
                continue;
            self.bf.add( base_url + app['href'] );
            yield Request(
                url = base_url + app['href'],
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                meta = response.meta,
                callback = self.parse_detail
            );


    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        metedata = soup.select('div.left.inside_left')[0];
        platform = self.name;
        category = metedata.select('.current')[0]['title'];
        packagenamepattern = re.compile(ur'package_name=.*');
        packagename = packagenamepattern.search(response.url).group()[13:];
        urllink = response.url;
        app_titles = metedata.find_all("span",class_="app_title");
        app_content = metedata.find_all('div',class_='app_content');
        size = app_content[5].get_text().strip();
        version = app_content[3].get_text().strip();
        updatetime = app_content[6].get_text().strip();
        developer = app_content[2].get_text().strip();
        commonname = soup.find_all('div',class_='app_detail')[0];
        commonname = commonname.find_all('div',class_='detail_top')[0];
        commonname = commonname.find_all('h3')[0].get_text();
        apkid = soup.select('.price_bg.downloading')[0]['data-appid'];
        yield Request(
            url = self.download_url%(response.meta['type'],int(apkid)),
            headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
            meta = {'commonname':commonname, 'platform': platform , 'category': category, 'developer':developer, 'packagename':packagename,
                'updatetime' : updatetime, 'size':size, 'version':version, 'urllink':urllink},
            callback = self.parse_download
        );



    def parse_download(self, response):
        json_response = json.loads(response.body_as_unicode());
        if not json_response['code'] == 200:
            return;
        urllink = json_response['value']['downloadUrl'];
        apkid = response.meta['packagename'];
        if apkid in self.apkbf:
            return;
        self.apkbf.add(apkid);
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('apkid_specifiedbyplaform',apkid);
        item.add_value('commonname',response.meta['commonname']);
        item.add_value('apkplaform',response.meta['platform']);
        item.add_value('category',response.meta['category']);
        item.add_value('developer',response.meta['developer']);
        item.add_value('packagename',response.meta['packagename']);
        item.add_value('updatetime',response.meta['updatetime']);
        item.add_value('size',response.meta['size']);
        item.add_value('version',response.meta['version']);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        item.add_value('checkpoint',self.checkpoint);
        yield item.load_item();
