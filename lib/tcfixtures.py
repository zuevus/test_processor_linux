# -*- coding: utf-8 -*-
'''
@author                     yzx
@tested_version             Python 3.6.5
'''
import os
import shutil
import re
import time
import shlex
from lib.testing import process, db_communicate
from subprocess import run as runprocess, PIPE
import uuid
from decimal import Decimal
import traceback
import lib.testing
import logging
import testcases.smoke


class TestCaseWrap():
    def __init__(self, cfg, self_id=None):
        self.esrv_regexp_pars = {
                'some_ip': '^Server Address:\s*\[(?P<some_ip>([0-9]{1,3}\.{1}){3}[0-9]{1,3})',
                'some_port': '^Server Port:\s*\[(?P<some_port>[0-9]{1,5})',
                'some_samples': 'Samples:\s*\[(?P<some_samples>[0-9]{1,10})',
                'some_error_count':'Error\s*\[(?P<some_error_count>[0-9]{1,10})',
                'some_info_count' : "\[I\]nformational:\.+\[\s*(?P<some_info_count>[0-9]+)\]\.*",
                'some_warns_count' : "\[W\]arning\(s\):\.+\[\s*(?P<some_warns_count>[0-9]+)\]\.*",
                'some_rerror_count' : "\[R\]ecoverable error\(s\):\.+\[\s*(?P<some_rerror_count>[0-9]+)\]\.*",
                'some_uerror_count' : "\[U\]nrecoverable error\(s\):\.+\[\s*(?P<some_uerror_count>[0-9]+)\]\.*",
                'some_cerror_count' : "\[C\]atastrophic error\(s\):\.+\[\s*(?P<some_cerror_count>[0-9]+)\]\.*",
                'warns_description' : "(?P<warns_description>\-+\[Warning\]\-+\r?\n[ A-Za-z.,:0-9\[\]/\\()*_\n\r]+)",
                'uerror_description' : "(?P<uerror_description>\-+\[Unrecoverable\]\-+\r?\n[ A-Za-z.,:0-9\[\]/\\()*_\n\r]+)",
                'cerror_description' : "(?P<cerror_description>\-+\[Catastrophic\]\-+\r?\n[ A-Za-z.,:0-9\[\]/\\()*_\n\r]+)",
                'rerror_description' : "(?P<rerror_description>\-+\[Recoverable\]\-+\r?\n[ A-Za-z.,:0-9\[\]/\\()*_\n\r]+)"
                }
        self.error_description = None
        tctime = Decimal(time.time())
        if self_id is None:
            self_id = uuid.uuid4()
        #Duty cycle
        tb = None
        self.stdout = "TestCase ID: %s" % (self_id)
        result = None
        try:
            result = self.do(cfg, self_id)
        except Exception as excep:
            except_txt = excep
            tb=traceback.format_exc()
            cfg.mcfg.log.error(tb)
            if hasattr(excep, "errno"):
                returncode = excep.errno
            else:
                returncode = 1
        os.chdir(cfg.mcfg.script_home_dir)
        tctime = Decimal(time.time()) - tctime
        #Reporting
        #   -- TestCase report instance
        self.report = lib.testing.tests_report.TestCase(cfg.name,
                '%s.%s.%s_%s' % (cfg.tscfg.test_domain, self.taxon, cfg.cname,
                        cfg.mcfg.os_release.pretty_name),
                            tctime,
                            self.stdout)
        #Set default return code
        self.report.returncode = 0
        if (tb is not None):
            if self.error_description is not None:
                self.error_description = "%s\n%s" % (self.error_description, tb)
            else:
                self.error_description = tb
            if ((result is not None)
                and (hasattr(result, "errors_out_decoded"))):
                if (result.errors_out_decoded > 0):
                    self.error_description += "\nErrOut:\n %s" % (
                            result.errors_out_decoded)
            self.report.add_error_info(except_txt,
                                       self.error_description,
                                       "uncategorized")
            self.report.returncode = returncode
            if not hasattr(self.report, "assertions"):
                self.report.assertions = []
                print (self.report.assertions)
        else:
            #-- Assertion checks
            self.asserts(cfg, self_id)
            if not hasattr(self.report, "assertions"):
                self.report.assertions = []
                print (self.report.assertions)

    def build_or_unpack_if_not_done_yet(self, temp_path, cfg, self_id):
        if not os.path.isdir(temp_path):
            if ("make" in cfg.source_type):
                make_all_steps=testcases.smoke.make_all(cfg, self_id)
                if make_all_steps.report.returncode > 0:
                    raise Exception("make all error")
            elif ("archive" in cfg.source_type):
                unpack=testcases.smoke.check_content_of_tgz_archive_BOM(
                                                            cfg, self_id)
                if unpack.report.returncode > 0:
                    raise Exception("unpack archive with package error")

    def check_esrv_output_for_errors(self, cmd):
            self.err = 0
            self.error_description = ""
            if hasattr(cmd.result.screen_capture, "esrv_rerror_count"):
                if int(cmd.result.screen_capture.esrv_rerror_count) > 0:
                    self.err += int(cmd.result.screen_capture.esrv_rerror_count)
                    logging.error("Recoverable error(s) found!")
                    if hasattr(cmd.result.screen_capture,
                                                "rerror_description"):
                        self.error_description += cmd.result.screen_capture.rerror_description
            if hasattr(cmd.result.screen_capture, "esrv_uerror_count"):
                if int(cmd.result.screen_capture.esrv_uerror_count) > 0:
                    self.err += int(cmd.result.screen_capture.esrv_rerror_count)
                    logging.error("Unrecoverable error(s) found!")
                    if hasattr(cmd.result.screen_capture,
                                                "uerror_description"):
                        self.error_description += cmd.result.screen_capture.uerror_description
            if hasattr(cmd.result.screen_capture, "esrv_cerror_count"):
                if int(cmd.result.screen_capture.esrv_cerror_count) > 0:
                    self.err += int(cmd.result.screen_capture.esrv_rerror_count)
                    logging.error("Catastrophic error(s) found!")
                    if hasattr(cmd.result.screen_capture,
                                                "cerror_description"):
                        self.error_description += cmd.result.screen_capture.cerror_description
            #if (err > 0):
            #    cfg.mcfg.log.error("Returned code %s but"
            #                                +" %i error(s) found" % (
            #                                    cmd.result.return_code,
            #                                    err))
            raise Exception(("esrv server "
                            +" stopped and return %i") % (
                                            cmd.result.return_code))

