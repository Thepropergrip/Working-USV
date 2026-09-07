import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tpg_rubble_common import build
# Hero-quality 20 ft rubble reference build.
build('intact',2)
