# apkscrapy
app store crawler  
  
denpendencies:  
>python 2.7  
>scrapy  
>pycurl  
>more python package...  
  
finished:  
>[xiaomi](http://app.mi.com/)  
>[qq](https://sj.qq.com/myapp/index.htm)  
>[wandoujia](https://www.wandoujia.com)  
>[baidu](https://shouji.baidu.com)  
>[MEIZU](http://app.meizu.com/)   
>[HUAWEI](http://app.hicloud.com/)  
>[360](http://zhushou.360.cn/)  
>[lenovo](https://www.lenovomm.com/)  
>[25pp](https://www.25pp.com/android/)  
>[anzhi](http://www.anzhi.com/)  
>[liqu](https://www.liqucn.com/)  
>[sougou](http://zhushou.sogou.com/apps)  
>[appchina](http://www.appchina.com/)  
  
  
TODO:  
>[pconline](https://dl.pconline.com.cn/android/)  main challenge: Can't generate token, it need browser to execute js code and receive token from server.  Sulotion: using selenium.  
>[oppo](https://store.oppomobile.com/) main challenge: It provide apk downloading in mobile app store(apk), didn't find a website to provide apk downloading.  
>[hiapk](http://apk.hiapk.com/)  main challenge: It provide apk downloading in mobile app store(apk), didn't find a website to provide apk downloading.  
    
Demo:  
>scrapy crawl xiaomi(any vendor)  

checkpoint:  
>scrapy crawl xiaomi -a checkpoint=[checkpointfile]
