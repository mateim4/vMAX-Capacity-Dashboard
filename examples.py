"""
Example usage script demonstrating different ways to use the VmaxCapacityCollector.

This script shows:
1. Basic configuration and connection
2. Individual level collection
3. Complete snapshot collection
4. Custom data processing
5. Export options
"""

from config import load_config
from vmax_collector import VmaxCapacityCollector
import json


def example_1_basic_usage():
    """Example 1: Basic usage with complete snapshot."""
    print("=== Example 1: Basic Complete Collection ===\n")
    
    # Load configuration
    config = load_config("config.json")
    
    # Create collector with context manager (auto-cleanup)
    with VmaxCapacityCollector(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        array_id=config.array_id
    ) as collector:
        
        # Get complete snapshot
        snapshot = collector.get_all_capacity_data(config.array_id)
        
        # Print summary
        print(f"Array: {snapshot.array_id}")
        print(f"Total Volumes: {snapshot.total_volumes}")
        print(f"System Utilization: {snapshot.system_capacity.utilization_percent:.2f}%")


def example_2_individual_levels():
    """Example 2: Collect individual levels separately."""
    print("\n=== Example 2: Individual Level Collection ===\n")
    
    config = load_config("config.json")
    
    with VmaxCapacityCollector(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password
    ) as collector:
        
        # Collect only system-level data
        system = collector.get_system_summary(config.array_id)
        print(f"System Used: {system.effective_used_capacity_gb:,.2f} GB")
        
        # Collect only SRP data
        srps = collector.get_srp_capacity(config.array_id)
        print(f"Number of SRPs: {len(srps)}")
        for srp in srps:
            print(f"  {srp.srp_id}: {srp.utilization_percent:.2f}% utilized")
        
        # Collect only Storage Groups (without volumes)
        storage_groups = collector.get_all_storage_groups(config.array_id)
        print(f"Number of Storage Groups: {len(storage_groups)}")
        
        # Note: Can skip volume collection for faster execution
        # volumes = collector.get_all_volumes(config.array_id)


def example_3_filtered_collection():
    """Example 3: Filter and analyze specific data."""
    print("\n=== Example 3: Filtered Analysis ===\n")
    
    config = load_config("config.json")
    
    with VmaxCapacityCollector(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password
    ) as collector:
        
        # Get all storage groups
        storage_groups = collector.get_all_storage_groups(config.array_id)
        
        # Filter by service level
        diamond_sgs = [
            sg for sg in storage_groups 
            if sg.service_level == 'Diamond'
        ]
        
        print(f"Diamond tier storage groups: {len(diamond_sgs)}")
        
        # Find largest storage groups
        top_5 = sorted(storage_groups, key=lambda x: x.capacity_gb, reverse=True)[:5]
        
        print("\nTop 5 Largest Storage Groups:")
        for i, sg in enumerate(top_5, 1):
            print(f"{i}. {sg.storage_group_id}: {sg.capacity_gb:,.2f} GB")


def example_4_custom_export():
    """Example 4: Custom data export formats."""
    print("\n=== Example 4: Custom Export ===\n")
    
    config = load_config("config.json")
    
    with VmaxCapacityCollector(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password
    ) as collector:
        
        snapshot = collector.get_all_capacity_data(config.array_id)
        
        # Create custom summary report
        report = {
            'report_metadata': {
                'array_id': snapshot.array_id,
                'collection_time': snapshot.collection_timestamp,
                'report_type': 'Capacity Summary'
            },
            'system_summary': {
                'total_capacity_gb': snapshot.system_capacity.total_usable_capacity_gb,
                'used_capacity_gb': snapshot.system_capacity.effective_used_capacity_gb,
                'free_capacity_gb': snapshot.system_capacity.free_capacity_gb,
                'utilization_percent': round(snapshot.system_capacity.utilization_percent, 2)
            },
            'srp_summary': [
                {
                    'srp_id': srp.srp_id,
                    'total_gb': srp.total_managed_space_gb,
                    'used_gb': srp.used_capacity_gb,
                    'utilization_percent': round(srp.utilization_percent, 2)
                }
                for srp in snapshot.srp_capacities
            ],
            'storage_groups': {
                'total_count': snapshot.total_storage_groups,
                'total_capacity_gb': sum(sg.capacity_gb for sg in snapshot.storage_group_capacities),
                'by_service_level': {}
            },
            'volumes': {
                'total_count': snapshot.total_volumes,
                'total_capacity_gb': sum(v.capacity_gb for v in snapshot.volume_capacities),
                'average_size_gb': sum(v.capacity_gb for v in snapshot.volume_capacities) / len(snapshot.volume_capacities) if snapshot.volume_capacities else 0
            }
        }
        
        # Group storage groups by service level
        for sg in snapshot.storage_group_capacities:
            slo = sg.service_level or 'None'
            if slo not in report['storage_groups']['by_service_level']:
                report['storage_groups']['by_service_level'][slo] = {
                    'count': 0,
                    'total_capacity_gb': 0
                }
            report['storage_groups']['by_service_level'][slo]['count'] += 1
            report['storage_groups']['by_service_level'][slo]['total_capacity_gb'] += sg.capacity_gb
        
        # Export to JSON
        output_file = f"custom_report_{config.array_id}.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Custom report exported to: {output_file}")


def example_5_error_handling():
    """Example 5: Proper error handling."""
    print("\n=== Example 5: Error Handling ===\n")
    
    from vmax_collector import ConnectionError, AuthenticationError, DataCollectionError
    
    try:
        config = load_config("config.json")
        
        with VmaxCapacityCollector(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password
        ) as collector:
            
            # Attempt collection with specific error handling
            try:
                system = collector.get_system_summary(config.array_id)
                print(f"✓ System data collected successfully")
            except DataCollectionError as e:
                print(f"✗ Failed to collect system data: {e}")
                # Continue with other collections
            
            try:
                srps = collector.get_srp_capacity(config.array_id)
                print(f"✓ SRP data collected successfully")
            except DataCollectionError as e:
                print(f"✗ Failed to collect SRP data: {e}")
    
    except ConnectionError as e:
        print(f"Connection Error: {e}")
        print("Check network connectivity and Unisphere availability")
    
    except AuthenticationError as e:
        print(f"Authentication Error: {e}")
        print("Verify username and password")
    
    except Exception as e:
        print(f"Unexpected Error: {e}")


if __name__ == "__main__":
    # Run examples (comment out as needed)
    
    # example_1_basic_usage()
    # example_2_individual_levels()
    # example_3_filtered_collection()
    # example_4_custom_export()
    # example_5_error_handling()
    
    print("\nUncomment the example functions above to run them.")
    print("Make sure config.json is configured with valid credentials first.")
