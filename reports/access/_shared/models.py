from dataclasses import dataclass, field

from reports._shared.input import BaseReportInputs


@dataclass
class AccountReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["target_account"])
    target_address: str = ""
    target_account: str = ""
    common_name: str = ""


@dataclass
class AccountRestrictionsReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=list)
    target_address: str = ""


@dataclass
class HostsReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=list)
    user_name: str = ""
    user_id: str = ""
    principal: str = ""
    directory: str | None = None
    to_map: bool = False


@dataclass
class RoleMapReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["target_address"])
    target_address: str = ""


@dataclass
class QueryReportInputs(BaseReportInputs):
    target_address: str = ""
    common_name: str = ""
    target_account: str = ""
    access_group_name: str = ""
    access_group_comment: str = ""
    service_type: str = ""
    role_name: str = ""
    user_name: str = ""
    tags: str = ""
