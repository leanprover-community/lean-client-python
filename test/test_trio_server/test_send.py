from lean_client.commands import SyncRequest, InfoRequest, SleepRequest, LongSleepRequest, InfoResponse
from test.test_trio_server.mock_lean import \
    LeanShouldGetRequest, LeanSendsResponse, LeanShouldNotGetRequest, LeanTakesTime, start_with_mock_lean
from lean_client.trio_server import TrioLeanServer
import trio
import trio.testing


def test_normal_commands_wait_for_and_return_response():
    """
    Most commands, like the info command should wait for a response.
    """
    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest(SyncRequest(file_name="test.lean"), seq_num=1),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # info request 1
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=1, column=25), seq_num=2),
        LeanShouldNotGetRequest(),  # waiting for a lean response
        LeanSendsResponse({
            "record": {
                "full-id": "max",
                "source": {
                    "column": 11,
                    "file": "path/lib/lean/library/init/algebra/functions.lean",
                    "line": 12
                },
                "type": "\xce\xa0 {\xce\xb1 : Type u} [_inst_1 : decidable_linear_order \xce\xb1], \xce\xb1 \xe2\x86\x92 \xce\xb1 \xe2\x86\x92 \xce\xb1"
            },
            "response": "ok",
            "seq_num": 2
        }),

        LeanTakesTime(.01),

        # info request 2
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=100, column=0), seq_num=3),
        LeanSendsResponse({"response": "ok", "seq_num": 3}),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery, debug_bytes=True)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean')

            # check response object is parsed and of the correct type
            # (more parsing tests can be found in unit tests for the commands.py file)
            response1 = await server.send(InfoRequest(file_name="test.lean", line=1, column=25))
            assert isinstance(response1, InfoResponse)
            assert response1.record.source.column == 11

            response2 = await server.send(InfoRequest(file_name="test.lean", line=100, column=0))
            assert isinstance(response2, InfoResponse)
            assert response2.record is None

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)


def test_sleep_commands_do_not_wait_for_response():
    """
    The sleep commands should not wait for a response.
    """

    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest(SyncRequest(file_name="test.lean"), seq_num=1),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # Sleep request
        LeanShouldGetRequest(SleepRequest(), seq_num=2),

        # An info request sent during the sleep request.
        # The server should wait for a response from the sleep request
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=1, column=0), seq_num=3),
        LeanTakesTime(.01),
        LeanSendsResponse({"response": "ok", "seq_num": 3}),

        # Long sleep request
        LeanShouldGetRequest(LongSleepRequest(), seq_num=4),
        # Lean does not wait for a response and the trio server shouldn't block

        # An info request sent during the sleep request.
        # The server should wait for a response from the sleep request
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=1, column=0), seq_num=5),
        LeanTakesTime(.01),
        LeanSendsResponse({"response": "ok", "seq_num": 5}),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery, debug_bytes=True)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean')

            response1 = await server.send(SleepRequest())
            assert response1 is None

            response2 = await server.send(InfoRequest(file_name="test.lean", line=1, column=0))
            assert isinstance(response2, InfoResponse)

            response3 = await server.send(LongSleepRequest())
            assert response3 is None

            response4 = await server.send(InfoRequest(file_name="test.lean", line=1, column=0))
            assert isinstance(response4, InfoResponse)

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)


def test_errors_are_handled():
    """
    If a Lean server returns an error (specifically the "response" field is "error",
    then the Trio server should also raise an error.
    """

    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest(SyncRequest(file_name="test.lean"), seq_num=1),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # An info request sent during the sleep request.
        # The server should wait for a response from the sleep request
        LeanShouldGetRequest(InfoRequest(file_name="wrongfile.lean", line=1, column=0), seq_num=2),
        LeanTakesTime(.01),
        LeanSendsResponse({
            "message": "file \'wrongfile.lean\' not found in the LEAN_PATH",
            "response": "error",
            "seq_num": 2
        })
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery, debug_bytes=True)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean')

            # for this test to pass it has to throw an error
            try:
                await server.send(InfoRequest(file_name="wrongfile.lean", line=1, column=0))
                assert False, "An error should have been thrown here"
            except ChildProcessError:
                pass

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)
