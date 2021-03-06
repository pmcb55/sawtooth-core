# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

from sawtooth_validator.server.events.extractor import EventExtractor
from sawtooth_validator.protobuf.events_pb2 import Event


class BlockEventExtractor(EventExtractor):
    def __init__(self, block):
        self._block = block

    def _make_event(self):
        block = self._block
        attributes = [
            Event.Attribute(key="block_id", value=block.identifier),
            Event.Attribute(key="block_num", value=str(block.block_num)),
            Event.Attribute(
                key="state_root_hash", value=block.state_root_hash),
            Event.Attribute(
                key="previous_block_id", value=block.previous_block_id)]
        return Event(event_type="block_commit", attributes=attributes)

    def extract(self, subscriptions):
        if subscriptions:
            for sub in subscriptions:
                if sub.event_type == "block_commit":
                    return [self._make_event()]
