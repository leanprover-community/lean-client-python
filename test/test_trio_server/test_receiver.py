from lean_client.commands import SyncRequest, InfoRequest
from test.test_trio_server.mock_lean import \
    LeanShouldGetRequest, LeanSendsBytes, LeanSendsResponse, LeanShouldNotGetRequest, LeanTakesTime, start_with_mock_lean
from lean_client.trio_server import TrioLeanServer
import trio
import trio.testing


def test_reciever_processes_only_whole_messages():
    """
    Lean sometimes will not send a complet message over at a time.  It may even break up a unicode character
    like "⊢" (three bytes).

    This tests that the message is properly received.
    """

    expected_state = "⊢ true"  # In bytes this is b'\xe2\x8a\xa2 true'

    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest(SyncRequest(file_name="test.lean", content="example : true := \nbegin end"), seq_num=1),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),
        LeanShouldGetRequest(InfoRequest(file_name="test.lean", line=2, column=0), seq_num=2),

        # response sent in two chunks over the stream splitting the "⊢" character b'\xe2\x8a\xa2' in half.
        LeanSendsBytes(b'{"record":{"state":"\xe2\x8a'),
        LeanTakesTime(.01),
        LeanSendsBytes(b'\xa2 true"},"response":"ok","seq_num":2}\n'),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery, debug_bytes=True)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean', content='example : true := \nbegin end')
            state = await server.state(filename="test.lean", line=2, col=0)

            assert state == "⊢ true"

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)