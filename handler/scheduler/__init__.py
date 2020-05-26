# -*- coding: utf-8 -*-

import os
import psutil
import json
import resource
import time

from multiprocessing import Process

from model.worker.redis import model_redis_task_process_id
from model.worker.redis import model_redis_task_job
from model.worker.redis import model_redis_test_task

from request.http.tellTestTaskStatus import http_tell_test_task_status
from handler.log import app_logger
from handler.scheduler.testTaskScheduler import test_task_scheduler


def new_test_task_job(base_data):
    app_logger.debug('准备新增测试任务')
    app_logger.debug('准备从redis中获取测试任务定时任务数据')
    # 从redis中获取测试任务定时任务数据，包含add_task新增测试任务定时任务/kill_task强制终止测试任务定时任务
    jobs = model_redis_task_job.query(base_data['task_id'])
    task_info = model_redis_test_task.query(base_data['task_id'])
    if jobs:
        app_logger.debug('从redis中获取测试任务定时任务数据成功')
        try:
            jobs_dict = json.loads(jobs)
            task_info_dict = json.loads(task_info)
        except Exception as e:
            app_logger.error('测试任务定时任务数据反序列化失败:%s' % repr(e))
            http_tell_test_task_status(task_id=base_data['task_id'], status=-2)
        else:
            app_logger.debug('测试任务定时任务数据反序列化成功')
            # 将测试任务的定时任务状态中run字段值变更为True，代表任务已发起
            jobs_dict['add_task']['run'] = True
            set_flag = model_redis_task_job.set(base_data['task_id'], json.dumps(jobs_dict))
            if set_flag:
                app_logger.debug('测试任务定时任务数据重写成功')
                # 获取插件数据
                json_file_path = os.path.join(task_info_dict['file_path'], 'task.json')
                if os.path.exists(json_file_path) and os.path.isfile(json_file_path):
                    try:
                        # 读取测试插件数据列表，并传递给新增测试任务方法
                        with open(os.path.join(base_data["file_path"], 'task.json'), encoding='utf-8') as json_file:
                            task_json = json.load(json_file)
                    except Exception as e:
                        app_logger.error('测试任务插件数据文件内容反序列化失败:%s' % repr(e))
                        http_tell_test_task_status(task_id=base_data['task_id'], status=-2)
                    else:
                        # 新增进程-一个测试任务一个进程
                        p = Process(
                            target=create_task_run_flow_controller,
                            args=[base_data, task_json, os.getpid()]
                        )
                        p.start()
                else:
                    app_logger.error('测试任务插件数据文件读取失败，文件路径:%s' % json_file_path)
                    http_tell_test_task_status(task_id=base_data['task_id'], status=-2)
            else:
                app_logger.error('测试任务定时任务数据重写失败')
                http_tell_test_task_status(task_id=base_data['task_id'], status=-2)
    else:
        app_logger.error('从redis中获取测试任务定时任务数据失败，任务新增失败')
        http_tell_test_task_status(task_id=base_data['task_id'], status=-2)


def create_task_run_flow_controller(task_data, plugin_data, _pid):
    # 限制进程使用内存大小200MB
    # linux有效/macOS无效
    # 自测可把数值调小
    resource.setrlimit(resource.RLIMIT_AS, (250 * 1024 * 1024, 250 * 1024 * 1024))
    app_logger.debug('开始创建测试插件运行时流程控制器')
    # 获取父进程号以及子进程号并写入redis
    set_flag = model_redis_task_process_id.set(task_data['task_id'], _pid, os.getpid())
    if set_flag:
        app_logger.debug('测试任务所属父进程号%d及自身进程号%d数据入库成功' % (_pid, os.getpid()))
        # 首先实例化流程控制器
        flow_controller = FlowController(task_data, plugin_data)
        app_logger.debug('测试插件运行时流程控制器创建完成')
        # 然后处理内部虚拟用户事务准备运行
        flow_controller.init_vusers()
        # 如果递归初始化的结果是失败或者异常，则不执行run方法，进程结束
        if flow_controller.flow_init_result:
            app_logger.debug('测试开始')
            # 运行这个测试计划
            try:
                flow_controller.run()
            except MemoryError:
                flow_controller.trans_init_log('测试任务终止，内存溢出', 'ERROR')
                http_tell_test_task_status(task_id=task_data['task_id'], status=-3)
            except Exception as e:
                flow_controller.trans_init_log('测试任务终止，程序异常:%s' % repr(e), 'ERROR')
                http_tell_test_task_status(task_id=task_data['task_id'], status=-3)
        else:
            flow_controller.trans_init_log('测试任务终止，流处理器初始化失败', 'ERROR')
            http_tell_test_task_status(task_id=task_data['task_id'], status=-3)
    else:
        app_logger.debug('测试任务终止，测试任务所属父进程号及自身进程号入库失败')
        http_tell_test_task_status(task_id=task_data['task_id'], status=-3)


def kill_test_task_job(base_data):
    jobs = model_redis_task_job.query(base_data['task_id'])
    jobs_dict = json.loads(jobs)
    if not jobs_dict['add_task']['run']:
        test_task_scheduler.remove_job(jobs_dict['add_task']['id'])
        jobs_dict['add_task']['remove'] = True
        http_tell_test_task_status(task_id=base_data['task_id'], status=10)
        if 'kill_task' in jobs_dict:
            try:
                test_task_scheduler.remove_job(jobs_dict['kill_task']['id'], 'redis')
            except:
                pass
                # 任务已经执行
            finally:
                jobs_dict['kill_task']['run'] = True
                jobs_dict['kill_task']['remove'] = True
        model_redis_task_job.set(base_data['task_id'], json.dumps(jobs_dict))
    else:
        # 从redis中查询task_id对应的ppid以及pid
        ppid_pid = model_redis_task_process_id.query(base_data['task_id'])
        times = 0
        while not ppid_pid:
            time.sleep(2)
            ppid_pid = model_redis_task_process_id.query(base_data['task_id'])
            times += 1
            if times == 30:
                break
        if ppid_pid:
            proc_ppid, proc_pid = ppid_pid.split(':')
            # 尝试实例化pid，并查找ppid，与redis1中的数据进行比对
            try:
                p = psutil.Process(int(proc_pid))
                # 可以创建代表有这个进程
                # 查询它的父进程
                if p.ppid() == int(proc_ppid):
                    # kill
                    p.kill()
            except:
                # 无法创建则代表无此进程
                pass
            finally:
                # finish
                http_tell_test_task_status(
                    task_id=base_data['task_id'],
                    status=10
                )
                if 'kill_task' in jobs_dict:
                    try:
                        test_task_scheduler.remove_job(jobs_dict['kill_task']['id'], 'redis')
                    except:
                        pass
                        # 任务已经执行
                    finally:
                        jobs_dict['kill_task']['run'] = True
                        jobs_dict['kill_task']['remove'] = True
                        model_redis_task_job.set(base_data['task_id'], json.dumps(jobs_dict))


from lib.controller.flowController import FlowController
