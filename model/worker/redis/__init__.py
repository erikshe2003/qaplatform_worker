# -*- coding: utf-8 -*-

from handler.log import sys_logger

from .startUpLog_r import StartUpLogR
from .testTask_r import TestTaskR
from .taskProcessId_r import TaskProcessIdR
from .taskJob_r import TaskJobR

msg = "准备初始化redis数据库模型"
sys_logger.info(msg)
try:
    # 实例化redis的model
    model_redis_startup_log = StartUpLogR()
    model_redis_test_task = TestTaskR()
    model_redis_task_process_id = TaskProcessIdR()
    model_redis_task_job = TaskJobR()
    msg = "redis数据库模型初始化成功"
    sys_logger.debug(msg)
except Exception as e:
    msg = "redis数据库模型初始化失败，失败原因：" + repr(e)
    sys_logger.error(msg)
    raise RuntimeError(msg)
