# -*- coding: utf-8 -*-
'''
@author                         yzx
@tested_version                 Python 3.6.5
'''
from select import select
import pty
import termios
import tty
import time
from subprocess import Popen, PIPE, run
import os
import sys
import signal
from datetime import datetime
import re
import socket
import shutil
#we don't care about GIL!, because it not multiple calculation it's just the tests
import threading
import queue
import sqlite3
import uuid
import shlex
from decimal import *
import xlsxwriter
import junit_xml
import lib.config
import traceback


#<external library>
#psutil - BSD License
import psutil
#<external library>

#<current project lib>
from lib.measure import system_measure, __psutil_measure__
#</current project lib>

def testsuite_wrap(func):
    cfg=lib.config.cfg.ts_cfg
    #Duty cycle
    #cfg.mcfg.log.debug("Dir of cfg: %s" % (dir(cfg)))
    test_cases = []
    tb = None
    test_suite_name = "%s_%s" %(cfg.name, func.__name__)
    hello_message = cfg.hello_msg.format(test_suite_name, cfg=cfg.mcfg)
    cfg.mcfg.log.info(hello_message)
    stdout = "%s\n" % hello_message
    #recive pair test case func name and number of tc in cfg file (like
    #    tc[1]_some)
    tc_func_pairs = func(cfg)
    if tc_func_pairs is not None:
        for tc_func_pair in func(cfg):
            try:
                test_cases.append(tc_func_pair[0](cfg.tc(tc_func_pair[1])).report)
            except Exception as excep:
                if (tb is None):
                    tb=traceback.format_exc()
                else:
                    tb = "%s\n\n%s" % (tb, traceback.format_exc())
                cfg.mcfg.log.error(tb)
    cfg.mcfg.log.debug(test_cases)
    #Reporting            
    report = lib.testing.tests_report.TestSuite("%s_%s" % (func.__name__,
                                    cfg.mcfg.os_release.pretty_name),
                                                    test_cases,
                                                    stdout=stdout)
    report.returncode = 0
    if (len(test_cases) > 0) and (tb is not None):
        report.stderr = tb
    #Set return code
    if len(test_cases) > 0:
        for test_case in test_cases:
            if test_cases[-1].returncode > 0:
                report.returncode = test_cases[-1].returncode
    else:
        report = 2
    return report


def __format_indent__(level, config):
        return str(" "*(int(config.common.tab_wite_space_lenght)*level))

def __format_span_next_line__(repeated, config):
        return ("%s\n" % (("%s" % (repeated)) * int(config.common.span_lenght)))

class db_communicate():
    def __init__(self, dbname, config, logger):
        self.logger = logger
        self.dbname = dbname
        self.logger.debug("{1} Creating connection to DB: {0} {1}".format(dbname
                                      , __format_span_next_line__("*_*", config)
                                                                          )
                          )
        self.config = config
        self.connection = sqlite3.connect(dbname, int(config.common.db_timeout))
        self.cursor = self.connection.cursor()
        #Get tables name for test
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        self.name_tables = [x[0] for x in self.cursor.fetchall()]
        self.logger.debug(("{1} Connected to DB. "+
                        "Tables:\n {0} {1}").format("\n".join(self.name_tables),
                                        __format_span_next_line__("*_*", config)
                                                       )
                          )

    def instert(self, query):
        self.cursor.execute(query)
        self.connection.commit()

    def fetch(self, query):
        self.logger.debug("Fetch data by query: %s" % (query))
        result = self.cursor.execute(query)
        result = self.cursor.fetchall()
        return (self.cursor.description, result)

    def finish(self):
        self.__del__()

    def __del__(self):
        self.connection.close()
        self.logger.debug("{1} Connection to DB {0} closed! {1}".format(self.dbname,
                                      __format_span_next_line__("*_*", self.config)
                                                                        )
                          )

