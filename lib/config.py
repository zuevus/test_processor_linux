# -*- coding: utf-8 -*-
'''
@author                         yzx
@tested_version                 Python 3.6.5
'''

import configparser as ConfigParser
import argparse
import os
import sys
import re
import logging
import time
from datetime import datetime as dati
import logging.config
from importlib import import_module
import traceback
import junit_xml
import lib.testing

#<DEFAULT PARAMETERS>
path_to_script, script_name = os.path.split(sys.argv[0])
#Path to log dir
__LOG_FILES_PATH__ = os.path.join(path_to_script,
                                       'log')
#Path to config file
__CONFIG_FILE_NAME__ = "main.cfg"
__CONFIG_DIR_PATH__ = os.path.join(path_to_script,
                                    "cfg")
__CONFIG_FILE_PATH__ = os.path.join(__CONFIG_DIR_PATH__,
                               __CONFIG_FILE_NAME__
                               )
def preparing_initial_files():
    #Create if not exist log dir
    if not os.path.isdir(__LOG_FILES_PATH__):
        os.makedirs(__LOG_FILES_PATH__)

    #Checking for exist of config file
    if os.path.isfile(__CONFIG_FILE_PATH__):
        logging.config.fileConfig(__CONFIG_FILE_PATH__)
    else:
        print ("Configuration file %s is not exist!" %
                                                    (__CONFIG_FILE_PATH__))
        sys.exit(127)

#</DEFAULT PARAMETERS>
class str_formatter():
    def __init__(self, **vargs):
        for key, value in vargs.items():
            setattr(self, key, value)

    def ssifns(self, value, name):
        """
        set self if not set value
        """
        return (value if value else getattr(self, name))

    def indent(string, indent_value=False):
        indent_value = ssifns(indent_value, "indent_value")
        return ("%s%s" % (" "*indt,string))

    def repeat(string, repeat_value=False):
        repeat_value = ssifns(repeat_value, "repeat_value")
        return (("%s"%(string))*repeat_value)

