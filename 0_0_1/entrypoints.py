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
            # TODO

            return True
        return False


def _init():
    """Initialize arguments"""
    parser.add_argument("--resize-to", type=str, default='full',
                        choices=('full', 'half', 'quarter', 'eighth'),
                        help="resizes images by the largest side for opensfm. Set to 'full' to \
                        disable. Default: full")
    parser.add_argument("--opensfm-depthmap-method", type=str,
                        choices=(
                            'BRUTE_FORCE',
                            'PATCH_MATCH',
                            'PATCH_MATCH_SAMPLE'
                            ),
                        help="Raw depthmap computation algorithm. PATCH_MATCH and \
                        PATCH_MATCH_SAMPLE are faster, but might miss some  \
                        valid points. BRUTE_FORCE takes longer but produces \
                        denser reconstructions. Default: PATCH_MATCH")
    parser.add_argument("--opensfm-depthmap-min-consistent-views", type=int,
                        default=3, choices=(3, 6),
                        help="Minimum number of views that should reconstruct a \
                        point for it to be valid. Use lower values if your \
                        images have less overlap. Lower values result in \
                        denser point clouds but with more noise. Default: 3")
    parser.add_argument("--texturing-nadir-weight",  type=str, required=True,
                        choices=('urban', 'rural'),
                        help="Affects orthophotos only.")
    parser.add_argument("--georeferencing", type=str, default='EXIF',
                        choices=('GCP', 'EXIF'),
                        help="Mode of georeferencing: either GCP, or EXIF.")
    parser.add_argument("--pc-las", action="store_true",
                        help="Export the georeferenced point cloud in LAS format. \
                        Default: False")
    parser.add_argument("--dsm", action="store_true",
                        help="Use this tag to build a DSM (Digital Surface Model, \
                        ground + objects) using a progressive morphological \
                        filter. Default: False")
    parser.add_argument("--dem-resolution", type=float,
                        default=range(0, 1000000),
                        help="DSM/DTM resolution in cm / pixel. Default: 5")
    parser.add_argument("--orthophoto-resolution", type="float",
                        default=range(0, 1000000),
                        help="Orthophoto resolution in cm / pixel. Default: 5")
    parser.add_argument("--min-num-features", type=int, default=10000,
                        help="Minimum number of features to extract per image. More \
                        features leads to better results but slower execution.\
                        Default: 10000")


_init()
