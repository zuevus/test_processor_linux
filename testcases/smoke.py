import lib.tcfixtures
import lib.tcasserts
import os
import re
import shutil
import time

class some_test_name(lib.tcfixtures.TestCaseWrap):
    taxon="smoke"
    def do(self, cfg, self_id):
        pass

    def asserts(self, cfg, self_id):
        pass
