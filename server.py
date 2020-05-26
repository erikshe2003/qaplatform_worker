# -*- coding: utf-8 -*-

import os
import socketserver
import psutil
import datetime
import struct
import json
import zipfile

from handler.log import app_logger
from handler.config import app_config
from handler.scheduler import new_test_task_job, kill_test_task_job
from handler.scheduler.testTaskScheduler import test_task_scheduler

from model.worker.redis import model_redis_test_task
from model.worker.redis import model_redis_task_job

"""
    数据格式
        action
            20s - 请求动作
        newTestTask
            i - task_id测试任务编号
            i - v_user虚拟用户数
            i - ramp_up虚拟用户全部唤醒时间
            i - start_type启动类型
            i - stop_type停止类型
            i - if_error出错后续
            i - exc_times执行次数
            q - file_size压缩包大小
            20s - start_time开始时间
            20s - end_time结束时间
        stopTestTask
            i - task_id测试任务编号
"""
dataFormat = {
    'action': '20s',
    'newTestTask': 'iiiiiiiq20s20s',
    'stopTestTask': 'i'
}


class WorkerServer(socketserver.StreamRequestHandler):
    @staticmethod
    def struct_unpack(package):
        """
        解包内容，并根据包内action决定执行哪个方法
        :param package: 测试任务名称/...
        :return: action(string)
        """
        app_logger.debug('准备解包')
        try:
            action = struct.unpack(dataFormat['action'], package)[0]
        except Exception as e:
            app_logger.warn('解包异常:%s' % repr(e))
            return 'error'
        else:
            return action.decode().strip('\x00')

    @staticmethod
    def check_task_id(package):
        """
        :param package: 包内需包含task_id测试任务id
        :return: True, {}/False, None
        """
        # 接收的struct数据中，s需要解码，i不需要解码
        try:
            task_id = struct.unpack(
                dataFormat['stopTestTask'],
                package
            )
        except Exception as e:
            app_logger.error('解包异常:' + repr(e))
            return False, None
        else:
            return True, {
                'task_id': task_id[0]
            }

    @staticmethod
    def check_test_task(package):
        """
        :param package: 包内需包含task_name测试任务名称/v_user虚拟用户数/start_type启动类型
                        stop_type停止类型/if_error出错后续/start_time开始时间/end_time结束时间
        :return: True, 解包后的数据/False, None
        """
        # 接收的struct数据中，s需要解码，i不需要解码
        try:
            tid, u, up, st1, st2, ie, exct, fs, st, et = struct.unpack(
                dataFormat['newTestTask'],
                package
            )
            st = st.decode().strip('\x00')
            et = et.decode().strip('\x00')
        except Exception as e:
            app_logger.error('解包异常:' + repr(e))
            return False, None
        else:
            return True, {
                'task_id': tid,
                'v_user': u,
                'ramp_up': up,
                'start_type': st1,
                'stop_type': st2,
                'if_error': ie,
                'exc_times': exct,
                'file_size': fs,
                'start_time': None if st == '' or st == 'None' else st,
                'end_time': None if et == '' or et == 'None' else et
            }

    @staticmethod
    def file_dir_handle(_data):
        """
        :return: True, 创建成功的测试任务目录路径(str)/False, None
        """
        # 检查文件存放路径
        the_now = datetime.datetime.now()
        the_year_path = '%s/%d' % (app_config.get('file', 'path'), the_now.year)
        the_month = the_now.month
        the_day = the_now.day
        if not os.path.exists(the_year_path):
            app_logger.debug('年份文件夹不存在，尝试创建...')
            try:
                os.makedirs(the_year_path)
            except Exception as e:
                app_logger.error('年份文件夹创建失败:%s' % repr(e))
                return False, None
            else:
                app_logger.debug('年份文件夹创建成功')
        if not os.path.exists('%s/%d' % (the_year_path, the_month)):
            app_logger.debug('月份文件夹不存在，尝试创建...')
            try:
                os.makedirs('%s/%d' % (the_year_path, the_month))
            except Exception as e:
                app_logger.error('月份文件夹创建失败:' + repr(e))
                return False, None
            else:
                app_logger.debug('月份文件夹创建失败')
        if not os.path.exists('%s/%d/%d' % (the_year_path, the_month, the_day)):
            app_logger.debug('日子文件夹不存在，尝试创建...')
            try:
                os.makedirs('%s/%d/%d' % (the_year_path, the_month, the_day))
            except Exception as e:
                app_logger.error('日子文件夹创建失败:' + repr(e))
                return False, None
            else:
                app_logger.debug('日子文件夹创建成功')
        task_dir_path = '%s/%d/%d/task_%d_%s' % (
            the_year_path,
            the_month,
            the_day,
            _data['task_id'],
            the_now.strftime('%Y%m%d%H%M%S')
        )
        try:
            os.makedirs(task_dir_path)
        except Exception as e:
            app_logger.error('测试任务文件夹创建失败:' + repr(e))
            return False, None
        else:
            app_logger.debug('测试任务文件夹创建成功')
            return True, task_dir_path

    def insert_test_task(self, base_data):
        # 准备向redis中插入新增task数据
        insert_result = model_redis_test_task.set(base_data['task_id'], json.dumps(base_data, ensure_ascii=False))
        if insert_result:
            return True
        else:
            app_logger.error('测试任务数据写入redis失败')
            self.request.send(str.encode('Failure'))
            self.request.close()

    def handle(self):
        # --- client发起connet请求，handler检测到后开始执行下面代码
        app_logger.debug('收到来自IP:%s的请求' % self.client_address[0])
        # --- connet请求代码末
        # --- 第1次send/recv开始
        app_logger.debug('准备接收第1次数据传输...')
        # --- recv方法阻塞handler，程序进入监听数据状态
        # 根据内容长度接受内容
        action_struct_data = self.request.recv(struct.calcsize(dataFormat['action']))
        # --- clent发起第1次send，handler检测到后开始执行下面代码
        app_logger.debug('接收到第1次数据传输')
        # 第1次recv接收的数据为请求类型action
        # 预备数据接收到内容不为空才可继续执行
        if action_struct_data:
            # 解包内容
            request_action = self.struct_unpack(action_struct_data)
            """
            当前支持action
            1.newTestTask 新测试任务
            2.stopTestTask stopTestTask
            其余字符串一律返回错误信息
            """
            if request_action == 'newTestTask':
                app_logger.debug('action为新测试任务')
                # 回传成功状态
                # 检查系统当前资源
                # 如果内存剩余不足500MB，则禁止创建测试任务
                if int(psutil.virtual_memory().available / 1024 / 1024) < 500:
                    app_logger.warn('测试机剩余内存不足，无法创建测试任务')
                    self.request.send(str.encode('Failure.测试机剩余内存不足，无法创建测试任务'))
                    self.request.close()
                else:
                    self.request.send(str.encode('Success'))
                    # --- 第1次send/recv结束
                    app_logger.debug('准备接收第2次数据传输...')
                    # --- recv方法阻塞handler，程序进入监听数据状态
                    # 根据内容长度接受内容
                    base_struct_data = self.request.recv(struct.calcsize(dataFormat[request_action]))
                    app_logger.debug('接收到第2次数据传输')
                    # --- clent发起第2次send，handler检测到后开始执行下面代码
                    # 检查新增测试任务数据基础信息
                    check_result, base_data = self.check_test_task(base_struct_data)
                    if check_result:
                        # 第2次测试任务基础数据检查通过后，新增测试任务目录，用以存放相关文件，然后再返回状态数据
                        handle_flag, task_dir_path = self.file_dir_handle(base_data)
                        if handle_flag:
                            # 回传成功状态
                            app_logger.debug('测试任务文件夹处理成功')
                            self.request.send(str.encode('Success'))
                            # --- 第2次send/recv结束
                            # 准备接收task文件
                            recvd_size = 0
                            file = open(task_dir_path + '.zip', 'wb')
                            app_logger.debug('准备接收第3次数据传输...')
                            while not recvd_size == base_data['file_size']:
                                if base_data['file_size'] - recvd_size > 1024:
                                    # --- recv方法阻塞handler，程序进入监听数据状态
                                    rdata = self.request.recv(1024)
                                    recvd_size += len(rdata)
                                else:
                                    rdata = self.request.recv(base_data['file_size'] - recvd_size)
                                    recvd_size = base_data['file_size']
                                file.write(rdata)
                                file.flush()
                            file.close()
                            app_logger.debug('接收到第3次数据传输')
                            # 解压缩文件
                            try:
                                with zipfile.ZipFile(task_dir_path + '.zip') as zfile:
                                    zfile.extractall(path=task_dir_path)
                            except Exception as e:
                                app_logger.error('压缩包处理失败:' + repr(e))
                                self.request.send(str.encode('Failure.测试任务压缩包处理失败，测试任务创建失败'))
                                self.request.close()
                            else:
                                app_logger.debug('压缩包处理成功')
                                # 新增测试任务数据
                                base_data['file_path'] = task_dir_path
                                # 0未启动/1运行中/2已结束
                                base_data['run_status'] = 0
                                self.insert_test_task(base_data)
                                # 新增定时测试任务
                                add_task = test_task_scheduler.add_job(
                                    func=new_test_task_job,
                                    args=[base_data],
                                    trigger='date',
                                    jobstore='redis',
                                    next_run_time=datetime.datetime.strptime(
                                        base_data['start_time'], '%Y-%m-%d %H:%M:%S'
                                    ) if base_data['start_time'] else datetime.datetime.now(),
                                    misfire_grace_time=3000
                                )
                                # 如果有结束时间，则还需创建kill的job
                                kill_task = None
                                if base_data['end_time']:
                                    kill_task = test_task_scheduler.add_job(
                                        func=kill_test_task_job,
                                        args=[base_data],
                                        trigger='date',
                                        jobstore='redis',
                                        next_run_time=datetime.datetime.strptime(
                                            base_data['end_time'], '%Y-%m-%d %H:%M:%S'),
                                        misfire_grace_time=3000
                                    )
                                # 定时任务信息存入redis
                                # run默认为false
                                job_value = {
                                    'add_task': {
                                        '_jobstore_alias': add_task._jobstore_alias,
                                        'id': add_task.id,
                                        'next_run_time': add_task.next_run_time.strftime('%Y-%m-%d %H:%M:%S'),
                                        'run': False,
                                        'remove': False
                                    }
                                }
                                if kill_task:
                                    job_value['kill_task'] = {
                                        '_jobstore_alias': kill_task._jobstore_alias,
                                        'id': kill_task.id,
                                        'next_run_time': kill_task.next_run_time.strftime('%Y-%m-%d %H:%M:%S'),
                                        'run': False,
                                        'remove': False
                                    }
                                set_result = model_redis_task_job.set(
                                    base_data['task_id'], json.dumps(job_value, ensure_ascii=False))
                                if set_result:
                                    self.request.send(str.encode('Success'))
                                    # --- 第三次send/recv结束
                                    self.request.close()
                                else:
                                    self.request.send(str.encode('Failure.测试任务入库失败，无法创建测试任务'))
                                    self.request.close()
                        else:
                            app_logger.warn('测试任务文件夹处理失败')
                            self.request.send(str.encode('Failure.测试任务文件夹处理失败，无法创建测试任务'))
                            self.request.close()
                    else:
                        app_logger.warn('测试任务数据检查失败')
                        self.request.send(str.encode('Failure.测试任务基础数据检查失败，无法创建测试任务'))
                        self.request.close()
            elif request_action == 'stopTestTask':
                app_logger.debug('action为强制停止测试任务')
                self.request.send(str.encode('Success'))
                # --- 第一次send/recv结束
                # --- handler进入监听状态，程序阻塞
                app_logger.debug('listen second send from client...')
                # 根据action选择内容长度并接受内容
                base_info_size = struct.calcsize(dataFormat[request_action])
                base_struct_data = self.request.recv(base_info_size)
                # --- clent发起第二次send，handler检测到后开始执行下面代码
                # 检查新增测试任务数据基础信息
                check_result, base_data = self.check_task_id(base_struct_data)
                if check_result:
                    # 调用终止进程方法
                    kill_test_task_job(base_data)
                    self.request.send(str.encode('Success'))
                    # --- 第二次send/recv结束
                    self.request.close()
                else:
                    self.request.send(str.encode('Failure.测试任务ID检查失败，无法终止测试任务'))
                    self.request.close()
            elif request_action == 'test':
                app_logger.debug('action为测试连接状态')
                self.request.send(str.encode('Success'))
                self.request.close()
            else:
                app_logger.warn('action内容为空或非法')
                self.request.send(str.encode('Failure.操作暂不支持'))
                self.request.close()
        else:
            app_logger.warn('首次数据传输内容为空')
            self.request.send(str.encode('Failure.接收到空数据'))
            self.request.close()
