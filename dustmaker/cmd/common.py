""" Shared CLI definitions """
import abc
import argparse
from typing import Type


class CliUtility(metaclass=abc.ABCMeta):
    """Abstract utility base class"""

    @abc.abstractmethod
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Allow the utility to set up its arg parser.

        Arguments:
            parser (argparse.ArgumentParser): the parser to setup arguments for.
        """

    @abc.abstractmethod
    def main(self, args) -> int:
        """Run utility with parsed args.

        Returns:
            The utility exit code
        """


def run_utility(utility: Type[CliUtility]) -> int:
    """Run a single command line utility.

    Arguments:
        utility (type[CliUtilitiy]): class of utility to run.

    Returns:
        The desired exit code
    """
    util = utility()
    parser = argparse.ArgumentParser()
    util.setup_parser(parser)
    return util.main(parser.parse_args())
