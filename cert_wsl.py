#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
@author     : yunlong.lee
@contact    : yunlong.lee@163.com
"""
#sysctl -n -w fs.inotify.max_user_watches=100000

import sys
import socket
import os
import datetime
import pyinotify
import logging
import logging.handlers
import time
import datetime
import signal
import hashlib
import collections
import argparse
import functools

import threading
import Queue
import random

import struct
import zmq
import msgpack
import json
import re
from ctypes import *

print " __      _(_)_ __ | |_ ___ _ __  (_)___    ___ ___  _ __ ___ (_)_ __   __ _"
print " \ \ /\ / / | '_ \| __/ _ \ '__| | / __|  / __/ _ \| '_ ` _ \| | '_ \ / _` |"
print "  \ V  V /| | | | | ||  __/ |    | \__ \ | (_| (_) | | | | | | | | | | (_| |"
print "   \_/\_/ |_|_| |_|\__\___|_|    |_|___/  \___\___/|_| |_| |_|_|_| |_|\__, |"
print "                                                                      |___/"

parser = argparse.ArgumentParser()
parser = argparse.ArgumentParser(description='CERT MONITOR  by yunlong.lee@163.com')
parser.add_argument('-d', '--dir', help = 'the sample directory which is recursively monitored', type = str)
parser.add_argument('-m', '--mdir', help = 'the monitor log file directory which is recursively monitored', type = str, required = True)
parser.add_argument('-t', '--thread', help = 'The number of threads concurrently', type = int)
parser.add_argument('-q', '--qlen', help = 'task queue size', type = int)
parser.add_argument('-w', '--delay', help = 'delay microseconds after push sample', type = int)
parser.add_argument('-s', '--idsvr', help = 'ident server addr', type = str)
parser.add_argument('-b', '--backgroud', help = 'run as daemon', action = 'store_true')
args = parser.parse_args()

def test_network( svr_addr ):
    req_addr = svr_addr.split(':')
    host = req_addr[0]
    port = req_addr[1]

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error, e:
        print "Strange error creating socket: %s = %s" % (e, svr_addr)
        sys.exit(1)

    try:
        port = int(port)
    except ValueError:
        print "Couldn't find your port: %s = %s" % (e, svr_addr)
        sys.exit(1)

    try:
        s.connect((host, port))
    except socket.gaierror, e:
        print "Address-related error connecting to server: %s = %s" % (e, svr_addr)
        sys.exit(1)
    except socket.error, e:
        print "Connection error: %s = %s" % (e, svr_addr)
        sys.exit(1)

    print 'test connect zserver %s ok' % ( svr_addr )

if args.idsvr:
    test_network( args.idsvr )
else: 
    test_network( '127.0.0.1:6666' )

if not args.delay:
    args.delay = 100

if not os.path.isdir( args.mdir ):
    print 'monitor log file directory %s is not exist' % args.mdir 
    print "create mlog directory please"
    sys.exit(0)

if args.backgroud:
    LOG_FILE = os.getcwd() + "/log/cert_wsl.log"
    logger = logging.getLogger()
    file_handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='D', interval=1, backupCount=30)
    file_handler.suffix = "%Y%m%d.log"
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    #logging.getLogger().addHandler(console)

LOG_DICT={"md5": "473c143b01c714f2158a73de8bd0eae4", "sha1": "cc9dd80174b56165ef31324b015cae65de6d9ba1", "path": "/home/liqi3-s/sample/0000000000000cf3", "filesize": 245143, "name": "0000000000000cf3"} #example
ZMQ_ADDR = "tcp://127.0.0.1:6666"

def dump_obj(obj):
    logging.info( '\t'.join(['%s:%s' % item for item in obj.__dict__.items()]) )

class ZmqClient(object):
    def __init__(self, zmq_addr):
        context = zmq.Context()
        sender = context.socket(zmq.PUSH)
        sender.setsockopt(zmq.LINGER, 0)  # 10 seconds
        sender.set_hwm(200000)
        sender.connect(zmq_addr)
        self.sender = sender

    def send(self, data):
        self.sender.send(data)


class ZMQWriter(object):
    def __init__(self, zmq_socket_addr):
        self.zmq_client = ZmqClient(zmq_socket_addr)

    @classmethod
    def _init_file(cls, filename):
        with open(filename, 'rb') as read_file:
            content = read_file.read()
            md5 = hashlib.md5(content).hexdigest()
            sha1 = hashlib.sha1(content).hexdigest()
            return content, md5, sha1

    @classmethod
    def _get_log_entry(cls, md5, sha1, filename, content, content_len):
        result = LOG_DICT
        result["md5"] = md5
        result["sha1"] = sha1
        result["filesize"] = content_len
        result["path"]=os.path.abspath(filename)
        result["name"]=os.path.split(filename)[-1]
        result["engine_sel"] = 118
        result["is_custom"] = 1

        return result

    def init_memory_content(self,filename,args):
        content, md5, sha1 = self._init_file(filename)
        content_len = len(content)

       # print "content len : %d" % content_len
        task_dict = self._get_log_entry(md5,sha1,filename,content,content_len)
        if task_dict == {}:
            logging.info("The sample is empty")
            exit(0)
        if "file_size" in task_dict:
            if task_dict["file_size"] >= 10485760:
                logging.info("The sample is large")
                exit(0)
        task_dict["content"] = content
        msg_data_buf = msgpack.dumps(task_dict)
        msg_len = len(msg_data_buf)
        format_string = "H%ds" % (msg_len)
        data_buff = create_string_buffer(msg_len+0x100)
        struct.pack_into(format_string,data_buff,0,27,msg_data_buf)
        return data_buff,2 + msg_len

    def write_memory(self, filename,args):
        data_buff, prelog_len = self.init_memory_content(filename,args)
        #logging.info("send %s pre_log_len %d to zmq" % (filename, prelog_len))
        self.zmq_client.send(data_buff.raw[:(prelog_len + 2)])
        return data_buff

    def write_dir_memory(self, dirname,args):
        for root_dir, _, filenames in os.walk(dirname):
            for filename in filenames:
                filepath = os.path.join(root_dir, filename)
                self.write_memory(filepath,args)

#zmq_writer = ZMQWriter(ZMQ_ADDR)
#zmq_writer = None
wcq = Queue.Queue(0) 
last_op_log_file = os.getcwd() + '/log/last_op_monitor_file.log'
delay_send_sec = float( args.delay ) / 1000

MAX_QUEUE_LEN = 50
MAX_WORKER_NUM = 2

class Worker(threading.Thread):  
    def __init__(self, queue, writer, delay):  
        threading.Thread.__init__(self)  
        self.wcq = queue  
        self.zmq_writer = writer 
        self.thread_stop = False  
        self.delay_sec = delay 
   
    def run(self):
        while not self.thread_stop:  
            try:  
                task_file = self.wcq.get(block=True, timeout=20)
                try:
                    if os.path.exists(task_file):
                        self.zmq_writer.write_memory(task_file, task_file)
                        logging.info("%s send task file %s to zserver" % (self.name, task_file))  
                        time.sleep( self.delay_sec )
                    else:
                        logging.info("%s send task file %s is not exist" % (self.name, task_file))  

                except Exception as err:
                    print "error happen: ", err
                    logging.error("%s" % err, exc_info=1)
                    self.thread_stop = True  
                    time.sleep(0.1)
                
                if os.path.exists(task_file):
                    os.remove( task_file )
                    logging.info("%s remove task file %s" % (self.name, task_file))  

                self.wcq.task_done()
                cq_len = self.wcq.qsize()
                if cq_len > 0:  
                    logging.info("%s there are still %d tasks in the task queue" % (self.name, cq_len))  
                else:
                    logging.info("%s there are still %d tasks in the task queue" % (self.name, cq_len))  

            except Queue.Empty:  
                logging.info("%s Nothing to do!" % (self.name)) 

    def stop(self):  
        self.thread_stop = True  
        logging.info("stop %s OK!" % (self.name)) 

def resume_monitor_log( fpath, delay_sec ):
    resume_info = []
    if os.path.exists(fpath):
        logging.info('loading last op monitor log file %s' % (fpath))
        
        f = open(fpath, "r")
        while True:
            line = f.readline()
            if line:
                resume_info = line.strip('\n').split('\t')
            else:
                break
        f.close()

        if resume_info:
            logging.info( 'resuming monitor log file %s\t%s\t%s' % (resume_info[0], resume_info[1], resume_info[2]) )
            monitor_file = resume_info[0]
            file_pos = int(resume_info[1])
            if os.path.exists( monitor_file ):
                process_monitor_file( monitor_file, file_pos, delay_sec )
            else:
                logging.info('resuming monitor log file %s is not exist' % (resume_info[0]))
        else:
            logging.info('resuming info is empty')
            
    else: 
        logging.info('last op monitor log file %s is not exist' % (fpath))
    
    return

    if args.dir:
        if not os.path.isdir(args.dir):
            return

        sample_path = args.dir
        for root , dirs, files in os.walk(sample_path):
            for name in files:
                sample_file = os.path.join(root, name)
                if os.path.exists(sample_file):
                    logging.info("main process deliver sample file %s to the task queue" % (sample_file))  
                    wcq.put(sample_file, block=True, timeout=20)
                    time.sleep( delay_sec )
                else:
                    logging.info("sample file is not exist %s" % (sample_file))  


def update_op_log(fpath, monitor_file, pos, time):

    resume_info = '\t'.join([monitor_file, str(pos), time]) + '\n'
    fp = open(last_op_log_file, 'w')
    fp.write(resume_info)
    fp.close()

def process_monitor_file( file_name, file_pos = 0, delay_sec = 0.1 ): 

    f = open(file_name, "r")
    f.seek(file_pos)
    while True:
        line = f.readline()
        if line:
            sample_file = line[line.find("/"):].strip('\n')
            if os.path.exists(sample_file):
                logging.info("main process deliver sample file %s to the task queue" % (sample_file))  
                wcq.put(sample_file, block=True, timeout=20)
                time.sleep( delay_sec )
            else:
                logging.info("sample file is not exist %s" % (sample_file))  

            update_op_log( last_op_log_file, file_name, f.tell(), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) )
        else:
            break
    f.close()  

    if os.path.exists(file_name):
        logging.info("fake remove monitor log file %s" % (file_name))  
        #os.remove(file_name)


class Counter(object):
    """
    Simple counter.
    """
    def __init__(self):
        self.count = 0
    def plusone(self):
        self.count += 1

def on_loop(notifier, counter):
    """
    Dummy function called after each event loop, this method only
    ensures the child process eventually exits (after 5 iterations).
    """
    #if counter.count > 4:
        # Loops 5 times then exits.
    #    sys.stdout.write("Exit\n")
    #    notifier.stop()
    #    sys.exit(0)
    #else:
    #    sys.stdout.write("Loop %d\n" % counter.count)
    #    counter.plusone()

    if counter.count > 0:
        pass
    else:
        sys.stdout.write("Loop %d\n" % counter.count)
        counter.plusone()
        init_sys_wsl()
        logging.info("timer start counter : %d" % counter.count)

class MyEventHandler(pyinotify.ProcessEvent):
    #if args.backgroud:
    #    LOG_FILE = os.getcwd() + "/log/cert_wsl.log"
    #    logger = logging.getLogger()
    #    file_handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='D', interval=1, backupCount=30)
    #    file_handler.suffix = "%Y%m%d.log"
    #    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    #    file_handler.setFormatter(formatter)
    #    logger.addHandler(file_handler)
    #    logger.setLevel(logging.INFO)
    #else:
    #    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    #    console = logging.StreamHandler()
    #    console.setLevel(logging.INFO)
    #    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    #    console.setFormatter(formatter)
        #logging.getLogger().addHandler(console)

    logging.info("Starting monitor...")


    def __init__(self, exec_pwd, delay):
        super(self.__class__, self).__init__()
        self.exec_pwd = exec_pwd
        self.delay_sec = delay 

    def process_IN_ACCESS(self, event):
        logging.info("ACCESS event : %s" % (os.path.join(event.path, event.name)))
     
    def process_IN_ATTRIB(self, event):
        logging.info("IN_ATTRIB event : %s" % (os.path.join(event.path,event.name)))
     
    def process_IN_CLOSE_NOWRITE(self, event):
        logging.info("CLOSE_NOWRITE event : %s" % (os.path.join(event.path,event.name)))
     
    def process_IN_CLOSE_WRITE(self, event):
        logging.info("CLOSE_WRITE event : %s" % (os.path.join(event.path,event.name)))
     
    def process_IN_CREATE(self, event):
        logging.info("CREATE event : %s" % (os.path.join(event.path,event.name)))
     
    def process_IN_MOVED_FROM(self, event):
        logging.info("MOVED FROM event : %s" % (os.path.join(event.path,event.name)))

    def process_IN_MOVED_TO(self, event):
        target = self.exec_pwd + '/mlog/' + event.name
        if os.path.isdir(target) == False:
            logging.info("MOVED TO event : %s" % target)
            if os.path.exists( target ):
                logging.info("process monitor file : %s" % target)
                process_monitor_file( target, 0, self.delay_sec )

    def process_IN_MOVE_SELF(self, event):
        logging.info("MOVE SELF event : %s" % (os.path.join(event.path,event.name)))

    def process_IN_Q_OVERFLOW(self, raw_event):
        logging.info("OVERFLOW event : %s" % (os.path.join(event.path,event.name)))

    def process_IN_IGNORED(self, raw_event):
        logging.info("IGNORED event : %s" % (os.path.join(event.path,event.name)))

    def process_IN_DELETE(self, event):
        logging.info("DELETE event : %s" % (os.path.join(event.path,event.name)))
     
    def process_IN_MODIFY(self, event):
        logging.info("MODIFY event : %s" % (os.path.join(event.path,event.name)))
     
    def process_IN_OPEN(self, event):
        logging.info("OPEN event : %s" % (os.path.join(event.path,event.name)))
     

def init_monitor_log( path, delay_sec ):     
    for root, dirs, files in os.walk(path):
        for fname in files:
            if fname == "monitor.log":
                continue
            file_name = os.path.join(root,fname)
            logging.info('loading monitor log file %s' % (file_name))  
            if os.path.exists( file_name ):
                process_monitor_file( file_name, 0, delay_sec )


workerPool = []

def handler(signum, frame):
    print 'Signal handler called with signal', signum

    for worker in workerPool:
        worker.stop()

    #while True:
    #    alive = False
    #    for worker in workerPool:
    #        alive = alive or worker.isAlive()
    #        if alive == True:
    #            break
    #    if not alive:
    #        break  
    #cq.join()

    pid_file = os.getcwd() + '/log/cert_wsl.pid'
    if os.path.exists( pid_file ):
        os.remove(os.getcwd() + '/log/cert_wsl.pid')

    sys.exit(0)


def init_sys_wsl():
    signal.signal(signal.SIGINT, handler)

    #global zmq_writer
    #zmq_writer = ZMQWriter(ZMQ_ADDR)
    
    global MAX_QUEUE_LEN
    max_queue_len = MAX_QUEUE_LEN
    if args.qlen:
        max_queue_len = args.qlen

    if max_queue_len < 30:
        MAX_QUEUE_LEN = 50
    else:
        MAX_QUEUE_LEN = max_queue_len

    global MAX_WORKER_NUM
    worker_num = MAX_WORKER_NUM 
    if args.thread:
        worker_num = args.thread
    if worker_num < 0:
        worker_num = MAX_WORKER_NUM 

    #wcq = Queue.Queue(0) 

    for x in range(worker_num):
        if args.idsvr:
            zmq_writer = ZMQWriter('tcp://' + args.idsvr)
            workerPool.append( Worker(wcq, zmq_writer, delay_send_sec) )
        else:
            zmq_writer = ZMQWriter(ZMQ_ADDR)
            workerPool.append( Worker(wcq, zmq_writer, delay_send_sec) )

    for worker in workerPool:
        worker.setDaemon(True)
        worker.start()

    resume_monitor_log( last_op_log_file, delay_send_sec ) 
    init_monitor_log( args.mdir, delay_send_sec )


def main():

    if not args.backgroud:
        init_sys_wsl()

    #Exclude patterns from list
    excl_lst = [args.mdir + '/monitor.log']
    excl = pyinotify.ExcludeFilter(excl_lst)
    wm = pyinotify.WatchManager()
    mask = pyinotify.IN_MOVED_TO
    wm.add_watch(args.mdir, mask, rec=True, auto_add=True, exclude_filter=excl)

    eh = MyEventHandler( os.getcwd(), delay_send_sec )
    notifier = pyinotify.Notifier(wm, eh)
    try:
        if args.backgroud:
            wfs_log_file = os.getcwd() + "/log/cert_wsl.log"
            wfs_pid_file = os.getcwd() + "/log/cert_wsl.pid"
            on_loop_func = functools.partial(on_loop, counter=Counter())
            notifier.loop(daemonize = True, callback = on_loop_func, pid_file = wfs_pid_file, stdout = wfs_log_file)
        else:
            notifier.loop(daemonize = False)
    except pyinotify.NotifierError, err:
        print >> sys.stderr, err


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
