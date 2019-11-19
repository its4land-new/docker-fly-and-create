"""Orthophoto tool ODM"""

from typing import (Dict, List, Any)
import os
import shutil
import argparse
import zipfile
import traceback
import subprocess
import time
import tempfile
import json
import pathlib

import imageio

try:
    from .Its4landAPI import Its4landAPI, Its4landException
except:
    from Its4landAPI import Its4landAPI, Its4landException


def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))

# sample call:
# python3 orthophoto.py --texturing-nadir-weight urban --spatial-source-id 487c67f5-7820-4d1b-bc0b-274c59157053 --project-id 8d7e9cf1-1a4d-4366-992d-7ae49370978a

PROJECT_PATH = '/datasets'
WORK_VOLUME = os.path.join(PROJECT_PATH, 'code')
# WORK_VOLUME = './0_0_1/dataset'
PLATFORM_URL = 'https://platform.its4land.com/api/'
PLATFORM_API_KEY = '1'

if 'I4L_PUBLICAPIURL' in os.environ:
    PLATFORM_URL = os.environ['I4L_PUBLICAPIURL']


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
    defaults = args.copy()
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

    defaults['resize_to'] = resize_to[defaults['resize_to']]
    defaults['texturing_nadir_weight'] = texturing_nadir_weight[defaults['texturing_nadir_weight']]

    defaults['opensfm_depthmap_method'] = defaults['opensfm_depthmap_method']
    defaults['opensfm_depthmap_min_consistent_views'] = defaults['opensfm_depthmap_min_consistent_views']
    defaults['pc_las'] = defaults['pc_las']
    defaults['dsm'] = defaults['dsm']
    defaults['dem_resolution'] = defaults['dem_resolution']
    defaults['orthophoto_resolution'] = defaults['orthophoto_resolution']
    defaults['min_num_features'] = defaults['min_num_features']
    defaults['project_path'] = PROJECT_PATH

    if defaults['georeferencing'] == 'EXIF':
        defaults['use_exif'] = True
    elif defaults['georeferencing'] == 'GCP':
        defaults['use_exif'] = False

    del defaults['georeferencing']
    del defaults['spatial_source_id']
    del defaults['project_id']
    del defaults['zip']

    return defaults


