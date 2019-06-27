import testcases.functional
import lib.testing
import traceback

def some_ts(cfg):
    enabled = True
    if enabled:
        tc_lib_s = testcases.smoke
        tc_lib = testcases.functional
        return [
            (tc_lib_s.some_test_name, 1),
            (tc_lib.some_test_name, 1),
        ]
