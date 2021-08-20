#!/usr/bin/env python3
"""
Sample script to extract and set map thumbnails.
"""
import argparse
import io
import os
import sys

from dustmaker import DFReader, DFWriter


def get_args():
    """Read CLI arguments"""
    parser = argparse.ArgumentParser(description="extract or update a map thumbnail")
    parser.add_argument("map")
    parser.add_argument("image")
    parser.add_argument(
        "--force",
        action="store_const",
        const=True,
        default=False,
        required=False,
        help="allow overwrite of existing image",
    )
    parser.add_argument(
        "--update",
        action="store_const",
        const=True,
        default=False,
        required=False,
        help="read in the image and update the map thumbnail",
    )
    parser.add_argument(
        "--auto-convert",
        action="store_const",
        const=True,
        default=False,
        required=False,
        help="automatically convert to PNG format (implies --update)",
    )
    parser.add_argument(
        "--auto-scale",
        action="store_const",
        const=True,
        default=False,
        required=False,
        help="automaticaly scale image to expected 382 x 182 size (implies --auto-convert)",
    )
    args = parser.parse_args()
    if args.auto_scale:
        args.auto_convert = True
    if args.auto_convert:
        args.update = True
    return args


def main():
    """thumbnail CLI entrypoint"""
    args = get_args()
    with DFReader(open(args.map, "rb")) as reader:
        mmap = reader.read_map()

    if not args.update:
        if not args.force and os.path.exists(args.image):
            print("path already exists, use --force to ignore")
            return 1

        with open(args.image, "wb") as fout:
            fout.write(mmap.sshot)

        return 0

    if args.auto_convert:
        try:
            # pylint: disable=import-outside-toplevel
            from PIL import Image
        except ImportError:
            print(
                "failed to import PIL, cannot convert image (try `pip install pillow`)"
            )
            return 1

        with Image.open(args.image) as im:
            if args.auto_scale:
                im = im.resize((382, 182))
            with io.BytesIO() as io_out:
                im.save(io_out, format="PNG")
                mmap.sshot = io_out.getvalue()
    else:
        with open(args.image, "rb") as fimg:
            mmap.sshot = fimg.read()

    with DFWriter(open(args.map, "wb")) as writer:
        writer.write_map(mmap)

    return 0


if __name__ == "__main__":
    sys.exit(main())