class __result__():
    pass


def get_error_stack_file(tmp_path, log=None):
    debug=info=warning=print
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    debug("Get_error_stack_file:path %s" % (tmp_path))
    debug("Get_error_stack_file:file list %s" % (os.listdir(tmp_path)))
    files_with_stack = [f for f in os.listdir(tmp_path) if "error_stack" in f]
    #error_srack_sep = "Error Stack Dump BEGIN ([\n A-Za-z.,:\-0-9\[\]/\\()*_]+) Error Stack Dump END"
    fields_re = "\.*(?P<field>[\w\s]+):\.*\[(?P<value>[ A-Za-z.,:\-0-9/\\()*_\]\[]+)\]\.\n"
    cof = len(files_with_stack)
    if cof > 0:
        debug("Get_error_stack_file:found %i files" % (cof))
        files_dict = dict()
        for file_ws in files_with_stack:
            files_dict[file_ws] = list()
            path_to_es=os.path.join(tmp_path, file_ws)
            with open(path_to_es, "r") as f:
                text = f.read()
            grab_lst = text.split("Error Stack Dump BEGIN")#re.findall(error_srack_sep, text, re.MULTILINE)
            debug("Get_error_stack_file:grab_list = %s" % (grab_lst))
            cod = len(grab_lst)
            if cod >0:
                debug("Get_error_stack_file:found %i dumps in file" % (cod))
                for stk_dump in grab_lst:
                    error_items_list = stk_dump.split("ERROR ENTRY:")
                    coi = len(error_items_list)
                    if cod > 0:
                        files_dict[file_ws].append(list())
                        for eis in error_items_list:
                            stk_fields = re.findall(fields_re, eis, re.MULTILINE)
                            files_dict[file_ws][-1].append(dict(stk_fields))
                    else:
                        debug("Get_error_stack_file")
            if len(files_dict[file_ws]) == 0:
                debug("Get_error_stack_file:Dump section didn't find in stack file")
        return files_dict





