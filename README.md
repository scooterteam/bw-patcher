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

# Usage
```bash
python -m bwpatcher --help
usage: __main__.py [-h] {mi4} infile outfile patches

positional arguments:
  {mi4}       Dev name of scooter.
  infile
  outfile
  patches     The patches that are to be applied.

options:
  -h, --help  show this help message and exit
```

### Examples

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

## License
Licensed under AGPLv3, see [LICENSE.md](LICENSE.md).