# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy

import json

class ApkspiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    commonname = scrapy.Field(default=None);
    apkplaform = scrapy.Field(default=None);
    apkid_specifiedbyplaform = scrapy.Field(default=None);
    category = scrapy.Field(default=None);
    developer = scrapy.Field(default=None);
    developerid = scrapy.Field(default=None);
    packagename = scrapy.Field(default=None);
    updatetime = scrapy.Field(default=None);
    size = scrapy.Field(default=None);
    version = scrapy.Field(default=None);
    permission = scrapy.Field(default=None);
    install_num = scrapy.Field(default=None);
    urllink = scrapy.Field(default=None);
    description = scrapy.Field(default=None);
    
    file_urls = scrapy.Field();
    files = scrapy.Field();

    checkpoint = scrapy.Field(default=None);
    #use by pipeline
    #store_path = scrapy.Field(default=None);
    #sha1 = scrapy.Field(default=None);

def ItemToJsonString(item, addupinfodict):
    jsondict = dict();
    '''jsondict['commonname'] = item['commonname'];
    jsondict['apkplaform'] = item['apkplaform'];
    jsondict['apkid_specifiedbyplaform'] = item['apkid_specifiedbyplaform'];
    jsondict['category'] = item['category'];
    jsondict['developer'] = item['developer'];
    jsondict['developerid'] = item['developerid'];
    jsondict['packagename'] = item['packagename'];
    jsondict['updatetime'] = item['updatetime'];
    jsondict['size'] = item['size'];
    jsondict['version'] = item['version']
    jsondict['permission'] = item['permission'];
    jsondict['install_num'] = item['install_num']
    jsondict['urllink'] = item['urllink'];
    jsondict['description'] = item['description']
    jsondict['file_urls'] = item['file_urls'];
    jsondict['files'] = item['files'];'''
    for key in item.keys():
        jsondict[key] = item[key];
    for aitem in addupinfodict:
        jsondict[aitem] = addupinfodict[aitem];
    result = json.dumps(jsondict).decode("unicode-escape").encode(encoding="UTF-8");
    #print(teststr.decode("unicode-escape"));
    return result;
