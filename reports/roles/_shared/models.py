from dataclasses import dataclass, field

from reports._shared.input import BaseReportInputs


@dataclass
class QueryReportInputs(BaseReportInputs):
    role_name: str = ""
    access_group_name: str = ""


@dataclass
class MembersReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["role_name"])
    role_name: str = ""


@dataclass
class UserReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["user_name"])
    user_name: str = ""


@dataclass
class RestrictionsReportInputs(BaseReportInputs):
    pass