class process():
    """
    Start process in thread or single mode, capture parameters, make mesure
        and preparing result
    """
    class __result__():
        class __screen_capture__():
            pass
        def __init__(self, pid, logger, extend_psutil_measure=None):
            self.return_code = None
            self.std_out_decoded = ""
            self.std_out_bytes = b''
            self.errors_out_bytes = b''
            self.errors_out_decoded = ""
            self.clean_up_log_dir = False
            self.measure = system_measure(pid, logger, extend_psutil_measure)
            self.screen_capture = self.__screen_capture__()

    def __init__(self, config, logger, cmd,
                 wait_word=None,
                 response_timeout=10,
                 general_timeout=600,
                 ready_timeout=1,
                 select_timeout=1,
                 stop_cmd=None,
                 regexp_pars=None,
                 thread_mode=False):
        self.logger = logger
        self.config = config
        self.hard_stop_cmd = "kill -9 {pids}"
        self.cmd = cmd
        #Regular expression for parsing screen
        #it's doctionary for example if dictionary element:
        #{"esrv_ip" : "^Server Address:\s*\[(?P<esrv_ip>([0-9]{1,3}\.{1}){3}[0-9]{1,3})"}
        #it's meaning that will be add esrv_ip attribute to result.screen_capture
        self.regexp_pars = regexp_pars

        #<Timeouts:>
        # - timeout that we will be waiting for response from the process in stdout
        #   e.g. if we haven't any recive from esrv server(nothing changed on screen)
        #   we will stop it by this timeout with send to pid(s) self.hard_stop_cmd
        #   and also this timeout use when thread stop
        self.response_timeout = float(response_timeout)
        # - timout that we will be running program, it's not depending on response
        #   from process. Also will stop it by this timeout with send to pid(s)
        #   self.hard_stop_cmd
        self.general_timeout = float(general_timeout)
        # - timeout that we will be waiting responce from stdout in while cicle,
        #   after this we will just continue routine (isn't not need changed in
        #   standart situation)
        self.select_timeout = float(select_timeout)
        # - timeout that we will be waiting before we will be ready (or kill it)
        self.ready_timeout = float(ready_timeout)
         #</:Timeouts>

        self.logger.debug("MULTILINE:\n{1} Creating process:\n {0}\n {1}".format(cmd,
                                        __format_span_next_line__("*_*", self.config)
                                                                                 )
                          )
        #This word is definding when will be stop process if this process loop and
        #  not thread mode or if it thread mode, when we'll be starting communicate
        if wait_word is not None:
            self.wait_word = wait_word
            self.logger.debug("Waiting word set and equal: '%s'" % (self.wait_word))
            #After the world that we will waiting for (look to lines before) we
            #need some cmd for stop by default we will use
            #kill -9 (self.hard_stop_cmd), but it can be some other e.g.
            #esrv --stop --port (for knowing port we can use {result.measure.port})
            #but you have to remember, that if we'll recive not 0 result from
            #this proceess, we'll return non zerro result at the end in result object
            self.stop_cmd = stop_cmd if stop_cmd is not None else self.hard_stop_cmd
        else:
            self.wait_word = False
        #Immediately running process if we in thread_mode
        self.thread_mode = thread_mode
        if self.thread_mode:
            self.id = uuid.uuid4()
            self.queue = queue.Queue()
            self.logger.debug("Creating thread with name: '%s'" % (str(self.id)))
            self.thread = threading.Thread(target=self.run, name=str(self.id), daemon=True)
            self.queue.put("OLLEH")
            self.thread.start()
            self.queue.join()
        #and if not
        else:
            self.logger.debug("Single mode running: %s" % self.cmd)
            self.run()

    def __stoptime__(self, timeout):
        return ((time.time() + timeout) if timeout is not None else None)


    def get_children_of_pid(self, pid):
        pids=[]
        for fl in [os.path.join("/proc", x, "stat") for x in os.listdir("/proc") if (os.path.isdir(os.path.join("/proc", x)) and re.match("[0-9]+", x))]:
            if os.path.isfile(fl):
                with open(fl, "r") as f:
                    fdata = f.read()
                    if str(pid) == fdata.split(" ")[3]:
                        sub_pid = int(fdata.split(" ")[0])
                        pids.append(sub_pid)
                        dip_sub_pid = self.get_children_of_pid(sub_pid)
                        if (isinstance(dip_sub_pid, list)):
                            pids.extend(dip_sub_pid)
                        elif dip_sub_pid != sub_pid:
                            pids.append(dip_sub_pid)
        if len(pids) > 0:
            return pids[0]
        if len(pids) < 1:
            return pid
        return pids


    def run(self):
        #Opening pseudo terminal
        mfd, sfd = pty.openpty()
        #Measure system before run
        extend_psutil_measure = __psutil_measure__()
        self.logger.debug(("MULTILINE:\n{1} Running"
                            +" process:\n {0}\n {1}").format(
                                self.cmd,
                        __format_span_next_line__("*_*", self.config)))
        #start process
        popen_obj = Popen(self.cmd,
                          stdin=sfd,
                          stdout=sfd,
                          stderr=sfd,
                          shell=True)

        self.logger.info(("\n{span:-^80}\n"+
                            "{message: ^80}\n{span:-^80}\n").format(
                                               span="PROCESS",
                                               message=self.cmd
                                               )
                         )

        #calculate stoptimes
        general_time_out = self.__stoptime__(self.general_timeout)
        ready_time_out = self.__stoptime__(self.ready_timeout)
        response_time_out = self.__stoptime__(self.response_timeout)

        #<Play wiht pids:>
        self.logger.debug("Python process pid is: %i" % os.getpid())
        #Get real pid of process by sh pid
        #  - becouse we ran this process in shell mode
        #  and we need to find all children of this process (must be only one of cource).
        real_pid = self.get_children_of_pid(popen_obj.pid)
        process_dubbed = False
        if real_pid != popen_obj.pid:
            process_dubbed = True
            self.pids = [real_pid, popen_obj.pid]
            self.logger.info("Shell /bin/sh pid: %i" % popen_obj.pid)
            self.logger.info("Sub process pid is: %i" % real_pid)
        else:
            self.pids = [real_pid]
            self.logger.info("Sub process pid is: %i" % real_pid)
        #</:Play wiht pids>
        #preparing result object
        self.result = self.__result__(real_pid, self.logger, extend_psutil_measure=extend_psutil_measure)
        communicator = None
        jogging_status = [".", "..", "...", ".."]
        jogging_status_idx = 0
        jogging = False
        while True:
            self.logger.debug(("MULTILINE:\n{1}\nCurrent time is:"
                                +" {4}\n{1}Times for out:\n\t\t -"
                                +" response_time_out = {0}\n\t\t -"
                                +" general_time_out={2}\n\t\t - "
                                +"ready_time_out={3}\n {1}").format(
                                                response_time_out,
                                        __format_span_next_line__(
                                                "*_*", self.config),
                                                general_time_out,
                                                ready_time_out,
                                                float(time.time())
                                    )
                              )

            #<Select result from pty by file description>
            self.logger.debug("Before select")
            #Calculate time that we spent for select response
            time_spend_for_respons = float(time.time())
            r,w,e = select([mfd], [], [mfd], self.select_timeout)
            time_spend_for_respons = float(time.time()) - time_spend_for_respons
            self.logger.debug("After select")
            #</Select result from pty by file description>

            #Update status of process
            popen_obj.poll()

            #<system measure of current process>
            #Update measure
            self.result.measure.update()
            if hasattr(self.result.measure, "cpu_usage_average"):
                self.logger.debug("Current cpu usage average is : %f" % (self.result.measure.cpu_usage_average))
            #</system measure of current process>
            self.result.return_code = popen_obj.returncode

            #recive cmd`s from queue in thread mode
            if (self.thread_mode):
                if not self.queue.empty():
                    queue_command = self.queue.get()
                if "KILL" in queue_command.upper():
                    self.logger.debug("KILL signal recived")
                    self.stop()
                    self.queue.task_done()
                elif ("jogging" in queue_command):
                    jogging = True

            if jogging:
                if jogging_status_idx < (len(jogging_status) - 1):
                        jogging_status_idx += 1
                else:
                        jogging_status_idx = 0
                self.logger.info("Pid %s work in thread%s" % (real_pid, jogging_status[jogging_status_idx]))
            communicator_decoded = ""
            if mfd in r:
                #self.logger.debug("Return code: %s " % str(self.result.return_code))
                #Reading data from pty
                communicator = os.read(mfd, 10240)
                #communicator = communicator.replace(b'\x08', b'') ????????????

                #Sometimes event problem with decoding of unrecognize simbols
                #   because screen out from process came in two parts
                #   and simbols starting at the end of one part ended at the begin of other -
                #   - in two differents communicators variable (divided in time)
                #   todo: need first collect than decode
                try:
                    communicator_decoded = communicator.decode(self.config.common.default_codepage)
                  #  self.logger.debug("Decoded std(err)out: %s" % (repr(communicator_decoded)))
                except UnicodeDecodeError as ude:
                    self.logger.debug("Durring decoding result to %s raised error: %s\t-\t Try to workaroud." % (self.config.common.default_codepage,
                                                                                                                 ude)
                                      )
                    start_pos = ude.args[2]
                    end_pos = ude.args[3]
                    bad_bit = communicator[start_pos:end_pos]
                    self.logger.debug("Bad simbol is %s, between %i and %i posions.\t Will be trim part: %s" % (bad_bit, start_pos, end_pos, communicator[start_pos:]))
                    communicator_trim = communicator[:start_pos]
                    communicator_decoded = communicator_trim.decode(self.config.common.default_codepage)

                #<Sudo mechanism:>
                #   !ATTENTION!: use -S option with sudo for recive password through stdin
                if "password for" in communicator_decoded:
                    self.logger.debug("Asking for root password: %s" % communicator_decoded)
                    if hasattr(self.config.common, "user_password"):
                        pswd = bytes("%s\n" % (self.config.common.user_password), self.config.common.default_codepage)
                        if "Sorry, try again" in communicator_decoded:
                            self.logger.warning("!!ERROR: Password for sudo user %s is uncorrect %s " % (self.config.common.user_name, self.config.common.user_password))
                            self.result.errors_out_decoded = communicator_decoded
                        self.logger.debug("Password set to %s" % (repr(pswd)))
                        os.write(mfd, pswd)
                        continue
                    else:
                        self.logger.info("Sudo password is not provide! Stop process and exit...")
                        self.result.errors_out_decoded = "Sudo password is not provide!"
                        if (self.thread_mode):
                            self.stop()
                #</Sudo mechanism>

                #Check if process returned more than 0 meaning error
                if (self.result.return_code is not None) and (self.result.return_code > 0):
                    self.logger.warning("!!ERROR: Returned non zero! %s " % (communicator_decoded))
                    self.result.errors_out_decoded = communicator_decoded
                    self.result.errors_out_bytes = communicator
                #else work with result
                else:
                    self.logger.debug("\t++: %s " % communicator_decoded)
                    response_time_out=self.__stoptime__(self.response_timeout)
                    self.result.std_out_decoded += communicator_decoded
                    self.result.std_out_bytes += communicator

                    #<parce output by regular exprasion>
                    if (len(communicator_decoded)>0) and (self.regexp_pars is not None):
                        self.logger.debug("regexp_pars is not none. We are starting parsing standart output to class field...")
                        for key, value in self.regexp_pars.items():
                            try:
                                #self.logger.debug("Commu decode repr: %s" % (repr(communicator_decoded)) )
                                re_search = re.search (value, communicator_decoded, re.MULTILINE)
                                if re_search is not None:
                                    setattr(self.result.screen_capture, key, re_search.group(key))
                                    self.logger.debug("Great we found %s it is %s" % (key, re_search.group(key)))
                                else:
                                    self.logger.debug("!!WARNING: Couldn't find %s" % key)
                            except IndexError:
                                self.logger.debug("!!WARNING: Output hasn't this group of data")
                    #</parce output by regular exprasion>

                    #Word after that we will be ready to communicate or just stop(kill or something like this) this process
                    if (self.wait_word) and (self.wait_word in communicator_decoded) and (ready_time_out < time.time()):
                        self.logger.debug("Catch wait word!")
                        #  - thread mode
                        if (self.thread_mode):
                            if (not jogging):
                                #<work with thread>
                                self.logger.debug("\t-thread mode case starting preparing communicate...")
                                #queue_get = self.queue.get()
                                self.logger.debug("\t-thread: %s, recived %s" % (str(self.id), queue_command[::-1]))
                                self.queue.task_done()
                                #</work with thread>
                        #  - single mode
                        else:
                            command = shlex.split(self.stop_cmd.format(pids=" ".join([str(pi) for pi in self.pids]),
                                                                       result=self.result
                                                                       #port=self.result.screen_capture.esrv_port if hasattr(self.result.screen_capture, 'esrv_port'} else ""
                                                                       )
                                                  )
                            self.logger.debug("\t\t-single mode case starting stop procedure by the command: %s" % (" ".join(command)))
                            killer_return = run(command, stdout=PIPE, stderr=PIPE)
                            if killer_return.returncode > 0:
                                #softly exit not immplimented
                                raise Exception("Process stop errors! Return more than zerro. Error: %s "% (self.result.stderr))

            #<Timeout predicates>
            #General time out exit
            if (general_time_out < time.time()):
                self.result.errors_out_decoded += "General timeout pass out! pass %f sec" % (general_time_out)
                self.logger.warning(self.result.errors_out_decoded)
                if (self.thread_mode):
                    if (self.thread_mode):
                        try:
                            self.queue.task_done()
                        except:
                            pass
                    self.stop()
                self.result.return_code = 1
                break
            #Response time out exit
            if (response_time_out < time.time()):
                self.result.errors_out_decoded += "Wait response timeout pass out! pass %f sec" % (response_time_out)
                self.logger.warning(self.result.errors_out_decoded)
                if (self.thread_mode):
                    if (self.thread_mode):
                        try:
                            self.queue.task_done()
                        except:
                            pass
                    self.stop()
                self.result.return_code = 1
                break
            #</Timeout predicates>
            self.logger.debug("self.result.return_code: '%s' " % (str(self.result.return_code)))
            #<error predicat>
            if (self.result.return_code is not None) and (self.result.return_code > 0):
                self.logger.debug("A-a-a-a! its returned more than zerro!! Stopping...")
                if (len(self.result.errors_out_decoded) < 1):
                    if (communicator_decoded in locals().keys()
                            and communicator_decoded is not None):
                        error_descr = "Unrecognized error:\n %s" % (communicator_decoded)
                    else:
                        error_descr = "Unrecognized error."
                        self.result.errors_out_decoded = error_descr
                if (self.thread_mode):
                    try:
                        self.queue.task_done()
                    except:
                        pass
                    self.stop()
                break
            #</error predicat>
            #if return zerro or below zerro meaning that we successfully done
            elif (self.result.return_code is not None):
                if (self.thread_mode):
                    self.queue.task_done()
                break
        self.logger.debug("{1} Finish prompt line {0} ...\n {1}".format(self.cmd, __format_span_next_line__("*_*", self.config)))
        return self.result


    def stop(self):
        "Using for immediatly stop thread anyway"
        command = self.hard_stop_cmd.format(pids=" ".join([str(x) for x in self.pids]))
        self.logger.warning("Proccess with id %s will be immediatly stoped!" % (self.id))
        self.logger.warning("Will run cmd: '%s'" % command)
        command = shlex.split(command)
        #Using PSUTIL!!! pid_exists
        if len([True for x in self.pids if psutil.pid_exists(x)])>0:
            #Send 9 to process (or some other it depeding on self.hard_stop_cmd)
            result = run(command, stdout=PIPE, stderr=PIPE)
            if result.returncode > 0:
                self.result = result
                raise Exception("Process stop errors! Return more than zerro. Error: %s "% (self.result.stderr))
        #self.queue.task_done()
