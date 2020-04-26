from test.test_trio_server.mock_lean import \
    LeanShouldGetRequest, LeanShouldNotGetRequest, LeanTakesTime, LeanSendsResponse, start_with_mock_lean
from lean_client.trio_server import TrioLeanServer
import trio
import trio.testing


def test_full_sync_waits_until_lean_ready():
    """
    Check that full_sync waits until the Lean server is ready.
    In particular, it must first get a "file invalidated" response, and then an "all_tasks" response
    before continuing.
    """
    mock_lean_script = [
        LeanShouldGetRequest({"file_name": "test.lean", "content": '--', "seq_num": 1, "command": "sync"}),

        # current_tasks response is sent BEFORE the ok response
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),

        # shouldn't be receiving anything yet
        LeanShouldNotGetRequest(),

        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # now it is ok to get a new request
        LeanShouldGetRequest({"file_name": "test.lean", "line": 1, "column": 0, "seq_num": 2, "command": "info"}),
        LeanSendsResponse({"response": "ok", "seq_num": 2}),
    ]

    async def check_waiting_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean', content='--')
            await server.state(filename="test.lean", line=1, col=0)

            nursery.cancel_scope.cancel()

    trio.run(check_waiting_behavior)


def test_syncing_same_file_again():
    """
    If the same file is synced with no changes, then Lean won't send the same sort of responses.
    """

    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest({"file_name": "test.lean", "seq_num": 1, "command": "sync"}),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # sync same file again which hasn't changed.  Lean WON'T send a current_tasks response
        LeanShouldGetRequest({"file_name": "test.lean", "seq_num": 2, "command": "sync"}),
        LeanSendsResponse({"message": "file unchanged", "response": "ok", "seq_num": 2}),
        LeanTakesTime(.01),

        # The python-lean interface should not block and instead send an info request right away
        LeanShouldGetRequest({"file_name": "test.lean", "line": 1, "column": 0, "seq_num": 3, "command": "info"}),
        LeanSendsResponse({"response": "ok", "seq_num": 3}),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync("test.lean")
            await server.full_sync("test.lean")  # sync same file twice

            await server.state(filename="test.lean", line=1, col=0)

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)


def test_error_in_sync():
    """
    If there is an error in syncing (such as the file not existing), then one shouldn't wait
    for a current_tasks response.
    """

    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest({"file_name": "bad_file_name", "seq_num": 1, "command": "sync"}),
        LeanSendsResponse({"message": "file 'bad_file_name' not found in the LEAN_PATH", "response": "error", "seq_num": 1}),
        LeanTakesTime(.01),

        # the lean process should throw an error (which will be caught and handled)

        # If this part fails, that means the interface blocked waiting for a current_tasks response
        LeanShouldGetRequest({"file_name": "test.lean", "seq_num": 2, "command": "sync"}),
        LeanSendsResponse({"message": "file unchanged", "response": "ok", "seq_num": 2}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery)
            await start_with_mock_lean(server, mock_lean_script)

            # for this test to pass it has to (1) not block forever and (2) throw an error
            try:
                await server.full_sync("bad_file_name")
                assert False, "An error should have been thrown here"
            except ValueError:
                pass

            await server.full_sync("test.lean")  # sync a different file

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)
