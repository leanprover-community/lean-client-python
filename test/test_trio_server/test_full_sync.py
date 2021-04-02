from test.test_trio_server.mock_lean import (
    LeanSendsResponse,
    LeanShouldGetRequest,
    LeanShouldNotGetRequest,
    start_with_mock_lean,
)

import trio  # type: ignore
import trio.testing  # type: ignore

from lean_client.commands import InfoRequest, SyncRequest
from lean_client.trio_server import TrioLeanServer


def test_full_sync_waits_until_lean_ready():
    """
    Check that full_sync waits until the Lean server is ready.
    In particular, it must first get a "file invalidated" response, and then an "all_tasks" response
    before continuing.
    """
    mock_lean_script = [
        LeanShouldGetRequest(SyncRequest(file_name="test.lean", content="--"), seq_num=1),

        # current_tasks response is sent BEFORE the ok response
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),

        # shouldn't be receiving anything yet
        LeanShouldNotGetRequest(),

        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # now it is ok to get a new request
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=1, column=0), seq_num=2),
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
