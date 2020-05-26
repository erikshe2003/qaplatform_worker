# -*- coding: utf-8 -*-

import requests
import json
import uuid

from handler.config import app_config
from handler.log import app_logger

"""
    向用户界面发起注册请求-http请求
"""


def http_register_user_ui_server():
    # 准备参数
    # 用户界面的执行应用注册接口地址
    server_ip = app_config.get('server', 'host')
    server_port = app_config.get('server', 'port')
    api_url = 'http://' + server_ip + ':' + str(server_port) + '/api/task/workerRegister.json'
    api_headers = {'Content-Type': 'application/json;charset=UTF-8'}
    # 生成uuid/ip/port
    worker_uuid = app_config.get('worker', 'uuid')
    worker_host = app_config.get('worker', 'host')
    worker_port = int(app_config.get('worker', 'port'))
    api_json = json.dumps({
        'uuid': worker_uuid,
        'ip': worker_host,
        'port': worker_port
    })
    try:
        api_response = requests.post(api_url, data=api_json, headers=api_headers, timeout=10)
    except Exception as e:
        app_logger.error('服务注册失败，失败原因：' + repr(e))
        return False
    else:
        if api_response.status_code == 200:
            # 如果返回码为200则成功，否则失败
            api_response_dict = json.loads(api_response.text)
            if api_response_dict['error_code'] != 200:
                app_logger.error('服务注册失败，失败原因：' + api_response_dict['error_msg'])
                return False
            else:
                app_logger.debug('服务注册成功')
                return {
                    'worker_id': api_response_dict['data']['worker_id']
                }
        else:
            app_logger.error('服务注册失败，失败原因：用户界面服务异常')
            return False
