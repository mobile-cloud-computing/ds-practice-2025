from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AppendEntriesRequest(_message.Message):
    __slots__ = ("term", "leader_id", "entries", "previous_log_index", "previous_log_term", "commit_index")
    TERM_FIELD_NUMBER: _ClassVar[int]
    LEADER_ID_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_LOG_INDEX_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_LOG_TERM_FIELD_NUMBER: _ClassVar[int]
    COMMIT_INDEX_FIELD_NUMBER: _ClassVar[int]
    term: int
    leader_id: str
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    previous_log_index: int
    previous_log_term: int
    commit_index: int
    def __init__(self, term: _Optional[int] = ..., leader_id: _Optional[str] = ..., entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ..., previous_log_index: _Optional[int] = ..., previous_log_term: _Optional[int] = ..., commit_index: _Optional[int] = ...) -> None: ...

class AppendEntriesResponse(_message.Message):
    __slots__ = ("term", "success")
    TERM_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    term: int
    success: bool
    def __init__(self, term: _Optional[int] = ..., success: bool = ...) -> None: ...

class RequestVoteRequest(_message.Message):
    __slots__ = ("term", "candidate_id", "last_log_index", "last_log_term")
    TERM_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_LOG_INDEX_FIELD_NUMBER: _ClassVar[int]
    LAST_LOG_TERM_FIELD_NUMBER: _ClassVar[int]
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int
    def __init__(self, term: _Optional[int] = ..., candidate_id: _Optional[str] = ..., last_log_index: _Optional[int] = ..., last_log_term: _Optional[int] = ...) -> None: ...

class RequestVoteResponse(_message.Message):
    __slots__ = ("term", "granted")
    TERM_FIELD_NUMBER: _ClassVar[int]
    GRANTED_FIELD_NUMBER: _ClassVar[int]
    term: int
    granted: bool
    def __init__(self, term: _Optional[int] = ..., granted: bool = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("term", "command")
    TERM_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    term: int
    command: Command
    def __init__(self, term: _Optional[int] = ..., command: _Optional[_Union[Command, _Mapping]] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("operation", "key", "value")
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    operation: str
    key: str
    value: str
    def __init__(self, operation: _Optional[str] = ..., key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
