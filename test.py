# -*- coding: utf-8 -*-

import urllib3


p = urllib3.PoolManager()
s = p.request('get', 'http://localhost:5050/api/test/httpGet', timeout=1.001, retries=0)
print(s)