def get_formated(string, cfg):
    if hasattr(cfg, "tscfg"):
        result = string.format(cfg=cfg,
                                mcfg=cfg.mcfg.common,
                                        tscfg=cfg.tscfg)
    else:
        result = string.format(cfg=cfg, mcfg=cfg.mcfg.common)
    return result


def read_from_file(path):
    result = __result__()
    with open(path, "r") as f:
        result.readed_from_file = f.read()
    return result

"""
def send_to_thread_of_process(signal):
    ns.results_obj.start_process.queue.put(signal)

def sleep(ns, **keyargs):
    sleep = int(__preparing_variables__(ns, ns.tc, "seconds"))
    sleep = eval(sleep) if (hasattr(ns.tc, "eval")
                            and ns.tc.eval == True) else sleep
    ns.info("Main thread go to bed for %i seconds" % sleep)
    time.sleep(sleep)
"""

"""
def change_dir(ns, **keyargs):
    directory = __preparing_variables__(ns, ns.tc, "directory")
    os.chdir(directory)
    ns.info("Directory chaged to: %s" % (directory))
"""
"""
def back_to_wd(ns, **keyargs):
    os.chdir(ns.cfg.script_home_dir)
    ns.info("Directory chaged to script home directory: %s" %
                                        (ns.cfg.script_home_dir))
"""

def create_path(path, cleaning = True, log=None):
    debug=info=warning=print
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    debug("Starting create path: %s " % path)
    if (os.path.isdir(path)):
        if (cleaning):
            debug("Directory %s exist!" % path)
            shutil.rmtree(path)
    else:
        debug("Old directory(es) '%s' doesn't exist!" % path)
    if (not os.path.isdir(path)):
        os.makedirs(path)
    info("Created directory(es) '%s'!" % path)

def copy_files_to(source_path, destination_path,
                                    cfg, different_names= None, log=None):
    debug=info=warning=print
    fixture_hader = "Fixture copy_files_to: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    destination_path_mod = destination_path
    if isinstance(source_path, list):
        for cfile in source_path:
            presu = start_process("cp -rf %s %s" % (cfile,
                                                destination_path),
                                            cfg.mcfg, log=cfg.mcfg.log)
            if presu.result.return_code > 0:
                raise Exception(("Some error durring copy files to:\n"
                            +": StdOut:\n %s \n StdErr:\n %s!") % (
                                presu.result.std_out_decoded,
                                presu.result.errors_out_decoded))
            '''
            if (different_names is not None):
                destination_path_mod = os.path.join(
                            destination_path,
                            different_names[source_path.index(cfile)])
            debug("%s Copy from %s to %s " % (fixture_hader, cfile,
                                                destination_path_mod))
            if (os.path.isfile(cfile) or os.path.islink(cfile)):
                shutil.copy(cfile, destination_path_mod)
            elif (os.path.isdir(cfile)):
                #need extend to append files into dir
                #   now only replace posible
                if os.path.lexists(destination_path_mod):
                    debug("Distination directory exist! Removing..." )
                    shutil.rmtree(destination_path_mod)
                shutil.copytree(cfile, destination_path_mod)
            '''
    else:
         raise Exception("Path to file(s) need define as list!")

