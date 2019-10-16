"""Orthophoto tool ODM"""

from typing import (Dict, List, Any)
import os
import argparse
import zipfile
import traceback
import subprocess
import datetime

import imageio

from Its4landAPI import Its4landAPI, Its4landException


# sample call:
# python3 orthophoto.py --texturing-nadir-weight urban --content-item-id 50c4e5fe-0017-4dc3-93a6-983896839efa --project-id 8d377f30-d244-41b9-9f97-39a711b4679a


WORK_VOLUME = '/code'
# WORK_VOLUME = './dataset'
PLATFORM_URL = 'https://platform.its4land.com/api/'
PLATFORM_API_KEY = '1'


def download(url: str, dest: str) -> str:
    """Download file on specified URL to specified location."""
    api = Its4landAPI(url=PLATFORM_URL, api_key=PLATFORM_API_KEY)

    api.session_token = 'NEW'
    api.download_content_item(url, filename=dest)

    return dest


def unzip(file: str, dest: str) -> None:
    """Unzip specified file to a destination."""
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(dest)


def get_image_properties(dirname: str) -> Dict:
    """Get image properties like size etc."""
    image_basename = None

    for file in os.listdir(dirname):
        if (
            file.endswith('.jpg') or
            file.endswith('.jpeg') or
            file.endswith('.JPG') or
            file.endswith('.JPEG')
        ):
            image_basename = file
            break

    assert image_basename

    image_filename = os.path.join(dirname, image_basename)
    width, height = imageio.imread(image_filename).shape[:2]

    return {
        'width': width,
        'height': height,
    }


def to_odm_args(args: Dict[str, str], image_max_side_size: int) -> Dict[str, Any]:
    """Input params translated to ODM params."""
    defaults = {}
    texturing_nadir_weight = {
        'rural': 16,
        'urban': 24,
    }
    resize_to = {
        'full': -1,
        'half': image_max_side_size / 2,
        'quarter': image_max_side_size / 4,
        'eighth': image_max_side_size / 8,
    }

    defaults['resize_to'] = resize_to[args['resize_to']]
    defaults['texturing_nadir_weight'] = texturing_nadir_weight[args['texturing_nadir_weight']]

    defaults['opensfm_depthmap_method'] = args['opensfm_depthmap_method']
    defaults['opensfm_depthmap_min_consistent_views'] = args['opensfm_depthmap_min_consistent_views']
    defaults['pc_las'] = args['pc_las']
    defaults['dsm'] = args['dsm']
    defaults['dem_resolution'] = args['dem_resolution']
    defaults['orthophoto_resolution'] = args['orthophoto_resolution']
    defaults['min_num_features'] = args['min_num_features']

    if args['georeferencing'] == 'EXIF':
        defaults['use_exif'] = True
    elif args['georeferencing'] == 'GCP':
        defaults['use_exif'] = False

    return defaults


def upload_results(project_id: str) -> Dict:
    """Upload files to their final destination on the platform."""

    api = Its4landAPI(url=PLATFORM_URL, api_key=PLATFORM_API_KEY)

    api.session_token = 'token'
    dt = datetime.datetime.now().replace(microsecond=0).isoformat()
    name = 'Orthophoto_%s' % dt

    print('Uploading orthophoto "%s" ...' % name)

    return api.upload_ddi_layer(
        file=os.path.join(WORK_VOLUME, 'odm_orthophoto', 'odm_orthophoto.tif'),
        spatial_source_type='orthophoto',
        tags=['orthophoto'],
        project_id=project_id,
        name=name,
        descr='Orthophoto was generated for project with id: %s' % project_id
    )


def stringify_args(args: Dict[str, Any]) -> List[str]:
    """Stringify arguments back to command line."""
    arr = []

    for key, val in args.items():
        arg = '--' + key.replace('_', '-')

        if val is None or val == '':
            continue

        if isinstance(val, bool):
            if val:
                arr.append(arg)
        else:
            arr.append(arg)
            arr.append(str(val))

    return arr


