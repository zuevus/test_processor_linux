# -*- coding: utf-8 -*-
'''
@author                         yzx
@tested_version                 Python 3.6.5
@comply_with_python_3           yes
'''
import os
import re
import socket

#<external library>
#psutil
#       - license:   BSD License
#       - docu:      https://psutil.readthedocs.io/en/latest
import psutil
#<external library>

class __psutil_measure__():
                def __init__(self, pid=None, logger=None):
                        #<Global system measure>
                        self.global_net_io = psutil.net_io_counters()

                        self.global_cpu_freq = psutil.cpu_freq().current
                        self.global_cpu_count_all = psutil.cpu_count()
                        self.global_cpu_count_physics = psutil.cpu_count(logical=False)
                        self.global_cpu_percent = psutil.cpu_percent(0.1)

                        self.global_virtual_memory_used = psutil.virtual_memory().used

                        self.global_sensors_temperatures = psutil.sensors_temperatures
                        #</Global system measure>
                        if (pid is not None) and (psutil.pid_exists(pid)):
                                #<Particular peocess measure>
                                process = psutil.Process(pid)
                                self.io_counter = process.io_counters()
                                self.cpu_percent = process.cpu_percent()
                                
                                #self.disk_io_counters = process.disk_io_counters
                                #self.disk_usage = process.disk_usage
                                #self.virtual_memory = process.virtual_memory
                                #self.net_connections = process.net_connections
                                #<Particular peocess measure>

