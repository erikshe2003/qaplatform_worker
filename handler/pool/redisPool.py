# -*- coding: utf-8 -*-

from redis import Redis, ConnectionPool
from handler.config import database_config
from handler.log import sys_logger


msg = "准备初始化worker存储(redis)连接池"
sys_logger.info(msg)
try:
    pool = ConnectionPool(
        host=database_config.get("redis", "host"),
        port=int(database_config.get("redis", "port")),
        password=database_config.get("redis", "password") if database_config.get("redis", "password") else None,
        max_connections=int(database_config.get("redis", "max_connections"))
    )
    redis_pool = Redis(connection_pool=pool)
    msg = "worker存储(redis)连接池初始化成功"
    sys_logger.info(msg)
except Exception as e:
    msg = "worker存储(redis)连接池初始化失败，失败原因：" + repr(e)
    sys_logger.error(msg)
    raise RuntimeError(msg)
