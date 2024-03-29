"""
Communicating with the Lean server in a trio context
(see https://trio.readthedocs.io/en/stable/).

This is only the beginning, implementing reading a file and requesting tactic
state. See the example use in examples/trio_example.py.
"""
from typing import Optional, List, Dict, Union
from subprocess import PIPE

import trio # type: ignore

from lean_client.commands import (SyncRequest, InfoRequest,
                                  Request, CommandResponse, Message, Task,
                                  InfoResponse, AllMessagesResponse, CurrentTasksResponse, ErrorResponse,
                                  OkResponse, SyncResponse)


class TrioLeanServer:
    def __init__(self, nursery, lean_cmd: Union[str, List[str]] = 'lean', debug=False, debug_bytes=False):
        """
        Lean server trio interface.
        """
        self.nursery = nursery
        self.seq_num: int = 0
        self.lean_cmd: List[str] = lean_cmd if isinstance(lean_cmd, List) else [lean_cmd]
        self.messages: List[Message] = []
        self.current_tasks: List[Task] = []
        self.process: Optional[trio.Process] = None
        self.debug: bool = debug
        self.debug_bytes: bool = debug_bytes
        # Each request, with sequence number seq_num, gets an event
        # self.response_events[seq_num] that it set when the response comes in
        self.response_events: Dict[int, trio.Event] = dict()
        # and the corresponding response is stored in self.responses until
        # handled
        self.responses: Dict[int, Union[ErrorResponse, OkResponse]] = dict()
        self.is_fully_ready: trio.Event = trio.Event()

    async def start(self):
        self.process = await trio.open_process(
                self.lean_cmd + ["--server"], stdin=PIPE, stdout=PIPE)
        self.nursery.start_soon(self.receiver)

    async def send(self, request: Request) -> Optional[CommandResponse]:
        if not self.process:
            raise ValueError('No Lean server')
        self.seq_num += 1
        request.seq_num = self.seq_num

        if self.debug:
            print(f'Sending {request}')
        if self.debug_bytes:
            bytes = (request.to_json() + '\n').encode()
            print(f'Sending {bytes!r}')

        await self.process.stdin.send_all((request.to_json()+'\n').encode())

        # Some responses like sleep and long_sleep don't get responses
        if not request.expect_response:
            return None

        self.response_events[self.seq_num] = trio.Event()
        await self.response_events[request.seq_num].wait()
        self.response_events.pop(request.seq_num)

        response = self.responses.pop(request.seq_num)

        # Lean errors are rare and signify problems with the command itself
        # (e.g. an incorrect file).  They should be raised as Python errors.

        if isinstance(response, OkResponse):
            cmd_response = response.to_command_response(request.command)
        else:
            assert isinstance(response, ErrorResponse)
            raise ChildProcessError(f'Lean server error while executing "{request.command}":\n{response}')

        return cmd_response

    async def receiver(self):
        """This task waits for Lean responses, updating the server state
        (tasks and messages) and triggering events when a response comes."""
        if not self.process:
            raise ValueError('No Lean server')
        unfinished_message = b''
        async for data in self.process.stdout:
            lines = (unfinished_message + data).split(b'\n')
            unfinished_message = lines.pop()  # usually empty, but can be half a message

            for line in lines:
                if self.debug_bytes:
                    print(f'Received {line}')
                resp = CommandResponse.parse_response(line.decode())
                if self.debug:
                    print(f'Received {resp}')

                if isinstance(resp, CurrentTasksResponse):
                    self.current_tasks = resp.tasks
                    if not resp.is_running:
                        self.is_fully_ready.set()
                elif isinstance(resp, AllMessagesResponse):
                    self.messages = resp.msgs
                elif isinstance(resp, (ErrorResponse, OkResponse)):
                    self.responses[resp.seq_num] = resp
                    self.response_events[resp.seq_num].set()

    async def full_sync(self, filename, content=None) -> None:
        """Fully compile a Lean file before returning."""
        # Waiting for the response is not enough, so we prepare another event
        response = await self.send(SyncRequest(filename, content))
        assert isinstance(response, SyncResponse)

        if response.message == "file invalidated":
            self.is_fully_ready = trio.Event()
            await self.is_fully_ready.wait()

    async def state(self, filename, line, col) -> str:
        """Tactic state"""
        resp = await self.send(InfoRequest(filename, line, col))
        if isinstance(resp, InfoResponse) and resp.record:
            return resp.record.state or ''
        else:
            return ''

    def kill(self):
        """Kill the Lean process."""
        self.process.kill()
