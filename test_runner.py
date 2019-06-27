#!/usr/bin/env python
# -*- coding: utf-8 -*-

def main(args):
    '''
    @author                     yzx
    @tested_version             Python 3.6.5
    @comply_with_python_3       yes
    '''
    cfg.play()

if (__name__=="__main__"):

    import sys
    from lib.config import cfg
    if __debug__:
        cfg=main(sys.argv)
    else:
        sys.exit(main(sys.argv))
