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

class WandoujiaSpider(scrapy.Spider):
    name = 'wandoujia'
    allowed_domains = ['wandoujia.com']
    start_urls = ['https://www.wandoujia.com']

    custom_settings = {"CONCURRENT_REQUESTS": 3}

    def __init__(self,*a,**kw):
        super(WandoujiaSpider,self).__init__(*a,**kw);
        self.categorybf = BloomFilter(capacity=10000000);
        self.category_base_url = 'https://www.wandoujia.com/wdjweb/api/category/more?catId=%d&subCatId=%d&page=%d';

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                dont_filter=True
            );

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text,"html.parser");
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if not href.find('category') == -1 and not href in self.categorybf:
                self.categorybf.add(href);
                yield Request(
                    url = href,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_category
                );

    def parse_category(self, response):
        soup = bs4.BeautifulSoup(response.text,"html.parser");
        idandsubidpattern = re.compile(ur'[0-9]+_[0-9]+');
        numpattern = re.compile(ur'[0-9]+');
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href'):
                continue;
            href = aitem['href'];
            if not href.find('category') == -1 and not href in self.categorybf:
                self.categorybf.add(href);
                id_subid = idandsubidpattern.search(href);
                if id_subid == None:
                    continue;
                id_subid = id_subid.group();
                id_sib_find_all = numpattern.findall(id_subid);
                mid = id_sib_find_all[0];
                subid = id_sib_find_all[1];
                url = self.category_base_url%(int(mid),int(subid),0);
                self.categorybf.add(url);
                yield Request(
                    url = url,
                    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                    callback=self.parse_json
                );

    def get_id_sid_page(self,url):
        catidpattern = re.compile(ur'catId=[0-9]+');
        subcatidpattern = re.compile(ur'subCatId=[0-9]+');
        pagepattern = re.compile(ur'page=[0-9]+');
        numpattern = re.compile(ur'[0-9]+');
        catid = catidpattern.search(url).group();
        subcatid = subcatidpattern.search(url).group();
        page = pagepattern.search(url).group();
        catid = numpattern.search(catid).group();
        subcatid = numpattern.search(subcatid).group();
        page = numpattern.search(page).group();
        return int(catid), int(subcatid), int(page);

    def get_next_page(self, base_url, cid, scid, page):
        return base_url%(cid, scid, page+1);

    def parse_json(self,response):
        json_response = json.loads(response.body_as_unicode());
        if not json_response.has_key('data'):
            return;
        json_data = json_response['data'];
        if not json_data.has_key('currPage'):
            return;
        currpage = json_data['currPage'];
        if currpage == -1:
            return;
        if not json_data.has_key('content'):
            return;
        content = json_data['content'];
        catid, subcatid, page = self.get_id_sid_page(response.url);
        nextpage = self.get_next_page('https://www.wandoujia.com/wdjweb/api/category/more?catId=%d&subCatId=%d&page=%d', catid, subcatid, page);
        self.categorybf.add(nextpage);
        yield Request(
            url = nextpage,
            headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
            callback = self.parse_json
        );
        soup = bs4.BeautifulSoup(content,"html.parser");
        for aitem in soup.find_all('a'):
            if not aitem.has_attr('href') or aitem.has_attr('class'):
                continue;
            href = aitem['href'];
            if href in self.categorybf:
                continue;
            self.categorybf.add(href);
            yield Request(
                url = href,
                headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0"},
                callback = self.parse_detail
            );

    def parse_detail(self, response):
        versionpattern =  re.compile(ur'[0-9\.]+');
        soup = bs4.BeautifulSoup(response.text, "html.parser");
        commonname = soup.select('.app-name')[0].get_text();
        info = soup.select('.infos-list')[0];
        size = info.find('dd').get_text();
        platform = self.name;
        urllink = soup.find_all('a', class_='normal-dl-btn')[0];
        if not urllink.has_attr('href'):
            return;
        urllink = urllink['href'];
        version = info.select('dd')[2].get_text();
        print(version);
        if versionpattern.search(version) == None:
            version = info.select('dd')[3].get_text();
        developer = info.select('.dev-sites');
        if len(developer) == 0:
            developer = "";
        else:
            developer = developer[0].get_text();
        permission = list();
        permlist = info.find_all('span',class_='perms');
        for perm in permlist:
            permission.append(perm.get_text());
        category = info.find_all('a')[0].get_text();
        updatetime = soup.find('span', class_='update-time').get_text();
        timepattern = re.compile(ur'[0-9/]+');
        updatetime = timepattern.search(updatetime).group();
        packagename = response.url[response.url.rfind('/')+1:];
        item = ItemLoader(item=ApkspiderItem(), response=response);
        item.add_value('commonname',commonname);
        item.add_value('apkplaform',platform);
        item.add_value('category',category);
        item.add_value('developer',developer);
        item.add_value('packagename',packagename);
        item.add_value('updatetime',updatetime);
        item.add_value('size',size);
        item.add_value('version',version);
        item.add_value('permission',permission);
        item.add_value('urllink',urllink);
        item.add_value('file_urls',urllink);
        yield item.load_item();
