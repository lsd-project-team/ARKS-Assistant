import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scope_review import build_book,GROUPS_COR as GROUPS
def build():return build_book('correction-process',GROUPS,'3.0')
