#!/usr/bin/env python3
""" Shared dustmaker CLI entrypoint """
import argparse
import sys

from dustmaker.cmd.thumbnail import Thumbnail
from dustmaker.cmd.transform import Transform
from dustmaker.cmd.variables import Variables

UTILITIES = (
    Thumbnail,
    Transform,
    Variables,
)


def main() -> int:
    """Shared CLI entrypoint for all dustmaker utilities"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="utility", help="which utility to use")

    util_map = {}
    for utility in UTILITIES:
        util = utility()  # type: ignore
        util_key = utility.__name__.lower()
        util.setup_parser(subparsers.add_parser(util_key))
        util_map[util_key] = util

    args = parser.parse_args()
    if args.utility is None:
        parser.print_help()
        return 0

    util = util_map[args.utility]
    del args.utility
    sys.exit(util.main(args))


if __name__ == "__main__":
    sys.exit(main())
