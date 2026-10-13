"""Validate Brick's first complete kit using the existing strict package checks."""
from pathlib import Path
import sys
from validate_gallery_package import build

if __name__=='__main__':
    build(Path(sys.argv[1]),'Brick Realm','bricks-buildout',
          {'cast':'brick-cast','creatures':'brick-creatures','environment':'brick-environment'})
