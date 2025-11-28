# bw-patcher

Research tool for analyzing and modifying firmware parameters on Brightway-based controllers.

## ⚠️ IMPORTANT SAFETY WARNING

**Modifying device firmware can be dangerous and illegal.**

- May void your warranty
- May violate local laws and regulations
- Creates serious safety risks by bypassing manufacturer safety features
- Modified devices may be illegal to operate
- You assume ALL liability for injuries, accidents, and legal consequences

**Use at your own risk. This software is for educational and research purposes only.**

👉 Read the full [PRINCIPLES.md](PRINCIPLES.md) and [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md) before using this software.

## Setup

This patcher requires Python and the `keystone-engine` package installed.

### Using Poetry (recommended)
```bash
poetry install
```

### Using pip
```bash
pip install -r requirements.txt
```

## Supported Models

- Mi4
- Mi4Pro2nd
- Mi4Lite
- Mi5
- Mi5Pro
- Mi5Max
- Mi5Elite
- Ultra4

## Available Modifications

This tool can modify various firmware parameters. The specific parameters available depend on the device model and firmware version.

**WARNING:** Modifying firmware parameters may bypass safety features, void warranties, and create legal liability. Users assume all responsibility.

## Usage

### CLI
```bash
poetry run python -m bwpatcher --help
usage: __main__.py [-h] {model} infile outfile patches

positional arguments:
  {model}       Device model (see supported models above)
  infile        Input firmware file
  outfile       Output firmware file
  patches       Comma-separated list of patches to apply

options:
  -h, --help    show this help message and exit
```

### GUI
```bash
poetry run streamlit run app.py
```

The GUI provides an interactive interface for selecting firmware modifications. A legal disclaimer must be accepted before use.

### Example Usage

Apply modifications to firmware:
```bash
poetry run python -m bwpatcher mi4 firmware.bin firmware_modified.bin patch1,patch2
```

**Note:** Always maintain backups of original firmware before modification.

## License

Licensed under CC BY-NC-SA 4.0 (NonCommercial, ShareAlike). See [LICENSE](LICENSE) for full terms.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## Disclaimer

This tool is provided for educational and research purposes only. The authors accept no liability for any consequences of using this software. See [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md) for complete terms.
