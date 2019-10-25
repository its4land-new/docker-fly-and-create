"""API integration with its4land project.

Attributes:
    DEBUG (bool): is debug enabled (logs the whole communication)
    Payload (TYPE): the payload sent to server

Notes:
    begin                : 2019-04-14
    git sha              : $Format:%H$

    development          : 2019, Ivan Ivanov @ ITC, University of Twente
    email                : ivan.ivanov@suricactus.com
    copyright            : (C) 2019 by Ivan Ivanov

License:
    /***************************************************************************
     *                                                                         *
     *   This program is free software; you can redistribute it and/or modify  *
     *   it under the terms of the GNU General Public License as published by  *
     *   the Free Software Foundation; either version 2 of the License, or     *
     *   (at your option) any later version.                                   *
     *                                                                         *
    /***************************************************************************

"""

from typing import (Any, Optional, Dict, List)
from enum import Enum
from urllib.parse import (urljoin, quote)
import os

from requests import (request, exceptions)

DEBUG = False

if DEBUG:
    import logging

    # These two lines enable debugging at httplib level
    # (requests->urllib3->http.client). You will see the REQUEST, including
    # HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


class ResponseType(Enum):
    """Response type data class."""

    json = 1
    text = 2
    html = 3
    stream = 4


Payload = Dict[str, Any]


class Its4landException(Exception):
    """Custom exception."""

    def __init__(
        self,
        msg: str = None,
        error: Optional[exceptions.RequestException] = None,
        url: str = None,
        code: int = None,
        content: Any = None,
    ):
        self.msg = msg
        self.code = code
        self.url = url
        self.error = error
        self.count = 0
        self.content = content

        if error:
            if isinstance(error, Its4landException):
                self.msg = msg or error.msg
                self.code = code or error.code
                self.url = url or error.url
                self.count = error.count + 1
            elif isinstance(error, exceptions.RequestException):
                self.msg = msg or str(error)
            else:
                self.msg = msg or str(error)

                if 'response' in error:
                    self.code = error.response.code
                    self.url = error.response.url
                else:
                    self.code = code
                    self.url = url
        else:
            self.msg = msg
            self.code = code
            self.url = url

        super().__init__(self.msg)