def start_process(command_prompt, cfg, thread_mode = False, wait_word=None,
                                            regexp_pars=None, log=None):
    debug=info=warning=print
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    if thread_mode and (wait_word is None):
        raise Exception("Fixture start_process: If you running"
                            + " in thread mode "
                           +"also need set wait_word, after that word"
                                  +" we will be ready for communicate")
    process_obj = process(config = cfg,
                        cmd = command_prompt,
                        logger=log,
                        thread_mode=thread_mode,
                        regexp_pars=regexp_pars,
                        wait_word=wait_word,
                        ready_timeout=3)
    #if ((process_obj.result.return_code is not None)
    #                            and (int(process_obj.result.return_code) > 0)):
    #        raise Exception("Process returned more than zerro: '%s'" %
    #                                    process_obj.result.return_code)
    return process_obj

def grab_from(reg_exp, retype, text, log=None):
    debug=info=warning=print
    fixture_hader = "Fixture grab_from: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    result = __result__()
    regfunc = getattr(re, retype)
    result.stdgrab = regfunc(reg_exp, text, re.MULTILINE)
    result.stdgrab_str = "\n".join(result.stdgrab)
    debug("%s grabbed from stdout '%s' by re %s" % (fixture_hader,
                                                    result.stdgrab_str,
                                                    reg_exp))
    return result

def save_to_file(content, path):
    with open(path, "w") as f:
        f.write(content)

def read_from_file(path):
    with open(path, "r") as f:
        text = f.read()
    return text

def prepar_fi_fr_templ(template, save_to, cfg):
    with open(template, "r") as f:
        content = f.read()
    content = content.format(cfg=cfg)
    with open(save_to, "w") as f:
        f.write(content)

def find_package_file(cfg, log=None, file_type=False, pretty_name=None):
    debug=info=warning=print
    fixture_hader = "Fixture find_package_file: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    path_to_current_package_folder=os.path.join(
                                    cfg.mcfg.common.package_mount_dir,
                                cfg.mcfg.common.package_version_name,
                        cfg.mcfg.common.package_source_sub_directory)
    debug("Current network packackage folder: %s" % path_to_current_package_folder)
    current_package_folder_dir_listing = os.listdir(
                            path_to_current_package_folder)
    debug(current_package_folder_dir_listing)
    curent_package_name_re = ("(?P<filename>dca-%s-"
                            +"(([0-9]+[.]{1}){3}[0-9]+)-%s-64[.]%s)") % (
                cfg.tscfg.package_midlename,
                                    pretty_name if pretty_name is not \
                                None else cfg.mcfg.os_release.pretty_name,
                cfg.mcfg.os_release.arc if not file_type else file_type)
    debug(curent_package_name_re)
    current_package_filtered_list = [x for x in \
                            current_package_folder_dir_listing if \
                            re.match(curent_package_name_re, x)]
    path_to_current_package = os.path.join(
                                path_to_current_package_folder,
                                current_package_filtered_list[0])
    
    return path_to_current_package

def find_installed_pkg(cfg, log=None):
    debug=info=warning=print
    fixture_hader = "Fixture find_installed_pkg: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    remove_pkg_name = cfg.mcfg.common.rpm_package_name \
                                if cfg.mcfg.os_release.arc == "rpm"\
                                   else cfg.mcfg.common.deb_package_name
    presu = start_process(cfg.mcfg.os_release.list_pkg_cmd,
                                        cfg.mcfg,
                                        log=cfg.mcfg.log)
    if presu.result.return_code > 0:
        raise Exception(("Some error durring looking for install"
                            +" package: StdOut: %s \n StdErr: %s!") % (
                                presu.result.std_out_decoded,
                                presu.result.errors_out_decoded))
    stdout_list = presu.result.std_out_decoded.strip().split("\n")
    stdout_list = [x for x in stdout_list if remove_pkg_name in x]
    if (len(stdout_list) > 1):
        raise Exception("Find more than one: %s!" % (", ".join(stdout_list)))
    elif (len(stdout_list) > 0):
        return (True, stdout_list[0])
    else:
        return (False, "")

