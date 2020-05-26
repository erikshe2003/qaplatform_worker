# -*- coding: utf-8 -*-

import urllib3
import json
import datetime
import uuid

from handler.config import app_config
from handler.log import app_logger

"""
    告知用户界面测试任务结束-http请求
    status:0推送中，1推送成功，-1推送失败，2任务初始化中，-2任务初始化失败，3任务执行中，-3执行异常，10任务结束
"""


def http_tell_test_task_status(task_id, status):
    # 准备参数
    # 用户界面的执行应用注册接口地址
    server_ip = app_config.get('server', 'host')
    server_port = app_config.get('server', 'port')
    try:
        api_response = urllib3.PoolManager(1).request(
            method='post',
            url='http://' + server_ip + ':' + str(server_port) + '/api/task/testTaskFinished.json',
            headers={'Content-Type': 'application/json;charset=UTF-8'},
            body=json.dumps({
                'taskId': task_id,
                'uuid': app_config.get('worker', 'uuid'),
                'status': status
            })
        )
    except Exception as e:
        app_logger.error('回传测试任务结束时间失败，失败原因：' + repr(e))
        return False
    else:
        if api_response.status == 200:
            # 如果返回码为200则成功，否则失败
            api_response_dict = json.loads(api_response.data.decode('utf-8'))
            if api_response_dict['error_code'] != 200:
                app_logger.error('回传测试任务结束时间失败，失败原因：' + api_response_dict['error_msg'])
            else:
                app_logger.debug('回传测试任务结束时间成功')
        else:
            app_logger.error('回传测试任务结束时间失败，失败原因：用户界面服务异常')
            return False
