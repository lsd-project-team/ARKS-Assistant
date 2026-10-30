"""连续讲解版共享设置，复用已验证的排版和绘图基础，不改动旧版。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
LEGACY = Path(__file__).resolve().parent.parent/'plain-language'
sys.path.append(str(LEGACY))

import build as layout
import figures as old_figures
import verify as old_checks
from drawing import *


def page(title, lead, diagram, caption, explain, detail, remember, bridge,
         part, stage, old, main=False, extra=None):
    return dict(title=title,lead=lead,diagram=diagram,caption=caption,
                explain=explain,detail=detail,remember=remember,bridge=bridge,
                part=part,stage=stage,old=old,main=main,extra=extra)