def get_recursive_listing(path, log=None):
    debug=info=warning=print
    fixture_hader = "Fixture get_recursive_listing: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    out = ""
    for (current_file,
                dirs_in_current_dir,
                            files_in_current_dir) in os.walk(path):
        out+="%s\n" % current_file
        if len(dirs_in_current_dir) > 0:
            for f in dirs_in_current_dir:
                out+="%s\n" % os.path.join(current_file,f)
        if len(files_in_current_dir) > 0:
            for f in files_in_current_dir:
                out+="%s\n" % os.path.join(current_file,f)
    return out

def unpack_archive(path, cfg, log=None):
    debug=info=warning=print
    fixture_hader = "Fixture unpack_archive: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    #tgz archive
    if (re.match(".+\.tar\.gz", path)
            or re.match(".+\.tgz", path)):
        debug("Detected type tgz archive: '%s'" % path)
        cmd = "tar -xvf %s"
    else:
        warning("Archive type is not detected!: '%s'" % path)
        return 1

    presu = start_process(cmd % path, cfg.mcfg, log=log)
    if presu.result.return_code > 0:
        raise Exception(("Some error durring unpack file"
                            +": StdOut: %s \n StdErr: %s!") % (
                                presu.result.std_out_decoded,
                                presu.result.errors_out_decoded))

def get_service_status(service_name, cfg, log=None):
    debug=info=warning=print
    fixture_hader = "Fixture get_service_status: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    enabled_cmd = "sudo -S systemctl is-enabled %s" % service_name
    active_cmd = "sudo -S systemctl is-active %s" % service_name
    pid_cmd = "sudo -S systemctl status --no-pager %s | grep PID" % service_name
    reg_exp = {
        'status_is': '^.*Active:\s*(?P<status_is>[a-z]+)',
        'esrv_pid': '.*Main\s?PID:\s?(?P<esrv_pid>[0-9]+)\s?\(esrv_svc\)',
        }
    presu = start_process(enabled_cmd, cfg.mcfg, log=cfg.mcfg.log,
                                                    regexp_pars=reg_exp,
                                                    wait_word="esrv_svc")
    if presu.result.return_code > 0:
        raise Exception(("Some error durring getting service info"
                            +": StdOut: %s \n StdErr: %s!") % (
                                presu.result.std_out_decoded,
                                presu.result.errors_out_decoded))
    presu.result.std_out_decoded
    presu = start_process(active_cmd, cfg.mcfg, log=cfg.mcfg.log,
                                                    regexp_pars=reg_exp,
                                                    wait_word="esrv_svc")
    if presu.result.return_code > 0:
        raise Exception(("Some error durring getting service info"
                            +": StdOut: %s \n StdErr: %s!") % (
                                presu.result.std_out_decoded,
                                presu.result.errors_out_decoded))
    presu = start_process(pid_cmd, cfg.mcfg, log=cfg.mcfg.log,
                                                    regexp_pars=reg_exp,
                                                    wait_word="esrv_svc")
    if presu.result.return_code > 0:
        raise Exception(("Some error durring getting service info"
                            +": StdOut: %s \n StdErr: %s!") % (
                                presu.result.std_out_decoded,
                                presu.result.errors_out_decoded))
    return presu


#Not modified yet
def create_archive(ns, **keyargs):
    path = __preparing_variables__(ns, ns.tc, "path")
    content=__check_variables__(ns, ns.tc, "content")
    files=" ".join([__unpack_param__(ns, x) for x in content])
    command = shlex.split("tar -czvf %s.tgz %s" %(path, files))
    runprocess(command)

