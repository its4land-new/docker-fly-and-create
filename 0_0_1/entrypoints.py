#!/usr/bin/python

"""Entrypoint functions for the Publish and Share wp4_odm tool.

@author: Ivan Ivanov
@email: ivan.ivanov@suricactus.com
@copyright: MIT, ITC, University of Twente, Enchede, NL, 2019
"""

import argparse
import os
import sys

from publishandshare.toolwrapper.wrapper.basicprocessing import BasicProcessing

from .orthophoto import (start, parse_args)

sys.path.append(os.path.split(__file__)[0])

parser = argparse.ArgumentParser(prog="wp4_odm")


def orthophoto(process, parameters):
    processing = Wp4odm(process, parameters)

    if processing.start():
        processing.finish()
        return True

    processing.abort()

    return False


class Wp4odm(BasicProcessing):
    """Work package 4 - OpenDroneMap."""

    def start(self):
        if super(Wp4odm, self).start():
            args = parse_args()
            start(args)

            return True
        return False

if __name__ == '__main__':
    args = parse_args()
    start(args)