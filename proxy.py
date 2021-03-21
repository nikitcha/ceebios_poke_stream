import requests
from itertools import cycle
import re

def get_proxies1():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    proxies = re.findall(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):\d{1,5}\b", response.text)
    return proxies

def get_proxies2():
    url = 'https://www.sslproxies.org'
    response = requests.get(url)
    proxies = re.findall(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):\d{1,5}\b", response.text)
    return proxies


def main():
    #If you are copy pasting proxy ips, put in the list below
    #proxies = ['121.129.127.209:80', '124.41.215.238:45169', '185.93.3.123:8080', '194.182.64.67:3128', '106.0.38.174:8080', '163.172.175.210:3128', '13.92.196.150:8080']
    proxies = get_proxies2()
    proxy_pool = cycle(proxies)

    url = 'https://httpbin.org/ip'
    for i in range(len(proxies)):
        #Get a proxy from the pool
        proxy = next(proxy_pool)
        print("Request #%d"%i)
        try:
            response = requests.get(url,proxies={"http": 'http://'+proxy, "https": 'http://'+proxy})
            print(response.json())
        except:
            #Most free proxies will often get connection errors. You will have retry the entire request using another proxy to work. 
            #We will just skip retries as its beyond the scope of this tutorial and we are only downloading a single url 
            print("Skipping. Connnection error")

if __name__=='__main__':
    main()