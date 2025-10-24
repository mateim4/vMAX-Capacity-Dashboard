"""
VMAX/PowerMax Capacity Dashboard - Main Application

This is the main entry point for the capacity monitoring application.
It demonstrates usage of the VmaxCapacityCollector and provides
examples of different output formats.
"""

import sys
import json
import logging
from typing import Optional
from pathlib import Path

from config import load_config, load_config_from_env, UnisphereConfig
from vmax_collector import (
    VmaxCapacityCollector,
    ConnectionError,
    AuthenticationError,
    DataCollectionError
)
from data_models import CapacitySnapshot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_capacity_summary(snapshot: CapacitySnapshot) -> None:
    """
    Print a human-readable summary of capacity data.
    
    Args:
        snapshot: CapacitySnapshot object to summarize
    """
    print("\n" + "=" * 80)
    print(f"CAPACITY DASHBOARD - Array: {snapshot.array_id}")
    print(f"Collection Time: {snapshot.collection_timestamp}")
    print("=" * 80)
    
    # System-level summary
    sys_cap = snapshot.system_capacity
    print(f"\n📊 SYSTEM CAPACITY")
    print(f"  Total Usable:     {sys_cap.total_usable_capacity_gb:,.2f} GB")
    print(f"  Used:             {sys_cap.effective_used_capacity_gb:,.2f} GB")
    print(f"  Free:             {sys_cap.free_capacity_gb:,.2f} GB")
    print(f"  Utilization:      {sys_cap.utilization_percent:.2f}%")
    print(f"  Subscribed:       {sys_cap.subscribed_capacity_gb:,.2f} GB")
    
    # SRP summary
    print(f"\n💾 STORAGE RESOURCE POOLS ({snapshot.total_srps})")
    for srp in snapshot.srp_capacities:
        print(f"  {srp.srp_id}:")
        print(f"    Total:          {srp.total_managed_space_gb:,.2f} GB")
        print(f"    Used:           {srp.used_capacity_gb:,.2f} GB ({srp.utilization_percent:.2f}%)")
        print(f"    Subscription:   {srp.subscription_percent:.2f}%")
    
    # Storage Group summary
    print(f"\n📦 STORAGE GROUPS ({snapshot.total_storage_groups})")
    total_sg_capacity = sum(sg.capacity_gb for sg in snapshot.storage_group_capacities)
    print(f"  Total Allocated:  {total_sg_capacity:,.2f} GB")
    
    # Show top 10 largest storage groups
    top_sgs = sorted(
        snapshot.storage_group_capacities,
        key=lambda x: x.capacity_gb,
        reverse=True
    )[:10]
    
    if top_sgs:
        print(f"  Top 10 by Size:")
        for i, sg in enumerate(top_sgs, 1):
            print(f"    {i}. {sg.storage_group_id}: {sg.capacity_gb:,.2f} GB ({sg.num_volumes} vols)")
    
    # Volume summary
    print(f"\n💿 VOLUMES ({snapshot.total_volumes})")
    total_vol_capacity = sum(v.capacity_gb for v in snapshot.volume_capacities)
    print(f"  Total Capacity:   {total_vol_capacity:,.2f} GB")
    
    if snapshot.volume_capacities:
        avg_size = total_vol_capacity / snapshot.total_volumes
        print(f"  Average Size:     {avg_size:,.2f} GB")
    
    print("\n" + "=" * 80 + "\n")


