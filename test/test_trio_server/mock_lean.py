"""
This makes it possible to have tests for the Lean Python server
interface which do not depend on having Lean installed in a certain manner.

Instead one can build a "lean script" which is run by a fake lean server.
"""

import trio  # type: ignore
from typing import List, Dict
import json
from collections import deque
from dataclasses import dataclass
import trio.testing

from lean_client.trio_server import TrioLeanServer


class LeanScriptStep:
    pass


@dataclass
class LeanTakesTime(LeanScriptStep):
    """
    Simulate taking a while to start up or processes a request.
    """
    seconds: float


@dataclass
class LeanShouldGetRequest(LeanScriptStep):
    """
    Used to check that Lean gets the request it is looking for from Lean-Python interface.
    """
    message: Dict  # should be JSON encodable


@dataclass
class LeanSendsResponse(LeanScriptStep):
    """
    Simulate Lean's output behaviour
    """
    message: Dict  # should be JSON encodable


@dataclass
class LeanSendsBytes(LeanScriptStep):
    """
    Simulate Lean's output behaviour at the byte level.
    Doesn't include new line characters unless passed in.
    """
    message_bytes: bytes


@dataclass
class LeanShouldNotGetRequest(LeanScriptStep):
    """
    Check that Lean has not received any requests (perhaps sent prematurely).
    """
    pass



class MockLeanServerProcess(trio.Process):

    def __init__(self, script: List[LeanScriptStep]):
        self.stdin = trio.testing.MemorySendStream()      # a stream for mock lean to read from
        self.stdout = trio.testing.MemoryReceiveStream()  # a stream for mock lean to write to
        self.messages: deque[Dict] = deque()
        self.partial_message: bytes = b""
        self.script: List[LeanScriptStep] = script

    def kill(self):
        pass

    @staticmethod
    def parse_message(b: bytes) -> Dict:
        return json.loads(b.decode())

    @staticmethod
    def messages_are_equal(m1: Dict, m2: Dict):
        s1 = json.dumps(m1, sort_keys=True)
        s2 = json.dumps(m2, sort_keys=True)
        return s1 == s2

    def collect_stdin_messages(self):
        data = self.partial_message + self.stdin.get_data_nowait()
        if data:
            raw_messages = data.split(b"\n")
            self.partial_message = raw_messages.pop()
            self.messages.extend(self.parse_message(m) for m in raw_messages)

    async def assert_message_is_received(self, message_expected):
        await trio.sleep(0.01)
        self.collect_stdin_messages()

        assert self.messages, f"Mock Lean was expecting\n{message_expected}\nbut no messages were received."

        message_received = self.messages.pop()
        assert self.messages_are_equal(message_expected, message_received), \
            f"Mock Lean was expecting\n{message_expected}\nbut received\n{message_received}"

    async def assert_no_messages_received(self):
        await trio.sleep(0.01)
        self.collect_stdin_messages()

        assert not self.messages, f"Mock Lean was not expecting as message, but \n{self.messages[0]}\nwas received."

    def send_bytes(self, message_bytes: bytes):
        self.stdout.put_data(message_bytes)

    def send_message(self, message):
        message_bytes = json.dumps(message).encode() + b"\n"
        self.stdout.put_data(message_bytes)

    async def follow_script(self):
        for step in self.script:
            if isinstance(step, LeanTakesTime):
                print(f"\nLean is taking {step.seconds} seconds before doing anything.")
                await trio.sleep(step.seconds)
            elif isinstance(step, LeanShouldGetRequest):
                print(f"\nLean should receive the following request:\n{step.message}")
                await self.assert_message_is_received(step.message)
            elif isinstance(step, LeanSendsResponse):
                print(f"\nLean sends the following response:\n{step.message}")
                self.send_message(step.message)
            elif isinstance(step, LeanSendsBytes):
                print(f"\nLean sends the following bytes:\n{step.message_bytes}")
                self.send_bytes(step.message_bytes)
            elif isinstance(step, LeanShouldNotGetRequest):
                print(f"\nLean should receive have any requests yet.")
                await self.assert_no_messages_received()


async def start_with_mock_lean(lean_server: TrioLeanServer, script: List[LeanScriptStep]):
    """
    Call this in place of TrioLeanServer.start().  It will run a mock Lean server following the script,
    in place of the real Lean server.
    """

    # start up the mock lean process
    mock_lean_process = MockLeanServerProcess(script)
    lean_server.nursery.start_soon(mock_lean_process.follow_script)

    # attach to the lean interface
    lean_server.process = mock_lean_process

    # perform the remainder of the start up processes as normal
    lean_server.nursery.start_soon(lean_server.receiver)
