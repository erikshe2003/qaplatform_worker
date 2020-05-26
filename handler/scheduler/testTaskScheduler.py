# -*- coding: utf-8 -*-


import pickle

from handler.config import database_config

from apscheduler.schedulers.gevent import GeventScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore


jobstores = {
    'redis': RedisJobStore(
        db=10,
        jobs_key='apscheduler.jobs',
        run_times_key='apscheduler.run_times',
        pickle_protocol=pickle.HIGHEST_PROTOCOL,
        host=database_config.get("redis", "host"),
        port=int(database_config.get("redis", "port")),
        password=database_config.get("redis", "password"),
        max_connections=int(database_config.get("redis", "max_connections"))
    )
}
test_task_scheduler = GeventScheduler(jobstores=jobstores)
# test_task_scheduler = BackgroundScheduler(jobstores=jobstores)
test_task_scheduler.start()
