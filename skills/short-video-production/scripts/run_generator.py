#!/usr/bin/env python3
"""以「補上 pymediainfo 空殼」的方式執行 capcut-mate 的 plan_to_draft.py。

生成器只是用 pymediainfo 做素材探測，載入後立刻會被 ffprobe 版本取代，
所以給一個空殼模組就能正常跑（本機沒裝 pymediainfo）。
"""
import os
import runpy
import sys
import types

GEN = os.path.expanduser("~/Developer/capcut-mate/local/plan_to_draft.py")

if "pymediainfo" not in sys.modules:
    stub = types.ModuleType("pymediainfo")
    stub.MediaInfo = type("MediaInfo", (), {})
    sys.modules["pymediainfo"] = stub

sys.argv = [GEN] + sys.argv[1:]
runpy.run_path(GEN, run_name="__main__")
