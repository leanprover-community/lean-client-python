"""
This makes it possible to have tests for the Lean Python server
interface which do not depend on having Lean installed in a certain manner.

Instead one can build a "lean script" which is run by a fake lean server.
"""

import trio  # type: ignore
from typing import List, Dict, Deque, Awaitable
import json
from collections import deque
from dataclasses import dataclass
import trio.testing # type: ignore

from lean_client.commands import Request
from lean_client.trio_server import TrioLeanServer


class LeanScriptStep:
    pass


@dataclass
class LeanTakesTime(LeanScriptStep):
    """
    Simulate taking a while to start up or processes a request.
    """
    seconds: float

    async def run(self, server: 'MockLeanServerProcess') -> Awaitable[None]:
        print(f"\nLean is taking {self.seconds} seconds before doing anything.")
        return await trio.sleep(self.seconds)


@dataclass
class LeanShouldGetRequestJSON(LeanScriptStep):
    """
    Used to check that Lean gets the request it is looking for from Lean-Python interface.
    This version is very specific.  It tests that the JSON produced by the Lean-Python interface is
    as expected.
    """
    message: Dict  # should be JSON encodable
    wait_time_seconds: float = 0.1

    async def run(self, server: 'MockLeanServerProcess') -> Awaitable[None]:
        print(f"\nLean should receive the following request:\n{self.message}")
        return await server.assert_message_is_received(self.message, self.wait_time_seconds)


@dataclass
class LeanShouldGetRequest(LeanScriptStep):
    """
    Used to check that Lean gets the request it is looking for from Lean-Python interface.
    This version is less specific.  It checks that the request is of the correct type and
    has the desired fields.
    """
    request: Request
    seq_num: int
    wait_time_seconds: float = 0.1

    async def run(self, server: 'MockLeanServerProcess') -> Awaitable[None]:
        self.request.seq_num = self.seq_num
        message = json.loads(self.request.to_json())
        print(f"\nLean should receive the following request:\n{message}")
        return await server.assert_message_is_received(message, self.wait_time_seconds)


@dataclass
class LeanSendsResponse(LeanScriptStep):
    """
    Simulate Lean's output behaviour
    """
    message: Dict  # should be JSON encodable

    async def run(self, server: 'MockLeanServerProcess') -> None:
        print(f"\nLean sends the following response:\n{self.message}")
        server.send_message(self.message)


@dataclass
class LeanSendsBytes(LeanScriptStep):
    """
    Simulate Lean's output behaviour at the byte level.
    Doesn't include new line characters unless passed in.
    """
    message_bytes: bytes

    async def run(self, server: 'MockLeanServerProcess') -> None:
        print(f"\nLean sends the following bytes:\n{self.message_bytes!r}")
        server.send_bytes(self.message_bytes)

@dataclass
class LeanShouldNotGetRequest(LeanScriptStep):
    """
    Check that Lean has not received any requests (perhaps sent prematurely).
    """
    wait_time_seconds: float = 0.1
    async def run(self, server: 'MockLeanServerProcess') -> Awaitable[None]:
        print(f"\nLean should not have received any requests yet.")
        return await server.assert_no_messages_received(self.wait_time_seconds)



class MockLeanServerProcess(trio.Process):

    def __init__(self, script: List[LeanScriptStep]):
        self.stdin = trio.testing.MemorySendStream()      # a stream for mock lean to read from
        self.stdout = trio.testing.MemoryReceiveStream()  # a stream for mock lean to write to
        self.messages: Deque[Dict] = deque()
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

    async def collect_stdin_messages(self, wait_time_seconds: float):
        """
        This method waits wait_time_seconds for data (sent from the Trio client) to enter Mock Lean's stdin.
        It has a few properties.
        1. This coroutine (and the coroutines which call it) behave asynchronously.  In particular, it allows
           passing execution from Mock Lean to the Trio lean client which runs asynchronously with Mock Lean.
        2. It gives the Trio lean client time to send data to Mock Lean's stdin (and for that data to become available).
           That amount of time can be adjusted with the wait_time_seconds parameter.
        3. It does not block (except for the given wait time).  This way, it can handle the case where no data was sent.
        """
        # this sleep command accomplishes properties (1) and (2)
        await trio.sleep(wait_time_seconds)
        try:
            # we use the nowait version of get_data to accomplish property (3)
            data = self.stdin.get_data_nowait()
        except trio.WouldBlock:  # no data
            return

        raw_messages = (self.partial_message + data).split(b"\n")
        self.partial_message = raw_messages.pop()
        self.messages.extend(self.parse_message(m) for m in raw_messages)

    async def assert_message_is_received(self, message_expected: dict, wait_time_seconds: float):

        await self.collect_stdin_messages(wait_time_seconds)

        assert self.messages, f"Mock Lean was expecting\n{message_expected}\nbut no messages were received."

        message_received = self.messages.pop()
        assert self.messages_are_equal(message_expected, message_received), \
            f"Mock Lean was expecting\n{message_expected}\nbut received\n{message_received}"

    async def assert_no_messages_received(self, wait_time_seconds: float):
        await self.collect_stdin_messages(wait_time_seconds)

        assert not self.messages, f"Mock Lean was not expecting a message, but \n{self.messages[0]}\nwas received."

    def send_bytes(self, message_bytes: bytes):
        self.stdout.put_data(message_bytes)

    def send_message(self, message):
        message_bytes = json.dumps(message).encode() + b"\n"
        self.stdout.put_data(message_bytes)

    async def follow_script(self):
        for step in self.script:
            await step.run(self)


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