#        if self.thread.is_alive():
          #  self.thread.join(self.response_timeout)
        #if self.thread.is_alive():
         #   raise Exception("Thread %s didn't stoped!" % (self.id))

class tests_report(list):
    '''
    temporary insted of tests_report
    '''
    j_xml_head = "<?xml version=\'1.0\' encoding=\'utf-8\'?>\n"
    j_xml_with_el = "%s<%s %s>\n"
    j_xml_without_el = "%s<%s %s/>\n"
    j_xml_with_el_close = "%s</%s>\n"
    #---- xlsx ----
    class __xlsx_report__():
        def __init__(self, path):
            self.workbook = xlsxwriter.Workbook("%s.xlsx" % path)
            self.sheets = []

        @property
        def ts_result_flag(self):
            results = []
            for tr in self.report:
                if ((tr.ts_result is not None)
                            and (tr.ts_result)):
                    results.append("V")
                elif ((tr.ts_result is not None)
                            and (not tr.ts_result)):
                    results.append("X")
                else:
                    results.append("-")
                for trs in tr.testcases:
                    results.append("")
            return results

        @property
        def tc_result_flag(self):
            results = []
            for trm in self.report:
                results.append("")
                for tr in trm.testcases:
                    if ((tr.__tc_result__ is not None)
                                and (tr.__tc_result__)):
                        results.append("V")
                    elif ((tr.__tc_result__ is not None)
                                and (not tr.__tc_result__)):
                        results.append("X")
                    else:
                        results.append("-")
            return results

        @property
        def ts_name(self):
            results = []
            for tr in  self.report:
                results.append([tr.attribs.name, (None, None, {'level': 1})])
                for trs in tr.testcases:
                    results.append(["", (None, None, {'level': 2})])
            
            return results

        @property
        def tc_name(self):
            results = []
            for trm in self.report:
                results.append("")
                for tr in trm.testcases:
                    results.append(tr.name)
            return results

        @property
        def ts_running_time(self):
            results = []
            for tr in self.report:
                results.append(tr.attribs.time)
                for trs in tr.testcases:
                    results.append("")
            return results

        @property
        def tc_running_time(self):
            results = []
            for trm in self.report:
                results.append("")
                for tr in trm.testcases:
                    results.append(tr.time)
            return results

        @property
        def tss_matrix(self):
            cols = []
            for name, link in self.fields_tmplt:
                cols.append([name])
                for row in getattr(self, link):
                    #row[0] - value row[1] - format
                    cols[-1].append(row)
            return cols

        def finalize(self):
            for sheet in self.sheets:
                self.worksheet = self.workbook.add_worksheet(sheet[0])
                col = 0
                for data in sheet[1]():
                    row = 0
                    for rowd in data:
                        if isinstance(rowd, list) and len(rowd) > 1:
                            self.worksheet.write(row, col, rowd[0])
                            self.worksheet.set_row(row, *rowd[1])
                        else:
                            self.worksheet.write(row, col, rowd)
                        row += 1
                    col +=1
                self.workbook.close()

        def add_result_to_sheet(self,
                                result_obj,
                                level=1,
                                row = 0,
                                cname=None,
                                worksheet=None):
            col = 0
            if cname is not None:
                worksheet = self.workbook.add_worksheet(cname[:30])
            for key, value in {x:y for x,y in result_obj.__dict__.items() if not "_" in x}.items():
                if isinstance(value, list):
                        worksheet.write(row, col, key)
                        for value_s in value:
                            row += 1
                            if isinstance(value_s, str):
                                worksheet.write(row, col +1, value_s)
                                worksheet.set_row(row, None, None, {'level': level+1})
                            else:
                                self.add_result_to_sheet(value_s, level + 1, row, worksheet=worksheet)
                elif isinstance(value, str) or isinstance(value, int):
                        worksheet.write(row, col, key)
                        worksheet.write(row, col +1, value)
                elif value is None:
                    worksheet.write(row, col + 1, "None")
                else:
                    self.add_result_to_sheet(value, level+1, row, worksheet=worksheet)
                row += 1

        def __del__(self):
            self.workbook.close()
    #---- xlsx ----
    #---- new junit (external inheritance) ---
    class TestSuite(junit_xml.TestSuite):
        def __str__(self):
            print(dir(self))
    class TestCase(junit_xml.TestCase):
        def __str__(self):
            print(dir(self))
    #---- new junit (external inheritance) ---
    """
    #---- old junit ---
    class __testsuite__():
        class __attribs__():
            j_xml_attrib_tmpl = '%s="%s" '

            @property
            def key_eq_value(self):
                strr = ""
                for key, value in self.__dict__.items():
                    if "__" in key:
                        key = key.replace("_", "")
                    strr += (self.j_xml_attrib_tmpl % (key, value)).lstrip()
                return strr

            def __init__(self, **argsv):
                if len(argsv.keys())>0:
                    for key, value in argsv.items():
                        setattr(self, key, value)
            @property
            def time(self):
                return self.__time__

            @time.setter
            def time(self, value):
                self.__time__ = round(value, 10)

        tag_name = "testsuite"
        ts_result = None

        @property
        def system_out(self):
            '''
            this is system-out tag
            Data that was written to standard out while the test was executed
            Wite space std out
            using systemout += "message"
            '''
            return '%s' % ("\n".join(self.__system_out__))
            #return self.__system_outs__

        @property
        def system_err(self):
            '''
            this is system-err tag
            Data that was written to standard error while the test was executed
            Wite space std out
            using systemerr += "message"
            '''
            return '%s' % ("\n".join(self.__system_err__))


        def add_property(self, **argv):
            '''
            Properties (e.g., environment settings) set during test execution
            name, value
            '''
            self.properties.append(self.__attribs__(**argv))
            return (len(self.properties)-1)

        def add_testcase(self, **argv):
            '''
            name - token -required - Name of the test method
            classname - token - required- Full class name for the class the test method is in.
            time - decimal -required - Time taken (in seconds) to execute the test
            '''
            self.testcases.append(self.__attribs__(**argv))
            self.testcases[-1].__tc_result__=None
            return (len(self.testcases)-1)

        def add_testcase_failure(self, number, **argv):
            '''
            number - index of testcase in testcases list
            Indicates that the test failed. A failure is a test which the code has explicitly failed by using the mechanisms for that purpose. e.g., via an assertEquals. Contains as a text node relevant data for the failure, e.g., a stack trace
            pre-string -> message
                        The message specified in the assert
                       -> type
                       The type of the assert.
            '''
            self.__testcase_failures__[number] = self.__attribs__(**argv)

        def slice_systemout(self, sysout):
            self.__system_out__.append(sysout)

        def add_testcase_error(self, number, **argv):
            '''
            number - index of testcase in testcases list
            Indicates that the test errored.  An errored test is one that had an unanticipated problem. e.g., an unchecked throwable; or a problem with the implementation of the test. Contains as a text node relevant data for the error, e.g., a stack trace
            pre-string -> message
                        The error message. e.g., if a java exception is thrown, the return value of getMessage()
                       -> type
                        The type of error that occured. e.g., if a java execption is thrown the full class name of the exception.
            '''
            self.__testcase_error__[number] = self.__attribs__(**argv)

        def start(self):
            self.attribs.time=Decimal(time.time())

        def stop(self):
            self.attribs.time=(Decimal(time.time())-self.attribs.time)

        def __init__(self, **argsv):
                if len(argsv.keys())>0:
                    for key, value in argsv.items():
                        setattr(self, key, value)

                self.properties = []
                self.testcases = []

                #self.calc=self.__calc__()
                self.__system_out__ = []
                self.__system_outs__ = []
                self.__system_err__ = []
                self.__testcase_failures__ = {}
                self.__testcase_error__ = {}
                #self.xlsx_report = __xlsx_report__()
                #self.xlsx_report.report = self

        @property
        def errors(self):
            return len(self.__system_err__)

        @property
        def tests(self):
            return len(self.__system_err__)

    def add_testsuite(self, name, timestamp=None, hostname = None, time=0.0):
        '''
        Contains the results of exexuting a testsuite
        name - int - required - Full class name of the test for non-aggregated testsuite documents. Class name without the package for aggregated testsuites documents
        timestamp - ISO8601_DATETIME_PATTERN - required (autonow) - when the test was executed. Timezone may not be specified
        hostname - int - required - Host on which the tests were executed. 'localhost' should be used if the hostname cannot be determined.
        tests - int - required - The total number of tests in the suite that failed. A failure is a test which the code has explicitly failed by using the mechanisms for that purpose. e.g., via an assertEquals
        errors - required - The total number of tests in the suite that errored. An errored test is one that had an unanticipated problem. e.g., an unchecked throwable; or a problem with the implementation of the test.
        time - decimal - Time taken (in seconds) to execute the tests in the suite
        '''
        hostname =  socket.gethostname() if hostname is None else hostname
        timestamp =  datetime.now().isoformat() if timestamp is None else timestamp
        self.append(self.__testsuite__(attribs = self.__testsuite__.__attribs__(name=name
                                           , timestamp=timestamp
                                           , hostname=hostname
                                           , time=time
                                           )
                                       )
                    )
        return self[-1]

    @property
    def out_xml(self):
        j_xml_content = self.j_xml_head
        j_xml_content += self.j_xml_with_el % ("", "testsuites", 'name="%s"' % self.tss_name)
        for testsuite in self:
            j_xml_content += self.j_xml_with_el % (__format_indent__(1, self.config), testsuite.tag_name, testsuite.attribs.key_eq_value)
            if len(testsuite.properties) > 0 :
                j_xml_content += self.j_xml_with_el % (__format_indent__(2, self.config), "properties", "")
                for sproperty in testsuite.properties:
                    j_xml_content += self.j_xml_without_el % (__format_indent__(3, self.config), "property", sproperty.key_eq_value)
                j_xml_content += self.j_xml_with_el_close % (__format_indent__(2, self.config), "properties")
            if hasattr(testsuite, "testcases"):
                for testcase in testsuite.testcases:
                    testcase_index = testsuite.testcases.index(testcase)
                    condition_1=((testcase_index in testsuite.__testcase_failures__.keys())
                                    or (testcase_index in testsuite.__testcase_error__.keys()))
                    #condition_2=(len(testsuite.__system_outs__) > 0)
                    if condition_1: # or condition_2:
                        j_xml_content += self.j_xml_with_el % (__format_indent__(2, self.config), "testcase", testcase.key_eq_value)
                        #if len(testsuite.__system_outs__) > 0:
                        #    if len(testsuite.__system_outs__[testcase_index])>0:
                        #        j_xml_content += ("%s\n"
                        #                % testsuite.__system_outs__[testcase_index])
                        if (testcase_index in testsuite.__testcase_failures__.keys()):
                            j_xml_content += self.j_xml_without_el % (__format_indent__(3, self.config), "failure", testsuite.__testcase_failures__[testcase_index].key_eq_value)
                        if (testcase_index in testsuite.__testcase_error__.keys()):
                            j_xml_content += self.j_xml_without_el % (__format_indent__(3, self.config), "error", testsuite.__testcase_error__[testcase_index].key_eq_value)
                        j_xml_content += self.j_xml_with_el_close % (__format_indent__(2, self.config), "testcase")
                    else:
                        j_xml_content += self.j_xml_without_el % (__format_indent__(2, self.config), "testcase", testcase.key_eq_value)
            if len(testsuite.system_out) > 0 and False:
                if len(testsuite.system_out)>0:
                    j_xml_content += self.j_xml_with_el % (__format_indent__(2, self.config), "system-out", "")
                    j_xml_content += "%s\n" % testsuite.system_out
                    j_xml_content += self.j_xml_with_el_close % (__format_indent__(2, self.config), "system-out")
            if len(testsuite.system_err) > 0:
                j_xml_content += self.j_xml_with_el % (__format_indent__(2, self.config), "system-err", "")
                j_xml_content += "%s\n" % testsuite.system_err
                j_xml_content += self.j_xml_with_el_close % (__format_indent__(2, self.config), "system-err")
            j_xml_content += self.j_xml_with_el_close % (__format_indent__(1, self.config), testsuite.tag_name)
        j_xml_content += self.j_xml_with_el_close % ("", "testsuites")
        return j_xml_content
    #--- old junit ---
    """
