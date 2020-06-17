#!/usr/bin/env python
from pathlib import Path
from pprint import pprint

import trio # type: ignore

from lean_client.commands import SleepRequest, SearchRequest, HoleCommandsRequest, AllHoleCommandsRequest, HoleRequest, \
    CompleteRequest, RoiRequest, FileRoi, CheckingMode, LongSleepRequest
from lean_client.trio_server import TrioLeanServer


async def main():
    async with trio.open_nursery() as nursery:

        server = TrioLeanServer(nursery, debug_bytes=True)
        await server.start()
        resp = await server.full_sync('test.lean')
        pprint(resp)

        # Bad sync requests
        await server.full_sync('blank.lean', content="")

        # Bad sync requests
        await server.full_sync('test.lean')
        await server.full_sync('test.lean')

        # Hole commands - Good cases
        await server.full_sync('test2.lean', content="theorem foo : 1={!1!} := { }")
        pprint(server.messages)
        resp = await server.send(AllHoleCommandsRequest(file_name='test2.lean'))
        pprint(resp)
        for hole_commands in resp.holes:
            print(hole_commands)
            resp = await server.send(HoleCommandsRequest(
                file_name=hole_commands.file,
                line=hole_commands.end.line,
                column=hole_commands.end.column
            ))
            pprint(resp)
            for action in hole_commands.results:
                print(action)
                resp = await server.send(HoleRequest(
                    file_name=hole_commands.file,
                    line=hole_commands.end.line,
                    column=hole_commands.end.column,
                    action=action.name
                ))
                print(resp)

        # Hole commands - Bad cases
        await server.full_sync('empty.lean', content="")
        resp = await server.send(AllHoleCommandsRequest(
            file_name="empty.lean"
        ))
        print(resp)
        resp = await server.send(HoleCommandsRequest(
            file_name="test2.lean",
            line=1,
            column=0
        ))
        print(resp)

        # Hole commands - Bad cases
        resp = await server.send(HoleRequest(
            file_name="test2.lean",
            line=1,
            column=0,
            action="Use"
        ))
        print(resp)

        resp = await server.send(HoleRequest(
            file_name="test2.lean",
            line=1,
            column=21,
            action="asdfasf"
        ))
        print(resp)

        # Complete commands
        await server.full_sync('test3.lean', content="theorem foobar : 1=1 := begin refl end\n#check foo")
        print(server.messages)
        resp = await server.send(CompleteRequest(
            file_name="test3.lean",
            line=2,
            column=10,
            skip_completions=False
        ))
        print(resp)

        # Complete commands
        resp = await server.send(CompleteRequest(
            file_name="test3.lean",
            line=2,
            column=10,
            skip_completions=True
        ))
        print(resp)

        # Complete commands - bad case
        resp = await server.send(CompleteRequest(
            file_name="test3.lean",
            line=1,
            column=0,
            skip_completions=False
        ))
        print(resp)

        # Search request
        resp = await server.send(SearchRequest(query='a'))
        print(resp)

        # Sleep request
        resp = await server.send(SleepRequest())
        print(resp)

        # Long Sleep request
        resp = await server.send(LongSleepRequest())
        print(resp)

        # Widget request
        # TODO: Add widgets

        # ROI request
        resp = await server.send(RoiRequest(files=[FileRoi(file_name='test.lean', ranges=[])], mode=CheckingMode['open-files']))
        print(resp)

        # This is necessary to stop the receiver process in the Lean server.  Without this the
        # nursery will never exit the context block since it is waiting forever for all the
        # children processes to end.
        nursery.cancel_scope.cancel()

if __name__ == '__main__':
    trio.run(main)