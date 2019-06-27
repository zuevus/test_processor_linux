# -*- coding: utf-8 -*-
'''
@author                         yzx
@tested_version                 Python 3.6.5
@comply_with_python_3           yes
'''
import time
from subprocess import run, PIPE
import psutil
import os
from lib.testing import db_communicate
import re

def exist_files_according_bom(bom_file_content, root_path,
                                            inverted = False, log=None):
    debug=info=warning=print
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    bom_file_content = bom_file_content.split("\n")
    for file_path in bom_file_content:
        if len(file_path) > 0:
            file_path = os.path.join(root_path, file_path)
            if ((not os.path.lexists(file_path))
                    and (not inverted)):
                warning("File is not exist: '%s'!" % file_path)
                return (False, "File is not exist: '%s'!" % file_path)
            elif ((os.path.lexists(file_path)) and (inverted)):
                warning("File exist: '%s'!" % file_path)
                return (False, "File exist: '%s'!" % file_path)
    return (True, "")

def exist_files_one_to_one_bom_list(bom_file_content, checking_directory,
                                            inverted = False, log=None):
    debug=info=warning=print
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    debug("Checking directory: %s" % checking_directory)
    if not inverted:
        if not os.path.isdir(checking_directory):
            msg="Nothing to check '%s' is not exist!" % (checking_directory)
            warning(msg)
            return (False, msg)
        bom_file_content_list = bom_file_content.split("\n")
        directory_list_of_files = [os.path.join(checking_directory, x) \
                            for x in os.listdir(checking_directory)]
        if len(bom_file_content_list) != len(directory_list_of_files):
            msg=("Count of files is different!"
                    +"Bom file content '%s' files,"
                    +" but checking directory '%s'!") % (
                                len(bom_file_content_list),
                                len(directory_list_of_files))
            warning(msg)
            return (False, msg)
        for file_path in directory_list_of_files:
            if file_path not in bom_file_content_list:
                warning("File is not exist: '%s'!" % file_path)
                return (False, "File is not exist: '%s'!" % file_path)
    elif os.path.isdir(checking_directory):
        warning("Directory exist: '%s'!" % checking_directory)
        if len(directory_list_of_files) > 0:
            warning("Found some files in directory: '%s'!" % (
                                        checking_directory))
        for file_path in directory_list_of_files:
            if file_path in bom_file_content_list:
                msg =("File '%s' exist in directory,"
                                +" also counted in bom!") % file_path
                warning(msg)
                return (False, msg)
            else:
                msg =("File '%s' exist in directory!"
                                +" and didn't count in bom!") % file_path
                warning(msg)
                return (False, msg)
    return (True, "")

def process_stoped_durring_timeout(timeout, pid, log=None):
    debug=info=warning=print
    fixture_hader = "process_stoped_durring_timeout: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    """
    Waiting when process with `pid` stoped untill timeout, if not
    test failed
    """
    time_to_stop = time.time() + timeout
    while (time_to_stop > time.time()):
            if not psutil.pid_exists(int(pid)):
                    break
    if (time_to_stop < time.time()):
        warning("Time is out!")
    result = ((not psutil.pid_exists(int(pid))), "")
    if not result:
        warns_txt = ("Assert process_stoped_durring_timeout failed!"
                        +" Killing process with pid %i " % int(pid))
        warning(warns_txt)
        result = (False, warns_txt)
        run(["kill", "-9", pid])
    return result

def query_is_true(query, assert_value, db_path, cfg, log=None, error_query=None):
    debug=info=warning=print
    fixture_hader = "query_is_true: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    db_obj = db_communicate(db_path, cfg.mcfg, cfg.mcfg.log)
    #try:
    db_result = db_obj.fetch(query)
    result = (eval(assert_value), "")
    #except Exception as exp:
    #    result = False
    #    ns.debug("Raise exception: %s " % exp)
    if (not result and (error_query is not None)):
        db_result = db_obj.fetch(query)
        if sub_select is not None:
                    fetch_all = db_obj.fetch(error_query)
                    draw_table = "%s\n" % (sub_select)
                    draw_table += "%s\n"%("".join(["|{0:40}|".format(row_name[0]) for row_name in fetch_all[0]]))
                    draw_table += "%s\n"%("-"*100)
                    draw_table += "\n".join([["|{0:40}|".format(col) for col in row] for row in fetch_all[1]])
                    warning(draw_table)
                    result = (result, draw_table)
    return result

def got_re_is_equal(grab_reg_exp, txt, equal, log=None):
    debug=info=warning=print
    fixture_hader = "get_re_is_equal: "
    if log is not None:
        debug = log.debug
        info = log.info
        warning = log.warning
    grabs = re.findall(grab_reg_exp, txt, re.MULTILINE)
    for grab in grabs:
        if equal in grab:
            return (True, "")
    return (False, "Reg Exp is not extracted! %s didn't found by %s" % (
                                   equal, grab_reg_exp ))
