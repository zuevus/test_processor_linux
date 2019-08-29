# test_processor_linux
For easy start testing procedure (only for linux based)
<h3>Necessory structure</h3>
<ul>
  <li> lib\ - library folder with necessory libs.</li>
  <li> testcases\ - folder that content lib with set of testcases</li>
  <li> testsuites\ - folder that content set of test cases</li>
  <li> cfg\main.cfg - configuration file</li>
  <li>test_runner.py - using for start testing</li>
</ul>
 <br/>
 <h3>Main configuration file</h3>
 <p>Configuration file based on ConfigParcer Python's standart library. 
 In common section of the configuration file we have parameters, 
 that translate as command line arguments, with default values from this file.</p>
 <p>Also in this file we have logger settings.</p>
 <p>Example of configuration: <i><br/> [common] <br/>timeout=600<br/>
dca_linux_dir_postfix=<br/>
dca_linux_dir_prefix=../iecsdk<br/>
dca_linux_dir_mask={self.dca_linux_dir_prefix}{self.dca_linux_dir_postfix}<br/>
dca_linux_build_dir=/_build/linux<br/>
[loggers]<br/>
keys=root,main_log<br/>
<br/>
[handlers]<br/>
keys=consoleHandler,fileHandler<br/>
<br/>
[formatters]<br/>
keys=form01<br/>
<br/>
[logger_root]<br/>
level=DEBUG<br/>
handlers=consoleHandler,fileHandler<br/>
<br/>
[logger_main_log]<br/>
level=DEBUG<br/>
handlers=consoleHandler,fileHandler<br/>
qualname=main_log<br/>
propagate=0<br/>
<br/>
[handler_consoleHandler]<br/>
class=StreamHandler<br/>
level=DEBUG<br/>
formatter=form01<br/>
args=(sys.stdout,)<br/>
<br/>
[handler_fileHandler]<br/>
class=FileHandler<br/>
level=DEBUG<br/>
formatter=form01<br/>
args=('log/main.log', 'w')<br/>
<br/>
[formatter_form01]<br/>
format=%(asctime)s - %(levelname)s - %(message)s<br/>
datefmt=%m/%d/%Y %I:%M:%S %p<br/>
</i>
</p>
 <h3>test_runner.py test runner command line interface</h3>
 <p>For check avalible parameters (that set in main.cfg) you could use -h option:</p>
 <p>

/usr/bin/env python3 .\test_runner.py -h<br/>
<br/>
usage: test_runner.py [-h] [-l [LOGLEVEL]] [-r RUNTEST [RUNTEST ...]]<br/>
                      [--script_human_name [SCRIPT_HUMAN_NAME]]<br/>
                      [--out_path [OUT_PATH]]<br/>
                      [--dca_linux_dir_prefix [DCA_LINUX_DIR_PREFIX]]<br/>
                      [--user_name [USER_NAME]]<br/>
                      [--user_password [USER_PASSWORD]]<br/>
                      [--dca_linux_dir_postfix [DCA_LINUX_DIR_POSTFIX]]<br/>
                      [--output_xml_file [OUTPUT_XML_FILE]]<br/>
                      [--timeout [TIMEOUT]]<br/>
                      [--default_log_level [DEFAULT_LOG_LEVEL]]<br/>
                      [--dca_linux_dir_mask [DCA_LINUX_DIR_MASK]]<br/>
                      [--config_xml_file [CONFIG_XML_FILE]]<br/>
                      [dca_linux_dir]<br/>
<br/>
positional arguments:<br/>
  dca_linux_dir         Directory to testing product(dca_linux_dir)<br/>
<br/>
optional arguments:<br/>
  -h, --help            show this help message and exit<br/>
  -l [LOGLEVEL], --loglevel [LOGLEVEL]<br/>
                        Set log level: 10 - DEBUG - Detailed information,<br/>
                        typically of interest only when diagnosing problems.<br/>
                        20 - INFO - Confirmation that things are working as<br/>
                        expected. 30 - WARNING - An indication that something<br/>
                        unexpected happened, or indicative of some problem in<br/>
                        the near future (e.g. 'disk space low'). The software<br/>
                        is still working as expected. 40 - ERROR - Due to a<br/>
                        more serious problem, the software has not been able<br/>
                        to perform some function. 50 - CRITICAL - A serious<br/>
                        error, indicating that the program itself may be<br/>
                        unable to continue running.<br/>
  -r RUNTEST [RUNTEST ...], --runtest RUNTEST [RUNTEST ...]<br/>
                        Paths to test for running or directory with tests<br/>
  --timeout [TIMEOUT]   This parameter setted by default in config file with<br/>
                        value: 600<br/>
  --dca_linux_dir_postfix [DCA_LINUX_DIR_POSTFIX]<br/>
                        This parameter setted by default in config file with<br/>
                        value: /development/clientside/collector/iecsdk<br/>
  --dca_linux_dir_prefix [DCA_LINUX_DIR_PREFIX]
                        This parameter setted by default in config file with<br/>
                        value: ../dca-linux<br/>
  --dca_linux_dir_mask [DCA_LINUX_DIR_MASK]<br/>
                        This parameter setted by default in config file with<br/>
                        value: {self.dca_linux_dir_prefix}{self.dca_linux_dir_postfix}<br/>
  --script_human_name [SCRIPT_HUMAN_NAME]<br/>
                        This parameter setted by default in config file with<br/>
                        value: DCA tests<br/>
  --output_xml_file [OUTPUT_XML_FILE]<br/>
                        This parameter setted by default in config file with<br/>
                        value: output.xml<br/>
  --out_path [OUT_PATH]<br/>
                        This parameter setted by default in config file with<br/>
                        value: out<br/>
  --config_xml_file [CONFIG_XML_FILE]<br/>
                        This parameter setted by default in config file with<br/>
                        value: tests_config_file.xml<br/>
  --user_name [USER_NAME]<br/>
                        This parameter setted by default in config file with<br/>
                        value: test<br/>
  --user_password [USER_PASSWORD]<br/>
                        This parameter setted by default in config file with<br/>
                        value: <br/>
  --default_log_level [DEFAULT_LOG_LEVEL]<br/>
                        This parameter setted by default in config file with<br/>
                        value: 10<br/>
  --sudo_prompt_content [SUDO_PROMPT_CONTENT]<br/>
                        This parameter setted by default in config file with<br/>
                        value: password for test<br/>
  --span_lenght [SPAN_LENGHT]<br/>
                        This parameter setted by default in config file with<br/>
                        value: 15<br/>
  --default_codepage [DEFAULT_CODEPAGE]<br/>
                        This parameter setted by default in config file with<br/>
                        value: UTF-8<br/>
</p>
