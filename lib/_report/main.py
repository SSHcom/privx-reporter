# Tests are not necessary for this module.

import logging
import sys

import toml

from lib.clients.privx import get_privx_client

from .cli_parser import build_parser
from .generator import generate

# Configure logging to stderr to avoid interfering with stdout output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


def _preprocess_fields_arg(argv: list[str]) -> list[str]:
    """
    Preprocess command line arguments to handle whitespace in --fields values.

    When --fields is used with spaces (e.g., "--fields type, user_id"),
    argparse treats "user_id" as a separate argument. This function combines
    such arguments into a single --fields value.

    Args:
        argv: Original command line arguments

    Returns:
        Preprocessed command line arguments with --fields values combined
    """
    result = []
    i = 0
    while i < len(argv):
        if argv[i] == "--fields":
            result.append(argv[i])
            i += 1
            # Collect all following non-option arguments as part of --fields value
            fields_parts = []
            while i < len(argv) and not argv[i].startswith("--"):
                fields_parts.append(argv[i])
                i += 1
            # Join the parts with spaces (they may contain commas)
            if fields_parts:
                result.append(" ".join(fields_parts))
        else:
            result.append(argv[i])
            i += 1
    return result


def main() -> None:
    args_config_file = "reports/config.toml"

    with open(args_config_file) as f:
        args_spec = toml.load(f)

    # Preprocess arguments to handle whitespace in --fields values
    preprocessed_argv = _preprocess_fields_arg(sys.argv[1:])

    # Build parser and parse arguments
    # If '--help' or '-h' is provided, argsparse library prints help and exits
    parser = build_parser(args_spec)
    args = parser.parse_args(preprocessed_argv)

    # Suppress INFO-level logs when using stdout to keep output clean
    if hasattr(args, "to_stdout") and args.to_stdout:
        logging.getLogger().setLevel(logging.WARNING)

    # Create PrivX client
    api = get_privx_client()

    # Run the report
    result = generate(api, args, args_spec)

    if result["error_message"]:
        logger.error(result["error_message"])
        sys.exit(1)
    elif result["info_message"]:
        logger.info(result["info_message"])


if __name__ == "__main__":
    main()
