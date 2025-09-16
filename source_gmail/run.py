#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_gmail import SourceGmail


def run():
    source = SourceGmail()
    launch(source, sys.argv[1:])


if __name__ == "__main__":
    run()