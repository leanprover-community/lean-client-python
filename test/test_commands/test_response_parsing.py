"""
Unit tests for lean server response classes

Test that responses are properly converted from JSON into
Python classes and that new fields do not cause the parser
to crash.

When possible, tests should use ACTUAL LEAN OUTPUT under a
range of scenarios to ensure that all cases are covered.
(One way to generate output is to use the trio server with
debug_bytes=True.)
"""
import json

import lean_client.commands as cmds


class TestAllMessagesResponse:
    def test_no_messages(self):
        response_json = '{"msgs":[],"response":"all_messages"}'
        resp = cmds.Response.parse_response(response_json)

        assert isinstance(resp, cmds.AllMessagesResponse)
        assert resp.response == "all_messages"
        assert len(resp.msgs) == 0

    def test_multiple_messages(self):
        response_json = '{"msgs":[{"caption":"","file_name":"test3.lean","pos_col":7,"pos_line":2,"severity":"error","text":"unknown identifier \'foo\'"},{"caption":"","file_name":"test2.lean","pos_col":0,"pos_line":1,"severity":"warning","text":"declaration \'foo\' uses sorry"}],"response":"all_messages"}'
        resp = cmds.Response.parse_response(response_json)

        assert isinstance(resp, cmds.AllMessagesResponse)
        assert resp.response == "all_messages"
        assert len(resp.msgs) == 2

        assert resp.msgs[0].caption == ""
        assert resp.msgs[0].file_name == "test3.lean"
        assert resp.msgs[0].pos_col == 7
        assert resp.msgs[0].pos_line == 2
        assert resp.msgs[0].severity == cmds.Severity.error
        assert resp.msgs[0].text == "unknown identifier 'foo'"

        assert resp.msgs[1].severity == cmds.Severity.warning

    def test_extra_fields(self):
        """
        Should not crash if given extra fields where are added in later versions of Lean.
        """

        response_json = '{"_new_field_a":12345, "msgs":[{"_new_field_b":12345, "caption":"","file_name":"test3.lean","pos_col":7,"pos_line":2,"severity":"error","text":"unknown identifier \'foo\'","_new_field_a":12345},{"caption":"","file_name":"test2.lean","pos_col":0,"pos_line":1,"severity":"warning","text":"declaration \'foo\' uses sorry"}],"response":"all_messages"}'
        resp = cmds.Response.parse_response(response_json)

        assert isinstance(resp, cmds.AllMessagesResponse)
        assert resp.response == "all_messages"
        assert len(resp.msgs) == 2

        assert resp.msgs[0].caption == ""
        assert resp.msgs[0].file_name == "test3.lean"
        assert resp.msgs[0].pos_col == 7
        assert resp.msgs[0].pos_line == 2
        assert resp.msgs[0].severity == cmds.Severity.error
        assert resp.msgs[0].text == "unknown identifier 'foo'"

        assert resp.msgs[1].severity == cmds.Severity.warning


class TestCurrentTasksResponse:
    def test_no_tasks(self):
        response_json = '{"is_running":false,"response":"current_tasks","tasks":[]}'
        resp = cmds.Response.parse_response(response_json)

        assert isinstance(resp, cmds.CurrentTasksResponse)
        assert resp.is_running == False
        assert resp.response == "current_tasks"
        assert resp.tasks == []

    def test_extra_fields(self):
        """
        Should not crash if given extra fields where are added in later versions of Lean.
        """
        response_json = '{"_new_field_a":123,"is_running":false,"response":"current_tasks","tasks":[]}'
        resp = cmds.Response.parse_response(response_json)

        assert isinstance(resp, cmds.CurrentTasksResponse)
        assert resp.is_running == False
        assert resp.response == "current_tasks"
        assert resp.tasks == []

    def test_multiple_tasks(self):
        # TODO: Find example where tasks is not empty
        # TODO: Find example where is_running = true
        pass


class TestErrorResponse:
    # TODO: Find examples of error responses
    pass


