from dataclasses import dataclass, field

from reports._shared.input import BaseReportInputs


@dataclass
class DetailsReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["connection_id"])
    connection_id: str = ""
    json_source: bool = False


@dataclass
class QueryReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=list)
    from_date: str = ""
    to_date: str = ""
    target_address: str = ""
    target_account: str = ""
    user_name: str = ""
    connection_type: str = ""
