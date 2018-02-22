import multiprocessing, Queue
import os
import time
from multiprocessing import Process, Pool
from time import sleep
from random import randint

class Producer(multiprocessing.Process):
    def __init__(self, queue):
        multiprocessing.Process.__init__(self)
        self.queue = queue
        
    def run(self):
        while True:
            self.queue.put('one product')
            print multiprocessing.current_process().name + str(os.getpid()) + ' produced one product, the no of queue now is: %d' %self.queue.qsize()
            sleep(randint(1, 3))
        
        
class Consumer(multiprocessing.Process):
    def __init__(self, queue):
        multiprocessing.Process.__init__(self)
        self.queue = queue
        
    def run(self):
        while True:
            d = self.queue.get(1)
            if d != None:
                print multiprocessing.current_process().name + str(os.getpid()) + ' consumed  %s, the no of queue now is: %d' %(d,self.queue.qsize())
                sleep(randint(1, 4))
                continue
            else:
                break
                
#create queue
queue = multiprocessing.Queue(40)
       
if __name__ == "__main__":
    print 'come on baby ...' 
    #create processes    
    processed = []
    for i in range(3):
        processed.append(Producer(queue))
        processed.append(Consumer(queue))
        
    #start processes        
    for i in range(len(processed)):
        processed[i].start()
    
    #join processes    
    for i in range(len(processed)):
        processed[i].join()  