def get_orthophoto_name(name: str, metadata: Dict[str, Any]):
    current_time = str(int(time.time()))
    flight_date = metadata['Date of flight'][0]
    return '{}_{}_{}_{}'.format(name[:25], flight_date, 'orthophoto', current_time)


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
        pathlib.Path(WORK_VOLUME).mkdir(parents=True, exist_ok=True)

        api = Its4landAPI(url=PLATFORM_URL, api_key=PLATFORM_API_KEY)
        api.session_token = '1'

        project_id = os.environ['I4L_PROJECTUID'] if 'I4L_PROJECTUID' in os.environ else args['project_id']

        assert project_id is not None, 'Missing project id'

        print('Downloading ...'.format())

        spatial_source = api.get_spatial_source(args['spatial_source_id'])
        metadata = None
        metadata_id = None
        gcp_filename = None

        assert spatial_source['Type'] == 'UAVimagery', 'Expected the spatial source type to be "UAVimagery"'

        for doc in api.get_additional_documents(args['spatial_source_id']):
            if doc['Type'] == 'Metadata':
                assert metadata_id is None, 'Metadata has already been defined, aborting...'
                tmp = tempfile.NamedTemporaryFile(mode='w+', encoding='utf8')
                api.download_content_item(doc['ContentItem'], tmp.name)

                metadata_id = doc['ContentItem']

                metadata = json.load(tmp)
            elif doc['Type'] == 'GCP List':
                assert metadata_id is None, 'GCP list have already been defined, aborting...'
                gcp_filename = os.path.join(WORK_VOLUME, 'gcp_list.txt')
                api.download_content_item(doc['ContentItem'], gcp_filename)

            print(doc)

        assert metadata_id is not None, 'Metadata is not defined, aborting...'
        assert isinstance(metadata, dict), 'Metadata is not a dictionary, aborting...'

        if args['georeferencing'] == 'GCP':
            args['gcp'] = gcp_filename

            assert gcp_filename is not None, 'GCP file is missing'

        downloaded_filename = os.path.join(WORK_VOLUME, 'images.zip')
        extracted_dirname = os.path.join(WORK_VOLUME, 'images')

        if args['zip']:
            print('using local zip')
            shutil.copyfile(args['zip'], downloaded_filename)
        else:
            print('downloading zip')
            api.download_content_item(spatial_source['ContentItem'], downloaded_filename)

        unzip(downloaded_filename, extracted_dirname)

        list_files(WORK_VOLUME)

        print('Dir contents:', os.listdir(extracted_dirname))

        image_props = get_image_properties(extracted_dirname)
        image_max_side_size = max(image_props['width'], image_props['height'])

        odm_args = to_odm_args(args, image_max_side_size=image_max_side_size)

        print('Arguments are {}'.format(odm_args))
        print('Processing ...'.format())

        returncode = subprocess.call(['python', '/code/run.py', *stringify_args(odm_args)],
                                    #  stdout=subprocess.PIPE,
                                    #  stderr=subprocess.PIPE
                                    )

        if returncode != 0:
            raise Exception('Called ODM and received return code: %s' % str(returncode))

        orthophoto_filename = os.path.join(WORK_VOLUME, 'odm_orthophoto', 'odm_orthophoto.tif')
        name = get_orthophoto_name(spatial_source['Name'], metadata)
        print('Uploading orthophoto "{}" ...'.format(name))

        content_item = api.upload_content_item(orthophoto_filename)
        content_item_id = content_item['ContentID']

        print('Creating orthophoto spatial source with ContentItemId {} ...'.format(
            content_item_id))

        spatial_source = api.post_spatial_source(
            project_id=project_id,
            content_item_id=content_item_id,
            tags=[],
            descr='{}'.format(name),
            name=name,
            type='Orthomosaic'
        )
        
        spatial_source_id = spatial_source['UID']

        print('Adding metadata as additional document to SpatialSourceId {} ...'.format(
            spatial_source_id))

        api.post_additional_document(
            spatial_source_id, metadata_id, type='Metadata', descr='Flight metadata')

        print('Generating DDILayer "{}" ...'.format(name))

        api.post_ddi_layer(
            project_id=project_id,
            content_item_id=content_item_id,
            tags=['orthophoto'],
            name=name,
            descr=''
        )

        if args['dsm']:
            dsm_filename = os.path.join(
                WORK_VOLUME, 'odm_dem', 'dsm.tif')

            print('Uploading DSM...')

            dsm_content_item = api.upload_content_item(dsm_filename)
            dsm_content_item_id = dsm_content_item['ContentID']

            api.post_additional_document(
                spatial_source_id, dsm_content_item_id, type='DSM', descr='DSM')

        if args['pc_las']:
            point_cloud_filename = os.path.join(
                WORK_VOLUME, 'odm_georeferencing', 'odm_georeferenced_model.laz')

            print('Uploading LAZ point cloud...')

            point_cloud = api.upload_content_item(point_cloud_filename)
            point_cloud_id = point_cloud['ContentID']

            api.post_additional_document(
                spatial_source_id, point_cloud_id, type='PointCloud', descr='Point Cloud in LAZ format')

        print('Successfully uploaded! Finished!')

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
    parser.add_argument('--min-num-features', type=int, default=8000,
                        help='Minimum number of features to extract per '
                             'image. More features leads to better results '
                             'but slower execution. Default: 8000')
    parser.add_argument('--spatial-source-id', type=str, required=True,
                        help='spatial-source storing the .zip file with all'
                             'the flight images.')
    parser.add_argument('--zip', type=str,
                        help='zipfile storing the data')
    parser.add_argument('--project-id', type=str,
                        help='Project id.')

    args = parser.parse_args()

    return vars(args)


if __name__ == '__main__':
    args = parse_args()

    start(args)
