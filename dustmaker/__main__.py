"""Main CLI entry point for dustmaker utility scripts"""

import sys

from .cmd.main import main


sys.argv[0] = "dustmaker"
sys.exit(main())