class TestCommandResponse:
    class TestSyncResponse:
        def test_file_invalidated_response(self):
            response_json = '{"message":"file invalidated","response":"ok","seq_num":2}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 2

            resp = ok_resp.to_command_response(command="sync")

            assert isinstance(resp, cmds.SyncResponse)
            assert resp.command == "sync"
            assert resp.response == "ok"
            assert resp.seq_num == 2
            assert resp.message == "file invalidated"

        def test_extra_fields(self):
            response_json = '{"_new_field_a":123,"message":"file invalidated","response":"ok","seq_num":2}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 2

            resp = ok_resp.to_command_response(command="sync")

            assert isinstance(resp, cmds.SyncResponse)
            assert resp.command == "sync"
            assert resp.response == "ok"
            assert resp.seq_num == 2

            assert resp.message == "file invalidated"

        def test_file_unchanged_response(self):
            response_json = '{"message":"file unchanged","response":"ok","seq_num":3}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 3

            resp = ok_resp.to_command_response(command="sync")

            assert isinstance(resp, cmds.SyncResponse)
            assert resp.command == "sync"
            assert resp.response == "ok"
            assert resp.seq_num == 3

            assert resp.message == "file unchanged"

    class TestAllHoleCommandsResponse:
        def test_holes(self):
            response_json = '{"holes":[{"end":{"column":21,"line":1},"file":"test2.lean","results":[{"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"start":{"column":16,"line":1}}],"response":"ok","seq_num":6}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 6

            resp = ok_resp.to_command_response(command="all_hole_commands")

            assert isinstance(resp, cmds.AllHoleCommandsResponse)
            assert resp.command == "all_hole_commands"
            assert resp.response == "ok"
            assert resp.seq_num == 6

            assert len(resp.holes) == 1

            assert resp.holes[0].file == "test2.lean"
            assert resp.holes[0].start.line == 1
            assert resp.holes[0].start.column == 16
            assert resp.holes[0].end.line == 1
            assert resp.holes[0].end.column == 21

            assert len(resp.holes[0].results) == 3
            assert resp.holes[0].results[0].name == "Infer"
            assert resp.holes[0].results[0].description == "Infer type of the expression in the hole"

        def test_extra_fields(self):
            response_json = '{"_new_field_a":123,"holes":[{"_new_field_b":123,"end":{"_new_field_c":123,"column":21,"line":1},"file":"test2.lean","results":[{"_new_field_d":123,"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"start":{"_new_field_e":123,"column":16,"line":1}}],"response":"ok","seq_num":6}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 6

            resp = ok_resp.to_command_response(command="all_hole_commands")

            assert isinstance(resp, cmds.AllHoleCommandsResponse)
            assert resp.command == "all_hole_commands"
            assert resp.response == "ok"
            assert resp.seq_num == 6

            assert len(resp.holes) == 1

            assert resp.holes[0].file == "test2.lean"
            assert resp.holes[0].start.line == 1
            assert resp.holes[0].start.column == 16
            assert resp.holes[0].end.line == 1
            assert resp.holes[0].end.column == 21

            assert len(resp.holes[0].results) == 3
            assert resp.holes[0].results[0].name == "Infer"
            assert resp.holes[0].results[0].description == "Infer type of the expression in the hole"

    class TestHoleCommandsResponse:
        def test_hole_not_found(self):
            response_json = '{"message":"hole not found","response":"ok","seq_num":11}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 11

            resp = ok_resp.to_command_response(command="hole_commands")

            assert isinstance(resp, cmds.HoleCommandsResponse)
            assert resp.command == "hole_commands"
            assert resp.response == "ok"
            assert resp.seq_num == 11

            assert resp.message == "hole not found"

            assert resp.file is None
            assert resp.start is None
            assert resp.end is None
            assert resp.results is None

        def test_holes(self):
            response_json = '{"end":{"column":21,"line":1},"file":"test2.lean","response":"ok","results":[{"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"seq_num":7,"start":{"column":16,"line":1}}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 7

            resp = ok_resp.to_command_response(command="hole_commands")

            assert isinstance(resp, cmds.HoleCommandsResponse)
            assert resp.command == "hole_commands"
            assert resp.response == "ok"
            assert resp.seq_num == 7

            assert resp.message is None

            assert resp.file == "test2.lean"
            assert resp.start.line == 1
            assert resp.start.column == 16
            assert resp.end.line == 1
            assert resp.end.column == 21

            assert len(resp.results) == 3
            assert resp.results[0].name == "Infer"
            assert resp.results[0].description == "Infer type of the expression in the hole"

        def test_extra_fields(self):
            response_json = '{"_new_field_a":123, "end":{"_new_field_b":123, "column":21,"line":1},"file":"test2.lean","response":"ok","results":[{"_new_field_c":123, "description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"seq_num":7,"start":{"_new_field_d":123, "column":16,"line":1}}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 7

            resp = ok_resp.to_command_response(command="hole_commands")

            assert isinstance(resp, cmds.HoleCommandsResponse)
            assert resp.command == "hole_commands"
            assert resp.response == "ok"
            assert resp.seq_num == 7

            assert resp.message is None

            assert resp.file == "test2.lean"
            assert resp.start.line == 1
            assert resp.start.column == 16
            assert resp.end.line == 1
            assert resp.end.column == 21

            assert len(resp.results) == 3
            assert resp.results[0].name == "Infer"
            assert resp.results[0].description == "Infer type of the expression in the hole"

    class TestHoleResponse:
        def test_hole_not_found(self):
            response_json = '{"message":"hole not found","response":"ok","seq_num":14}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 14

            resp = ok_resp.to_command_response(command="hole")

            assert isinstance(resp, cmds.HoleResponse)
            assert resp.command == "hole"
            assert resp.response == "ok"
            assert resp.seq_num == 14

            assert resp.replacements is None
            assert resp.message == "hole not found"

        def test_hole_infer_action(self):
            response_json = '{"message":"\xe2\x84\x95\\n","response":"ok","seq_num":8}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 8

            resp = ok_resp.to_command_response(command="hole")

            assert isinstance(resp, cmds.HoleResponse)
            assert resp.command == "hole"
            assert resp.response == "ok"
            assert resp.seq_num == 8

            assert resp.replacements is None
            assert resp.message == "\xe2\x84\x95\n"

        def test_hole_use_action(self):
            response_json = '{"replacements":{"alternatives":[{"code":"1","description":""}],"end":{"column":21,"line":1},"file":"test2.lean","start":{"column":16,"line":1}},"response":"ok","seq_num":10}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 10

            resp = ok_resp.to_command_response(command="hole")

            assert isinstance(resp, cmds.HoleResponse)
            assert resp.command == "hole"
            assert resp.response == "ok"
            assert resp.seq_num == 10

            assert resp.message is None
            assert resp.replacements.file == "test2.lean"
            assert resp.replacements.start.line == 1
            assert resp.replacements.start.column == 16
            assert resp.replacements.end.line == 1
            assert resp.replacements.end.column == 21
            assert len(resp.replacements.alternatives) == 1
            assert resp.replacements.alternatives[0].code == "1"
            assert resp.replacements.alternatives[0].description == ""

        def test_extra_fields(self):
            response_json = '{"_new_field_a":123,"replacements":{"_new_field_b":123,"alternatives":[{"_new_field_c":123,"code":"1","description":""}],"end":{"_new_field_e":123,"column":21,"line":1},"file":"test2.lean","start":{"_new_field_f":123,"column":16,"line":1}},"response":"ok","seq_num":10}'
            ok_resp = cmds.Response.parse_response(response_json)

            assert isinstance(ok_resp, cmds.OkResponse)
            assert ok_resp.response == "ok"
            assert ok_resp.seq_num == 10

            resp = ok_resp.to_command_response(command="hole")

            assert isinstance(resp, cmds.HoleResponse)
            assert resp.command == "hole"
            assert resp.response == "ok"
            assert resp.seq_num == 10

            assert resp.message is None
            assert resp.replacements.file == "test2.lean"
            assert resp.replacements.start.line == 1
            assert resp.replacements.start.column == 16
            assert resp.replacements.end.line == 1
            assert resp.replacements.end.column == 21
            assert len(resp.replacements.alternatives) == 1
            assert resp.replacements.alternatives[0].code == "1"
            assert resp.replacements.alternatives[0].description == ""


