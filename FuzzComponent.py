#!/usr/bin/env python      
# -*- coding: gbk -*-
from drozer.modules import Module, common
from drozer import android
import time

__author__ = 'zhouliwei'

"""
function: 用于对Android组件进行调用，发送空action或者启动Activity
          主要针对Activity，service，broadcastReceiver
date:2017/7/14

"""


class Fuzz(Module, common.Filters, common.PackageManager, common.Provider, common.TableFormatter, common.Strings,
           common.ZipFile, common.FileSystem, common.IntentFilter):
    name = "fuzz component"
    description = "fuzz Activity, service, broadcastReceiver"
    examples = ""
    author = "zlw (zlw@xdja.com)"
    date = "2017-7-14"
    license = "BSD (3-clause)"
    path = ["xdja", "safe"]

    execute_interval = 10

    actions = ['android.intent.action.MAIN',
               'android.intent.action.VIEW',
               'android.intent.action.ATTACH_DATA',
               'android.intent.action.EDIT',
               'android.intent.action.PICK',
               'android.intent.action.CHOOSER',
               'android.intent.action.GET_CONTENT',
               'android.intent.action.DIAL',
               'android.intent.action.CALL',
               'android.intent.action.SEND',
               'android.intent.action.SENDTO',
               'android.intent.action.ANSWER',
               'android.intent.action.INSERT',
               'android.intent.action.DELETE',
               'android.intent.action.RUN',
               'android.intent.action.SYNC',
               'android.intent.action.PICK_ACTIVITY',
               'android.intent.action.SEARCH',
               'android.intent.action.WEB_SEARCH',
               'android.intent.action.FACTORY_TEST',
               'android.intent.action.TIME_TICK',
               'android.intent.action.TIME_CHANGED',
               'android.intent.action.TIMEZONE_CHANGED',
               'android.intent.action.BOOT_COMPLETED',
               'android.intent.action.PACKAGE_ADDED',
               'android.intent.action.PACKAGE_CHANGED',
               'android.intent.action.PACKAGE_REMOVED',
               'android.intent.action.PACKAGE_RESTARTED',
               'android.intent.action.PACKAGE_DATA_CLEARED',
               'android.intent.action.UID_REMOVED',
               'android.intent.action.BATTERY_CHANGED',
               'android.intent.action.ACTION_POWER_CONNECTED',
               'android.intent.action.ACTION_POWER_DISCONNECTED',
               'android.intent.action.ACTION_SHUTDOWN',
               'android.net.conn.CONNECTIVITY_CHANGE']  # Last 3 are the exception to the rule

    def add_arguments(self, parser):
        android.Intent.addArgumentsTo(parser)
        parser.add_argument("-p", "--package", default=None, help="The Package Name")

    """
      the Function to execute
    """

    def execute(self, arguments):
        # 先判断是否输入了package
        if arguments.package is None:
            self.stdout.write("请通过-p指定测试包名！！\n\n")
        else:
            package = self.packageManager().getPackageInfo(arguments.package,
                                                           common.PackageManager.GET_ACTIVITIES | common.PackageManager.GET_RECEIVERS | common.PackageManager.GET_PROVIDERS | common.PackageManager.GET_SERVICES)
            # 先对provider进行处理，因为一般provider比较少
            self.__handle_providers(arguments, package)

            # 对Activity进行处理
            self.__handle_activity(arguments, package)

            # 对service进行处理
            self.__handle_service(arguments, package)

            # 对broadcastReceiver进行处理
            self.__handle_receivers(arguments, package)

    """
        对broadReceiver进行处理
    """

    def __handle_receivers(self, arguments, package):
        self.stdout.write("===================开始测试broadcastReceiver===================== \n\n")
        exported_receivers = self.match_filter(package.receivers, 'exported', True)
        if len(exported_receivers) > 0:
            self.stdout.write("  %d broadcast receivers exported\n " % len(exported_receivers))

            # 启动broadcast Receivers
            for receivers in exported_receivers:
                self.stdout.write(" 启动ContentProvider %s \n" % receivers.name)
                # 发送空 action的receiver
                self.__start_receivers(package, receivers.name)
                # 两个操作之间间隔一段时间
                time.sleep(self.execute_interval)
                # 发送不带Extras的receiver
                self.__start_receivers_with_action(package, receivers.name, receivers)
                time.sleep(self.execute_interval)

        else:
            self.stdout.write(" No exported BroadcastReceiver .\n\n")
        self.stdout.write("===================结束测试broadcastReceiver===================== \n\n")

    """
        启动broadCastReceiver，使用component启动。
        no action    no extras
    """

    def __start_receivers(self, package, receiver_name):
        intent = self.new("android.content.Intent")
        comp = (package.packageName, receiver_name)
        com = self.new("android.content.ComponentName", *comp)
        intent.setComponent(com)
        self.getContext().sendBroadcast(intent)

    """
        发送带action的receiver
    """

    def __start_receivers_with_action(self, package, receiver_name, receiver):
        intent = self.new("android.content.Intent")
        comp = (package.packageName, receiver_name)
        com = self.new("android.content.ComponentName", *comp)
        intent.setComponent(com)
        # 获取action
        intent_filters = self.find_intent_filters(receiver, 'receiver')
        for intent_filter in intent_filters:
            if len(intent_filter.actions) > 0:
                self.stdout.write("%s  has Actions:\n" % receiver_name)
                for action in intent_filter.actions:
                    try:
                        # 将系统的action过滤掉
                        if self.actions.index(action) > 0:
                            continue
                    except ValueError:
                        # 如果不存在说明是自定义的action，就启动。
                        try:
                            intent.setAction(action)
                            self.getContext().sendBroadcast(intent)
                            break
                        except Exception:
                            continue

    """
       对service进行处理
    """

    def __handle_service(self, arguments, package):
        self.stdout.write("===================开始测试service===================== \n\n")
        exported_services = self.match_filter(package.services, 'exported', True)
        if len(exported_services) > 0:
            self.stdout.write("  %d services exported\n " % len(exported_services))

            # 启动Service
            for service in exported_services:
                self.stdout.write(" 启动exported service %s \n" % service.name)
                self.__start_service(service.name, arguments, package)
                time.sleep(self.execute_interval)

        else:
            self.stdout.write(" No exported services.\n\n")

        self.stdout.write("===================完成测试Service===================== \n\n")

    """
        启动service，默认只是去开启service，不传递参数,使用component启动。
    """

    def __start_service(self, service_name, arguments, package):
        intent = self.new("android.content.Intent")
        comp = (package.packageName, service_name)
        com = self.new("android.content.ComponentName", *comp)
        intent.setComponent(com)
        self.getContext().startService(intent)

    """
        检查apk中是否有导出的Activity
    """

    def __handle_activity(self, arguments, package):
        self.stdout.write("===================开始测试Activity===================== \n\n")
        exported_activitys = self.match_filter(package.activities, 'exported', True)
        if len(exported_activitys) > 0:
            self.stdout.write("  %d activities exported\n" % len(exported_activitys))

            # 执行Activity启动
            for activity in exported_activitys:
                self.stdout.write("启动exported activity %s \n" % activity.name)
                self.__start_activity(arguments, package, activity.name)
                # 暂停10s再执行下一个
                time.sleep(self.execute_interval)
        else:
            self.stdout.write(" No exported activity.\n\n")

        self.stdout.write("===================结束测试Activity===================== \n\n")

    """
        启动Activity
    """

    def __start_activity(self, arguments, package, activity_name):
        try:
            intent = self.new("android.content.Intent")
            comp = (package.packageName, activity_name)
            com = self.new("android.content.ComponentName", *comp)
            intent.setComponent(com)
            intent.setFlags(0x10000000)
            self.getContext().startActivity(intent)
        except Exception:
            self.stderr.write("%s need some premission or other failure. \n " % activity_name)

    """
          获取所有导出的providers
          然后读取
    """

    def __handle_providers(self, arguments, package):
        self.stdout.write("===================开始测试Contentprovider===================== \n\n")
        exported_providers = self.match_filter(package.providers, 'exported', True)
        if len(exported_providers) > 0:
            self.stdout.write("  %d content providers exported\n" % len(exported_providers))
            # 去获取可以查询的uri
            for provider in exported_providers:
                self.stdout.write(" 开始查询 exported provider %s \n " % provider.name)
                self.__get_read_URi(arguments, package)
        else:
            self.stdout.write(" No exported providers.\n\n")
        self.stdout.write("===================结束测试Contentprovider===================== \n\n")

    """
        获取所有可以访问的ContentProvider的uri
    """

    def __get_read_URi(self, arguments, package):
        # attempt to query each content uri
        for uri in self.findAllContentUris(arguments.package):
            try:
                self.stdout.write("开始查询 exported provider %s \n " % uri)
                response = self.contentResolver().query(uri)
                time.sleep(self.execute_interval)
            except Exception:
                response = None

            if response is None:
                self.stdout.write("Unable to Query  %s\n" % uri)
            else:
                self.stdout.write("Able to Query    %s\n" % uri)
                # 直接去查询数据
                self.stdout.write("开始查询 uri %s 对应的数据 \n" % uri)
                self.__read_data_from_uri(uri)

    """
        如果uri是可以读取的，那么就从uri尝试读取数据，并将数据打印出来。
    """

    def __read_data_from_uri(self, uri):
        c = self.contentResolver().query(uri, None, None, None, None)

        if c is not None:
            rows = self.getResultSet(c)
            # 打印表数据
            self.print_table(rows, show_headers=True, vertical=False)
        else:
            self.stdout.write("Unknown Error.\n\n")

    """
        获取所有导出的Activity
    """

    def __get_activities(self, arguments, package):
        exported_activities = self.match_filter(package.activities, 'exported', True)
        if len(exported_activities) > 0:
            return exported_activities
        else:
            self.stdout.write(" No exported activities.\n\n")

    """
        获取所有导出的services
    """

    def __get_services(self, arguments, package):
        exported_services = self.match_filter(package.services, "exported", True)
        if len(exported_services) > 0:
            return exported_services
        else:
            self.stdout.write(" No exported services.\n\n")

    """
        获取所有导出的广播
    """

    def __get_receivers(self, arguments, package):
        exported_receivers = self.match_filter(package.receivers, 'exported', True)
        if len(exported_receivers) > 0:
            return exported_receivers
        else:
            self.stdout.write(" No exported receivers.\n\n")
