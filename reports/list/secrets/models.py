from dataclasses import dataclass

from reports._shared.input import BaseReportInputs


@dataclass
class SecretsReportInputs(BaseReportInputs):
    name: str = ""
    read_role: str = ""
    write_role: str = ""
