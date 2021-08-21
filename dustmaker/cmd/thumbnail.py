#!/usr/bin/env python3
"""
Sample script to extract and set level thumbnails.
"""
import argparse
import io
import os
import sys

from dustmaker import DFReader, DFWriter
from dustmaker.cmd.common import (
    run_utility,
    CliUtility,
)
from dustmaker.variable import VariableBool


class Thumbnail(CliUtility):
    """CLI utility for adjusting level thumbnails"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Read CLI arguments"""
        parser.description = "extract or update a level thumbnail"
        parser.add_argument("level")
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
            help="read in the image and update the level thumbnail",
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

    def main(self, args) -> int:
        """thumbnail CLI entrypoint"""
        if args.auto_scale:
            args.auto_convert = True
        if args.auto_convert:
            args.update = True

        with DFReader(open(args.level, "rb")) as reader:
            level, region_offsets = reader.read_level_ex()
            region_data = b""
            if args.update:
                region_data = reader.read_bytes(region_offsets[-1])

        if not args.update:
            if not args.force and os.path.exists(args.image):
                print("path already exists, use --force to ignore")
                return 1

            with open(args.image, "wb") as fout:
                fout.write(level.sshot)

            return 0

        if args.auto_convert:
            try:
                # pylint: disable=import-outside-toplevel
                from PIL import Image  # type: ignore
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
                    level.sshot = io_out.getvalue()
        else:
            with open(args.image, "rb") as fimg:
                level.sshot = fimg.read()

        level.variables["icon_taken"] = VariableBool(True)
        with DFWriter(open(args.level, "wb")) as writer:
            writer.write_level_ex(level, region_offsets, region_data)

        return 0


if __name__ == "__main__":
    sys.exit(run_utility(Thumbnail))
