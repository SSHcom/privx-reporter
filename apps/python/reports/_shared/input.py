from argparse import Namespace
from dataclasses import dataclass, field, fields


@dataclass
class BaseReportInputs:
    """Base class for report inputs."""

    to_json: bool = False
    to_stdout: bool = False
    output_dir: str | None = None
    _mandatory: list[str] = field(default_factory=list)
    _error_message: str | None = None


def get_report_inputs[T: BaseReportInputs](clazz: type[T], args: Namespace) -> T | BaseReportInputs:
    """Create report inputs instance with validation.

    Args:
        clazz: The report inputs class to instantiate
        args: Argparse Namespace containing field values (extra fields are ignored)

    Returns:
        Instance of the specified class if validation passes,
        otherwise BaseReportInputs with error message
    """
    # Get the field names from the dataclass
    field_names = {f.name for f in fields(clazz)}

    # Filter args.__dict__ to only include fields that exist in the dataclass
    filtered_kwargs = {k: v for k, v in args.__dict__.items() if k in field_names}

    # Create instance with filtered kwargs
    instance = clazz(**filtered_kwargs)

    # Get mandatory fields from the instance
    mandatory_fields = getattr(instance, "_mandatory", [])

    # Validate mandatory fields
    if mandatory_fields:
        missing_fields = []
        for field_name in mandatory_fields:
            value = getattr(instance, field_name, None)
            if value is None or value == "":
                missing_fields.append(field_name)

        if missing_fields:
            # Format field names for error message (convert snake_case to kebab-case)
            formatted_fields = [f.replace("_", "-") for f in missing_fields]
            fields_str = "', '".join(formatted_fields)
            error_msg = f"'{fields_str}' {'is' if len(missing_fields) == 1 else 'are'} required"
            return BaseReportInputs(_error_message=error_msg)

    return instance
