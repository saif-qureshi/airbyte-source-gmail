import sys
import os

# Add the current directory to Python path to ensure custom modules are found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airbyte_cdk.entrypoint import launch
from source_gmail import SourceGmail

if __name__ == "__main__":
    source = SourceGmail()
    launch(source, sys.argv[1:])