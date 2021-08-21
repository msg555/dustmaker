#!/usr/bin/env python3
"""
Sample script to perform level transforms
"""
import argparse
import sys

from dustmaker import DFReader, DFWriter
from dustmaker.cmd.common import (
    run_utility,
    CliUtility,
)
from dustmaker.level import LevelType


def matmul(lhs, rhs):
    """Multiply two matrixes"""
    return [
        [
            sum(lhs[i][k] * rhs[k][j] for k in range(len(lhs[0])))
            for j in range(len(rhs[0]))
        ]
        for i in range(len(lhs))
    ]


class Transform(CliUtility):
    """CLI utility for peforming affine transformations on levels"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Read CLI arguments"""
        parser.description = (
            "upscales, rotates, flips, and then shifts a level (in that order)."
        )
        parser.add_argument("input_level")
        parser.add_argument("output_level")
        parser.add_argument(
            "--upscale",
            type=int,
            default=1,
            required=False,
            help="how much to upscale level size",
        )
        parser.add_argument(
            "--rotate",
            type=int,
            default=0,
            required=False,
            help="how many 90 degree clockwise rotations to perform (use negative for counterclockwise)",
        )
        parser.add_argument(
            "--vflip",
            action="store_const",
            const=True,
            default=False,
            required=False,
            help="vertically flip result",
        )
        parser.add_argument(
            "--hflip",
            action="store_const",
            const=True,
            default=False,
            required=False,
            help="horizontally filp result",
        )
        parser.add_argument(
            "--translate-x",
            type=float,
            default=0,
            required=False,
            help="how much to shift the level elements' x-coordinates in pixels",
        )
        parser.add_argument(
            "--translate-y",
            type=float,
            default=0,
            required=False,
            help="how much to shift the level elements' y-coordinates in pixels",
        )

    def main(self, args):
        """Transform CLI entrypoint"""
        with DFReader(open(args.input_level, "rb")) as reader:
            level = reader.read_level()

        # Start out with the rotation matrix
        times = args.rotate % 4
        cs = [1, 0, -1, 0]
        sn = [0, 1, 0, -1]
        mat = [[cs[times], -sn[times], 0], [sn[times], cs[times], 0], [0, 0, 1]]

        # Perform the flips
        if args.vflip:
            mat = matmul([[1, 0, 0], [0, -1, 0], [0, 0, 1]], mat)

        if args.hflip:
            mat = matmul([[-1, 0, 0], [0, 1, 0], [0, 0, 1]], mat)

        # Add in the translations
        mat[0][2] += args.translate_x
        mat[1][2] += args.translate_y

        if args.upscale > 1:
            # Need dustmod level type for proper scaling of entities/props
            if level.level_type == LevelType.NORMAL:
                level.level_type = LevelType.DUSTMOD
            level.upscale(args.upscale, mat=mat)
        else:
            level.transform(mat)

        with DFWriter(open(args.output_level, "wb")) as writer:
            writer.write_level(level)


if __name__ == "__main__":
    sys.exit(run_utility(Transform))
