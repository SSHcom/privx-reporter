import logging
import sys

import toml

from .admin import run
from .cli_parser import build_parser

# Configure logging to stderr to avoid interfering with stdout output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


def main() -> None:
    args_config_file = "administration/config.toml"

    with open(args_config_file) as f:
        args_spec = toml.load(f)

    parser = build_parser(args_spec)
    args = parser.parse_args(sys.argv[1:])
    result = run(args, args_spec)

    if result["error_message"]:
        logger.error(result["error_message"])
        sys.exit(1)

    if result["info_message"]:
        logger.info(result["info_message"])


if __name__ == "__main__":
    main()
