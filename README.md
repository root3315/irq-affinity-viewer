# irq-affinity-viewer

Tool to check IRQ affinity settings on Linux. Because sometimes you need to know which CPU is handling your network interrupts.

## What is this?

IRQ affinity determines which CPU cores handle hardware interrupts. On multi-core systems, you might want to pin certain IRQs to specific CPUs for performance reasons, or just understand how your system is distributing interrupt load.

This tool reads from `/proc/irq` and shows you:
- Which IRQs exist on your system
- What each IRQ is for (device name)
- Which CPUs are assigned to handle each IRQ
- A summary of IRQ distribution across CPUs

## Why I wrote this

I kept needing to check IRQ affinity manually by reading `/proc/irq/*/smp_affinity_list` and cross-referencing with `/proc/interrupts`. That's annoying. This script does it in one go.

Also useful for debugging why one CPU core is at 100% while others are idle - might be all your network IRQs are pinned to core 0.

## Requirements

- Python 3.6+
- Linux (obviously, since it reads `/proc/irq`)
- Root or appropriate permissions to read `/proc/irq`

No external dependencies. Just stdlib.

## Usage

Show all IRQs and their affinity:
```bash
python3 irq_affinity_viewer.py
```

Show summary of IRQ distribution:
```bash
python3 irq_affinity_viewer.py --summary
```

Check a specific IRQ:
```bash
python3 irq_affinity_viewer.py --irq 12
```

Search IRQs by name (e.g., find all network-related):
```bash
python3 irq_affinity_viewer.py --name eth
python3 irq_affinity_viewer.py --name nvme
```

Verbose mode with extra info:
```bash
python3 irq_affinity_viewer.py --verbose --irq 12
```

Output in JSON format:
```bash
python3 irq_affinity_viewer.py --json
python3 irq_affinity_viewer.py --json --irq 12
python3 irq_affinity_viewer.py --json --summary
python3 irq_affinity_viewer.py --json --name eth
```

## Output format

### Text output

Each IRQ shows:
- IRQ number and device name
- Affinity as CPU list (e.g., `0-3` or `0,2,4`)
- Actual CPU set as Python list

Example:
```
IRQ 48: eth0-TxRx-0
  Affinity: 0
  CPUs: [0]

IRQ 49: eth0-TxRx-1
  Affinity: 1
  CPUs: [1]
```

### JSON output

JSON output includes structured data suitable for scripting or integration:

```json
{
  "irqs": [
    {
      "irq": 48,
      "name": "eth0-TxRx-0",
      "affinity": [0],
      "affinity_readable": "0"
    },
    {
      "irq": 49,
      "name": "eth0-TxRx-1",
      "affinity": [1],
      "affinity_readable": "1"
    }
  ],
  "count": 2
}
```

Summary JSON:
```json
{
  "total_irqs": 256,
  "total_cpus": 8,
  "distribution": {
    "0": 32,
    "1": 32,
    "2": 32,
    "3": 32,
    "4": 32,
    "5": 32,
    "6": 32,
    "7": 32
  }
}
```

## Notes

- Reads `smp_affinity_list` first (human-readable), falls back to `smp_affinity` (hex mask)
- Some IRQs might not have readable affinity (kernel internal stuff)
- You might need `sudo` to see all IRQs depending on your system

## License

Do whatever you want with it.
