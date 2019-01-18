# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from scrapy.exceptions import DropItem
from scrapy.http import Request
from scrapy.pipelines.files import FilesPipeline


from items import ItemToJsonString

import os
import hashlib
import logging
import urlparse
import urllib

import threadpool

import wget

import fcntl

import time

logger = logging.getLogger(__name__)


def downloadfile(urllink, outputroot, platform, category, packagename):
    targetdir = "%s/%s/%s"%(outputroot,platform,category);
    if not os.path.exists(targetdir):
        os.makedirs(targetdir);
    targetfile = "%s/%s.apk"%(targetdir,packagename);
    a = wget.download(urllink, targetfile);
    time.sleep(2);

def encodewithutf8(string):
    return string.encode(encoding = 'UTF-8',errors='strict');

class ApkspiderPipeline(FilesPipeline):
    #def process_item(self, item, spider):
    #    return item

    def __init__(self, store_uri, download_func=None, settings=None):
        self.pool = threadpool.ThreadPool(10);# magic num
        self.store_url = "./output"; # magic str
        super(ApkspiderPipeline, self).__init__(store_uri, download_func,settings);

    def close_spider(self,spider):
        self.pool.wait();

    @classmethod
    def from_settings(cls,settings):
        store_url = settings['FILES_STORE'];
        return cls(store_url, settings);

    def get_media_requests(self,item,info):
        if not 'urllink' in item or not 'packagename' in item or not 'apkplaform' in item or not 'category' in item:
            raise DropItem("Miss urllink or packagename or apkplaform");
        if not len(item['urllink']) == 1:
            raise DropItem("multi url in urllink");
        if not len(item['urllink']) == 1 or not len(item['apkplaform']) == 1 or not len(item['category']) == 1 or not len(item['packagename']) == 1:
            raise DropItem("len of item not right");
        targs = dict();
        targs['urllink'] = item['urllink'][0];
        targs['outputroot'] = self.store_url;
        targs['platform'] = item['apkplaform'][0];
        targs['category'] = item['category'][0];
        targs['packagename'] = item['packagename'][0];

        funcvar = [(None,targs)];
        requests = threadpool.makeRequests(downloadfile,funcvar);
        [self.pool.putRequest(req) for req in requests];
        metadatafile = "%s/%s.meta"%(self.store_url,item['apkplaform'][0]);
        storepath = "%s/%s/%s/%s.apk"%(targs['outputroot'],targs['platform'],targs['category'],targs['packagename']);
        addupinfo = dict();
        addupinfo['store_path'] = storepath;
        #item.add_value('store_path',storepath);
        metadata = ItemToJsonString(item, addupinfo);
        fp = open(metadatafile,"a+");
        fcntl.flock(fp,fcntl.LOCK_EX);
        fp.write(metadata);
        fp.write("\n");
        fcntl.flock(fp,fcntl.LOCK_UN);
        #self.pool.wait();
        #time.sleep(10);