def start(args: Dict) -> None:
    """Run orthophoto creation."""
    try:
        if not os.path.isdir(WORK_VOLUME):
            os.mkdir(WORK_VOLUME)

        downloaded_filename = os.path.join(WORK_VOLUME, 'images.zip')
        extracted_dirname = os.path.join('.', 'images')

        download(args['content_item_id'], downloaded_filename)
        unzip(downloaded_filename, extracted_dirname)

        image_props = get_image_properties(extracted_dirname)
        image_max_side_size = max(image_props['width'], image_props['height'])

        odm_args = to_odm_args(args, image_max_side_size=image_max_side_size)

        returncode = subprocess.call(['python', '/code/run.py', *stringify_args(odm_args)],
                                     # stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

        if returncode != 0:
            raise Exception('Called ODM and received return code: %s' % str(returncode))

        results = upload_results(args['project_id'])

        print('Successfully uploaded')
        print(results)

    except Its4landException as err:
        print(err.error)
        print(err.content)

        traceback.print_exc()
        exit(2)
    except Exception as err:
        # TODO better error handling
        print('Oopsie!')
        print(err)
        traceback.print_exc()
        exit(1)


def parse_args():
    """Parse command line argument."""
    parser = argparse.ArgumentParser(
        description='Create an orthophotos using OpenDroneMap',
        epilog='This tool is part of the Publish and Share platform'
    )

    '''Initialize arguments'''
    parser.add_argument('--resize-to', type=str, default='full',
                        choices=('full', 'half', 'quarter', 'eighth'),
                        help='resizes images by the largest side for opensfm.'
                             'Set to `full` to disable. Default: full')
    parser.add_argument('--opensfm-depthmap-method', type=str,
                        choices=(
                            'BRUTE_FORCE',
                            'PATCH_MATCH',
                            'PATCH_MATCH_SAMPLE'
                        ),
                        help='Raw depthmap computation algorithm. PATCH_MATCH '
                             'and PATCH_MATCH_SAMPLE are faster, but might '
                             'miss some valid points. BRUTE_FORCE takes '
                             'longer but produces denser reconstructions. '
                             'Default: PATCH_MATCH')
    parser.add_argument('--opensfm-depthmap-min-consistent-views', type=int,
                        default=3, choices=(3, 6),
                        help='Minimum number of views that should reconstruct '
                             'a point for it to be valid. Use lower values if '
                             'your images have less overlap. Lower values '
                             'result in denser point clouds but with more '
                             'noise. Default: 3')
    parser.add_argument('--texturing-nadir-weight',  type=str, required=True,
                        choices=('urban', 'rural'),
                        help='Affects orthophotos only.')
    parser.add_argument('--georeferencing', type=str, default='EXIF',
                        choices=('GCP', 'EXIF'),
                        help='Mode of georeferencing: either GCP, or EXIF.')
    parser.add_argument('--pc-las', action='store_true',
                        help='Export the georeferenced point cloud in LAS '
                             'format. Default: False')
    parser.add_argument('--dsm', action='store_true',
                        help='Use this tag to build a DSM (Digital Surface '
                             'Model, ground + objects) using a progressive '
                             'morphological filter. Default: False')
    parser.add_argument('--dem-resolution', type=float,
                        metavar='<float > 0.0>', default=5,
                        help='DSM/DTM resolution in cm / pixel. Default: 5')
    parser.add_argument('--orthophoto-resolution', type=float,
                        metavar='<float > 0.0>', default=5,
                        help='Orthophoto resolution in cm / pixel. Default: 5')
    parser.add_argument('--min-num-features', type=int, default=10000,
                        help='Minimum number of features to extract per '
                             'image. More features leads to better results '
                             'but slower execution. Default: 10000')
    parser.add_argument('--content-item-id', type=str, required=True,
                        help='spatial-source storing the .zip file with all'
                             'the flight images.')
    parser.add_argument('--project-id', type=str, required=True,
                        help='Project id.')

    args = parser.parse_args()

    return vars(args)


if __name__ == '__main__':
    args = parse_args()

    start(args)
