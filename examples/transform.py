#!/usr/bin/env python3
"""
Sample script to perform map transforms
"""
import argparse

from dustmaker import DFReader, DFWriter, LevelType


def get_args():
    """Read CLI arguments"""
    parser = argparse.ArgumentParser(
        description="upscales, rotates, flips, and then shifts a map (in that order)."
    )
    parser.add_argument("input_map")
    parser.add_argument("output_map")
    parser.add_argument(
        "--upscale",
        type=int,
        default=1,
        required=False,
        help="how much to upscale map size",
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
        help="how much to shift the map elements' x-coordinates in pixels",
    )
    parser.add_argument(
        "--translate-y",
        type=float,
        default=0,
        required=False,
        help="how much to shift the map elements' y-coordinates in pixels",
    )
    return parser.parse_args()


def matmul(lhs, rhs):
    """Multiply two matrixes"""
    return [
        [
            sum(lhs[i][k] * rhs[k][j] for k in range(len(lhs[0])))
            for j in range(len(rhs[0]))
        ]
        for i in range(len(lhs))
    ]


def main():
    """Transform CLI entrypoint"""
    args = get_args()

    with DFReader(open(args.input_map, "rb")) as reader:
        mmap = reader.read_map()

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
        if mmap.level_type == LevelType.NORMAL:
            mmap.level_type = LevelType.DUSTMOD
        mmap.upscale(args.upscale, mat=mat)
    else:
        mmap.transform(mat)

    with DFWriter(open(args.output_map, "wb")) as writer:
        writer.write_map(mmap)


if __name__ == "__main__":
    main()