class CommandResponseExample:
    def __init__(self, response_json: str, response_type):
        self.response_json = response_json
        self.data = json.loads(response_json)
        self.command = response_type.command
        self.response_type = response_type
        self.ok_resp = None
        self.resp = None

    def add_fields(self, data):
        if isinstance(data, dict):
            data2 = {k: self.add_fields(d) for k, d in data.items()}
            data2['_extra_field'] = "Extra field value"
            return data2
        if isinstance(data, list):
            data2 = [self.add_fields(d) for d in data]
            return data2
        else:
            return data

    def parse_intermediate(self, add_extra_fields):
        if add_extra_fields:
            json_string = json.dumps(self.add_fields(self.data))
        else:
            json_string = self.response_json
        self.ok_resp = cmds.Response.parse_response(self.response_json)

    def parse_final(self):
        self.resp = self.ok_resp.to_command_response(self.command)

    def test_intermediate_representation(self):
        assert isinstance(self.ok_resp, cmds.OkResponse)
        assert self.ok_resp.response == self.data['response']
        assert self.ok_resp.seq_num == self.data['seq_num']

    def assert_data_and_object_match(self, data, object, ignore_keys):
        print("Comparing:", object, "\nwith:   ", data)
        if isinstance(data, (int, float, str, bool)):
            assert data == object
        elif isinstance(data, list):
            assert isinstance(object, list)
            assert len(object) == len(data)
            for d, o in zip(data, object):
                self.assert_data_and_object_match(d, o, ignore_keys)
        elif isinstance(data, dict):
            for key, value in data.items():
                if key not in ignore_keys:
                    self.assert_data_and_object_match(value, object.__dict__[key], ignore_keys)

    def test_final_representation(self, ignore_keys=None):
        assert isinstance(self.resp, self.response_type)
        assert self.resp.command == self.command
        assert self.resp.response == self.data['response']

        if ignore_keys is None:
            ignore_keys = []
        self.assert_data_and_object_match(self.data, self.resp, ignore_keys=ignore_keys+['response'])

    def test_all(self, ignore_keys=None, add_extra_fields=False):
        self.parse_intermediate(add_extra_fields=add_extra_fields)
        self.test_intermediate_representation()
        self.parse_final()
        self.test_final_representation(ignore_keys)


