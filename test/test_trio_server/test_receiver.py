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
        LeanShouldGetRequest({"file_name": "test.lean", "content": 'example : true := \nbegin end', "seq_num": 1, "command": "sync"}),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),
        LeanShouldGetRequest({"file_name": "test.lean", "line": 2, "column": 0, "seq_num": 2, "command": "info"}),

        # response sent in two chunks over the stream splitting the "⊢" character b'\xe2\x8a\xa2' in half.
        LeanSendsBytes(b'{"record":{"state":"\xe2\x8a'),
        LeanTakesTime(.01),
        LeanSendsBytes(b'\xa2 true"},"response":"ok","seq_num":2}\n'),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync('test.lean', content='example : true := \nbegin end')
            state = await server.state(filename="test.lean", line=2, col=0)

            assert state == "⊢ true"

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)


def test_that_info_source_doesnt_need_line_and_column():
    """
    That issue is that the info source for the obviously tactic doesn't have a line or column, so we have to check
    that we don't require them.

    Here is an example in mathlib.  If we send an info request for line 22, column 0 we get the following response.
    Notice info_source has no line or column.

      {"record":
        {"doc": "The `obviously` tactic is a \\"replaceable\\" tactic, which means that its meaning is defined by tactics that are defined later with the `@[obviously]` attribute. It is intended for use with `auto_param`s for structure fields.",
         "full-id": "obviously",
         "source": {"file": "/mathlib/src/category_theory/category/default.lean"},
         "type": "tactic unit"},
         "response": "ok",
         "seq_num":44
         }
    """

    mock_lean_script = [
        # initial sync
        LeanShouldGetRequest({"file_name": "test.lean", "seq_num": 1, "command": "sync"}),
        LeanSendsResponse({"message": "file invalidated", "response": "ok", "seq_num": 1}),
        LeanTakesTime(.01),
        LeanSendsResponse({"is_running": False, "response": "current_tasks", "tasks": []}),

        # info request
        LeanShouldGetRequest({"file_name": "test.lean", "line": 1, "column": 0, "seq_num": 2, "command": "info"}),

        # response with no line or column
        LeanSendsResponse({"record":
            {"doc": "The `obviously` tactic ... blah blah blah",
             "full-id": "obviously",
             "source": {"file": "/mathlib/src/category_theory/category/default.lean"},
             "type": "tactic unit"},
             "response": "ok",
             "seq_num": 2
        }),
    ]

    async def check_behavior():
        async with trio.open_nursery() as nursery:
            server = TrioLeanServer(nursery)
            await start_with_mock_lean(server, mock_lean_script)

            await server.full_sync("test.lean")

            # state triggers an info request
            await server.state(filename="test.lean", line=1, col=0)

            nursery.cancel_scope.cancel()

    trio.run(check_behavior)