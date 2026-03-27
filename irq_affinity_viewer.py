#!/usr/bin/env python3
"""
irq-affinity-viewer: Tool to check IRQ affinity settings on Linux.
Displays which CPUs are assigned to handle specific hardware interrupts.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set


PROC_IRQ_PATH = "/proc/irq"
PROC_CPUINFO_PATH = "/proc/cpuinfo"


def get_cpu_count() -> int:
    """Get the number of available CPUs from /proc/cpuinfo."""
    try:
        with open(PROC_CPUINFO_PATH, "r") as f:
            return len([line for line in f if line.startswith("processor")])
    except (FileNotFoundError, PermissionError):
        return os.cpu_count() or 1


def hex_to_cpu_set(hex_mask: str, cpu_count: int) -> Set[int]:
    """Convert a hex affinity mask to a set of CPU numbers."""
    try:
        mask = int(hex_mask, 16)
    except ValueError:
        return set()
    
    cpus = set()
    for cpu in range(cpu_count):
        if mask & (1 << cpu):
            cpus.add(cpu)
    return cpus


def parse_affinity_list(affinity_str: str) -> Set[int]:
    """Parse CPU list format like '0-3,5,7-8' into a set of CPU numbers."""
    cpus = set()
    parts = affinity_str.strip().split(",")
    
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start_cpu = int(start.strip())
                end_cpu = int(end.strip())
                cpus.update(range(start_cpu, end_cpu + 1))
            except ValueError:
                continue
        else:
            try:
                cpus.add(int(part))
            except ValueError:
                continue
    
    return cpus


def get_irq_affinity(irq_num: int, cpu_count: int) -> Optional[Set[int]]:
    """Get the CPU affinity for a specific IRQ number."""
    irq_path = Path(PROC_IRQ_PATH) / str(irq_num)
    
    affinity_list_path = irq_path / "smp_affinity_list"
    affinity_path = irq_path / "smp_affinity"
    
    if affinity_list_path.exists():
        try:
            with open(affinity_list_path, "r") as f:
                affinity_str = f.read().strip()
                return parse_affinity_list(affinity_str)
        except (FileNotFoundError, PermissionError, ValueError):
            pass
    
    if affinity_path.exists():
        try:
            with open(affinity_path, "r") as f:
                hex_mask = f.read().strip()
                return hex_to_cpu_set(hex_mask, cpu_count)
        except (FileNotFoundError, PermissionError, ValueError):
            pass
    
    return None


def get_irq_name(irq_num: int) -> str:
    """Get the name/description of an IRQ from /proc/interrupts."""
    try:
        with open("/proc/interrupts", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        irq_id = int(parts[0].strip())
                        if irq_id == irq_num:
                            name_parts = parts[1].strip().split()
                            return " ".join(name_parts) if name_parts else "unknown"
                    except ValueError:
                        continue
    except (FileNotFoundError, PermissionError):
        pass
    return "unknown"


def list_all_irqs() -> List[int]:
    """List all available IRQ numbers from /proc/irq."""
    irq_nums = []
    try:
        for entry in os.listdir(PROC_IRQ_PATH):
            if entry.isdigit():
                irq_nums.append(int(entry))
    except (FileNotFoundError, PermissionError):
        pass
    return sorted(irq_nums)


def get_irq_type(irq_num: int) -> str:
    """Get the trigger type for an IRQ."""
    irq_path = Path(PROC_IRQ_PATH) / str(irq_num)
    type_path = irq_path / "type"
    
    type_map = {
        "0": "none",
        "1": "edge-rising",
        "2": "level-high",
        "3": "edge-rising+level-high",
        "4": "edge-falling",
        "8": "level-low",
    }
    
    try:
        with open(type_path, "r") as f:
            type_val = f.read().strip()
            return type_map.get(type_val, f"type-{type_val}")
    except (FileNotFoundError, PermissionError, ValueError):
        return "unknown"


def format_cpu_set(cpus: Set[int], cpu_count: int) -> str:
    """Format a CPU set as a readable string."""
    if not cpus:
        return "none"
    
    if cpus == set(range(cpu_count)):
        return "all"
    
    sorted_cpus = sorted(cpus)
    ranges = []
    start = sorted_cpus[0]
    end = sorted_cpus[0]
    
    for cpu in sorted_cpus[1:]:
        if cpu == end + 1:
            end = cpu
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = cpu
            end = cpu
    
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ",".join(ranges)


def display_irq_info(irq_num: int, cpu_count: int, verbose: bool = False) -> None:
    """Display detailed information about a specific IRQ."""
    affinity = get_irq_affinity(irq_num, cpu_count)
    name = get_irq_name(irq_num)
    
    print(f"IRQ {irq_num}: {name}")
    
    if affinity is not None:
        cpu_str = format_cpu_set(affinity, cpu_count)
        print(f"  Affinity: {cpu_str}")
        print(f"  CPUs: {sorted(affinity)}")
    else:
        print(f"  Affinity: unable to read")
    
    if verbose:
        irq_type = get_irq_type(irq_num)
        print(f"  Type: {irq_type}")
        
        irq_path = Path(PROC_IRQ_PATH) / str(irq_num)
        spurious_path = irq_path / "spurious_count"
        if spurious_path.exists():
            try:
                with open(spurious_path, "r") as f:
                    spurious = f.read().strip()
                    print(f"  Spurious count: {spurious}")
            except (FileNotFoundError, PermissionError):
                pass
    
    print()


def search_irqs_by_name(pattern: str, cpu_count: int) -> None:
    """Search and display IRQs matching a name pattern."""
    irq_nums = list_all_irqs()
    found = False
    
    for irq_num in irq_nums:
        name = get_irq_name(irq_num)
        if pattern.lower() in name.lower():
            display_irq_info(irq_num, cpu_count)
            found = True
    
    if not found:
        print(f"No IRQs found matching '{pattern}'")


def show_summary(cpu_count: int) -> None:
    """Show a summary of IRQ distribution across CPUs."""
    irq_nums = list_all_irqs()
    cpu_irq_count: Dict[int, int] = {cpu: 0 for cpu in range(cpu_count)}
    total = 0
    
    for irq_num in irq_nums:
        affinity = get_irq_affinity(irq_num, cpu_count)
        if affinity:
            for cpu in affinity:
                if cpu in cpu_irq_count:
                    cpu_irq_count[cpu] += 1
                    total += 1
    
    print("IRQ Distribution Summary")
    print("=" * 40)
    print(f"Total IRQs: {len(irq_nums)}")
    print(f"Total CPUs: {cpu_count}")
    print()
    
    for cpu in sorted(cpu_irq_count.keys()):
        count = cpu_irq_count[cpu]
        bar = "#" * min(count, 50)
        print(f"CPU {cpu:3d}: {count:4d} IRQs {bar}")
    
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check IRQ affinity settings on Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Show all IRQs and their affinity
  %(prog)s -s                 Show summary of IRQ distribution
  %(prog)s -i 12              Show info for specific IRQ
  %(prog)s -n eth             Search IRQs by name pattern
  %(prog)s -v -i 12           Verbose output for specific IRQ
        """
    )
    
    parser.add_argument(
        "-i", "--irq",
        type=int,
        help="Show affinity for specific IRQ number"
    )
    parser.add_argument(
        "-n", "--name",
        type=str,
        help="Search IRQs by name pattern"
    )
    parser.add_argument(
        "-s", "--summary",
        action="store_true",
        help="Show summary of IRQ distribution"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    args = parser.parse_args()
    cpu_count = get_cpu_count()
    
    if args.irq is not None:
        display_irq_info(args.irq, cpu_count, args.verbose)
    elif args.name:
        search_irqs_by_name(args.name, cpu_count)
    elif args.summary:
        show_summary(cpu_count)
    else:
        irq_nums = list_all_irqs()
        if not irq_nums:
            print("No IRQs found or unable to access /proc/irq")
            return 1
        
        print(f"Found {len(irq_nums)} IRQs on {cpu_count} CPU(s)")
        print("=" * 50)
        print()
        
        for irq_num in irq_nums:
            display_irq_info(irq_num, cpu_count, args.verbose)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