def run_command_response_tests(response_json: str, response_type):
    example = CommandResponseExample(
        response_json=response_json,
        response_type=response_type
    )

    # test parsing
    example.parse_intermediate(add_extra_fields=False)
    example.test_intermediate_representation()
    example.parse_final()
    example.test_final_representation()

    # test that still parses with extra fields
    example.parse_intermediate(add_extra_fields=False)
    example.test_intermediate_representation()
    example.parse_final()
    example.test_final_representation()


def test_stuff():
    run_command_response_tests(
        response_json='{"message":"file invalidated","response":"ok","seq_num":2}',
        response_type=cmds.SyncResponse
    )

    run_command_response_tests(
        response_json='{"message":"file unchanged","response":"ok","seq_num":3}',
        response_type=cmds.SyncResponse
    )

    run_command_response_tests(
        response_json='{"message":"\xe2\x84\x95\\n","response":"ok","seq_num":8}',
        response_type=cmds.HoleResponse
    )

    run_command_response_tests(
        response_json='{"holes":[{"end":{"column":21,"line":1},"file":"test2.lean","results":[{"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"start":{"column":16,"line":1}}],"response":"ok","seq_num":6}',
        response_type=cmds.AllHoleCommandsResponse
    )

    run_command_response_tests(
        response_json='{"holes":[{"end":{"column":21,"line":1},"file":"test2.lean","results":[{"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"start":{"column":16,"line":1}}],"response":"ok","seq_num":6}',
        response_type=cmds.AllHoleCommandsResponse
    )

    run_command_response_tests(
        response_json='{"holes":[{"end":{"column":21,"line":1},"file":"test2.lean","results":[{"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"start":{"column":16,"line":1}}],"response":"ok","seq_num":6}',
        response_type=cmds.AllHoleCommandsResponse
    )

    run_command_response_tests(
        response_json='{"message":"hole not found","response":"ok","seq_num":11}',
        response_type=cmds.HoleCommandsResponse
    )

    run_command_response_tests(
        response_json='{"end":{"column":21,"line":1},"file":"test2.lean","response":"ok","results":[{"description":"Infer type of the expression in the hole","name":"Infer"},{"description":"Show the current goal","name":"Show"},{"description":"Try to fill the hole using the given argument","name":"Use"}],"seq_num":7,"start":{"column":16,"line":1}}',
        response_type=cmds.HoleCommandsResponse
    )

    run_command_response_tests(
        response_json='{"message":"hole not found","response":"ok","seq_num":14}'
        response_type=cmds.HoleCommandsResponse
    )


