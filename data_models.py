"""
Data models for VMAX/PowerMax capacity metrics.

These dataclasses represent the capacity information collected
from Dell PowerMax/VMAX arrays at four distinct levels:
- System (Array-wide)
- Storage Resource Pool (SRP)
- Storage Group
- Volume
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class SystemCapacity:
    """
    System-level (Array-wide) capacity metrics.
    
    Retrieved from Legacy REST API performance resource.
    """
    array_id: str
    timestamp: str
    effective_used_capacity_gb: float
    max_effective_capacity_gb: float
    subscribed_capacity_gb: float
    total_usable_capacity_gb: float
    free_capacity_gb: float = 0.0
    utilization_percent: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.max_effective_capacity_gb > 0:
            self.free_capacity_gb = (
                self.max_effective_capacity_gb - self.effective_used_capacity_gb
            )
            self.utilization_percent = (
                (self.effective_used_capacity_gb / self.max_effective_capacity_gb) * 100
            )


@dataclass
class SrpCapacity:
    """
    Storage Resource Pool (SRP) capacity metrics.
    
    Retrieved from Legacy REST API performance/provisioning resources.
    Each array can have multiple SRPs.
    """
    array_id: str
    srp_id: str
    timestamp: str
    used_capacity_gb: float
    subscribed_capacity_gb: float
    total_managed_space_gb: float
    free_capacity_gb: float = 0.0
    utilization_percent: float = 0.0
    subscription_percent: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_managed_space_gb > 0:
            self.free_capacity_gb = (
                self.total_managed_space_gb - self.used_capacity_gb
            )
            self.utilization_percent = (
                (self.used_capacity_gb / self.total_managed_space_gb) * 100
            )
            self.subscription_percent = (
                (self.subscribed_capacity_gb / self.total_managed_space_gb) * 100
            )


@dataclass
class StorageGroupCapacity:
    """
    Storage Group capacity metrics.
    
    Retrieved from Enhanced REST API (/univmax/rest/v1/...).
    Storage Groups are logical containers for volumes.
    """
    array_id: str
    storage_group_id: str
    timestamp: str
    capacity_gb: float
    num_volumes: int = 0
    service_level: Optional[str] = None
    srp_name: Optional[str] = None
    compression_enabled: bool = False
    
    def __post_init__(self):
        """Validate and normalize data."""
        if self.capacity_gb < 0:
            self.capacity_gb = 0.0


@dataclass
class VolumeCapacity:
    """
    Volume-level capacity metrics.
    
    Retrieved from Enhanced REST API (/univmax/rest/v1/...).
    Volumes are the finest granularity of storage allocation.
    """
    array_id: str
    volume_id: str
    volume_identifier: str
    timestamp: str
    capacity_gb: float
    allocated_percent: float = 0.0
    storage_groups: List[str] = field(default_factory=list)
    wwn: Optional[str] = None
    emulation_type: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize data."""
        if self.capacity_gb < 0:
            self.capacity_gb = 0.0
        if not (0 <= self.allocated_percent <= 100):
            self.allocated_percent = 0.0


@dataclass
class CapacitySnapshot:
    """
    Complete capacity snapshot across all four levels.
    
    This is the aggregated result returned by get_all_capacity_data().
    """
    array_id: str
    collection_timestamp: str
    system_capacity: SystemCapacity
    srp_capacities: List[SrpCapacity]
    storage_group_capacities: List[StorageGroupCapacity]
    volume_capacities: List[VolumeCapacity]
    
    @property
    def total_srps(self) -> int:
        """Return count of SRPs."""
        return len(self.srp_capacities)
    
    @property
    def total_storage_groups(self) -> int:
        """Return count of storage groups."""
        return len(self.storage_group_capacities)
    
    @property
    def total_volumes(self) -> int:
        """Return count of volumes."""
        return len(self.volume_capacities)
    
    def summary(self) -> dict:
        """Return a summary of the capacity snapshot."""
        return {
            'array_id': self.array_id,
            'collection_timestamp': self.collection_timestamp,
            'system': {
                'total_usable_gb': self.system_capacity.total_usable_capacity_gb,
                'used_gb': self.system_capacity.effective_used_capacity_gb,
                'free_gb': self.system_capacity.free_capacity_gb,
                'utilization_percent': round(self.system_capacity.utilization_percent, 2)
            },
            'counts': {
                'srps': self.total_srps,
                'storage_groups': self.total_storage_groups,
                'volumes': self.total_volumes
            }
        }
