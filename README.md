# test_processor_linux
For easy start testing procedure
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
