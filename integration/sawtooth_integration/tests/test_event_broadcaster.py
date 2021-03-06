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

import time
import unittest
import logging
import json
import urllib.request
import urllib.error
import base64
import sys

from sawtooth_intkey.intkey_message_factory import IntkeyMessageFactory
from sawtooth_sdk.messaging.stream import Stream

from sawtooth_validator.protobuf import events_pb2
from sawtooth_validator.protobuf import validator_pb2

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class TestEventBroadcaster(unittest.TestCase):
    def test_subscribe_and_unsubscribe(self):
        """Tests that a client can subscribe and unsubscribe from events."""
        response = self._subscribe()
        self.assert_subscribe_response(response)

        response = self._unsubscribe()
        self.assert_unsubscribe_response(response)

    def test_block_commit_event_received(self):
        """Tests that block commit events are properly received on block
        boundaries."""
        self._subscribe()

        for i in range(1, 5):
            self.batch_submitter.submit_next_batch()
            msg = self.stream.receive().result()
            self.assertEqual(
                msg.message_type,
                validator_pb2.Message.CLIENT_EVENTS)
            event_list = events_pb2.EventList()
            event_list.ParseFromString(msg.content)
            events = event_list.events
            self.assertEqual(len(events), 1)
            self.assert_block_commit_event(events[0], i)

    @classmethod
    def setUpClass(cls):
        cls.batch_submitter = BatchSubmitter()

    def setUp(self):
        self.url = "tcp://validator:4004"
        self.stream = Stream(self.url)

    def tearDown(self):
        if self.stream is not None:
            self.stream.close()

    def _subscribe(self, subscriptions=None):
        if subscriptions is None:
            subscriptions = [
                events_pb2.EventSubscription(event_type="block_commit"),
            ]
        request = events_pb2.ClientEventsSubscribeRequest(
            subscriptions=subscriptions)
        response = self.stream.send(
            validator_pb2.Message.CLIENT_EVENTS_SUBSCRIBE_REQUEST,
            request.SerializeToString()).result()
        return response

    def _unsubscribe(self):
        request = events_pb2.ClientEventsUnsubscribeRequest()
        response = self.stream.send(
            validator_pb2.Message.CLIENT_EVENTS_UNSUBSCRIBE_REQUEST,
            request.SerializeToString()).result()
        return response

    def assert_block_commit_event(self, event, block_num):
        self.assertEqual(event.event_type, "block_commit")
        self.assertTrue(all([
            any(attribute.key == "block_id" for attribute in event.attributes),
            any(attribute.key == "block_num"
                for attribute in event.attributes),
            any(attribute.key == "previous_block_id"
                for attribute in event.attributes),
            any(attribute.key == "state_root_hash"
                for attribute in event.attributes),
        ]))
        for attribute in event.attributes:
            if attribute.key == "block_num":
                self.assertEqual(attribute.value, str(block_num))


    def assert_subscribe_response(self, msg):
        self.assertEqual(
            msg.message_type,
            validator_pb2.Message.CLIENT_EVENTS_SUBSCRIBE_RESPONSE)

        subscription_response = events_pb2.ClientEventsSubscribeResponse()
        subscription_response.ParseFromString(msg.content)

        self.assertEqual(
            subscription_response.status,
            events_pb2.ClientEventsSubscribeResponse.OK)

    def assert_unsubscribe_response(self, msg):
        self.assertEqual(
            msg.message_type,
            validator_pb2.Message.CLIENT_EVENTS_UNSUBSCRIBE_RESPONSE)

        subscription_response = events_pb2.ClientEventsUnsubscribeResponse()
        subscription_response.ParseFromString(msg.content)

        self.assertEqual(
            subscription_response.status,
            events_pb2.ClientEventsUnsubscribeResponse.OK)

class BatchSubmitter:
    def __init__(self):
        self.n = 0
        self.imf = IntkeyMessageFactory()

    def _post_batch(self, batch):
        headers = {'Content-Type': 'application/octet-stream'}
        response = self._query_rest_api('/batches', data=batch, headers=headers)
        return response

    def _query_rest_api(self, suffix='', data=None, headers={}):
        url = 'http://rest-api:8080' + suffix
        request = urllib.request.Request(url, data, headers)
        response = urllib.request.urlopen(request).read().decode('utf-8')
        return json.loads(response)

    def make_batch(self, n):
        return self.imf.create_batch([('set', str(n), 0)])

    def submit_next_batch(self):
        batch = self.make_batch(self.n)
        self.n += 1
        self._post_batch(batch)
        time.sleep(0.5)