class Its4landAPI:
    def __init__(self, url: str, api_key: str,
                 response_type: ResponseType = ResponseType.json):
        self.url = url + '/'
        self.api_key = api_key
        self.response_type = response_type
        self.session_token = ''

    def get(self, *argv, **kwargs):
        return self.request('GET', *argv, **kwargs)

    def post(self, *argv, **kwargs):
        return self.request('POST', *argv, **kwargs)

    def patch(self, *argv, **kwargs):
        return self.request('PATCH', *argv, **kwargs)

    def request(self,
                method: str,
                data: Optional[Payload],
                encode_as: str = 'form',
                response_type: ResponseType = None,
                files: Dict[str, Any] = None,
                headers: Dict[str, str] = dict(),
                auth_required: bool = True,
                url: str = None):
        url = url or self.url
        response_type = response_type or self.response_type

        assert not auth_required or self.session_token, 'No session token provided'

        try:
            headers['X-Api-Key'] = self.api_key

            if self.session_token:
                headers['X-Session-Token'] = self.session_token

            send_data = {
                'stream': (response_type == ResponseType.stream),
                'headers': headers,
            }

            if method == 'GET':
                send_data['params'] = data
            else:
                if encode_as == 'json':
                    send_data['json'] = data
                elif encode_as == 'form':
                    send_data['data'] = data
                else:
                    raise Exception(url, 998, 'Unknown encode type: %s' % encode_as)

            if files is not None and len(files):
                send_data['files'] = {}

                for k, v in files.items():
                    try:
                        send_data['files'][k] = open(v, 'rb')
                    except Exception as e:
                        raise Exception(url, 998, 'Unable to open file: %s' % v, e)

            print([method, url, send_data])
            resp = request(method, url, **send_data)

            if DEBUG:
                import curlify

                print(curlify.to_curl(resp.request))

            if resp is not None:
                if resp.ok and resp.content is not None:
                    if response_type == ResponseType.stream:
                        return resp
                    elif response_type == ResponseType.json:
                        return resp.json()
                    elif response_type == ResponseType.html:
                        return resp.content

                    assert False, 'Unrecognized response type'
                else:
                    content = ''

                    try:
                        content = resp.json()
                    except:
                        content = str(resp.content)

                    raise Its4landException(url=resp.url, code=resp.status_code, msg=resp.reason, content=content)
            else:
                raise Its4landException(url=url, msg='There is no response, something bad happened')
        except Its4landException as e:
            raise e
        except exceptions.RequestException as e:
            raise Its4landException(error=e)
        except Exception as e:
            raise Its4landException(url=url, error=e)

    def login(self, login: str, password: str) -> str:
        # self.session_token = self.post({
        #     'login': login,
        #     'password': password,
        # },
        # auth_required=False,
        # url=urljoin(self.url, 'login'))
        self.session_token = 'SESSION_TOKEN'
        return self.session_token

    def get_projects(self):
        return self.get(None, url=urljoin(self.url, 'projects'))

    def get_validation_sets(self, project_id: str):
        return self.get({
            'projects': project_id
        }, url=urljoin(self.url, 'WP5ValidationSets'))

    def get_boundary_strings(self, project_id: str):
        return self.get({
            'projects': project_id
        }, url=urljoin(self.url, 'boundaryfacestring'))

    def post_boundary_strings(self, geojson: str):
        url = urljoin(self.url, 'boundaryfacestring')

        return self.post(geojson, url=url, encode_as='json')

    def patch_boundary_strings(self, project_id: str, geojson: str):
        url = urljoin(self.url, 'boundaryfacestring/%s' % quote(project_id, safe=''))

        return self.patch(geojson, url=url, encode_as='json')

    def get_content_item(self, uid: str):
        return self.get({
            'uid': uid
        }, url=urljoin(self.url, 'contentitems'))


    def upload_content_item(self, file: Any) -> Dict:
        return self.post(
            None,
            url=urljoin(self.url, 'contentitems'),
            files={
                'newcontent': file,
            }
        )

    def get_spatial_source(
        self,
        spatial_source_id: str
    ):
        path = os.path.join('spatialsource', spatial_source_id)
        return self.get(None, url=urljoin(self.url, path))

    def post_spatial_source(
                            self,
                            project_id: str,
                            content_item_id: str,
                            tags: Optional[List[str]],
                            name: str,
                            descr: Optional[str],
                            type: str = 'File'
                            ):

        path = os.path.join('projects', project_id, 'SpatialSources')

        project = self.post({
            'Type': type,
            'Description': descr,
            'ContentItem': content_item_id,
            'Tags': tags,
            'Name': name,
        }, encode_as='json', url=urljoin(self.url, path))

        return self.get_spatial_source(project['features'][0]['properties']['SpatialSources'][-1]['UID'])

    def get_additional_documents(self, spatial_source_id):
        path = os.path.join(
            'spatialsource', spatial_source_id, 'AdditionalDocument')

        return self.get(None, url=urljoin(self.url, path))

    def post_additional_document(
        self,
        spatial_source_id: str,
        content_item_id: str,
        type: str = 'File',
        descr: str = '',
    ):
        path = os.path.join(
            'spatialsource', spatial_source_id, 'AdditionalDocument')

        return self.post({
            'Type': type,
            'Description': descr,
            'ContentItem': content_item_id,
        }, encode_as='json', url=urljoin(self.url, path))

    def post_ddi_layer(
        self,
        project_id: str,
        content_item_id: str,
        tags: Optional[List[str]],
        name: str,
        descr: Optional[str],
    ):
        path = os.path.join('DDIlayers')

        return self.post({
            'Name': name,
            'Description': descr,
            'LongDescription': "",
            "Service": "WMS",
            'Projects': [
                {
                    'UUID': project_id,
                },
            ],
            'ContentItems': [content_item_id],
            'Tags': tags,
        }, encode_as='json', url=urljoin(self.url, path))

    def download_content_item(self, uid: str, filename: str):
        url = urljoin(self.url, 'contentitems/%s' % quote(uid, safe=''))

        return self.download_file(None, url=url, filename=filename)

    def download_file(
                      self,
                      data: Optional[Payload],
                      filename: str,
                      **rest
    ) -> str:
        resp = self.get(data, response_type=ResponseType.stream, **rest)

        with open(filename, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=4096):
                if not chunk:  # filter out keep-alive new chunks
                    pass

                f.write(chunk)

        return filename