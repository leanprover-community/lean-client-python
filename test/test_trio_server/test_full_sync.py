from test.test_trio_server.mock_lean import \
    LeanShouldGetRequest, LeanShouldNotGetRequest, LeanSendsResponse, start_with_mock_lean
from lean_client.trio_server import TrioLeanServer
import trio # type: ignore
import trio.testing # type: ignore


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