class tests_runner():

#    class sub_cmds():
#        def __init__(self, **fieldsdict):
#            for key, value in fieldsdict.items():
#                setattr(self, key, value)

    def __init__(self, logger, cfg, testsuite_path="", test_number=1):
        self.test_number = test_number
        self.logger = logger
        self.testsuite_path = testsuite_path
        self.config = cfg
        self.timeout = float(self.config.common.timeout)
        self.report = tests_report()
        self.report.config = self.config
        self.path_to_plugin = os.path.split(self.testsuite_path)[0]
        self.testsute_short_name = os.path.split(self.testsuite_path)[1].replace(".py", "")
        self.pids_aggregator = []
        #Preparing for configuration file
        if (self.testsute_short_name in cfg.testsuites_cfg_dict.keys()):
            self.ts_config = cfg.testsuites_cfg_dict[
                                            self.testsute_short_name]
            #Distribution name
            self.ts_config.dist_name = self.config.linux_current_release[1],
            #Version number
            self.ts_config.dist_version = self.config.linux_current_release[2]
            if hasattr(self.ts_config, "ts_index"):
                if len(self.ts_config.ts_index) < 1:
                    self.ts_config.ts_index = self.test_number
            else:
                self.ts_config.ts_index = self.test_number
            if hasattr(self.ts_config, "test_routine_help"):
                self.run.__func__.__doc__ = self.ts_config.test_routine_help.format(
                                    ts_config=self.ts_config
                                    )
            if hasattr(self.ts_config, "ts_full_name"):
                testsuite_name = self.ts_config.ts_full_name.format(
                                    ts_config=self.ts_config
                                    )
                self.test_suite_report = self.report.add_testsuite(testsuite_name)
        else:
            self.ts_config = False
        #<default_parameters>
        self.clean_up_log_dir = True
        #</default_parameters>

    #<some_often_using_functions>

    #Change dir and return old dir
    def change_dir(self, *directory):
        current_dir = os.getcwd()
        directory = os.path.join(*directory)
        self.logger.debug("Current dir is: %s" % (current_dir))
        os.chdir(directory)
        self.logger.debug("Chaged to: %s" % (os.getcwd()))
        self.current_dir = current_dir
        return current_dir

    #Create if not exist path_to_plugin_s_dir
    def path_to_plugin_s_dir(self, clean_up_log_dir=True):

        path = os.path.join(self.current_dir,
                            self.path_to_plugin,
                            self.testsute_short_name
                            )
        if clean_up_log_dir:
            if os.path.isdir(path):
                shutil.rmtree(path)
        if not os.path.isdir(path):
            os.makedirs(path)
            self.logger.debug("Created path: %s" % path)
        return path

    #Create if not exist path_to_plugin_s_dir
    def path_to_log_s_dir(self, clean_up_log_dir=True):
        if clean_up_log_dir:
            rmpath = os.path.join(self.current_dir,
                                  "log",
                                  self.path_to_plugin,
                                  self.testsute_short_name
                                  )
            if os.path.isdir(rmpath):
                shutil.rmtree(rmpath)
        path = os.path.join(self.current_dir,
                            "log",
                            self.path_to_plugin,
                            self.testsute_short_name

                           # "{0:%Y%m%d_%H%M%S}".format(datetime.now())
                             )
        if not os.path.isdir(path):
            os.makedirs(path)
            self.logger.debug("Created path: %s" % path)
        self.path_to_log_s_dir = path
        return path

    #Create archive file with logs
    def create_log_archive(self, directory):
        if os.path.isdir(directory):
                uplevel_folder = os.path.split(directory)[0]
                file_name = os.path.split(directory)[1]
                archive_file_name="%s.tgz" % (file_name)
                print ([a for a in os.listdir(uplevel_folder) if (".tgz" in a)])
                for old_archives in [a for a in os.listdir(uplevel_folder) if (".tgz" in a)]:
                    os.remove(os.path.join(uplevel_folder, old_archives))
                os.chdir(uplevel_folder)
                self.logger.debug("arch_file_name: '%s'"% (archive_file_name))
                command = shlex.split("tar  -czvf %s %s" %(archive_file_name, file_name))
                self.logger.debug("Achive CMD: %s" % (" ".join(command)))
                archive_creater = run(command, stdout=PIPE, stderr=PIPE)
                if archive_creater.returncode > 0:
                        #softly exit not immplimented yet
                        raise Exception("Log create archive errors! Return more than zerro. Error: %s "% (archive_creater.stderr))
                os.chdir(self.current_dir)
                shutil.rmtree(directory)
    #</some_often_using_functions>

    def __testcase_failed_routine__(self, process_obj, testcase_idx):
        testcase = self.test_suite_report.testcases[testcase_idx]
        self.logger.warning("\n{1} TESTCASE FAILED: {0}\n {1}".format(testcase.name, __format_span_next_line__("    ", self.config)))
        self.logger.info("Error description: {0}".format(process_obj.result.errors_out_decoded))
        #Create directory if not exist need for cmd log collection
        path_to_log_s_dir = self.path_to_log_s_dir()
        #report
        #self.test_suite_report.__system_out__.append(process_obj.result.std_out_decoded)
        self.test_suite_report.__system_err__.append(process_obj.result.errors_out_decoded)
        self.test_suite_report.add_testcase_failure(testcase_idx, message="Returned non zero value from: %s" % testcase.name, type="__testcase_failed_routine__")
        #/report
        #Record stdout to file
        file_name = "%s.log" % (testcase.classname)
        self.logger.debug("file_name = %s " % file_name)
        path_to_file = os.path.join(path_to_log_s_dir, file_name)
        self.logger.debug("path_to_file = %s " % path_to_file)
        with open(path_to_file, "w+") as f:
            f.write(process_obj.result.std_out_decoded)
        return False

    def __testcase_pass_routine__(self, process_obj, testcase_idx):
        testcase = self.test_suite_report.testcases[testcase_idx]
        #if ret_res_obj.WARNINGS == 0:
        self.logger.info("\n{1} TESTCASE PASSED: {0}\n {1}".format(testcase.name,__format_span_next_line__("    ", self.config)))
        #else:
        #    self.logger.warning("{0} TEST PASSED WITH WARNING(s) {0}".format("*_!_*"*int(int(self.config.common.span_lenght)/1.5)))
        return True

