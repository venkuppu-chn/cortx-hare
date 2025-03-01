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

import ctypes as c
from enum import Enum, IntEnum
from threading import Thread
from typing import List, NamedTuple, Set


class FidStruct(c.Structure):
    _fields_ = [("f_container", c.c_uint64), ("f_key", c.c_uint64)]


class Uint128Struct(c.Structure):
    _fields_ = [("hi", c.c_uint64), ("lo", c.c_uint64)]


ObjT = Enum(
    'ObjT',
    [
        # These are the only conf object types we care about.
        ('PROCESS', 0x7200000000000001),
        ('SERVICE', 0x7300000000000001),
        ('SDEV', 0x6400000000000001),
        ('DRIVE', 0x6b00000000000001),
        ('PROFILE', 0x7000000000000001),
        ('OBJV', 0x6a00000000000001),
        ('NODE', 0x6e00000000000001),
        ('SITE', 0x5300000000000001),
        ('RACK', 0x6100000000000001),
        ('ENCLOSURE', 0x6500000000000001),
        ('CONTROLLER', 0x6300000000000001),
        ('ROOT', 0x7400000000000001),
        ('POOL', 0x6f00000000000001),
        ('PVER', 0x7600000000000001),
        ('FDMI_FILTER', 0x6c00000000000001),
        ('FDMI_FLT_GRP', 0x6700000000000001),
    ])
ObjT.__doc__ = 'Motr conf object types and their m0_fid.f_container values'


class HaNoteStruct(c.Structure):
    # Constants for no_state field values as they are described in ha/note.h

    # /** Object state is unknown. */
    M0_NC_UNKNOWN = 0
    # /** Object can be used normally. */
    M0_NC_ONLINE = 1
    # /**
    # * Object has experienced a permanent failure and cannot be
    # * recovered.
    # */
    M0_NC_FAILED = 2
    # /**
    # * Object is experiencing a temporary failure. Halon will notify Motr
    # * when the object is available for use again.
    # */
    M0_NC_TRANSIENT = 3
    # /**
    # * This state is only applicable to the pool objects. In this state,
    # * the pool is undergoing repair, i.e., the process of reconstructing
    # * data lost due to a failure and storing them in spare space.
    # */
    M0_NC_REPAIR = 4
    # /**
    # * This state is only applicable to the pool objects. In this state,
    # * the pool device has completed sns repair. Its data is re-constructed
    # * on its corresponding spare space.
    # */
    M0_NC_REPAIRED = 5
    # /**
    # * This state is only applicable to the pool objects. Rebalance process
    # * is complementary to repair: previously reconstructed data is being
    # * copied from spare space to the replacement storage.
    # */
    M0_NC_REBALANCE = 6

    M0_NC_NR = 7

    _fields_ = [("no_id", FidStruct), ("no_state", c.c_uint32)]


# Mostly duplicates motr/conf/ha.h:m0_conf_ha_process
class ConfHaProcess:
    def __init__(self, chp_event=0, chp_type=0, chp_pid=0, fid=None):
        self.chp_event = chp_event
        self.chp_type = chp_type
        self.chp_pid = chp_pid
        self.fid = fid


# Duplicates motr/fid/fid.h
class Fid:
    def __init__(self, container: int, key: int):
        self.container = container
        self.key = key

    @staticmethod
    def parse(val: str) -> 'Fid':
        cont, key = tuple(int(s, 16) for s in val.split(':', 1))
        return Fid(cont, key)

    @staticmethod
    def from_struct(val: FidStruct):
        return Fid(val.f_container, val.f_key)

    def to_c(self) -> FidStruct:
        return FidStruct(self.container, self.key)

    def get_copy(self) -> 'Fid':
        return Fid(self.container, self.key)

    def is_null(self) -> bool:
        return self.container == 0 and self.key == 0

    def __repr__(self):
        return f'0x{self.container:x}:0x{self.key:x}'

    def __eq__(self, other):
        return type(other) is Fid and \
            other.container == self.container and other.key == self.key

    def for_json(self):
        return self.__repr__()


