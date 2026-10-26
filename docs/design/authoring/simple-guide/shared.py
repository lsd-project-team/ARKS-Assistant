from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.append(str(Path(__file__).resolve().parent.parent/'plain-language'))
import build as layout
import verify as old_checks
from drawing import *
