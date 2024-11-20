# bw-patcher
Firmware patcher for scooters manufactured by Brightway.

# Setup
This patcher requires Python and the `keystone-engine` package installed.

```bash
pip install -r requirements.txt
```

# Supported models
Currently, only the Mi4 is supported. The next models maybe soon.

# Available patches
- rsls (Remove Speed Limit Sport) - removes the speed limiter on sport mode (technically sets it to a value that the scooter will never reach),
- dms (Dashboard Max Speed) (from 1.0km/h to 29.6km/h) - spoofs the maximum speed reached by the scooter on the dashboard,
- sld (Speed Limit Drive) (from 1.0km/h to 25.5km/h) - allows to change the maximum speed on Drive mode.
- rfm (Region Free) - remove regional restrictions such as speed and acceleration nerf.
- fdv (Fake DRV Version) - allows to change the DRV version. Can prevent unwanted updates.
- chk (Fix Checksum) - update checksum for the patched bytes (only required by mi4pro2nd).

# Usage
## CLI
```bash
python -m bwpatcher --help
usage: __main__.py [-h] {mi4,mi4pro2nd,ultra4} infile outfile patches

positional arguments:
  {mi4,mi4pro2nd,ultra4}
                        Dev name of scooter.
  infile
  outfile
  {rsls,dms,sld,rfm,fdv,chk}
                        The patches that are to be applied.

options:
  -h, --help  show this help message and exit
```

## GUI
```bash
poetry install
poetry run streamlit run app.py
```

### Examples

#### Mi4
RSLS and DMS (22.0km/h):
```bash
python -m bwpatcher mi4 my_dump.bin my_patched_dump.bin rsls,dms=22.0
```

SLD (25.5km/h):
```bash
python -m bwpatcher mi4 my_dump.bin my_patched_dump.bin sld=25.5
```

RSLS:
```bash
python -m bwpatcher mi4 my_dump.bin my_patched_dump.bin rsls
```

#### Mi4Pro2nd
RFM + RSLS + CHK:
```bash
python -m bwpatcher mi4pro2nd mcu_update.bin patched_mcu_update.bin rfm,rsls,chk
```
Important: CHK must always come last!

## License
Licensed under AGPLv3, see [LICENSE.md](LICENSE.md).