class Uint128:
    def __init__(self, hi, lo):
        self.hi = hi
        self.lo = lo

    def __repr__(self):
        return f'{self.hi:#x}:{self.lo:#x}'

    def to_c(self):
        return Uint128Struct(self.hi, self.lo)


# struct m0_fs_stats
FsStats = NamedTuple('FsStats', [('fs_free_seg', int), ('fs_total_seg', int),
                                 ('fs_free_disk', int), ('fs_avail_disk', int),
                                 ('fs_total_disk', int), ('fs_svc_total', int),
                                 ('fs_svc_replied', int)])

FsStatsWithTime = NamedTuple('FsStatsWithTime', [('stats', FsStats),
                                                 ('timestamp', float),
                                                 ('date', str)])


# enum m0_cm_status
class SnsCmStatus(Enum):
    CM_STATUS_INVALID = 0
    CM_STATUS_IDLE = 1
    CM_STATUS_STARTED = 2
    CM_STATUS_FAILED = 3
    CM_STATUS_PAUSED = 4


# struct m0_spiel_repreb_status
ReprebStatus = NamedTuple('ReprebStatus', [('fid', Fid),
                                           ('state', SnsCmStatus),
                                           ('progress', int)])

HaNote = NamedTuple('HaNote', [('obj_t', str), ('note', HaNoteStruct)])

# struct m0_stob_id
StobId = NamedTuple('StobId', [('domain_fid', Fid), ('fid', Fid)])

# SnsRepairStatusItem = NamedTuple('SnsRepairStatusItem', [('fid', Fid),
#                                                          ('status', str),
#                                                          ('progress', int)])


class StoppableThread(Thread):
    def stop(self) -> None:
        pass


class MessageId(NamedTuple):
    halink_ctx: int
    tag: int

    def __repr__(self):
        return f'MessageId(0x{self.halink_ctx:x}, {self.tag})'


class HaLinkMessagePromise:
    def __init__(self, message_ids: List[MessageId]):
        self._ids: Set[MessageId] = set(message_ids)

    def exclude_ids(self, ids: List[MessageId]) -> None:
        for message_id in ids:
            self._ids.discard(message_id)

    def is_empty(self) -> bool:
        return not self._ids

    def __contains__(self, message_id: MessageId) -> bool:
        return message_id in self._ids

    def __repr__(self):
        return 'HaLinkMessagePromise' + str(self._ids)


class ObjHealth(Enum):
    FAILED = (0, HaNoteStruct.M0_NC_FAILED)
    OK = (1, HaNoteStruct.M0_NC_ONLINE)
    UNKNOWN = (2, HaNoteStruct.M0_NC_UNKNOWN)
    OFFLINE = (3, HaNoteStruct.M0_NC_TRANSIENT)
    STOPPED = (4, HaNoteStruct.M0_NC_TRANSIENT)
    REPAIR = (5, HaNoteStruct.M0_NC_REPAIR)
    REPAIRED = (6, HaNoteStruct.M0_NC_REPAIRED)
    REBALANCE = (7, HaNoteStruct.M0_NC_REBALANCE)

    def __repr__(self):
        """Return human-readable constant name (useful in log output)."""
        return self.name

    @staticmethod
    def from_ha_note_state(state: int) -> 'ObjHealth':
        """
        Converts the int constant from HaNoteStruct into the corresponding
        ObjHealth.
        """
        for i in list(ObjHealth):
            (_, note) = i.value
            if note == state:
                return i
        return ObjHealth.UNKNOWN

    def to_ha_note_status(self) -> int:
        """
        Converts the given ObjHealth to the most suitable HaNoteStruct
        status.
        """
        ha_note: int = self.value[1]
        return ha_note


HAState = NamedTuple('HAState', [('fid', Fid), ('status', ObjHealth)])