def export_to_json(snapshot: CapacitySnapshot, output_file: str) -> None:
    """
    Export capacity data to JSON file.
    
    Args:
        snapshot: CapacitySnapshot object to export
        output_file: Path to output JSON file
    """
    try:
        # Convert dataclasses to dictionaries for JSON serialization
        data = {
            'array_id': snapshot.array_id,
            'collection_timestamp': snapshot.collection_timestamp,
            'system_capacity': {
                'array_id': snapshot.system_capacity.array_id,
                'timestamp': snapshot.system_capacity.timestamp,
                'effective_used_capacity_gb': snapshot.system_capacity.effective_used_capacity_gb,
                'max_effective_capacity_gb': snapshot.system_capacity.max_effective_capacity_gb,
                'subscribed_capacity_gb': snapshot.system_capacity.subscribed_capacity_gb,
                'total_usable_capacity_gb': snapshot.system_capacity.total_usable_capacity_gb,
                'free_capacity_gb': snapshot.system_capacity.free_capacity_gb,
                'utilization_percent': snapshot.system_capacity.utilization_percent
            },
            'srp_capacities': [
                {
                    'array_id': srp.array_id,
                    'srp_id': srp.srp_id,
                    'timestamp': srp.timestamp,
                    'used_capacity_gb': srp.used_capacity_gb,
                    'subscribed_capacity_gb': srp.subscribed_capacity_gb,
                    'total_managed_space_gb': srp.total_managed_space_gb,
                    'free_capacity_gb': srp.free_capacity_gb,
                    'utilization_percent': srp.utilization_percent,
                    'subscription_percent': srp.subscription_percent
                }
                for srp in snapshot.srp_capacities
            ],
            'storage_group_capacities': [
                {
                    'array_id': sg.array_id,
                    'storage_group_id': sg.storage_group_id,
                    'timestamp': sg.timestamp,
                    'capacity_gb': sg.capacity_gb,
                    'num_volumes': sg.num_volumes,
                    'service_level': sg.service_level,
                    'srp_name': sg.srp_name,
                    'compression_enabled': sg.compression_enabled
                }
                for sg in snapshot.storage_group_capacities
            ],
            'volume_capacities': [
                {
                    'array_id': vol.array_id,
                    'volume_id': vol.volume_id,
                    'volume_identifier': vol.volume_identifier,
                    'timestamp': vol.timestamp,
                    'capacity_gb': vol.capacity_gb,
                    'allocated_percent': vol.allocated_percent,
                    'storage_groups': vol.storage_groups,
                    'wwn': vol.wwn,
                    'emulation_type': vol.emulation_type
                }
                for vol in snapshot.volume_capacities
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Capacity data exported to: {output_file}")
        print(f"✅ Data exported to: {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to export to JSON: {e}")
        print(f"❌ Export failed: {e}")


def main():
    """
    Main application entry point.
    
    Demonstrates three usage patterns:
    1. Load configuration from file
    2. Connect to Unisphere
    3. Collect capacity data
    4. Display and export results
    """
    print("VMAX/PowerMax Capacity Dashboard")
    print("=" * 80)
    
    try:
        # Step 1: Load configuration
        # Try config file first, fall back to environment variables
        config: Optional[UnisphereConfig] = None
        
        if Path("config.json").exists():
            logger.info("Loading configuration from config.json")
            config = load_config("config.json")
        else:
            logger.info("config.json not found, checking environment variables")
            try:
                config = load_config_from_env()
            except ValueError as e:
                print("\n❌ Configuration Error:")
                print(f"   {e}")
                print("\nPlease either:")
                print("  1. Create a config.json file (see config.example.json)")
                print("  2. Set environment variables (UNISPHERE_HOST, UNISPHERE_USER, etc.)")
                sys.exit(1)
        
        print(f"\n✅ Configuration loaded")
        print(f"   Unisphere: {config.host}:{config.port}")
        print(f"   Array ID:  {config.array_id}")
        print(f"   User:      {config.username}")
        
        # Step 2: Initialize collector and connect
        print(f"\n🔌 Connecting to Unisphere...")
        
        # Use context manager to ensure connection is closed
        with VmaxCapacityCollector(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            verify_ssl=config.verify_ssl,
            array_id=config.array_id
        ) as collector:
            
            print(f"✅ Connected successfully\n")
            
            # Step 3: Collect capacity data
            print(f"📊 Collecting capacity data (this may take several minutes)...\n")
            
            snapshot = collector.get_all_capacity_data(config.array_id)
            
            # Step 4: Display results
            print_capacity_summary(snapshot)
            
            # Step 5: Export to JSON (optional)
            output_file = f"capacity_report_{config.array_id}_{snapshot.collection_timestamp.replace(':', '-')}.json"
            export_to_json(snapshot, output_file)
            
            print("✅ Collection completed successfully!")
    
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        print(f"\n❌ Connection Error:")
        print(f"   {e}")
        print("\nTroubleshooting:")
        print("  - Verify Unisphere is running and accessible")
        print("  - Check network connectivity to port 8443")
        print("  - Verify hostname/IP address is correct")
        sys.exit(1)
    
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        print(f"\n❌ Authentication Error:")
        print(f"   {e}")
        print("\nTroubleshooting:")
        print("  - Verify username and password are correct")
        print("  - Ensure user has 'Monitor' role in Unisphere")
        print("  - Check if account is locked or expired")
        sys.exit(1)
    
    except DataCollectionError as e:
        logger.error(f"Data collection failed: {e}")
        print(f"\n❌ Data Collection Error:")
        print(f"   {e}")
        print("\nTroubleshooting:")
        print("  - Check if array ID is correct")
        print("  - Verify user has sufficient permissions")
        print("  - Review logs for detailed error information")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection interrupted by user")
        logger.info("Collection interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected Error:")
        print(f"   {e}")
        print("\nPlease check the logs for more details")
        sys.exit(1)


if __name__ == "__main__":
    main()
