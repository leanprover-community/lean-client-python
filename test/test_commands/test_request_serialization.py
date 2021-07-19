"""
Test that requests are properly serialized.
"""

import json

import lean_client.commands as cmds


def check_request_serialization(request: cmds.Request, expected_dict):
    json_str = request.to_json()
    json_dict = json.loads(json_str)  # deserialize to a dictionary to make comparison easier
    assert json_dict == expected_dict


class TestRequests:
    def test_sync_no_content(self):
        req = cmds.SyncRequest(
            file_name="testfilename"
        )
        out = {
            "command": "sync",
            "file_name": "testfilename",
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_sync_has_content(self):
        req = cmds.SyncRequest(
            file_name="testfilename",
            content="#eval 1+1"
        )
        out = {
            "command": "sync",
            "file_name": "testfilename",
            "content": "#eval 1+1",
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_complete_default_skip(self):
        req = cmds.CompleteRequest(
            file_name="testfilename",
            line=1,
            column=0
        )
        out = {
            "command": "complete",
            "file_name": "testfilename",
            "line": 1,
            "column": 0,
            "skip_completions": False,
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_complete_with_skip(self):
        req = cmds.CompleteRequest(
            file_name="testfilename",
            line=1,
            column=0,
            skip_completions=True
        )
        out = {
            "command": "complete",
            "file_name": "testfilename",
            "line": 1,
            "column": 0,
            "skip_completions": True,
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_info(self):
        req = cmds.InfoRequest(
            file_name="testfilename",
            line=1,
            column=0
        )
        out = {
            "command": "info",
            "file_name": "testfilename",
            "line": 1,
            "column": 0,
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_search(self):
        req = cmds.SearchRequest(
            query="a"
        )
        out = {
            "command": "search",
            "query": "a",
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_hole_commands(self):
        req = cmds.HoleCommandsRequest(
            file_name="testfilename",
            line=1,
            column=0
        )
        out = {
            "command": "hole_commands",
            "file_name": "testfilename",
            "line": 1,
            "column": 0,
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_all_hole_commands(self):
        req = cmds.AllHoleCommandsRequest(
            file_name="testfilename"
        )
        out = {
            "command": "all_hole_commands",
            "file_name": "testfilename",
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_hole(self):
        req = cmds.HoleRequest(
            file_name="testfilename",
            line=1,
            column=0,
            action="Infer"

        )
        out = {
            "command": "hole",
            "file_name": "testfilename",
            "line": 1,
            "column": 0,
            "action": "Infer",
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_roi(self):
        req = cmds.RoiRequest(
            mode=cmds.CheckingMode['open-files'],
            files=[cmds.FileRoi(
                file_name='testfilename',
                ranges=[cmds.RoiRange(
                    begin_line=1,
                    end_line=2
                )]
            )]
        )
        out = {
            "command": "roi",
            "mode": "open-files",
            "files": [{"file_name": "testfilename", "ranges": [{"begin_line": 1, "end_line": 2}]}],
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_sleep(self):
        req = cmds.SleepRequest()
        out = {
            "command": "sleep",
            "seq_num": 0
        }
        check_request_serialization(req, out)

    def test_long_sleep(self):
        req = cmds.LongSleepRequest()
        out = {
            "command": "long_sleep",
            "seq_num": 0
        }
        check_request_serialization(req, out)