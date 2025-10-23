# Mellanox Firmware Manager

A comprehensive Python-based firmware management utility for Mellanox/NVIDIA ASICs in SONiC systems. Supports both Spectrum (switch) and BlueField (DPU) ASICs with unified architecture, parallel upgrades, and robust error handling.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing](#testing)
- [Development](#development)
- [Return Codes](#return-codes)
- [Error Handling](#error-handling)
- [License](#license)

## Features

### Core Capabilities
- **Multi-ASIC Support**: Automatic detection and parallel firmware upgrades for multi-ASIC systems
- **Platform Detection**: Automatic ASIC type detection (Spectrum 1-5, BlueField 3)
- **Parallel Processing**: Concurrent firmware upgrades across multiple ASICs
- **Error Recovery**: Persistent error tracking with automatic recovery mechanisms
- **SONiC Integration**: Seamless integration with SONiC image management
- **Comprehensive Logging**: Syslog and console logging with configurable verbosity

### Supported ASICs
- **Spectrum Family**: SPC1, SPC2, SPC3, SPC4, SPC5 (Ethernet switches)
- **BlueField Family**: BF3 (DPU - Data Processing Units)

## Architecture

### Component Overview

```
mellanox_fw_manager/
├── main.py                    # CLI entry point
├── firmware_coordinator.py    # Multi-ASIC orchestration
├── firmware_base.py           # Abstract base class
├── spectrum_manager.py        # Spectrum ASIC implementation
├── bluefield_manager.py       # BlueField ASIC implementation
├── asic_manager.py           # ASIC detection and configuration
├── error_handler.py          # Error tracking and recovery
├── platform_utils.py         # Platform detection utilities
└── fw_manager.py             # Factory functions
```

### Key Components

#### `FirmwareManagerBase`
Abstract base class providing:
- Firmware version detection and comparison
- MST device discovery with retry logic
- Command execution with automatic logging
- Process-based parallel execution framework
- Semaphore clearing capabilities

#### `SpectrumFirmwareManager`
Spectrum ASIC-specific implementation:
- Uses `mlxfwmanager` for firmware operations
- Supports automatic firmware reactivation
- Handles SPC1-SPC5 firmware files

#### `BluefieldFirmwareManager`
BlueField ASIC-specific implementation:
- Uses `flint` for firmware operations
- Supports firmware configuration reset
- Handles BF3 firmware files

#### `FirmwareCoordinator`
Orchestrates multi-ASIC operations:
- Parallel process management
- Result aggregation
- SONiC image integration
- Error coordination

## Installation

### From Source

```bash
cd platform/mellanox/fw-manager
pip install -e .
```

### Development Installation

```bash
cd platform/mellanox/fw-manager
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

#### Basic Operations

```bash
# Upgrade firmware (current SONiC image)
mlnx-fw-manager

# Upgrade firmware with verbose output
mlnx-fw-manager --verbose

# Upgrade from next SONiC image
mlnx-fw-manager --upgrade

# Check if upgrade is needed (dry-run)
mlnx-fw-manager --dry-run

# Clear hardware semaphore before upgrade
mlnx-fw-manager --clear-semaphore --upgrade
```

#### Firmware Status Check

```bash
# Check firmware version status (single-ASIC)
mlnx-fw-manager --status

# Check status for specific ASIC (multi-ASIC)
mlnx-fw-manager --status 0
mlnx-fw-manager --status all

# Check status against next SONiC image
mlnx-fw-manager --status all --upgrade
```

#### BlueField-Specific

```bash
# Reset firmware configuration (BlueField only)
mlnx-fw-manager --reset
```

#### Logging Options

```bash
# Disable syslog (console only)
mlnx-fw-manager --nosyslog

# Verbose mode with console output
mlnx-fw-manager --verbose
```

### Python API

#### Basic Usage

```python
from mellanox_fw_manager.firmware_coordinator import FirmwareCoordinator

# Create coordinator
coordinator = FirmwareCoordinator(verbose=True)

# Check if upgrade needed
if coordinator.check_upgrade_required():
    print("Firmware upgrade is required")

    # Perform upgrade
    coordinator.upgrade_firmware()
```

#### Advanced Usage

```python
from mellanox_fw_manager.firmware_coordinator import FirmwareCoordinator

# Create coordinator with options
coordinator = FirmwareCoordinator(
    verbose=True,
    from_image=True,           # Use next SONiC image
    clear_semaphore=True       # Clear semaphore before upgrade
)

# Get system information
num_asics = coordinator.get_asic_count()
print(f"System has {num_asics} ASIC(s)")

# Perform upgrade
try:
    coordinator.upgrade_firmware()
    print("Upgrade successful!")
except FirmwareUpgradeError as e:
    print(f"Upgrade failed: {e}")
```

#### Direct Manager Usage

```python
from mellanox_fw_manager.spectrum_manager import SpectrumFirmwareManager
from multiprocessing import Queue

# Create manager for specific ASIC
manager = SpectrumFirmwareManager(
    asic_index=0,
    pci_id="01:00.0",
    fw_bin_path="/etc/mlnx",
    verbose=True,
    clear_semaphore=False,
    asic_type="spc3",
    status_queue=Queue()
)

# Check if upgrade required
if manager.is_upgrade_required():
    print(f"Current: {manager.current_version}")
    print(f"Available: {manager.available_version}")

    # Run upgrade
    success = manager.run_firmware_update()
    if success:
        print("Upgrade completed successfully")
```

## Configuration

### ASIC Configuration File

Location: `/usr/share/sonic/device/{platform}/asic.conf`

**Single-ASIC Example:**
```ini
NUM_ASIC=1
DEV_ID_ASIC_0=01:00.0
```

**Multi-ASIC Example:**
```ini
NUM_ASIC=4
DEV_ID_ASIC_0=01:00.0
DEV_ID_ASIC_1=02:00.0
DEV_ID_ASIC_2=03:00.0
DEV_ID_ASIC_3=04:00.0
```

### Platform Detection

Location: `/host/machine.conf`

```ini
onie_platform=x86_64-nvidia_sn4280-r0
```

### Firmware Files

Default location: `/etc/mlnx/`

Supported firmware files:
- `fw-SPC.mfa` - Spectrum 1
- `fw-SPC2.mfa` - Spectrum 2
- `fw-SPC3.mfa` - Spectrum 3
- `fw-SPC4.mfa` - Spectrum 4
- `fw-SPC5.mfa` - Spectrum 5
- `fw-BF3.mfa` - BlueField 3

### Error Storage

Location: `/host/image/platform/fw/`

Each failure creates a file: `asic{N}_fw_upgrade_failure`

**Failure File Format:**
```
ASIC Index: 0
Timestamp: 2025-01-15 10:30:45
PCI ID: 01:00.0
Error: Failed to burn firmware with return code 1: Device busy
```

### Logging

**Syslog:** `/var/log/syslog` (default)
```
mellanox-fw-manager[12345]: INFO - Mellanox Firmware Manager started
mellanox-fw-manager[12345]: INFO - Executing: mlxfwmanager --query-format XML
```

**Console:** Enabled with `--verbose` or `--nosyslog`

## Testing

### Run All Tests

```bash
cd platform/mellanox/fw-manager
python3 -m unittest discover tests -v
```

### Run Specific Test Suite

```bash
# Test main CLI
python3 -m unittest tests.test_main -v

# Test spectrum manager
python3 -m unittest tests.test_spectrum_manager -v

# Test bluefield manager
python3 -m unittest tests.test_bluefield_manager -v

# Test platform detection
python3 -m unittest tests.test_platform_detection -v
```

### Coverage Report

```bash
# Run with coverage
python3 -m coverage run -m unittest discover tests
python3 -m coverage report -m

# Generate HTML report
python3 -m coverage html
# Open htmlcov/index.html in browser
```

### Current Test Statistics

- **Total Tests:** 226
- **Overall Coverage:** 97%
- **Modules with 100% Coverage:** 6 out of 10

## Development

### Code Structure

```
platform/mellanox/fw-manager/
├── mellanox_fw_manager/       # Source code
│   ├── __init__.py
│   ├── main.py                # CLI entry point
│   ├── firmware_coordinator.py
│   ├── firmware_base.py
│   ├── spectrum_manager.py
│   ├── bluefield_manager.py
│   ├── asic_manager.py
│   ├── error_handler.py
│   ├── platform_utils.py
│   └── fw_manager.py
├── tests/                     # Test suite
│   ├── test_main.py
│   ├── test_spectrum_manager.py
│   ├── test_bluefield_manager.py
│   ├── test_platform_detection.py
│   ├── test_firmware_coordinator.py
│   ├── test_error_handler.py
│   ├── test_asic_manager.py
│   └── test_*.py
├── setup.py                   # Package configuration
├── pytest.ini                 # Test configuration
└── README.md                  # This file
```

### Coding Standards

- **Style Guide:** PEP 8
- **Type Hints:** Required for all public APIs
- **Docstrings:** Google style for all modules, classes, and functions
- **Line Length:** 120 characters maximum
- **Imports:** Organized and sorted
- **Logging:** Use utility function `run_command()` for subprocess execution

### Adding New ASIC Support

1. Create new manager class inheriting from `FirmwareManagerBase`
2. Implement required abstract methods:
   - `_get_mst_device_type()`
   - `_get_available_firmware_version()`
   - `get_firmware_file_map()`
   - `run_firmware_update()`
3. Add ASIC detection in `platform_utils.py`
4. Update factory function in `fw_manager.py`
5. Add comprehensive unit tests

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Ensure all tests pass: `python3 -m unittest discover tests`
5. Check code style and linting
6. Submit pull request with detailed description

## Return Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | `EXIT_SUCCESS` | Operation completed successfully |
| 1 | `EXIT_FAILURE` | Operation failed completely |
| 2 | `FW_ALREADY_UPDATED_FAILURE` | Firmware already updated (reactivation needed) |
| 10 | `FW_UPGRADE_IS_REQUIRED` | Upgrade required (dry-run mode) |

### CLI Exit Codes

```bash
mlnx-fw-manager --dry-run
echo $?  # 10 = upgrade needed, 0 = up to date, 1 = error

mlnx-fw-manager --upgrade
echo $?  # 0 = success, 1 = failure, 2 = partial failure
```

## Error Handling

### Error Flow

1. **Detection**: Errors caught during upgrade process
2. **Storage**: Details written to persistent storage
3. **Reporting**: Error information available via CLI/API
4. **Recovery**: Automatic cleanup on successful retry
5. **Prevention**: Skip ASICs with previous failures

### Common Error Scenarios

#### Device Busy
```
Error: Failed to burn firmware with return code 1: Device busy
```
**Solution:** Clear semaphore with `--clear-semaphore`

#### Firmware File Not Found
```
Error: Firmware file not found: /etc/mlnx/fw-SPC3.mfa
```
**Solution:** Verify firmware files exist in `/etc/mlnx/`

#### MST Device Not Found
```
Error: Could not find MST device for ASIC 0
```
**Solution:** Verify MST service is running and PCI IDs are correct

### Debug Mode

Enable verbose logging to troubleshoot issues:

```bash
mlnx-fw-manager --verbose --nosyslog
```

This will:
- Show all command executions
- Display detailed error messages
- Print MFT diagnostic information
- Log to console instead of syslog

## Environment Variables

### MFT Debug Flags (Verbose Mode)

When `--verbose` is used, the following environment variables are set:

- `FLASH_ACCESS_DEBUG=1` - Enable flash access debugging
- `FW_COMPS_DEBUG=1` - Enable firmware components debugging

## Platform Integration

### SONiC Integration

The utility integrates with SONiC through:

1. **Platform Detection**: Reads `/host/machine.conf`
2. **ASIC Configuration**: Parses platform-specific `asic.conf`
3. **Image Management**: Uses `sonic-installer` for next image firmware
4. **Logging**: Writes to syslog via `/dev/log`

### Systemd Integration

Can be integrated as a systemd service for automatic upgrades:

```ini
[Unit]
Description=Mellanox Firmware Manager
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/mlnx-fw-manager --upgrade
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Check Firmware Versions

```bash
# Current firmware version
mlxfwmanager --query

# Available firmware version
mlxfwmanager --list-content -i /etc/mlnx/fw-SPC3.mfa
```

### Check MST Devices

```bash
# List MST devices
mst status -v

# Query specific device
mlxfwmanager --query -d /dev/mst/mt53104_pci_cr0
```

### Clear Hardware Semaphore

```bash
# Manual semaphore clear
flint -d /dev/mst/mt53104_pci_cr0 --clear_semaphore

# Or use utility flag
mlnx-fw-manager --clear-semaphore --upgrade
```

### View Logs

```bash
# View syslog
journalctl -u mellanox-fw-manager

# Or grep syslog
grep "mellanox-fw-manager" /var/log/syslog
```


---

**Project Status:** Active Development
**Python Version:** 3.8+
**Test Coverage:** 97%
**Last Updated:** 2025-01-15