class m0HaProcessEvent(IntEnum):
    M0_CONF_HA_PROCESS_STARTING = 0
    M0_CONF_HA_PROCESS_STARTED = 1
    M0_CONF_HA_PROCESS_STOPPING = 2
    M0_CONF_HA_PROCESS_STOPPED = 3

    @staticmethod
    def str_to_Enum(evt: str):
        events = {'M0_CONF_HA_PROCESS_STARTING':
                  m0HaProcessEvent.M0_CONF_HA_PROCESS_STARTING,
                  'M0_CONF_HA_PROCESS_STARTED':
                  m0HaProcessEvent.M0_CONF_HA_PROCESS_STARTED,
                  'M0_CONF_HA_PROCESS_STOPPING':
                  m0HaProcessEvent.M0_CONF_HA_PROCESS_STOPPING,
                  'M0_CONF_HA_PROCESS_STOPPED':
                  m0HaProcessEvent.M0_CONF_HA_PROCESS_STOPPED}
        return events[evt]

    def __repr__(self):
        return self.name

    def event_to_svchealth(self):
        m0ProcessEvToSvcHealth = {
            m0HaProcessEvent.M0_CONF_HA_PROCESS_STARTING: ObjHealth.OK,
            m0HaProcessEvent.M0_CONF_HA_PROCESS_STARTED: ObjHealth.OK,
            m0HaProcessEvent.M0_CONF_HA_PROCESS_STOPPING: ObjHealth.FAILED,
            m0HaProcessEvent.M0_CONF_HA_PROCESS_STOPPED: ObjHealth.FAILED}
        return m0ProcessEvToSvcHealth[self]


class m0HaProcessType(IntEnum):
    M0_CONF_HA_PROCESS_OTHER = 0
    M0_CONF_HA_PROCESS_KERNEL = 1
    M0_CONF_HA_PROCESS_M0MKFS = 2
    M0_CONF_HA_PROCESS_M0D = 3

    @staticmethod
    def str_to_Enum(t: str):
        types = {'M0_CONF_HA_PROCESS_OTHER':
                 m0HaProcessType.M0_CONF_HA_PROCESS_OTHER,
                 'M0_CONF_HA_PROCESS_KERNEL':
                 m0HaProcessType.M0_CONF_HA_PROCESS_KERNEL,
                 'M0_CONF_HA_PROCESS_M0MKFS':
                 m0HaProcessType.M0_CONF_HA_PROCESS_M0MKFS,
                 'M0_CONF_HA_PROCESS_M0D':
                 m0HaProcessType.M0_CONF_HA_PROCESS_M0D}
        return types[t]

    def __repr__(self):
        return self.name


class m0HaObjState(IntEnum):
    M0_NC_UNKNOWN = HaNoteStruct.M0_NC_UNKNOWN
    M0_NC_ONLINE = HaNoteStruct.M0_NC_ONLINE
    M0_NC_FAILED = HaNoteStruct.M0_NC_FAILED
    M0_NC_TRANSIENT = HaNoteStruct.M0_NC_TRANSIENT
    M0_NC_REPAIRED = HaNoteStruct.M0_NC_REPAIRED
    M0_NC_REBALANCE = HaNoteStruct.M0_NC_REBALANCE
    M0_NC_NR = HaNoteStruct.M0_NC_NR

    def __repr__(self):
        return self.name

    @staticmethod
    def parse(state: str) -> 'm0HaObjState':

        states = {
            'M0_NC_UNKNOWN': m0HaObjState.M0_NC_UNKNOWN,
            'M0_NC_ONLINE': m0HaObjState.M0_NC_ONLINE,
            'M0_NC_FAILED': m0HaObjState.M0_NC_FAILED,
            'M0_NC_TRANSIENT': m0HaObjState.M0_NC_TRANSIENT,
            'M0_NC_REPAIRED': m0HaObjState.M0_NC_REPAIRED,
            'M0_NC_REBALANCE': m0HaObjState.M0_NC_REBALANCE,
            'M0_NC_NR': m0HaObjState.M0_NC_NR
        }
        return states[state]


class Profile(NamedTuple):
    fid: Fid
    name: str
    pool_names: List[str]


KeyDelete = NamedTuple('KeyDelete', [('name', str), ('recurse', bool)])
