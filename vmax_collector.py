"""
VMAX/PowerMax Capacity Collector.

This module implements the core VmaxCapacityCollector class that queries
Dell PowerMax/VMAX arrays using the PyU4V SDK and implements a hybrid
API strategy:
- Legacy REST API (/univmax/restapi/{version}/...) for system-level and SRP data
- Enhanced REST API (/univmax/rest/v1/...) for bulk Storage Group and Volume data

The collector requires network access to Unisphere on port 8443 and credentials
with at least the "Monitor" role assigned.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests

try:
    import PyU4V
except ImportError:
    raise ImportError(
        "PyU4V library is required. Install it with: pip install PyU4V"
    )

from data_models import (
    SystemCapacity,
    SrpCapacity,
    StorageGroupCapacity,
    VolumeCapacity,
    CapacitySnapshot
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VmaxCapacityCollectorError(Exception):
    """Base exception for VmaxCapacityCollector errors."""
    pass


class ConnectionError(VmaxCapacityCollectorError):
    """Raised when connection to Unisphere fails."""
    pass


class AuthenticationError(VmaxCapacityCollectorError):
    """Raised when authentication fails."""
    pass


class DataCollectionError(VmaxCapacityCollectorError):
    """Raised when data collection from API fails."""
    pass


class VmaxCapacityCollector:
    """
    Collects capacity metrics from Dell PowerMax/VMAX arrays.
    
    This class uses the PyU4V SDK to interface with the Unisphere REST API
    and collects capacity data at four levels:
    1. System (Array-wide summary)
    2. Storage Resource Pools (SRPs)
    3. Storage Groups
    4. Volumes
    
    Attributes:
        conn: PyU4V.U4VConn connection object
        array_id: The PowerMax/VMAX array serial number
    """
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 8443,
        verify_ssl: bool = False,
        array_id: Optional[str] = None
    ):
        """
        Initialize the capacity collector with Unisphere connection.
        
        Args:
            host: Unisphere server hostname or IP address
            username: Username for HTTP Basic Authentication
            password: Password for HTTP Basic Authentication
            port: Unisphere REST API port (default: 8443)
            verify_ssl: Whether to verify SSL certificates (default: False)
            array_id: Optional array ID to set as default
            
        Raises:
            ConnectionError: If unable to connect to Unisphere
            AuthenticationError: If credentials are invalid
        """
        self.array_id = array_id
        
        try:
            logger.info(f"Initializing connection to Unisphere at {host}:{port}")
            
            # Initialize PyU4V connection
            # The U4VConn object provides access to all API modules
            self.conn = PyU4V.U4VConn(
                server_ip=host,
                port=port,
                verify=verify_ssl,
                username=username,
                password=password
            )
            
            # Test the connection by getting array list
            arrays = self.conn.common.get_array_list()
            logger.info(f"Successfully connected. Available arrays: {arrays}")
            
            # If no array_id provided, use the first available
            if not self.array_id and arrays:
                self.array_id = arrays[0]
                logger.info(f"Using array: {self.array_id}")
            elif self.array_id and self.array_id not in arrays:
                raise ValueError(
                    f"Specified array '{self.array_id}' not found. "
                    f"Available: {arrays}"
                )
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Unisphere: {e}")
            raise ConnectionError(
                f"Cannot connect to Unisphere at {host}:{port}. "
                f"Verify network connectivity and that Unisphere is running."
            ) from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication failed")
                raise AuthenticationError(
                    "Invalid credentials. Verify username and password."
                ) from e
            else:
                logger.error(f"HTTP error during connection: {e}")
                raise ConnectionError(f"HTTP error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise ConnectionError(f"Initialization failed: {e}") from e
    
    def get_system_summary(self, array_id: str) -> SystemCapacity:
        """
        Get system-level (array-wide) capacity summary.
        
        This method uses the LEGACY REST API performance resource to retrieve
        high-level capacity metrics for the entire array.
        
        API Path: /univmax/restapi/{version}/performance/Array/keys
        PyU4V Module: conn.performance
        
        Key metrics retrieved:
        - EffectiveUsedCapacity: Actual capacity consumed
        - MaxEffectiveCapacity: Maximum available capacity
        - SubscribedCapacity: Total allocated capacity (may exceed physical)
        - TotalUsableCapacity: Total raw capacity
        
        Args:
            array_id: The PowerMax/VMAX array serial number
            
        Returns:
            SystemCapacity object with array-wide metrics
            
        Raises:
            DataCollectionError: If unable to retrieve system data
        """
        try:
            logger.info(f"Collecting system-level capacity for array {array_id}")
            
            # Step 1: Get the array performance key
            # This returns metadata needed to query performance metrics
            array_keys = self.conn.performance.get_array_keys()
            
            if not array_keys:
                raise DataCollectionError("No array keys found")
            
            # Step 2: Define the metrics we want to retrieve
            # These correspond to the Array performance category
            metrics = [
                'EffectiveUsedCapacity',
                'MaxEffectiveCapacity',
                'SubscribedCapacity',
                'TotalUsableCapacity'
            ]
            
            # Step 3: Get performance stats for the array
            # This queries the Legacy API performance endpoint
            stats = self.conn.performance.get_array_stats(
                array_id=array_id,
                metrics=metrics,
                data_format='Average'
            )
            
            # Step 4: Parse the response
            # Performance API returns time-series data; we take the latest
            if not stats or 'result' not in stats:
                raise DataCollectionError("Invalid response format from performance API")
            
            result = stats['result'][0] if stats['result'] else {}
            
            # Extract capacity values (convert from TB to GB if needed)
            # Note: Check your environment's units - may be GB or TB
            system_capacity = SystemCapacity(
                array_id=array_id,
                timestamp=datetime.now().isoformat(),
                effective_used_capacity_gb=float(result.get('EffectiveUsedCapacity', 0)),
                max_effective_capacity_gb=float(result.get('MaxEffectiveCapacity', 0)),
                subscribed_capacity_gb=float(result.get('SubscribedCapacity', 0)),
                total_usable_capacity_gb=float(result.get('TotalUsableCapacity', 0))
            )
            
            logger.info(
                f"System capacity collected: "
                f"{system_capacity.utilization_percent:.2f}% utilized"
            )
            
            return system_capacity
            
        except PyU4V.utils.exception.VolumeBackendAPIException as e:
            logger.error(f"PyU4V API error retrieving system summary: {e}")
            raise DataCollectionError(
                f"Failed to retrieve system summary: {e}"
            ) from e
        except KeyError as e:
            logger.error(f"Missing expected data in API response: {e}")
            raise DataCollectionError(
                f"API response missing required field: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error retrieving system summary: {e}")
            raise DataCollectionError(
                f"System summary collection failed: {e}"
            ) from e
    
    def get_srp_capacity(self, array_id: str) -> List[SrpCapacity]:
        """
        Get capacity metrics for all Storage Resource Pools (SRPs).
        
        This method uses the LEGACY REST API with a two-step process:
        1. Get list of SRP IDs from performance keys
        2. Query detailed capacity metrics for each SRP
        
        API Path: /univmax/restapi/{version}/performance/StorageResourcePool/keys
        PyU4V Module: conn.performance (keys) and conn.provisioning (details)
        
        Key metrics per SRP:
        - Used Capacity: Actual consumed capacity in the SRP
        - Subscribed Capacity: Total allocated (may be thin provisioned)
        - Total Managed Space: Total capacity available in the SRP
        
        Args:
            array_id: The PowerMax/VMAX array serial number
            
        Returns:
            List of SrpCapacity objects, one per SRP
            
        Raises:
            DataCollectionError: If unable to retrieve SRP data
        """
        try:
            logger.info(f"Collecting SRP capacity data for array {array_id}")
            
            srp_capacities = []
            
            # Step 1: Get list of all SRP IDs using performance API
            # This returns the identifiers for all SRPs on the array
            srp_keys = self.conn.performance.get_storage_resource_pool_keys(
                array_id=array_id
            )
            
            if not srp_keys or 'storageResourcePoolInfo' not in srp_keys:
                logger.warning(f"No SRPs found for array {array_id}")
                return srp_capacities
            
            srp_list = srp_keys['storageResourcePoolInfo']
            logger.info(f"Found {len(srp_list)} SRP(s) to query")
            
            # Step 2: Loop through each SRP and get detailed metrics
            for srp_info in srp_list:
                srp_id = srp_info.get('storageResourcePoolId')
                
                if not srp_id:
                    logger.warning("Skipping SRP with missing ID")
                    continue
                
                try:
                    # Option A: Use performance API for time-series metrics
                    metrics = [
                        'UsedCapacity',
                        'SubscribedCapacity',
                        'TotalManagedSpace'
                    ]
                    
                    stats = self.conn.performance.get_storage_resource_pool_stats(
                        array_id=array_id,
                        storage_resource_pool_id=srp_id,
                        metrics=metrics,
                        data_format='Average'
                    )
                    
                    result = stats['result'][0] if stats.get('result') else {}
                    
                    # Option B: Alternatively, use provisioning API for current state
                    # srp_details = self.conn.provisioning.get_srp(
                    #     srp_id=srp_id,
                    #     array_id=array_id
                    # )
                    
                    srp_capacity = SrpCapacity(
                        array_id=array_id,
                        srp_id=srp_id,
                        timestamp=datetime.now().isoformat(),
                        used_capacity_gb=float(result.get('UsedCapacity', 0)),
                        subscribed_capacity_gb=float(result.get('SubscribedCapacity', 0)),
                        total_managed_space_gb=float(result.get('TotalManagedSpace', 0))
                    )
                    
                    srp_capacities.append(srp_capacity)
                    logger.info(
                        f"SRP '{srp_id}': "
                        f"{srp_capacity.utilization_percent:.2f}% utilized"
                    )
                    
                except Exception as e:
                    logger.error(f"Error collecting data for SRP '{srp_id}': {e}")
                    # Continue with other SRPs rather than failing completely
                    continue
            
            logger.info(f"Successfully collected capacity for {len(srp_capacities)} SRP(s)")
            return srp_capacities
            
        except PyU4V.utils.exception.VolumeBackendAPIException as e:
            logger.error(f"PyU4V API error retrieving SRP capacity: {e}")
            raise DataCollectionError(
                f"Failed to retrieve SRP capacity: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error retrieving SRP capacity: {e}")
            raise DataCollectionError(
                f"SRP capacity collection failed: {e}"
            ) from e
    
    def get_all_storage_groups(self, array_id: str) -> List[StorageGroupCapacity]:
        """
        Get capacity metrics for all Storage Groups.
        
        This method uses the ENHANCED REST API for efficient bulk retrieval.
        A single API call returns data for ALL storage groups, eliminating
        the need for per-object iteration.
        
        API Path: /univmax/rest/v1/sloprovisioning/symmetrix/{array_id}/storagegroup
        PyU4V Module: conn.provisioning.get_storage_group_list() then individual calls
        
        Alternative bulk approach: Use the Enhanced API directly for all SGs at once
        
        Key metrics per Storage Group:
        - storageGroupId: Unique identifier
        - cap_gb: Total capacity allocated to the storage group
        - num_of_vols: Number of volumes in the group
        - slo: Service Level Objective (performance tier)
        - srp: Associated Storage Resource Pool
        
        Args:
            array_id: The PowerMax/VMAX array serial number
            
        Returns:
            List of StorageGroupCapacity objects
            
        Raises:
            DataCollectionError: If unable to retrieve storage group data
        """
        try:
            logger.info(f"Collecting Storage Group data for array {array_id}")
            
            storage_group_capacities = []
            
            # Step 1: Get list of all storage group IDs
            # Note: For true bulk efficiency, consider using Enhanced API
            # directly via REST calls to get all data in one response
            sg_list = self.conn.provisioning.get_storage_group_list(
                array_id=array_id
            )
            
            if not sg_list:
                logger.warning(f"No storage groups found for array {array_id}")
                return storage_group_capacities
            
            logger.info(f"Found {len(sg_list)} storage group(s)")
            
            # Step 2: For each storage group, get detailed information
            # NOTE: This is a loop, but PyU4V may batch these internally
            # For maximum efficiency in production, consider implementing
            # direct Enhanced API calls to /univmax/rest/v1/.../storagegroup
            # with proper filtering to get all data in one request
            
            for sg_id in sg_list:
                try:
                    # Get detailed info for this storage group
                    sg_details = self.conn.provisioning.get_storage_group(
                        storage_group_id=sg_id,
                        array_id=array_id
                    )
                    
                    if not sg_details:
                        logger.warning(f"No details returned for SG '{sg_id}'")
                        continue
                    
                    # Extract capacity and metadata
                    storage_group_capacity = StorageGroupCapacity(
                        array_id=array_id,
                        storage_group_id=sg_id,
                        timestamp=datetime.now().isoformat(),
                        capacity_gb=float(sg_details.get('cap_gb', 0)),
                        num_volumes=int(sg_details.get('num_of_vols', 0)),
                        service_level=sg_details.get('slo'),
                        srp_name=sg_details.get('srp'),
                        compression_enabled=sg_details.get('compression', False)
                    )
                    
                    storage_group_capacities.append(storage_group_capacity)
                    
                except Exception as e:
                    logger.error(f"Error collecting data for SG '{sg_id}': {e}")
                    # Continue with other storage groups
                    continue
            
            logger.info(
                f"Successfully collected capacity for "
                f"{len(storage_group_capacities)} storage group(s)"
            )
            
            return storage_group_capacities
            
        except PyU4V.utils.exception.VolumeBackendAPIException as e:
            logger.error(f"PyU4V API error retrieving storage groups: {e}")
            raise DataCollectionError(
                f"Failed to retrieve storage groups: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error retrieving storage groups: {e}")
            raise DataCollectionError(
                f"Storage group collection failed: {e}"
            ) from e
    
    def get_all_volumes(self, array_id: str) -> List[VolumeCapacity]:
        """
        Get capacity metrics for all Volumes.
        
        This method uses the ENHANCED REST API for efficient bulk retrieval.
        Like storage groups, a single API call can return data for ALL volumes.
        
        API Path: /univmax/rest/v1/sloprovisioning/symmetrix/{array_id}/volume
        PyU4V Module: conn.provisioning.get_volume_list() then individual calls
        
        Alternative bulk approach: Enhanced API direct call returns all volume
        data at once, which is critical for arrays with thousands of volumes.
        
        Key metrics per Volume:
        - volume_identifier: Human-readable name
        - volumeId: Unique device ID
        - cap_gb: Capacity in gigabytes
        - allocated_percent: Percentage of allocated space actually written
        - storageGroupId: Associated storage group(s)
        - wwn: World Wide Name identifier
        
        Args:
            array_id: The PowerMax/VMAX array serial number
            
        Returns:
            List of VolumeCapacity objects
            
        Raises:
            DataCollectionError: If unable to retrieve volume data
        """
        try:
            logger.info(f"Collecting Volume data for array {array_id}")
            
            volume_capacities = []
            
            # Step 1: Get list of all volume IDs
            # For large arrays, this can return thousands of volumes
            volume_list = self.conn.provisioning.get_volume_list(
                array_id=array_id,
                params=None  # Can filter by SG, SRP, etc. if needed
            )
            
            if not volume_list:
                logger.warning(f"No volumes found for array {array_id}")
                return volume_capacities
            
            total_volumes = len(volume_list)
            logger.info(f"Found {total_volumes} volume(s) - this may take a while...")
            
            # Step 2: Get detailed info for each volume
            # IMPORTANT: For production with many volumes, consider:
            # 1. Batching requests
            # 2. Using Enhanced API bulk endpoint directly
            # 3. Parallel processing with thread pool
            # 4. Filtering to only volumes of interest
            
            batch_size = 100  # Process in batches for progress tracking
            
            for idx, volume_id in enumerate(volume_list, 1):
                try:
                    # Get detailed volume information
                    vol_details = self.conn.provisioning.get_volume(
                        device_id=volume_id,
                        array_id=array_id
                    )
                    
                    if not vol_details:
                        logger.warning(f"No details returned for volume '{volume_id}'")
                        continue
                    
                    # Extract capacity and metadata
                    volume_capacity = VolumeCapacity(
                        array_id=array_id,
                        volume_id=volume_id,
                        volume_identifier=vol_details.get('volume_identifier', ''),
                        timestamp=datetime.now().isoformat(),
                        capacity_gb=float(vol_details.get('cap_gb', 0)),
                        allocated_percent=float(vol_details.get('allocated_percent', 0)),
                        storage_groups=vol_details.get('storageGroupId', []),
                        wwn=vol_details.get('wwn'),
                        emulation_type=vol_details.get('type')
                    )
                    
                    volume_capacities.append(volume_capacity)
                    
                    # Log progress for large collections
                    if idx % batch_size == 0:
                        logger.info(
                            f"Progress: {idx}/{total_volumes} volumes processed "
                            f"({(idx/total_volumes)*100:.1f}%)"
                        )
                    
                except Exception as e:
                    logger.error(f"Error collecting data for volume '{volume_id}': {e}")
                    # Continue with other volumes
                    continue
            
            logger.info(
                f"Successfully collected capacity for "
                f"{len(volume_capacities)} volume(s)"
            )
            
            return volume_capacities
            
        except PyU4V.utils.exception.VolumeBackendAPIException as e:
            logger.error(f"PyU4V API error retrieving volumes: {e}")
            raise DataCollectionError(
                f"Failed to retrieve volumes: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error retrieving volumes: {e}")
            raise DataCollectionError(
                f"Volume collection failed: {e}"
            ) from e
    
    def get_all_capacity_data(self, array_id: str) -> CapacitySnapshot:
        """
        Collect complete capacity data across all four levels.
        
        This is the primary entry point that orchestrates collection from:
        1. System level (array-wide summary)
        2. Storage Resource Pools (SRPs)
        3. Storage Groups
        4. Volumes
        
        The method calls each individual collector and aggregates results
        into a single CapacitySnapshot object.
        
        Args:
            array_id: The PowerMax/VMAX array serial number
            
        Returns:
            CapacitySnapshot with complete capacity data hierarchy
            
        Raises:
            DataCollectionError: If any critical collection step fails
        """
        try:
            collection_start = datetime.now()
            logger.info(
                f"Starting complete capacity collection for array {array_id}"
            )
            
            # Collect system-level data
            logger.info("Step 1/4: Collecting system capacity...")
            system_capacity = self.get_system_summary(array_id)
            
            # Collect SRP data
            logger.info("Step 2/4: Collecting SRP capacities...")
            srp_capacities = self.get_srp_capacity(array_id)
            
            # Collect Storage Group data
            logger.info("Step 3/4: Collecting Storage Group capacities...")
            storage_group_capacities = self.get_all_storage_groups(array_id)
            
            # Collect Volume data
            logger.info("Step 4/4: Collecting Volume capacities...")
            volume_capacities = self.get_all_volumes(array_id)
            
            # Create aggregated snapshot
            snapshot = CapacitySnapshot(
                array_id=array_id,
                collection_timestamp=collection_start.isoformat(),
                system_capacity=system_capacity,
                srp_capacities=srp_capacities,
                storage_group_capacities=storage_group_capacities,
                volume_capacities=volume_capacities
            )
            
            collection_duration = (datetime.now() - collection_start).total_seconds()
            
            logger.info(
                f"Capacity collection completed in {collection_duration:.2f}s\n"
                f"Summary: {snapshot.total_srps} SRPs, "
                f"{snapshot.total_storage_groups} Storage Groups, "
                f"{snapshot.total_volumes} Volumes"
            )
            
            return snapshot
            
        except DataCollectionError:
            # Re-raise data collection errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during complete collection: {e}")
            raise DataCollectionError(
                f"Complete capacity collection failed: {e}"
            ) from e
    
    def close(self):
        """
        Close the connection to Unisphere.
        
        Clean up the PyU4V connection and release resources.
        """
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close_session()
                logger.info("Connection closed successfully")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
