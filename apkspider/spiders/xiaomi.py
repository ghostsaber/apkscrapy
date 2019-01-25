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


class XiaomiSpider(scrapy.Spider):
    name = 'xiaomi'
    allowed_domains = ['app.mi.com']
    start_urls = ['http://app.mi.com/']

    custom_settings = {"CONCURRENT_REQUESTS": 3}
    base_url = "http://app.mi.com";

    def __init__(self, checkpoint=None, *a, **kw):
        super(XiaomiSpider,self).__init__(*a,**kw);
        self.categorybf = BloomFilter(capacity=1000);
        self.apkbf = BloomFilter(capacity=100000000);
        self.urllinkdic = dict();
        self.checkpoint = checkpoint;
        if not checkpoint == None:
            fd = open(checkpoint,'r');
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
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter=True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        for aitem in soup.find_all('a'):
            href = aitem['href'];
            if not href.find("category") == -1 and not href in self.categorybf:
                self.categorybf.add(href);
                pattern = re.compile(ur'([0-9])+');
                categoryid = pattern.search(href).group();
                yield Request(
                    url=urlparse.urljoin(response.url, "/categotyAllListApi?page=0&categoryId=%s&pageSize=100000"%categoryid),
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_json
                );

    def parse_json(self, response):
        json_response = json.loads(response.body_as_unicode());
        allappinfos = "";
        if json_response.has_key('data'):
            allappinfos = json_response['data'];
        else:
            return;
        for appentry in allappinfos:
            if appentry.has_key("appId"):
                packageid = appentry["packageName"];
                yield Request(
                    url="http://app.mi.com/details?id=%s"%packageid,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_detail
                );

    def parse_detail(self, response):
        soup = bs4.BeautifulSoup(response.text,"html.parser");
        downloadlinks = soup.find_all("a", class_='download');
        hideinfos = soup.select("div .details.preventDefault");
        overviews = soup.select("div .intro-titles");
        if not (len(overviews) == 1 and len(hideinfos) == 1 and len(downloadlinks) == 1):
            return;
        downloadlink = downloadlinks[0];
        overview = overviews[0];
        commonname = overview.select("h3")[0].text.encode(encoding='UTF-8',errors='strict');#
        apkplaform = "xiaomi";#
        apkid_specifiedbyplaform = "";#
        category = overview.select("p.special-font.action")[0].text.encode(encoding='UTF-8',errors='strict');
        category = category[category.find("：") + 3:category.find("|")];#
        developer = overview.select("p")[0].text.encode(encoding='UTF-8',errors='strict');#
        packagename = "";#
        size = "";#
        version = "";#
        permissionlist = list();#
        urlink = urlparse.urljoin(self.base_url, downloadlink['href']);#
        #description = "";
        updatetime = '';#
        hideinfogenes = hideinfos[0].select('ul.cf');
        if not len(hideinfogenes) == 1:
            return;
        hideinfogene = hideinfogenes[0];
        generalinfos = hideinfogene.select('li');
        while len(generalinfos) > 1:
            infodes = generalinfos.pop(0).text.encode(encoding='UTF-8',errors='strict');
            if infodes.strip() == 'appId：':
                apkid_specifiedbyplaform = generalinfos.pop(0).text.encode(encoding = 'UTF-8',errors='strict');
            elif infodes.strip() == '更新时间：':
                updatetime = generalinfos.pop(0).text.encode(encoding = 'UTF-8',errors='strict');
            elif infodes.strip() == '包名：':
                packagename = generalinfos.pop(0).text.encode(encoding = 'UTF-8',errors='strict');
            elif infodes.strip() == '版本号：':
                version = generalinfos.pop(0).text.encode(encoding = 'UTF-8',errors='strict');
            elif infodes.strip() == '软件大小:':
                size = generalinfos.pop(0).text.encode(encoding = 'UTF-8',errors='strict');
        permissioninfos = hideinfos[0].select('ul.second-ul');
        if not len(permissioninfos) == 1:
            return;
        permissions = permissioninfos[0].select('li');
        while len(permissions) > 0:
            permission = permissions.pop(0).text.encode(encoding='UTF-8',errors='strict');
            permission = permission[3:].strip();
            permissionlist.append(permission);
        if apkid_specifiedbyplaform in self.apkbf:
            return;
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',apkplaform);
        item.add_value('apkid_specifiedbyplaform',apkid_specifiedbyplaform);
        item.add_value('category',category);
        item.add_value('developer',developer);
        item.add_value('packagename',packagename);
        item.add_value('updatetime',updatetime);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('permission',permissionlist);
        item.add_value('urllink',urlink);
        item.add_value('file_urls',urlink);
        item.add_value('checkpoint', self.checkpoint);
        yield item.load_item();
