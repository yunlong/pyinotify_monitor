 __      _(_)_ __ | |_ ___ _ __  (_)___    ___ ___  _ __ ___ (_)_ __   __ _
 \ \ /\ / / | '_ \| __/ _ \ '__| | / __|  / __/ _ \| '_ ` _ \| | '_ \ / _` |
  \ V  V /| | | | | ||  __/ |    | \__ \ | (_| (_) | | | | | | | | | | (_| |
   \_/\_/ |_|_| |_|\__\___|_|    |_|___/  \___\___/|_| |_| |_|_|_| |_|\__, |
                                                                      |___/




python -m py_compile cert_wfs.py
python -m py_compile cert_wsl.py
#sysctl -n -w fs.inotify.max_user_watches=100000
安装步骤：
准备：
1. tar zxvf ctoolbox.tar.gz
2. cd ctoolbox/pyinotify
3. python setup.py install

部署样本推送日志生产服务:
1. python cert_wfs.py -h

usage: cert_wfs.pyc [-h] -d DIR -m MLOG [-b]

python MONITOR by yunlong.lee@163.com

optional arguments:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     the directory which is recursively monitored  #样本推送监控目录( 支持递归监控 )
  -m MLOG, --mlog MLOG  monitor log dir                               #样本推送日志生产目录(monitor.log 或 monitor.log.20171019-1439.log)
  -b, --backgroud       run as daemon                                 #后台运行服务

执行方法:
前台运行：（ QA 验证调试用 ）
python cert_wfs.pyc -d /data/all_pack/samples/ -m mlog/ 
后台运行：
python cert_wfs.pyc -d /data/all_pack/samples/ -m mlog/ -b


部署样本推送日志消费服务: ( 默认开启2线程, 减轻鉴定器压力 )
1. python cert_wsl.pyc -h

usage: cert_wsl.py [-h] -d DIR [-t THREAD] [-q QLEN] [-b]

optional arguments:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     the directory which is recursively monitored #样本推送日志消费目录(monitor.log 或 monitor.log.20171019-1439.log)
  -t THREAD, --thread THREAD                                         #worker数
                        The number of threads concurrently
  -q QLEN, --qlen QLEN  task queue size                              #任务队列大小
  -b, --backgroud       run as daemon                                #后台运行服务

执行方法:
前台运行（ QA 验证调试用 ）
python cert_wsl.pyc -d mlog/     
后台运行：
python cert_wsl.pyc -d mlog/ -b


验证方法：
1. 建立目录 /data/all_pack/samples
2. 拷贝样本文件至 /data/all_pack/sample    
3. 自动生成样本推送日志，并自定消费推送日志， 推送样本给鉴定器

changelog:

1. cert_wfs.pyc 样本推送日志生产服务
    1.1 加入送日志monitor.log按分钟强制切割机制，保证推送日志最小分钟级别被消费及时推送至鉴定器 
    1.2 重写timer检测线程类，保证主线程和timer线程资源被同步释放
    1.3 主线程加入检测事件回调机制
   

2. cert_wsl.pyc 样本推送日志消费服务
    2.1 加入崩溃回退恢复功能， 如果服务崩溃， 记录上次的消费点： 文件名, 位置
last_op_file_pos.log样本回扫功能，自动回扫样本推送目录发送至鉴定器
    2.2 加入崩溃恢复样本回扫功能，自动回扫样本推送目录发送至鉴定器
    2.3 根据推送样本量, 可灵活配置消费线程个数
    2.4 根据推送样本量, 可灵活配置消费队列大小

3. cert_wfs.pyc 样本推送日志生产服务
    3.1 将timer检测线程启动加入到主进程fork后的子进程内部做callback, 保证主进程fork后台运行, 能够定时强制切割推送日志
    3.2 推送日志清理机制调整1440, 保留最近1440分钟的推送日志

4. cert_wsl.pyc 样本推送日志消费服务
    4.1 将服务初始化加入到主进程fork后的子进程内部做callback, fork后的子进程能够共享消费队列及所有系统初始配置

5. cert_wsl.pyc 样本推送日志消费服务
    5.1 加入启动探测鉴定服务联通性机制
    5.2 加入命名行参数-s , 用于指定鉴定服务器ip:port, 支持通过网络提交样本至鉴定器，
        可灵活适配使用，方便将样本调度服务内置到其综合调度平台内部。
    

