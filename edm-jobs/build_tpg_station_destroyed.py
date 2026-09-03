import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpg_station_common import build_station
build_station(True)
