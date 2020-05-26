# -*- coding: utf-8 -*-

import datetime
import socket
import socketserver
import re
import os
import uuid

from gevent import monkey

monkey.patch_all()

from handler.config import app_config
from handler.pool import redis_pool
from handler.error.configError import ConfigError
from server import WorkerServer

from model.worker.redis import model_redis_startup_log

from request.http.registerUserUiServer import http_register_user_ui_server


if __name__ == '__main__':
    """
        WORKER启动基本流程
        1.自检。自检包括配置文件检查及基础配置数据生成
        2.注册。向userUi服务申请注册，从而接收来自userUi的测试任务数据
        启动应仅包含最基本、尽可能少的类及方法调用
    """
    # 启动生成uuid，如果有了的话就不生成
    if not app_config.get('worker', 'uuid'):
        app_config.set('worker', 'uuid', str(uuid.uuid1()))
        app_config.write(open('config/app.ini', "w"))
    # 检查用户界面信息配置
    userServerHost = app_config.get('server', 'host')
    userServerPort = app_config.get('server', 'port')
    # 如果信息不全，直接报错
    if not userServerHost or not userServerPort:
        msg = '服务注册失败，app.ini中缺少用户界面应用服务相关信息'
        raise ConfigError(msg)
    else:
        # 检查worker配置文件中ip
        worker_ip = app_config.get('worker', 'host')
        compile_ip = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
        if not compile_ip.match(worker_ip):
            msg = '服务注册失败，worker的ip填写非法'
            raise ConfigError(msg)
        # 检查worker配置文件端口
        try:
            worker_port = int(app_config.get('worker', 'port'))
        except Exception as e:
            msg = '服务注册失败，worker的端口填写内容非法'
            raise ConfigError(msg)
        else:
            #
            if 1024 > worker_port or worker_port > 65534:
                msg = '服务注册失败，worker的端口填写值超出范围'
                raise ConfigError(msg)
            # 检查端口占用情况
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if s.connect_ex((worker_ip, worker_port)) != 0:
                    # 端口扫描通过
                    # 检查redis配置
                    if redis_pool.ping() is not True:
                        msg = '服务注册失败，redis连接异常'
                        raise ConnectionError(msg)
                    # 发起注册请求
                    registerResult = http_register_user_ui_server()
                    # 如果失败了
                    if not registerResult:
                        msg = '服务注册失败，注册请求失败'
                        # 将注册信息记录至本地redis
                        model_redis_startup_log.set(
                            userServerHost,
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            False,
                            msg
                        )
                        raise ConnectionError(msg)
                    else:
                        # 将log日志记录redis服务器信息记录至配置文件
                        app_config.set('worker', 'id', str(registerResult['worker_id']))
                        app_config.write(open("config/app.ini", "w"))
                        # 将注册信息记录至本地redis
                        model_redis_startup_log.set(
                            userServerHost,
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            True
                        )
                    # 检查测试任务文件存储主目录
                    if not os.path.exists(app_config.get('file', 'path')):
                        try:
                            os.makedirs(app_config.get('file', 'path'))
                        except Exception as e:
                            raise OSError(repr(e))
                    # 启动socketServer
                    try:
                        worker_server = socketserver.ThreadingTCPServer(
                            (worker_ip, int(worker_port)),
                            WorkerServer
                        )
                    except Exception as e:
                        raise OSError(repr(e))
                    else:
                        print("worker已启动，进程号%s，服务监听中..." % os.getpid())
                        worker_server.serve_forever()
                else:
                    msg = '服务注册失败，worker的端口已被占用'
                    raise ConfigError(msg)