def start_easy_process(ns, **keyargs):
    command = __preparing_variables__(ns, ns.tc,
                                        "command")
    arguments = __check_variables__(ns, ns.tc,
                                        "argu")
    args = ""
    for argument in arguments:
        unpack = argument.get("unpack")
        unpack = False if unpack is None else True
        findregexp = argument.get("regexp")
        if unpack:
            args += "%s " % __unpack_param__(ns, argument["key"])
        elif findregexp is not None:
            raise Exception
            re.search(findregexp)
        else:
            args += "%s " % argument["key"]
    command = shlex.split("%s %s" % (command, args))
    ns.debug(command)
    result = runprocess(command, stderr=PIPE, stdout=PIPE)
    ns.debug(result.stderr)
    ns.debug(result.stdout)
    ns.debug(result.returncode)
    ns.debug(result.stderr)
    if (result.returncode > 0):
        ns.tcerror("Process return more than zerro: '%s'! %s" %
                                    (result.returncode, result.stderr),
                                                True)
    return result

def search_file(ns, **keyargs):
    path = __check_variables__(ns, ns.tc,
                                        "path")
    regexp = __check_variables__(ns, ns.tc,
                                        "regexp")
    result = __result__()
    dir_listing = os.listdir(path)
    result.files = [x for x in dir_listing if re.match(regexp)]
    return result

def exist_files_according_bom(ns, **keyargs):
    template, save_to = __preparing_variables__(ns, ns.tc,
                                                "template",
                                                "save_to")

def set_ns_value(ns, **keyargs):
    ns_str, value = __preparing_variables__(ns, ns.tc,
                                        "ns",
                                        "value")
    _set_to_ns_ = ns
    ns_to_list = ns_str.split(".")
    for _ns_ in ns_to_list(".")[1:-1]:
        _set_to_ns_ = getattr(_set_to_ns_,_ns_)
    setattr(_set_to_ns_, ns_to_list[-1])
    ns.warning("Changed namespace value %s to %s!" % (ns_str))

