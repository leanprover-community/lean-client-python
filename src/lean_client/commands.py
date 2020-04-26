"""
Basic tools to convert back and forth between json expected or sent by the Lean
server and python objets. Mostly based on the TypeScript version.

Anything whose name contains Request is meant to be sent to the Lean server after
conversion by its to_json method.

Anything whose name contains Response is meant to be built from some json sent
by the Lean server by the parse_response function at the bottom of this file.

Everything else in this file are intermediate objects that will be contained in
response objects.
"""
from dataclasses import dataclass
from typing import Optional, List, NewType, ClassVar
from enum import Enum
import json

@dataclass
class Request:
    command: ClassVar[str] = ''

    def __post_init__(self):
        self.seq_num = 0

    def to_json(self) -> str:
        dic = self.__dict__.copy()
        dic['command'] = self.command
        return json.dumps(dic)


@dataclass
class Response:
    response: ClassVar[str]

    @classmethod
    def from_dict(cls, dic):
        if 'message' in dic and cls != ErrorResponse and cls != SyncResponse:
            dic.pop('message')  # TODO (jasonrute): Is this hack needed anymore?
        return cls(**dic)

Severity = Enum('Severity', 'information warning error')

@dataclass
class Message:
    file_name: str
    severity: Severity
    caption: str
    text: str
    pos_line: int
    pos_col: int
    end_pos_line: Optional[int] = None
    end_pos_col: Optional[int] = None

    @classmethod
    def from_dict(cls, dic):
        dic['severity'] = getattr(Severity, dic['severity'])
        return cls(**dic)

@dataclass
class AllMessagesResponse(Response):
    response = 'all_messages'
    msgs: List[Message]

    @classmethod
    def from_dict(cls, dic):
        return cls([Message.from_dict(msg) for msg in dic['msgs']])

@dataclass
class Task:
    file_name: str
    pos_line: int
    pos_col: int
    end_pos_line: int
    end_pos_col: int
    desc: str


@dataclass
class CurrentTasksResponse(Response):
    response = 'current_tasks'
    is_running: bool
    tasks: List[Task]
    cur_task: Optional[Task] = None

    @classmethod
    def from_dict(cls, dic):
        dic['tasks'] = [Task(**task) for task in dic.pop('tasks')]
        return cls(**dic)



@dataclass
class CommandResponse(Response):
    response = 'ok'
    seq_num: int


@dataclass
class ErrorResponse(Response):
    response = 'error'
    message: str
    seq_num: Optional[int] = None


@dataclass
class SyncResponse(Response):
    response = 'ok'
    message: str
    seq_num: Optional[int] = None


@dataclass
class SyncRequest(Request):
    command = 'sync'
    file_name: str
    content: Optional[str] = None

    def to_json(self):
        dic = self.__dict__.copy()
        dic['command'] = 'sync'
        if dic['content'] is None:
            dic.pop('content')
        return json.dumps(dic)


@dataclass
class CompleteRequest(Request):
    command = 'complete'
    file_name: str
    line: int
    column: int
    skip_completions: bool = False


@dataclass
class CompletionCandidate:
    text: str
    type_: Optional[str] = None
    tactic_params: Optional[str] = None
    doc: Optional[str] = None

    @classmethod
    def from_dict(cls, dic):
        dic['type_'] = dic.pop('type')
        return cls(**dic)


@dataclass
class CompleteResponse(CommandResponse):
    prefix: str
    completions: List[CompletionCandidate]

    @classmethod
    def from_dict(cls, dic):
        dic['completions'] = [CompletionCandidate.from_dict(cdt)
                              for cdt in dic.pop('completions')]
        return cls(**dic)


@dataclass
class InfoRequest(Request):
    command = 'info'
    file_name: str
    line: int
    column: int


@dataclass
class InfoSource:
    line: int = None
    column: int = None
    file: Optional[str] = None


GoalState = NewType('GoalState', str)

@dataclass
class InfoRecord:
    full_id: Optional[str] = None
    text: Optional[str] = None
    type_: Optional[str] = None
    doc: Optional[str] = None
    source: Optional[InfoSource] = None
    state: Optional[GoalState] = None
    tactic_param_idx: Optional[int] = None
    tactic_params: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, dic):
        if 'full-id' in dic:
            dic['full_id'] = dic.pop('full-id')
        if 'type' in dic:
            dic['type_'] = dic.pop('type')
        if 'source' in dic:
            dic['source'] = InfoSource(**dic.pop('source'))
        return cls(**dic)


