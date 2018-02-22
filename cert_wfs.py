#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
@author: yunlong.lee
@contact: yunlong.lee@163.com
"""
import os
import sys
import time
import signal
import getopt
import datetime
import logging
import logging.handlers
import argparse
import pyinotify
import functools
import threading

#sysctl -n -w fs.inotify.max_user_watches=16384

print " __      _(_)_ __ | |_ ___ _ __  (_)___    ___ ___  _ __ ___ (_)_ __   __ _"
print " \ \ /\ / / | '_ \| __/ _ \ '__| | / __|  / __/ _ \| '_ ` _ \| | '_ \ / _` |"
print "  \ V  V /| | | | | ||  __/ |    | \__ \ | (_| (_) | | | | | | | | | | (_| |"
print "   \_/\_/ |_|_| |_|\__\___|_|    |_|___/  \___\___/|_| |_| |_|_|_| |_|\__, |"
print "                                                                      |___/"

parser = argparse.ArgumentParser()
parser = argparse.ArgumentParser(description='CERT MONITOR  by yunlong.lee@163.com')
parser.add_argument('-d', '--dir', help='the sample directory which is recursively monitored', type = str, required = True)
parser.add_argument('-m', '--mdir', help='monitor log directory that produced by extern tool', type = str, required = True)
parser.add_argument('-b', '--backgroud', help='run as daemon', action='store_true')
args = parser.parse_args()  

if not os.path.isdir( args.dir ):
    print 'the sample directory %s is not exist' % args.dir
    sys.exit(0)

if not os.path.isdir( args.mdir ):
    print 'monitor log file directory %s is not exist' % args.mdir
    sys.exit(0)


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
        #logging.info("timer start counter : %d" % counter.count)
        monitor_log_timer.start()  


class MyEventHandler(pyinotify.ProcessEvent):

    log_file = args.mdir + '/monitor.log'
    logger = logging.getLogger()
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when='M', interval=1, backupCount=1440)
    file_handler.suffix = "%Y%m%d-%H%M.log"
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    
    if args.backgroud == False:
        logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)
     
    def process_IN_ACCESS(self, event):
        logging.info("ACCESS event : %s" % (os.path.join(event.path, event.name)))
     
    def process_IN_ATTRIB(self, event):
        logging.info("IN_ATTRIB event : %s" % (os.path.join(event.path, event.name)))
     
    def process_IN_CLOSE_NOWRITE(self, event):
        logging.info("CLOSE_NOWRITE event : %s" % (os.path.join(event.path, event.name)))
     
    def process_IN_CLOSE_WRITE(self, event):
        if os.path.isdir(event.pathname) == False:
            logging.info("CLOSE_WRITE event : %s" % event.pathname)
     
    def process_IN_CREATE(self, event):
        if os.path.isdir(event.pathname) == False:
            logging.info("CREATE event : %s" % event.pathname)

    def process_IN_DELETE(self, event):
        logging.info("DELETE event : %s" % (os.path.join(event.path, event.name)))
     
    def process_IN_MOVED_FROM(self, event):
        logging.info("MOVE FROM event : %s" % (os.path.join(event.path, event.name)))

    def process_IN_MOVED_TO(self, event):
        logging.info("MOVED TO event : %s" % (os.path.join(event.path, event.name)))

    def process_IN_MOVE_SELF(self, event):
        logging.info("MOVE_SELF event : %s" % (os.path.join(event.path, event.name)))

    def process_IN_Q_OVERFLOW(self, event):
        logging.info("OVERFLOW event : %s" % (os.path.join(event.path, event.name)))

    def process_IN_MODIFY(self, event):
        logging.info("MODIFY event : %s" % (os.path.join(event.path, event.name)))
     
    def process_IN_OPEN(self, event):
        logging.info("OPEN event : %s" % (os.path.join(event.path, event.name)))


class MonitorTimer(threading.Thread):  
    ''''' 
    MonitorTimer is simulate the C++ settimer , 
    it need  pass funciton pionter into the class ,  
    timeout and is_loop could be default , or customized 
    '''  
    def __init__(self, function, args=None, timeout=1, is_loop=False):  
        threading.Thread.__init__(self)  
        self.event = threading.Event()  
        # inherent the funciton and args  
        self.function = function  
        self.args = args      # pass a tuple into the class  
        self.timeout = timeout  
        self.is_loop = is_loop  
  
    def run(self):  
        while not self.event.is_set():  
            self.event.wait(self.timeout) # wait until the time eclipse  
            self.function(self.args)  
            if not self.is_loop:  
                self.event.set()  
  
    def stop(self):  
        self.event.set()  


def monitor_time_event(args):
    ctime = time.time()
    if os.path.exists(args):
        mtime = os.path.getmtime(args)
        if ctime - mtime > 60:
            print "Last modified : %s, current time: %s" % (mtime, ctime)
            event_str = '2017-10-20 16:36:44 INFO CREATE event : /data/all_pack/samples/44/11/2/A42468.EXE'
            logging.info("CREATE event : %s" % event_str)
    
    if os.path.exists(args):
        cur_path = os.path.dirname(args) 
        for root, dirs, files in os.walk(cur_path):
            for fname in files:
                if fname == "monitor.log":
                    continue
                file_name = os.path.join(root,fname)
                mtime = os.path.getmtime(file_name)
                if ctime - mtime > 86400:
                    if os.path.exists(file_name):
                        print "remove the oldest monitor log file %s" % (file_name)
                        os.remove(file_name)


monitor_log_file    = os.getcwd() + '/mlog/monitor.log'
monitor_log_timer   = MonitorTimer(monitor_time_event, monitor_log_file, 10, True ) 

def handler(signum, frame):
    print 'Signal handler called with signal', signum
    monitor_log_timer.stop()

    pid_file = os.getcwd() + '/log/cert_wfs.pid'
    if os.path.exists(pid_file):
        os.remove(os.getcwd() + '/log/cert_wfs.pid')

    sys.exit(0)

def main():

    signal.signal(signal.SIGINT, handler)

    if args.backgroud == False:
        monitor_log_timer.start()  

    print "Starting monitor..."
    wm = pyinotify.WatchManager()
    #mask = pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE
    #mask = pyinotify.IN_CLOSE_WRITE
    mask = pyinotify.IN_CREATE
    wm.add_watch(args.dir, mask, rec=True, auto_add=True)
    on_loop_func = functools.partial(on_loop, counter=Counter())
    eh = MyEventHandler()
    notifier = pyinotify.Notifier(wm, eh)
    try:
        if args.backgroud:
            wfs_log_file = os.getcwd() + "/log/cert_wfs.log"
            wfs_pid_file = os.getcwd() + "/log/cert_wfs.pid"
            notifier.loop(daemonize = True, callback=on_loop_func, pid_file = wfs_pid_file, stderr = wfs_log_file)
        else:
            notifier.loop(daemonize = False)

    except pyinotify.NotifierError, err:
        print >> sys.stderr, err

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print ""
    pass