def __pseudo__(ns, **keyargs):
    rtype = __preparing_variables__(ns, ns.tc,
                                        "type")
    name, rtypes = __preparing_variables__(ns, ns.tc,
                                        "name",
                                        "types")
    if "results_obj_old" in keyargs.keys():
        ns.results_obj_old = keyargs.get("results_obj_old")
    old_arguments = None
    if (hasattr(ns.tc, "arguments")
                        and (not isinstance(ns.tc.arguments, dict))):
        old_arguments = ns.tc.arguments
        ns.debug("Test 5678 %s " % old_arguments.__dict__)
    for yaml_tc_cfg in ns.tc_yaml:
        #Warning it's different block insted of orcehstra look to
        #    ns.tc.name insted of ns.ts.name
        if yaml_tc_cfg["name"] == ns.tc.name:
            ns.tc.__dict__.update(yaml_tc_cfg)
    #Preparing teststeps for keys of types
    rtypes = {x['name'] : x['teststeps'] for x \
                                    in ns.tc.types}
    if (hasattr(ns.tc, "arguments")
                and (isinstance(ns.tc.arguments, list))):
         ns.debug(ns.tc.arguments)

    whoami = ns.tc.name
    if (rtype in rtypes.keys()):
        ns.info("Starting %s routine for type: %s" % (whoami, rtype))
        results_obj = __namespace__()
        if ns.results_obj_old is not None:
            ns.debug (ns.results_obj_old.__dict__)
            results_obj.__dict__.update(ns.results_obj_old.__dict__)
            ns.debug (results_obj.__dict__)
        tstp_index=0
        for teststep in rtypes[rtype]:
            tstp_index+=1
            ts_name = teststep.get("name")
            sub_ns = __namespace__()
            sub_ns.__label__ = "root(sub)"
            sub_ns.tc = __namespace__()
            sub_ns.tc.__label__ = "root.tc(sub)"
            sub_ns.ts = __namespace__()
            sub_ns.ts.__label__ = "root.ts(sub)"
            sub_ns.__dict__.update(ns.__dict__)
            ns.debug(teststep)
            sub_ns.tc.__dict__.update(teststep)
            sub_ns.ts.__dict__.update(ns.ts.__dict__)
            if (hasattr(sub_ns.tc, "arguments")
                            and (sub_ns.tc.arguments is not None)
                            and (isinstance(sub_ns.tc.arguments, dict))):
                args = sub_ns.tc.arguments
                ns.debug("Self TC(St) arguments %s " % sub_ns.tc.arguments)
                sub_ns.tc.arguments = __namespace__()
                sub_ns.tc.arguments.__dict__.update(args)
                ns.debug("Self TC(St) arguments %s " % sub_ns.tc.arguments.__dict__)
            if hasattr(ns.tc, "arguments") and (ns.tc.arguments is not None):
                    if ((not hasattr(sub_ns.tc, "arguments"))
                                    or (sub_ns.tc.arguments is None)):
                        sub_ns.tc.arguments = __namespace__()
                    #Replaced by hight level function arguments
                    if old_arguments is not None:
                        sub_ns.tc.arguments.__dict__.update(old_arguments.__dict__)
                        ns.debug("TC arguments after update by master TC %s " %
                                                        (ns.tc.arguments.__dict__))
            if (hasattr(sub_ns.tc, "arguments")):
                     ns.debug("Self TC(St) arguments %s " % sub_ns.tc.arguments)
                     if (not isinstance(sub_ns.tc.arguments, dict)):
                         ns.debug("Self TC(St) arguments %s " % sub_ns.tc.arguments.__dict__)
            """
            if teststep.get("arguments") is not None:
                    ns.debug(teststep.get("arguments"))
                    sub_ns.tc.arguments.__dict__.update(teststep["arguments"])
            
            ns.debug("Test 123: %s" % (sub_ns.tc.arguments.__dict__))
            """
            sub_ns.results_obj = results_obj
            ns.debug(dir(sub_ns.results_obj))
            #set patch for error
            sub_ns.tcerror = lambda *args : [1].extend(args)
            ns.info("Starting teststep %s" % ts_name)
            if hasattr(ns.tc_funcs, ts_name):
                func = getattr(ns.tc_funcs, ts_name)
            else:
                func = __pseudo__
                ts_name = "%s_%s_%i" % (ts_name, rtype, tstp_index)
            result = func(sub_ns, results_obj_old=results_obj)
            ns.debug("After run: %s" % result)
            if (isinstance(result, int)
                        and (result > 0)):
                return ns.tcerror(("TestStep %s: Soft ERROR!! retunrned:"
                                    +" '%i' . Routine") % (ts_name, result))
            if result is not None:
                if not hasattr(results_obj, ts_name):
                    setattr(results_obj, ts_name, result)
                else:
                    getattr(results_obj
                             , ts_name).__dict__.update(result.__dict__)
                ns.debug(dir(results_obj))
            """
                if not hasattr(results_obj, ts_name):
                    setattr(results_obj, ts_name, result)
                else:
                    already_had_value = getattr(results_obj, ts_name)
                    if type(already_had_value) == type([]):
                        already_had_value.append(result)
                    else:
                        setattr(results_obj, ts_name,
                                                [already_had_value,
                                                        result])
            """
        ns.info("%s by type %s: Teststeps finished!" % (whoami, rtype))
        results_obj.returncode = 0
        return results_obj
    else:
        ns.tcerror(("We haven't type with name %s !") %
                                    (rtype))

def exist_files_according_bom(ns, **keyargs):
    check_ns_vars = check_ns_variable(ns.tc,
                                        "type")
    if (check_ns_vars):
        ns.tcerror(("Need set necessarry variables (%s) "
                                +"for making!") %
                                    (check_ns_vars),
                            True)
