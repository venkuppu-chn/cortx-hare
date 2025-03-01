# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

import json
import os
import re
import tempfile
from typing import Dict, List

import pkg_resources
import pytest
from hare_mp.cdf import CdfGenerator
from hare_mp.store import ConfStoreProvider, ValueProvider
from hax.util import KVAdapter


def substitute(content: str, replacement: Dict[str, str]) -> str:
    for k, new_value in replacement.items():
        content = re.sub(f'"{k}"',
                         f'"{new_value}"',
                         content,
                         flags=re.MULTILINE)
    return content


def template_files() -> List[str]:
    regex = r'^.*\.tmpl\.[^.]+$'
    paths: List[str] = pkg_resources.resource_listdir('hare_mp', 'templates')
    return [p for p in paths if re.match(regex, p)]


def read_template(filename: str) -> str:
    resource_path = f'templates/{filename}'
    raw_content: bytes = pkg_resources.resource_string('hare_mp',
                                                       resource_path)
    return raw_content.decode('utf-8')


def is_content_ok(content: str, mocker, kv_adapter) -> bool:
    if len(content) < 4:
        # Some templates represent empty JSONs and should be skipped
        return True
    _, path = tempfile.mkstemp()
    try:
        with open(path, 'w') as f:
            f.write(content)

        store = ConfStoreProvider(f'json://{path}')
        mocker.patch.object(store, 'get_machine_id', return_value='machine-id')
        mocker.patch.object(store, 'get_machine_ids_for_service', return_value=['machine-id'])
        motr_store = ValueProvider()
        mocker.patch.object(motr_store, '_raw_get', return_value='/dev/dummy')
        #
        # the method will raise an exception if either
        # Dhall is unhappy or some values are not found in ConfStore
        generator = CdfGenerator(provider=store)
        generator.utils.kv = kv_adapter
        generator.generate()
        return True

    finally:
        if os.path.isfile(path):
            os.unlink(path)


@pytest.fixture
def placeholders() -> Dict[str, str]:
    return {
        'TMPL_CLUSTER_ID': 'stub_cluster_id',
        'TMPL_CVG_COUNT': '1',
        'TMPL_DATA_DEVICE_1': '/dev/sdb',
        'TMPL_DATA_DEVICE_2': '/dev/sdc',
        'TMPL_DATA_DEVICE_11': '/dev/sdb',
        'TMPL_DATA_DEVICE_12': '/dev/sdc',
        'TMPL_DATA_DEVICE_21': '/dev/sdb',
        'TMPL_DATA_DEVICE_22': '/dev/sdc',
        'TMPL_DATA_INTERFACE_TYPE': 'tcp',
        'TMPL_DATA_UNITS_COUNT': '1',
        'TMPL_HOSTNAME': 'hostname',
        'TMPL_NODE_TYPE': 'storage_node',
        'TMPL_MACHINE_ID': 'machine-id',
        'TMPL_MACHINE_ID_1': 'machine-id',
        'TMPL_METADATA_DEVICE': '/dev/meta',
        'TMPL_PARITY_UNITS_COUNT': '0',
        'TMPL_POOL_TYPE': 'dix',
        'TMPL_PRIVATE_DATA_INTERFACE_1': 'tcp',
        'TMPL_PRIVATE_DATA_INTERFACE_2': 'tcp',
        'TMPL_S3SERVER_INSTANCES_COUNT': '4',
        'TMPL_SERVER_NODE_NAME': 'srvnode-1',
        'TMPL_SPARE_UNITS_COUNT': '0',
        'TMPL_STORAGESET_COUNT': '1',
        'TMPL_STORAGESET_NAME': 'storage-set',
        'TMPL_STORAGE_SET_ID': 'storage-set',
        'TMPL_PRIVATE_FQDN': 'my-node-1',
        'TMPL_PRIVATE_FQDN_1': 'my-node-1',
        'TMPL_PRIVATE_FQDN_2': 'my-node-2',
        'TMPL_PRIVATE_FQDN_3': 'my-node-3',
    }


def new_kv(key: str, val: str):
    return {
        'Key': key,
        'CreateIndex': 1793,
        'ModifyIndex': 1793,
        'LockIndex': 0,
        'Flags': 0,
        'Value': val,
        'Session': ''
    }


@pytest.fixture
def kv_adapter(mocker):
    kv = KVAdapter()
    exc = RuntimeError('Not allowed')

    def fake_get(key):
        if key in [f'my-node-{i}/facts' for i in [1, 2, 3]]:
            return new_kv(
                key, json.dumps({
                    'processorcount': 1,
                    'memorysize_mb': 1024.0
                }))
        if key in [
                f'my-node-{i}/dev/sd{x}' for i in [1, 2, 3]
                for x in ['b', 'c']
        ]:
            return new_kv(
                key,
                json.dumps({
                    'path': '/stub/',
                    'size': 102400,
                    'blksize': 8
                }))
        raise RuntimeError(f'Unexpected key = {key}')

    mock = mocker.patch.object
    mock(kv, 'kv_get', side_effect=fake_get)
    mock(kv, 'kv_put', side_effect=exc)
    mock(kv, 'kv_put_in_transaction', side_effect=exc)
    mock(kv, 'kv_delete_in_transaction', side_effect=exc)
    return kv


@pytest.mark.parametrize('tmpl_file', template_files())
def test_template_compiles(tmpl_file, placeholders, mocker, kv_adapter):
    content = read_template(tmpl_file)
    content = substitute(content, placeholders)

    assert is_content_ok(content, mocker, kv_adapter)


def test_template_files_found():
    assert len(template_files()) > 0
