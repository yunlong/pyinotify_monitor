#!/usr/bin/env python
# -*- coding:utf-8 -*-

import queue
import threading
import contextlib
import time

StopEvent = object()  # 线程池线程没有任务了，需要终止时使用，不是必要使用object类的

class ThreadPool(object):

    def __init__(self, max_num, max_task_num = None):

        # 指定最大队列则使用最大数，不指定则无限制
        # 这里创建的队列，是要装任务的，而不是线程
        if max_task_num:  
            self.q = queue.Queue(max_task_num)   
        else:
            self.q = queue.Queue()

        # 指定最多有多少个线程
        self.max_num = max_num   
        self.cancel = False
        self.terminal = False

        #保存当前已经创建了多少线程（假设线程池为10，你使用了2个，他就只有两个线程）
        self.generate_list = []   
        #当前空闲的进程
        self.free_list = []      

    def run(self, func, args, callback=None):

        """
        线程池执行一个任务
        :param func: 任务函数
        :param args: 任务函数所需参数
        :param callback: 任务执行失败或成功后执行的回调函数，回调函数有两个参数1、任务函数执行状态；2、任务函数返回值（默认为None，即：不执行回调函数）
        :return: 如果线程池已经终止，则返回True否则None
        """
        if self.cancel:
            return
        # 判断1：查看空闲线程列表还有没有空闲线程，有则不创建，无进入下一个判断，判断2：已经创建的线程，有没有大于最大可以创建的线程数，小于则创建
        if len(self.free_list) == 0 and len(self.generate_list) < self.max_num:   
            self.generate_thread()  

        # 将传入的将要执行的任务存入元组中
        w = (func, args, callback,) 
        self.q.put(w)  

    def generate_thread(self):

        """
        创建一个线程
        t对象封装了一个self.call函数，每一个线程在t.start时，都会执行call方法
        """
        t = threading.Thread(target=self.call)   
        t.start()

    def call(self):
        """
        循环去获取任务函数并执行任务函数
        """
        # 创建一个线程，就将线程保存到generate_list列表中
        current_thread = threading.currentThread
        self.generate_list.append(current_thread)   

        #取任务
        #取到任务不等于StopEvent，表示一直有任务，一直循环
        event = self.q.get()  
        while event != StopEvent: 

            #刚刚我们放入队列时，使用的是 （函数，元祖，函数），同样使用3个参数取出
            func, arguments, callback = event  
            try:
                #执行第一个函数
                result = func(*arguments) 
                success = True
            except Exception as e:
                success = False
                result = None

            if callback is not None:
                try:
                    #执行第二个函数
                    callback(success, result) 
                except Exception as e:
                    pass

            #当正常执行完以上函数后，我就去执行worker_state函数
            with self.worker_state(self.free_list, current_thread): 
                if self.terminal:
                    event = StopEvent
                else:
                    event = self.q.get()
        else:
            #当没有任务可取时，表示线程结束
            self.generate_list.remove(current_thread)  

    def close(self):
        """
        执行完所有的任务后，所有线程停止
        """
        self.cancel = True
        full_size = len(self.generate_list)
        while full_size:
            self.q.put(StopEvent)
            full_size -= 1

    def terminate(self):
        """
        无论是否还有任务，终止线程
        """
        self.terminal = True

        while self.generate_list:
            self.q.put(StopEvent)

        self.q.empty()

    @contextlib.contextmanager  # 上下文管理器
    def worker_state(self, state_list, worker_thread):
        """
        用于记录线程中正在等待的线程数
        """
        state_list.append(worker_thread)
        try:
            yield
        finally:
            state_list.remove(worker_thread)



pool = ThreadPool(5)
def callback(status, result):
    # status, execute action status
    # result, execute action return value
    pass


def action(i):
    print(i)

for i in range(300):
    ret = pool.run(action, (i,), callback)

time.sleep(5)
print(len(pool.generate_list), len(pool.free_list))
print(len(pool.generate_list), len(pool.free_list))
pool.close()
pool.terminate()
