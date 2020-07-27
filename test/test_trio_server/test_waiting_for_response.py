from lean_client.commands import SyncRequest, InfoRequest, SleepRequest, LongSleepRequest
from test.test_trio_server.mock_lean import \
    LeanShouldGetRequest, LeanSendsBytes, LeanSendsResponse, LeanShouldNotGetRequest, LeanTakesTime, start_with_mock_lean
from lean_client.trio_server import TrioLeanServer
import trio
import trio.testing


def test_normal_commands_wait_for_response():
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
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=1, column=0), seq_num=2),
        LeanShouldNotGetRequest(),  # waiting for a lean response
        LeanSendsResponse({"response": "ok", "seq_num": 2}),

        # info request 2
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=1, column=0), seq_num=3),
        LeanSendsResponse({"response": "ok", "seq_num": 3}),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery, debug_bytes=True)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean')
            await server.send(InfoRequest(file_name="test.lean", line=1, column=0))
            await server.send(InfoRequest(file_name="test.lean", line=1, column=0))

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)

def test_sleep_commands_do_not_wait_for_response():
    """
    The sleep commands should not wait for a response.
    """

    expected_state = "⊢ true"  # In bytes this is b'\xe2\x8a\xa2 true'


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
            await server.send(SleepRequest())
            await server.send(InfoRequest(file_name="test.lean", line=1, column=0))
            await server.send(LongSleepRequest())
            await server.send(InfoRequest(file_name="test.lean", line=1, column=0))

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)