#    def test_pass_check(self, process_obj, testcase):
#        if process_obj.result.return_code > 0:
#            retrn = self.__testcase_failed_routine__(process_obj, testcase)
#        else:
#            retrn = self.__testcase_pass_routine__(process_obj, testcase)
#        return retrn

    def thread_watcher(self, process_obj, testcase_idx):
        testcase = self.test_suite_report.testcases[testcase_idx]
        self.logger.info("Running thread wacher for %s..." % (testcase.name))
        started_time = testcase.time
        while process_obj.thread.is_alive():
            #python GIL trick
            time.sleep(0.01)
            #calculate time for passing test
            testcase.time=(time.time()-started_time)
        self.logger.info("Endding thread wacher for %s..." % (testcase.name))

    def start_process(self, testcase_idx, **keyargs):
        testcase = self.test_suite_report.testcases[testcase_idx]
        keyargs.update({'config':self.config, 'logger':self.logger})
        process_obj = process(**keyargs)
        self.pids_aggregator.extend(process_obj.pids)
        if ("thread_mode" in keyargs.keys()) and keyargs['thread_mode'] == True:
            thread_watcher = threading.Thread(target=self.thread_watcher, name="thread_wachdog", args=(process_obj, testcase_idx), daemon=True)
            thread_watcher.start()
            return process_obj
        else:
            #calculate time for passing test
            testcase.time=(time.time()-testcase.time)
            if self.test_pass_check(process_obj, testcase_idx):
                return process_obj
            else:
                raise (Exception("%s failed!" % testcase.name))





    def __del__(self):
        if __debug__:
            print ("Cleaning procedure")
        #at the end append python self, because:
        #   - yzuevx    6501  0.0  0.0      0     0 pts/1    Z+   13:39   0:00 [sh] <defunct> <!<!<!<!<!<!<
        #   in thread mode after esrv stop
        #??self.pids_aggregator.append(os.getpid())
        for pid in self.pids_aggregator:
            #Using PSUTIL!!! pid_exists
            if psutil.pid_exists(pid):
                command = "/bin/kill -9 %s" % (pid)
                command = shlex.split(command)
                if __debug__:
                    print ("Stop process with pid %s. Command: %s" % (pid, command))
                result = run(command, stdout=PIPE, stderr=PIPE)
                if result.returncode > 0:
                    self.result = result
                    raise Exception("Process stop errors! Return more than zerro. Error: %s "% (self.result.stderr))