class system_measure():
        #<initialization>
        def __init__(self, pid, logger, extend_psutil_measure=None):
            self.real_pid = int(pid)
            self.pid = int(pid)
            self.logger = logger
            self.logger.debug("Creating measure class for PID: %s" % (self.real_pid))
            self.sc_clk_tck= os.sysconf("SC_CLK_TCK")
            self.psutil_list_of_measure = []
            if extend_psutil_measure is not None:
                self.psutil_list_of_measure.append(extend_psutil_measure)

            #<dictionary>
            self.fields_name = ('position', 'field_name', 're_pattern', 'description')
            self.stat_fields = [(1, 'pid', '[0-9]+', 'The process ID.'),
                       (2, 'comm', '\(?\w+\)?', 'The filename of the executable, in parentheses. This is visible whether or not the executable is swapped out.'),
                       (3, 'state', '\w+', """One of the following characters, indicating process
                        state:

                        R  Running

                        S  Sleeping in an interruptible wait

                        D  Waiting in uninterruptible disk sleep

                        Z  Zombie

                        T  Stopped (on a signal) or (before Linux 2.6.33)
                           trace stopped

                        t  Tracing stop (Linux 2.6.33 onward)

                        W  Paging (only before Linux 2.6.0)

                        X  Dead (from Linux 2.6.0 onward)

                        x  Dead (Linux 2.6.33 to 3.13 only)

                        K  Wakekill (Linux 2.6.33 to 3.13 only)

                        W  Waking (Linux 2.6.33 to 3.13 only)

                        P  Parked (Linux 3.9 to 3.13 only)"""),
                       (4, 'ppid', '[0-9]+', 'The PID of the parent of this process.'),
                       (5, 'pgrp', '[0-9]+', 'The process group ID of the process.'),
                       (6, 'session', '[0-9]+', 'The session ID of the process.'),
                (7, 'tty_nr', '[0-9]+', 'The controlling terminal of the process.  (The minordevice number is contained in the combination of bits 31 to 20 and 7 to 0; the major device number is in bits 15 to 8.'),
                (8, 'tpgid', '[0-9]+', 'The ID of the foreground process group of the controlling terminal of the process.'),
                (9, 'flags', '[0-9]+', 'The kernel flags word of the process.  For bit meanings, see the PF_* defines in the Linux kernel source file include/linux/sched.h. Details depend on the kernel version. The format for this field was [0-9]+ before Linux 2.6.'),
                (10, 'minflt', '[0-9]+', 'The number of minor faults the process has made which have not required loading a memory page from disk.'),
                (11, 'cminflt', '[0-9]+', 'The number of minor faults that the process\'s waited-for children have made.'),
                (12, 'majflt', '[0-9]+', 'The number of major faults the process has made which have required loading a memory page from disk.'),
                (13, 'cmajflt', '[0-9]+', 'The number of major faults that the process\'s waited-for children have made.'),
                (14, 'utime', '[0-9]+', 'Amount of time that this process has been scheduled in user mode, measured in clock ticks (divide by sysconf(_SC_CLK_TCK)). This includes guest time, guest_time (time spent running a virtual CPU, see below), so that applications that are not aware of the guest time field do not lose that time from their calculations.'),
                (15, 'stime', '[0-9]+', 'Amount of time that this process has been scheduled in kernel mode, measured in clock ticks (divide by sysconf(_SC_CLK_TCK)).'),

              (16, 'cutime', '[0-9]+' , '''
                        Amount of time that this process's waited-for chil-
                        dren have been scheduled in user mode, measured in
                        clock ticks (divide by sysconf(_SC_CLK_TCK)).  (See
                        also times(2).)  This includes guest time,
                        cguest_time (time spent running a virtual CPU, see
                        below).
'''),
              (17, 'cstime', '[0-9]+', '''
                        Amount of time that this process's waited-for chil-
                        dren have been scheduled in kernel mode, measured in
                        clock ticks (divide by sysconf(_SC_CLK_TCK)).
'''),
              (18, 'priority', '[0-9]+', '''
                        (Explanation for Linux 2.6) For processes running a
                        real-time scheduling policy (policy below; see
                        sched_setscheduler(2)), this is the negated schedul-
                        ing priority, minus one; that is, a number in the
                        range -2 to -100, corresponding to real-time priori-
                        ties 1 to 99.  For processes running under a non-
                        real-time scheduling policy, this is the raw nice
                        value (setpriority(2)) as represented in the kernel.
                        The kernel stores nice values as numbers in the
                        range 0 (high) to 39 (low), corresponding to the
                        user-visible nice range of -20 to 19.
                        Before Linux 2.6, this was a scaled value based on
                        the scheduler weighting given to this process.
'''),
              (19, 'nice', '[0-9]+', '''
                        The nice value (see setpriority(2)), a value in the
                        range 19 (low priority) to -20 (high priority).
'''),
              (20, 'num_threads', '[0-9]+', '''
                        Number of threads in this process (since Linux 2.6).
                        Before kernel 2.6, this field was hard coded to 0 as
                        a placeholder for an earlier removed field.
'''),
              (21, 'itrealvalue', '[0-9]+', '''
                        The time in jiffies before the next SIGALRM is sent
                        to the process due to an interval timer.  Since ker-
                        nel 2.6.17, this field is no longer maintained, and
                        is hard coded as 0.
'''),
              (22, 'starttime', '[0-9]+', '''
                        The time the process started after system boot.  In
                        kernels before Linux 2.6, this value was expressed
                        in jiffies.  Since Linux 2.6, the value is expressed
                        in clock ticks (divide by sysconf(_SC_CLK_TCK)).

                        The format for this field was [0-9]+ before Linux 2.6.
'''),
              (23, 'vsize', '[0-9]+', '''
                        Virtual memory size in bytes.
'''),
              (24, 'rss', '[0-9]+', '''
                        Resident Set Size: number of pages the process has
                        in real memory.  This is just the pages which count
                        toward text, data, or stack space.  This does not
                        include pages which have not been demand-loaded in,
                        or which are swapped out.
'''),
              (25, 'rsslim', '[0-9]+', '''
                        Current soft limit in bytes on the rss of the
                        process; see the description of RLIMIT_RSS in
                        getrlimit(2).
'''),
              (26, 'startcode', '[0-9]+', '''  [PT]
                      The address above which program text can run.
'''),
              (27, 'endcode', '[0-9]+', '''  [PT]
                        The address below which program text can run.
'''),
              (28, 'startstack', '[0-9]+', '''  [PT]
                        The address of the start (i.e., bottom) of the
                        stack.
'''),
              (29, 'kstkesp', '[0-9]+', '''  [PT]
                        The current value of ESP (stack pointer), as found
                        in the kernel stack page for the process.
'''),
              (30, 'kstkeip', '[0-9]+', '''  [PT]
                        The current EIP (instruction pointer).
'''),
              (31, 'signal', '[0-9]+', '''
                        The bitmap of pending signals, displayed as a deci-
                        mal number.  Obsolete, because it does not provide
                        information on real-time signals; use
                        /proc/[pid]/status instead.
'''),
              (32, 'blocked', '[0-9]+', '''
                        The bitmap of blocked signals, displayed as a deci-
                        mal number.  Obsolete, because it does not provide
                        information on real-time signals; use
                        /proc/[pid]/status instead.
'''),
              (33, 'sigignore', '[0-9]+', '''
                        The bitmap of ignored signals, displayed as a deci-
                        mal number.  Obsolete, because it does not provide
                        information on real-time signals; use
                        /proc/[pid]/status instead.
'''),
              (34, 'sigcatch', '[0-9]+', '''
                        The bitmap of caught signals, displayed as a decimal
                        number.  Obsolete, because it does not provide
                        information on real-time signals; use
                        /proc/[pid]/status instead.
'''),
              (35, 'wchan', '[0-9]+', '''  [PT]
                        This is the "channel" in which the process is wait-
                        ing.  It is the address of a location in the kernel
                        where the process is sleeping.  The corresponding
                        symbolic name can be found in /proc/[pid]/wchan.
'''),
              (36, 'nswap', '[0-9]+', '''
                        Number of pages swapped (not maintained).
'''),
              (37, 'cnswap', '[0-9]+', '''
                        Cumulative nswap for child processes (not main-
                        tained).
'''),
              (38, 'exit_signal', '[0-9]+', '''  (since Linux 2.1.22)
                        Signal to be sent to parent when we die.
'''),
              (39, 'processor', '[0-9]+', '''  (since Linux 2.2.8)
                        CPU number last executed on.
'''),
              (40, 'rt_priority', '[0-9]+', '''  (since Linux 2.5.19)
                        Real-time scheduling priority, a number in the range
                        1 to 99 for processes scheduled under a real-time
                        policy, or 0, for non-real-time processes (see
                        sched_setscheduler(2)).
'''),
              (41, 'policy', '[0-9]+', '''  (since Linux 2.5.19)
                        Scheduling policy (see sched_setscheduler(2)).
                        Decode using the SCHED_* constants in linux/sched.h.

                        The format for this field was [0-9]+ before Linux
                        2.6.22.
'''),
              (42, 'delayacct_blkio_ticks', '[0-9]+', '''  (since Linux 2.6.18)
                        Aggregated block I/O delays, measured in clock ticks
                        (centiseconds).
'''),
              (43, 'guest_time', '[0-9]+', '''  (since Linux 2.6.24)
                        Guest time of the process (time spent running a vir-
                        tual CPU for a guest operating system), measured in
                        clock ticks (divide by sysconf(_SC_CLK_TCK)).
'''),
              (44, 'cguest_time', '[0-9]+', '''  (since Linux 2.6.24)
                        Guest time of the process's children, measured in
                        clock ticks (divide by sysconf(_SC_CLK_TCK)).
'''),
              (45, 'start_data', '[0-9]+', '''  (since Linux 3.3)  [PT]
                        Address above which program initialized and unini-
                        tialized (BSS) data are placed.
'''),
              (46, 'end_data', '[0-9]+', '''  (since Linux 3.3)  [PT]
                        Address below which program initialized and unini-
                        tialized (BSS) data are placed.
'''),
              (47, 'start_brk', '[0-9]+', '''  (since Linux 3.3)  [PT]
                        Address above which program heap can be expanded
                        with brk(2).
'''),
              (48, 'arg_start', '[0-9]+', '''  (since Linux 3.5)  [PT]
                        Address above which program command-line arguments
                        (argv) are placed.
'''),
              (49, 'arg_end', '[0-9]+', '''  (since Linux 3.5)  [PT]
                        Address below program command-line arguments (argv)
                        are placed.
'''),
              (50, 'env_start', '[0-9]+', '''  (since Linux 3.5)  [PT]
                        Address above which program environment is placed.
'''),
              (51, 'env_end', '[0-9]+', '''  (since Linux 3.5)  [PT]
                        Address below which program environment is placed.
'''),
              (52, 'exit_code', '[0-9]+', '''  (since Linux 3.5)  [PT]
                        The thread's exit status in the form reported by
''')
                       ]
            #</dictionary>
            #<default values>
            self.__num_q__ = 0
            self.__cpu_sum__ = 0
        
            self.re_pattern = '''\s*'''.join(['(?P<%s>%s)' % (x[1], x[2]) for x in self.stat_fields]) 

            self.cpu_usage = float()
    
            self.proc_dir='/proc'

            #</default values>
        #</initialization>

        #<properties>
        @property
        def proc_pid_path(self):
            return os.path.join(self.proc_dir,
                                str(self.real_pid)
                                )

        @property
        def proc_net_tcp(self):
            for tcp_file_name in ['tcp', 'tcp6']:
                yield os.path.join(self.proc_dir,
                                   'net',
                                   tcp_file_name
                                   )

        @property
        def smaps_path(self):
            return os.path.join(self.proc_pid_path,
                                'smaps'
                                )

        @property
        def stat_file_path(self):
            return os.path.join(self.proc_pid_path,
                                'stat'
                                )
        @property
        def uptime_file_path(self):
            return os.path.join(self.proc_dir,
                                'uptime'
                                )

        @property
        def uptime(self):
            with open(self.uptime_file_path) as f:
                return f.read().split(" ")

        @property
        def proc_fd_dir(self):
            return os.path.join(self.proc_pid_path,
                                'fd')

        @property
        def process_network_status(self):
            tcp = []
            if os.path.isdir(self.proc_fd_dir):
                try:
                    for inode in [re.search("([0-9]+)\]$"
                                        , os.path.realpath(os.path.join(self.proc_fd_dir, x))
                                        , re.MULTILINE).group(1) for x in os.listdir(self.proc_fd_dir) if "socket" in os.path.realpath(os.path.join(self.proc_fd_dir, x))]:
                            for file_path in self.proc_net_tcp:
                                with open(file_path, "r") as f:
                                    for line in f:
                                        if inode in line:
                                            tcp.append(line.rstrip().lstrip().split(" "))
                except Exception as exc:
                    self.logger.debug("Some troubles with getting port %s" % (exc))      
            return tcp


        #</properties>
           
        def update(self):
            self.logger.debug("Starting update measure for %i" % (self.real_pid))
            if os.path.isdir(self.proc_pid_path):
                re_pattern = '''\s*'''.join(['(?P<%s>%s)' % (x[1], x[2]) for x in self.stat_fields])
                try:
                    try:
                        self.psutil_list_of_measure.append(__psutil_measure__(self.real_pid))
                    except Exception as exep:
                        pass
                    if os.path.isfile(self.stat_file_path):
                        with open(self.stat_file_path) as f: 
                            content = f.read()
                        grap = re.search(re_pattern, content)
                        for key, value in grap.groupdict().items():
                            try:
                                setattr(self, key, int(value))
                            except (TypeError, ValueError):
                                setattr(self, key, value)
                        total_time = (self.utime
                                      + self.stime
                                      + self.cutime
                                      + self.cstime)
                        seconds = float(self.uptime[0]) - float(self.starttime / self.sc_clk_tck)
                        cpu_usage = 100 * ((total_time / self.sc_clk_tck) / seconds)
                        self.cpu_usage_calculated = cpu_usage
                        self.__num_q__ +=1
                        self.__cpu_sum__ +=cpu_usage
                        self.cpu_usage_average = (self.__cpu_sum__/self.__num_q__)
                        #IP Address and Port update
                        tcpstrs = self.process_network_status
                        self.logger.debug("TCP status: %s" % (tcpstrs))
                        if len(tcpstrs) > 0:
                            self.listen_ip_address = []
                            self.listen_port = []
                            for tcpstr in tcpstrs:
                                self.listen_ip_address.append(".".join(str(socket.inet_ntoa(bytes.fromhex(tcpstr[1].split(":")[0]))).split(".")[::-1]))
                                self.listen_port.append(str(int(float.fromhex(tcpstr[1].split(":")[1]))))

                        self.pid = self.real_pid
                        return cpu_usage
                except ProcessLookupError as ple:
                    self.logger.debug("System measure class: Process lookup errors: %s" % (ple))
            else:
                return self.cpu_usage