class configure():
    class _section_to_fields_():
        def get_formated(self, key, recursion = False):
            if not recursion:
                return getattr(self, key).format(ts_config = self
                                                , config = self)
            else:
                result = getattr(self, key).format(ts_config = self
                                                , config = self)
                def recur_format(res):
                    if "{" in res:
                        res = recur_format(res.format(ts_config = self
                                                , config = self))
                    return res
                result = recur_format(result)
                return result
        @property
        def joined_all_tc_name(self):
            reg_exp = "tc([0-9]+)_name"
            tmp_dct = {re.search(reg_exp, x).groups()[0] : x for x in \
                    self.__dict__.keys() \
                                    if re.match(reg_exp, x)}
            result=""
            for index, tc_name in tmp_dct.items():
                current_attrib_cont = getattr(self, tc_name).format(
                    ts_config = self)
                cur_ts_descr_name="tc%s_descr" % (index)
                self.tc_index=index
                if hasattr(self, cur_ts_descr_name):
                    descr_attrib_cont = getattr(self, cur_ts_descr_name)
                    result += ("\n    > %s\n\n        Description: %s\n"
                                % (current_attrib_cont.format(
                                                ts_config = self),
                                          descr_attrib_cont
                                          ))
                else:
                    result += "\n%s\n" % (current_attrib_cont.format(
                                                ts_config = self))
            self.tc_index = 0
            return result

        @property
        def dca_linux_dir(self):
            return (self.dca_linux_dir_mask.format(**{"self":self})
        if not hasattr(self, "__dca_linux_dir_mask__") 
                    else self.__dca_linux_dir_mask__)

        @dca_linux_dir.setter
        def dca_linux_dir(self, value):
            self.__dca_linux_dir_mask__ =value

        def __init__(self, section, config, repl=None):
            self.__config__ = config
            for item in config.items(section):
                if repl is None:
                    setattr(self, item[0],item[1])
                else:
                    if repl[0] in item[0]:
                        setattr(self, item[0].replace(*repl),item[1])
        def __str__(self):
            return "object:\n  |-%s" % ("\n  |-".join(["%s = %s" %(key,
                    value) for key, value in self.__dict__.items()\
                                if ("__" not in key)]))

    class __testsuite__():
        def __init__(self, ts_name, conf, cfg):
            self.mcfg = cfg
            self.conf = conf
            self.cfg = cfg._section_to_fields_("testsuites", conf)
            self.__dict__.update(cfg._section_to_fields_("testsuites",
                                            conf).__dict__)
            self.ts_name = ts_name

        def tc(self, number):
            return self.mcfg.__testcase__(self.ts_name,
                                self.conf,
                                self.mcfg,
                                number,
                                self.cfg)
            self.cfg = cfg._section_to_fields_(test, conf)

    class __testcase__():
        def __init__(self, ts_name, conf, mcfg, number, tscfg):
            self.mcfg = mcfg
            self.tscfg = tscfg
            self.__dict__.update(mcfg._section_to_fields_(ts_name,
                            conf, ("tc%i_" % number, "")).__dict__)

    def __init__(self):
        #Ready for start key
        self.tc_configured = False
        #Set current path and script name
        self.path_to_script, self.script_name = os.path.split(sys.argv[0])
        #Set current path and script name
        self.script_home_dir = os.getcwd()
        #Set path to dir before script
        self.path_to_upper_dir = os.path.split(self.script_home_dir)[0]
        #Set main log file
        preparing_initial_files()
        self.log = logging.getLogger('main_log')
        #Init config parser obj
        config = ConfigParser.ConfigParser()
        config.read(__CONFIG_FILE_PATH__)
        #Set self common field as section to fiels class instance
        self.common = self._section_to_fields_("common", config)
        #String formatter instance create
        self.format = str_formatter(
                repeat_value=self.common.span_lenght,
                indent_value=self.common.tab_wite_space_lenght
                                )
        #Create instance of arguments parcer class
        parser = argparse.ArgumentParser()
        #Preparing command prompt arguments
        #    - - - log level
        parser.add_argument("-l",
                            "--loglevel",
                            type=int,
                            help="""Set log level: 10 - DEBUG - Detailed
 information, typically of interest only when diagnosing problems.
20 - INFO - Confirmation that things are working as expected.
30 - WARNING - An indication that something unexpected happened,
or indicative of some problem in the near future (e.g. 'disk space low').
 The software is still working as expected. 40 - ERROR - Due to a more
serious problem, the software has not been able to perform some function.
50 - CRITICAL - A serious error, indicating that the program itself may
be unable to continue running. """,
                            default=self.common.default_log_level,
                            dest='loglevel',
                            nargs='?'
                            )
        #    - - - test suites for running
        parser.add_argument("-r",
                            "--runtestsuites",
                            type=str,
                    help=("MANDATORY! Setting paths to playbook"),
                            dest='testsuite_list',
                            nargs='+'
                            )
        #    - - - folder where placed DCA linux
        parser.add_argument("dca_linux_dir",
                            type=str,
                    help="Directory to testing product(dca_linux_dir)",
                            default=None,
                            nargs='?'
                            )
        #    - - - all parameters that sets in main configuration file
        args_lst = {key:value for key, value in \
                        dict(self.common.__dict__).items()
                                    if not ("__" in key)}
        for key, value in args_lst.items():
            parser.add_argument("--%s" % (key),
                                type=str,
                                dest='%s' % (key),
                    help=("This parameter setted by default"
                            +" in config file with value: '%s'" % (value)),
                                default=None,
                                nargs='?'
                                )
        #Parsing command prompt arguments
        args = parser.parse_args()
        if (args is not None):
            #Set log level by command argument
            if re.match("([1-5]{1}0)", str(args.loglevel)):
                self.log.setLevel(args.loglevel)
            else:
                self.log.setLevel(self.common.default_log_level)
            #Setting command prompt arguments to configuration fields
            for key, value in dict(args.__dict__).items():
                if ((value is not None) and hasattr(self.common, key)):
                    self.log.debug("Config field %s with value %s" %
                                    (key, getattr(self.common, key)))
                    self.log.debug("replaced by %s" % value)
                    setattr(self.common, key, value)
            #If setted -r (--runtestsuite)
            if (hasattr(args, "testsuite_list")
                and (args.testsuite_list is not None)
                and len(args.testsuite_list)>0 ):
                    self.tc_configured = True
                    self.testsuite_list = args.testsuite_list

            else:
                self.log.error("You have to set command prompt argument"
                                               +" -r (--runtestsuites)!")
                sys.exit(1)
        else:
            self.log.error("Configuring couldn't parse commant"
                                                +" prompt arguments!")
            sys.exit(1)


    def __cfg_to_fields__(self, config_file_path, sector_name):
                    #Init config parser obj
                    config = ConfigParser.ConfigParser()
                    config.read(config_file_path)
                    return self._section_to_fields_(sector_name, config)
    def play(self):
        if (self.tc_configured):
            for tss_name in self.testsuite_list:
                module_file_name = "testsuites.%s" % tss_name
                conf_file_name = "%s.cfg" % tss_name
                conf_file_path = os.path.join("testsuites"
                                                    , conf_file_name)
                config = ConfigParser.ConfigParser()
                config.read(conf_file_path)                
                artefact_path = self.common.artefact_path.format(cfg = self)
                source_path = self.common.source_path.format(cfg = self)
                create_dir_structure = [artefact_path, source_path]
                for tmp_path in create_dir_structure:
                    if not os.path.isdir(tmp_path):
                        self.log.info(("%s directory doesn't"
                                            +" exist!") % tmp_path)
                        self.log.info("Creating directory...")
                        os.mkdir(tmp_path)
                results=[]
                ns = import_module(module_file_name)
                for tc_name in [attr for attr in ns.__dict__.keys()\
                                            if ("__" not in attr)]:
                    self.ts_cfg =  self.__testsuite__(tc_name,
                                                config,
                                                self)
                    attrib = getattr(ns, tc_name)
                    if (callable(attrib)):
                        result = lib.testing.testsuite_wrap(attrib)
                        if isinstance(result, int):
                            #testsuite configuration errors
                            if result == 2:
                                self.log.error(
                                ("%s.%s - no one of testcases found."
                                            +" Ignored...") %
                                                (tss_name,
                                                        tc_name))
                            else:
                                self.log.error(
                                ("%s.%s - some error durring runnig."
                                            +" Ignored...") %
                                                (tss_name,
                                                        tc_name,
                                                            result))
                        else:
                            results.append(result)
                report_file_name = 'output_%s_%s.xml' % (tss_name,
                                            self.os_release.name)
                report_file_path = os.path.join(artefact_path,
                                                report_file_name)
                self.log.debug(results)
                with open(report_file_path, 'w') as f:
                     junit_xml.TestSuite.to_file(f, results)
                for result in results:
                    if result.returncode > 0:
                        sys.exit(result.returncode)
                if len(results) < 1:
                    sys.exit(2)

    @property
    def os_release(self):
        class linux_release():
            def __init__(self, cfg):
                self.cfg = cfg
            def set_relver(self, regexp, file_name):
                with open(file_name, "r") as f:
                    relver = re.search(regexp, f.read(), re.MULTILINE)
                    for key, value in relver.groupdict().items():
                        setattr(self, key, value)
            @property
            def install_cmd(self):
                if (self.arc == "rpm"):
                    return self.cfg.common.rpm_install_cmd
                elif (self.arc == "deb"):
                    return self.cfg.common.dpkg_install_cmd
            @property
            def remove_cmd(self):
                if (self.arc == "rpm"):
                    return self.cfg.common.rpm_remove_cmd
                elif (self.arc == "deb"):
                    return self.cfg.common.dpkg_remove_cmd
            @property
            def list_pkg_cmd(self):
                if (self.arc == "rpm"):
                    return self.cfg.common.rpm_list_installed_pkg_cmd
                elif (self.arc == "deb"):
                    return self.cfg.common.dpkg_list_installed_pkg_cmd
            @property
            def pretty_name(self):
                if ("centos" in self.name.lower()):
                    return "centos"
                elif ("clear linux" in self.name.lower()):
                    return "crs"
                elif ("suse" in self.name.lower()):
                    return "SuSE"
                elif ("ubuntu" in self.name.lower()):
                    return "Ubuntu"
        rhel = "/etc/redhat-release"
        deb = "/etc/lsb-release"
        other_release = "/etc/os-release"
        result=linux_release(self)
        if os.path.isfile(rhel):
            result.based = "RedHat"
            result.arc = "rpm"
            regexp = ("^(?P<name>\w+)(\s*\w*)*\s+(?P<version>"
                +"[0-9]+\.{1}[0-9]+\.{1}[0-9]+)\s")
            result.set_relver(regexp, rhel)
        elif os.path.isfile(deb):
            result.based = "Debian"
            result.arc = "deb"
            regexp = ("DISTRIB_ID=(?P<name>\w+)(\n*\s*)"
                    + "*DISTRIB_RELEASE=(?P<version>[0-9]+\.{1}[0-9]+)")
            result.set_relver(regexp, deb)
        elif os.path.isfile(other_release):
            regexp = ("PRETTY_NAME=(?P<name>\w+)(\n*\s*)"
                    + "*VERSION_ID=(?P<version>[0-9]+\.{1}[0-9]+)")
            result.set_relver(regexp, deb)
            if ("openSUSE" in result.name):
                result.based = "openSUSE"
                result.arc = "rpm"
            elif ("Clear Linux" in result.name):
                result.based = "Clear linux"
                result.arc = "rpm"
            else:
                result.based = "Unrecognized"
                result.arc = "rpm"
        else:
            result = None
        return result
            
cfg = configure()
