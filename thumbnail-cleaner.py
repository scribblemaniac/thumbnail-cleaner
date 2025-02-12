#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Thumbnail Cleaner - GNOME application to remove all invalid thumbnails.
# Copyright 2011 Gautier Portet
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import argparse
from enum import Enum, auto
from pathlib import Path
from urllib.parse import urlparse, unquote
from math import floor

from tqdm import tqdm
from PIL import Image

###########################################################################
# Thumbnail Scanner

NAME = 'Thumbnail Cleaner'
VERSION = '2.0'
print(NAME, VERSION)

class ThumbnailState(Enum):
    OUTDATED = auto()
    ORPHAN = auto()
    INVALID = auto()
    EXTERNAL = auto()
    VALID = auto()

THUMBNAIL_CACHE_DIR = Path('~/.cache/thumbnails').expanduser()

class ThumbnailScanner():
    """
    The main thumbnail scanner.
    """
    def __init__(self, args):
        self.args = args
        self.deletable = []

    def scan(self):
        '''Start the walking thread.'''
        self._do_walk()

        if not self.args.dry_run:
            for filepath in self.deletable:
                filepath.unlink()

    def _do_walk(self):
        self.deletable = []

        for filepath in tqdm(THUMBNAIL_CACHE_DIR.rglob("*.png"), total=len(list(THUMBNAIL_CACHE_DIR.rglob("*.png")))):
            status = self._get_status_from_thumbnail(filepath)

            if status in [ThumbnailState.OUTDATED, ThumbnailState.ORPHAN]:
                self.deletable.append(filepath)

    def _get_status_from_thumbnail(self, filepath):
        metadata = self._get_metadata_from_thumbnail(filepath)
        if "Thumb::URI" not in metadata:
            return ThumbnailState.INVALID

        url_scheme, _, local_path_str, *_ = urlparse(metadata["Thumb::URI"])
        if url_scheme and url_scheme != 'file':
            # external resource
            return ThumbnailState.EXTERNAL

        # Make sure source file still exists
        local_path = Path(unquote(local_path_str))
        if not local_path.exists():
            if self.args.dry_run:
                print(f"Thumbnail for nonexistant file {local_path}")
            return ThumbnailState.ORPHAN

        # Make sure source file has not been updated
        try:
            if floor(local_path.stat().st_mtime) > floor(float(metadata["Thumb::MTime"])):
                if self.args.dry_run:
                    print(f"Outdated thumbnail for file {local_path}")
                return ThumbnailState.OUTDATED
        except KeyError:
            pass

        return ThumbnailState.VALID

    def _get_metadata_from_thumbnail(self, filepath):
        try:
            with Image.open(filepath) as img:
                img.load()

                return img.info
        except OSError:
            return []


def parse_args():
    parser = argparse.ArgumentParser(description='Remove outdated thumbnails from the GNOME cache.')
    parser.add_argument('--dry-run', action='store_true', help='Print the files that would be deleted, but do not delete them.')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    scanner = ThumbnailScanner(args)
    scanner.scan()


if __name__ == "__main__":
    main()