@dataclass
class InfoResponse(CommandResponse):
    record: Optional[InfoRecord] = None

    @classmethod
    def from_dict(cls, dic):
        dic['record'] = InfoRecord.from_dict(dic.pop('record'))
        return cls(**dic)


@dataclass
class SearchRequest(Request):
    command = 'search'
    query: str


@dataclass
class SearchItem:
    text: str
    type_: str
    source: Optional[InfoSource] = None
    doc: Optional[str] = None

    @classmethod
    def from_dict(cls, dic):
        dic['type_'] = dic.pop('type')
        return cls(**dic)


@dataclass
class SearchResponse(CommandResponse):
    results: List[SearchItem]

    @classmethod
    def from_dict(cls, dic):
        dic['results'] = [SearchItem.from_dict(si)
                          for si in dic.pop('results')]
        return cls(**dic)


@dataclass
class HoleCommandsRequest(Request):
    command = 'hole_commands'
    file_name: str
    line: int
    column: int


@dataclass
class HoleCommandAction:
    name: str
    description: str

@dataclass
class Position:
    line: int
    column: int

@dataclass
class HoleCommands:
    file_name: str
    start: Position
    end: Position
    results: List[HoleCommandAction]

    @classmethod
    def from_dict(cls, dic):
        dic['results'] = [HoleCommandAction(**hc)
                          for hc in dic.pop('results')]
        return cls(**dic)


@dataclass
class HoleCommandsResponse(CommandResponse, HoleCommands):
    pass


@dataclass
class AllHoleCommandsRequest(Request):
    command = 'all_hole_commands'
    file_name: str


@dataclass
class AllHoleCommandsResponse(CommandResponse):
    holes: List[HoleCommands]

    @classmethod
    def from_dict(cls, dic):
        dic['holes'] = [HoleCommands.from_dict(hole)
                          for hole in dic.pop('holes')]
        return cls(**dic)


@dataclass
class HoleRequest(Request):
    command = 'hole'
    file_name: str
    line: int
    column: int
    action: str

@dataclass
class HoleReplacementAlternative:
    code: str
    description: str


@dataclass
class HoleReplacements:
    file_name: str
    start: Position
    end: Position
    alternatives: List[HoleReplacementAlternative]

    @classmethod
    def from_dict(cls, dic):
        dic['alternatives'] = [HoleReplacementAlternative(**alt)
                               for alt in dic.pop('alternatives')]
        return cls(**dic)



@dataclass
class HoleResponse(CommandResponse):
    replacements: Optional[HoleReplacements] = None
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, dic):
        if 'replacements' in dic:
            dic['replacements'] = HoleReplacements.from_dict(
                    dic.pop('replacements'))
        return cls(**dic)


CheckingMode = Enum('CheckingMode',
    'nothing visible-lines visible-lines-and-above visible-files open-files')

@dataclass
class RoiRange:
    begin_line: int
    end_line: int


@dataclass
class FileRoi:
    file_name: str
    ranges: List[RoiRange]

    def to_dict(self):
        return {'file_name': self.file_name,
                'ranges': [rr.__dict__ for rr in self.ranges] }

@dataclass
class RoiRequest(Request):
    command = 'roi'
    mode: CheckingMode
    files: List[FileRoi]

    def to_json(self) -> str:
        dic = self.__dict__.copy()
        dic['command'] = 'roi'
        dic['mode'] = dic['mode'].name
        dic['files'] = [fileroi.to_dict() for fileroi in dic['files']]

        return json.dumps(dic)


@dataclass
class SleepRequest(Request):
    command = 'sleep'


@dataclass
class LongSleepRequest(Request):
    command = 'long_sleep'


def parse_response(data: str) -> Response:
    dic = json.loads(data)
    response = dic.pop('response')
    if response == 'ok':
        if 'completions' in dic:
            return CompleteResponse.from_dict(dic)
        elif 'record' in dic:
            return InfoResponse.from_dict(dic)
        elif 'results' in dic and 'start' in dic:
            return HoleCommandsResponse.from_dict(dic)
        elif 'results' in dic:
            return SearchResponse.from_dict(dic)
        elif 'holes' in dic:
            return AllHoleCommandsResponse.from_dict(dic)
        elif 'replacements' in dic:
            return HoleResponse.from_dict(dic)
        elif 'message' in dic and dic['message'] in ["file invalidated", "file unchanged"]:
            return SyncResponse.from_dict(dic)


    # Now try classes for messages that do have a helpful response field
    for cls in [AllMessagesResponse, CurrentTasksResponse, CommandResponse,
            ErrorResponse]:
        if response == cls.response: # type: ignore
            return cls.from_dict(dic) # type: ignore
    raise ValueError("Couldn't parse response string.")


