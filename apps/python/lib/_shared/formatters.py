import argparse


class CommandWithoutDescriptionFormatter(argparse.HelpFormatter):
    """Custom help formatter that shows subcommands without a redundant section header."""

    def _format_action(self, action: argparse.Action) -> str:
        if isinstance(action, argparse._SubParsersAction):
            # Render each subcommand's one-liner help directly, skipping the group header
            lines = []
            for subaction in action._get_subactions():
                lines.append(super()._format_action(subaction))
            return "".join(lines)
        return super()._format_action(action)


class CommandWithDescriptionFormatter(argparse.RawDescriptionHelpFormatter):
    """
    Formatter for command groups: preserves raw description text and omits the subcommand positional line.
    """

    def _format_action(self, action: argparse.Action) -> str:
        # Skip sub-command rendering  - We use our own description as-is instead
        if isinstance(action, argparse._SubParsersAction):
            return ""
        # Render anything else with default formatter
        return super()._format_action(action)


class RawTextHelpFormatter(argparse.RawTextHelpFormatter):
    """Preserves formatting in help text including newlines."""

    pass
