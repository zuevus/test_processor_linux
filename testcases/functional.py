# -*- coding: utf-8 -*-
import lib.tcfixtures
import lib.tcasserts
import os
import shutil
import time
import lib.testing
import testcases.smoke
from subprocess import run as run_easy_process
import pprint

class some_test_name(lib.tcfixtures.TestCaseWrap):
    taxon = "functional"
    def do(self, cfg, self_id):
        pass

    def asserts(self, cfg, self_id):
        pass
