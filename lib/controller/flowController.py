# -*- coding: utf-8 -*-

"""
测试插件运行时的流程控制器
"""

import datetime

from gevent.pool import Pool as GeventPool

from handler.log import app_logger
from handler.config import app_config

from lib.controller.asyncLogController import AsyncLogController
from lib.controller.syncLogController import SyncLogController
from lib.plugin import *
from lib.storage.parametersStorage import ParametersStorage

from request.http.tellTestTaskStatus import http_tell_test_task_status


class FlowController:
    def __init__(self, base_data, plugin_data):
        #
        self.flow_init_result = True
        # 将测试任务基础数据转换为多个变量
        self.base_data = base_data
        self.base_task_id = base_data['task_id']
        self.base_exc_times = base_data['exc_times']
        self.base_vuser_num = base_data['v_user']
        self.plugin_data = plugin_data
        self.worker_info_id = app_config.getint("worker", "id")
        self.worker_info = {"id": self.worker_info_id}
        self.gevent_pool = None
        http_tell_test_task_status(task_id=self.base_task_id, status=2)
        self.parameters_storage = ParametersStorage()
        # 实例化日志控制器
        self.init_log_controller = SyncLogController('tasklog', self.base_task_id, '_init')
        if self.init_log_controller.log_pool_make_result:
            app_logger.debug('测试任务ID:%d基础日志控制器初始化成功' % self.base_task_id)
            self.trans_init_log('基础日志控制器初始化成功')
        else:
            app_logger.error('测试任务ID:%d基础日志控制器初始化失败')
            self.flow_init_result = False
        self.run_log_controller = AsyncLogController('tasklog', self.base_task_id, '_run')
        if self.run_log_controller.log_pool_make_result:
            app_logger.debug('测试任务ID:%d运行日志控制器初始化成功' % self.base_task_id)
            self.trans_init_log('运行日志控制器初始化成功')
        else:
            app_logger.error('测试任务ID:%d运行日志控制器初始化失败')
            self.flow_init_result = False
        if self.flow_init_result:
            # 写一些环境信息
            self.trans_init_log("启动测试任务")
            # 递归原始数据
            self.trans_init_log("准备初始化各虚拟用户的插件树")
            # self.recurse_plugin_tree(plugin_data[0])
            # self.trans_init_log("插件及流程控制器初始化结束")
        else:
            http_tell_test_task_status(task_id=self.base_task_id, status=-2)

    def trans_init_log(self, msg, level=None):
        log = "%s %s Worker:%d " % (
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
            'INFO' if level is None else 'ERROR',
            self.worker_info_id
        ) + msg
        self.init_log_controller.trans(log)

    def init_plugin_tree(self, tree_data, vuser_index=None):
        # 只在首次初始化插件树用以数据检查的时候才会用
        not vuser_index and self.trans_init_log("准备初始化插件树")

        def recurse_plugin_tree(_data, parent_node=None):
            """
            递归初始化插件树
            :param _data: 插件原始数据
            :param parent_node: 父级节点实例
            :return: 无返回
            """
            # 对于暂不支持的插件，忽略其初始化
            if _data['originalId'] in all_plugins:
                if _data['status'] is True:
                    self_plugin = all_plugins[_data['originalId']](
                        base_data=self.base_data,
                        plugin_data=_data,
                        worker_info=self.worker_info,
                        vuser_index=vuser_index if vuser_index else 0,
                        parent_node=parent_node,
                        init_log_ctrl=self.init_log_controller,
                        run_log_ctrl=self.run_log_controller,
                        parameter_ctrl=self.parameters_storage
                    )
                    if not self_plugin.plugin_check_result:
                        self.flow_init_result = False
                    not vuser_index and self.trans_init_log("插件'%s'初始化结果:%s" % (
                        self_plugin.plugin_title,
                        '成功' if self_plugin.plugin_check_result else ('失败,%s' % self_plugin.plugin_check_log)
                    ))
                    if "children" in _data:
                        for child in _data["children"]:
                            recurse_plugin_tree(child, self_plugin)
                    if parent_node is None:
                        return self_plugin
                    else:
                        if self_plugin.__class__.__bases__[0] in [ConfigurationPlugin, ParameterPlugin]:
                            parent_node.plugins_configuration.append(self_plugin)
                        elif self_plugin.__class__.__bases__[0] in [PreprocessorPlugin]:
                            parent_node.plugins_preprocessor.append(self_plugin)
                        elif self_plugin.__class__.__bases__[0] in [ControllerPlugin, RequestPlugin, TimerPlugin]:
                            parent_node.plugins_common.append(self_plugin)
                        elif self_plugin.__class__.__bases__[0] in [AssertionPlugin]:
                            parent_node.plugins_assertion.append(self_plugin)
                        elif self_plugin.__class__.__bases__[0] in [PostprocessorPlugin]:
                            parent_node.plugins_postprocessor.append(self_plugin)
            else:
                not vuser_index and self.trans_init_log("插件'%s'初始化结果:%s" % (_data['title'], '失败,插件暂不支持'))
                self.flow_init_result = False

        plugin_tree = recurse_plugin_tree(tree_data)
        not vuser_index and self.trans_init_log("插件树初始化完毕")
        return plugin_tree

    def vuser_excute(self, tree):
        # 不同的线程之间共用self.base_exc_times会导致执行时间误减
        base_exc_times = self.base_exc_times
        # 执行次数
        while base_exc_times > 0:
            tree.run_test()
            base_exc_times -= 1

    def init_vusers(self):
        # 首先初始化出来一颗原始的插件树用以基本检查
        self.init_plugin_tree(self.plugin_data[0])
        # 如果基本初始化失败则不操作协程池
        if self.flow_init_result:
            # 初始化协程池
            try:
                self.gevent_pool = GeventPool(self.base_vuser_num)
            except Exception as e:
                msg = '测试任务虚拟用户并发池创建失败:%s' % repr(e)
                self.flow_init_result = False
                app_logger.error(msg)
                self.trans_init_log(msg)
            else:
                msg = '测试任务虚拟用户并发池创建成功'
                app_logger.debug(msg)
                self.trans_init_log(msg)
                vuser_index = 1
                free_count = self.gevent_pool.free_count()
                while free_count > 0:
                    # 每个虚拟用户拥有属于自己的插件树，互不干扰
                    plugin_tree = self.init_plugin_tree(self.plugin_data[0], vuser_index)
                    self.gevent_pool.spawn(self.vuser_excute, plugin_tree)
                    self.trans_init_log("虚拟用户%d准备完毕" % vuser_index)
                    vuser_index += 1
                    free_count -= 1

    def run(self):
        # 调测阶段直接回写结束
        http_tell_test_task_status(task_id=self.base_task_id, status=3)
        self.gevent_pool.join()
        self.run_log_controller.cancel()
        self.trans_init_log("测试结束")
        http_tell_test_task_status(task_id=self.base_task_id, status=10)
