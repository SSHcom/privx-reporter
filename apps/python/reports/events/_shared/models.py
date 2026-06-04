from dataclasses import dataclass, field

from reports._shared.input import BaseReportInputs


@dataclass
class EventsAccountsReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=list)
    from_date: str = ""
    to_date: str = ""
    days: int = 0
    added: bool = False
    removed: bool = False
    json_source: bool = False


@dataclass
class EventsQueryReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=list)
    from_date: str = ""
    to_date: str = ""
    days: int = 0
    event_name: str = ""
    event_id: str = ""
    json_source: bool = False


@dataclass
class EventsRoleMembersReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=list)
    from_date: str = ""
    to_date: str = ""
    days: int = 0
    added: bool = False
    removed: bool = False
