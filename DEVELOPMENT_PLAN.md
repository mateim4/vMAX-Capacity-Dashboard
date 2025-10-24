# VMAX/PowerMax Capacity Dashboard - Development Plan

## Executive Summary

This document provides a detailed development plan for a Python-based capacity monitoring application targeting Dell PowerMax/VMAX storage arrays. The application uses the official PyU4V SDK to query the Unisphere for PowerMax REST API and collect capacity metrics at four hierarchical levels: System, Storage Resource Pool (SRP), Storage Group, and Volume.

---

## 1. Technical Architecture

### 1.1 Technology Selection Rationale

#### Chosen: PyU4V Python SDK
- **Official Support**: Actively maintained by Dell Technologies
- **API Coverage**: Supports both Legacy and Enhanced REST APIs
- **Abstraction**: Simplifies HTTP calls and authentication
- **Enterprise Ready**: Production-tested in large environments
- **Python 3.x**: Modern, maintainable codebase

#### Rejected Technologies
- **SMI-S Protocol**: Deprecated by Dell, replaced by REST API
- **Dell.PowerMax PowerShell Module**: End-of-Support (EOL) as of January 31, 2024

### 1.2 Hybrid API Strategy

The application must use different APIs for different data types:

```
┌─────────────────────────────────────────────────────┐
│         Unisphere for PowerMax REST API             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  LEGACY API                    ENHANCED API        │
│  /univmax/restapi/...          /univmax/rest/v1/...│
│                                                     │
│  ✓ System Summary              ✓ Storage Groups    │
│  ✓ SRP Capacity                ✓ Volumes           │
│  ✓ Performance Metrics         ✓ Bulk Operations   │
│                                                     │
└─────────────────────────────────────────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        │
                   ┌────▼────┐
                   │  PyU4V  │
                   └────┬────┘
                        │
                ┌───────▼────────┐
                │ VmaxCapacity   │
                │   Collector    │
                └────────────────┘
```

**Why Hybrid?**
- **Legacy API**: Required for system-level summaries and detailed SRP subscription metrics
- **Enhanced API**: Efficient bulk retrieval for Storage Groups and Volumes (single call vs. thousands)

---

## 2. Application Structure

### 2.1 File Organization

```
VMAX Capacity Dashboard/
│
├── main.py                    # Entry point, CLI interface
├── vmax_collector.py          # Core VmaxCapacityCollector class
├── data_models.py             # Dataclasses for capacity data
├── config.py                  # Configuration management
│
├── requirements.txt           # Python dependencies
├── config.example.json        # Configuration template
├── .gitignore                 # Git exclusions
└── README.md                  # Documentation
```

### 2.2 Module Responsibilities

| Module | Purpose | Key Components |
|--------|---------|----------------|
| `main.py` | Application entry, user interaction | CLI parsing, output formatting, error handling |
| `vmax_collector.py` | API communication, data collection | `VmaxCapacityCollector` class, PyU4V integration |
| `data_models.py` | Data structures | `SystemCapacity`, `SrpCapacity`, `StorageGroupCapacity`, `VolumeCapacity`, `CapacitySnapshot` |
| `config.py` | Configuration loading | `UnisphereConfig`, file/env loading, validation |

---

## 3. Core Class: VmaxCapacityCollector

### 3.1 Class Structure

```python
class VmaxCapacityCollector:
    """
    Collects capacity metrics from Dell PowerMax/VMAX arrays.
    """
    
    def __init__(self, host, username, password, port=8443, 
                 verify_ssl=False, array_id=None):
        """Initialize PyU4V connection."""
        pass
    
    def get_system_summary(self, array_id: str) -> SystemCapacity:
        """Get array-wide capacity summary (Legacy API)."""
        pass
    
    def get_srp_capacity(self, array_id: str) -> List[SrpCapacity]:
        """Get all SRP capacity metrics (Legacy API)."""
        pass
    
    def get_all_storage_groups(self, array_id: str) -> List[StorageGroupCapacity]:
        """Get all Storage Group capacities (Enhanced API)."""
        pass
    
    def get_all_volumes(self, array_id: str) -> List[VolumeCapacity]:
        """Get all Volume capacities (Enhanced API)."""
        pass
    
    def get_all_capacity_data(self, array_id: str) -> CapacitySnapshot:
        """Aggregate all four levels into single snapshot."""
        pass
```

### 3.2 Initialization

```python
def __init__(self, host: str, username: str, password: str, 
             port: int = 8443, verify_ssl: bool = False, 
             array_id: Optional[str] = None):
    """
    Initialize PyU4V connection to Unisphere.
    
    Creates U4VConn object which provides access to all API modules:
    - conn.performance (Legacy API metrics)
    - conn.provisioning (Storage Groups, Volumes)
    - conn.common (Array metadata)
    """
    self.conn = PyU4V.U4VConn(
        server_ip=host,
        port=port,
        verify=verify_ssl,
        username=username,
        password=password
    )
    
    # Test connection and get array list
    arrays = self.conn.common.get_array_list()
    
    # Set default array if not specified
    self.array_id = array_id or arrays[0]
```

---

## 4. Implementation Details by Level

### 4.1 System-Level Capacity

**Method**: `get_system_summary(array_id: str) -> SystemCapacity`

**API Type**: Legacy REST API  
**Endpoint**: `/univmax/restapi/{version}/performance/Array/keys`  
**PyU4V Module**: `conn.performance`

**Implementation**:

```python
def get_system_summary(self, array_id: str) -> SystemCapacity:
    # Step 1: Get array performance keys
    array_keys = self.conn.performance.get_array_keys()
    
    # Step 2: Define required metrics
    metrics = [
        'EffectiveUsedCapacity',      # Actual used capacity
        'MaxEffectiveCapacity',        # Maximum available
        'SubscribedCapacity',          # Total allocated
        'TotalUsableCapacity'          # Raw capacity
    ]
    
    # Step 3: Query performance stats
    stats = self.conn.performance.get_array_stats(
        array_id=array_id,
        metrics=metrics,
        data_format='Average'
    )
    
    # Step 4: Parse and return
    result = stats['result'][0]
    return SystemCapacity(
        array_id=array_id,
        timestamp=datetime.now().isoformat(),
        effective_used_capacity_gb=float(result['EffectiveUsedCapacity']),
        max_effective_capacity_gb=float(result['MaxEffectiveCapacity']),
        subscribed_capacity_gb=float(result['SubscribedCapacity']),
        total_usable_capacity_gb=float(result['TotalUsableCapacity'])
    )
```

**Key Metrics**:
- `EffectiveUsedCapacity`: Actual consumed capacity (accounts for compression/dedup)
- `MaxEffectiveCapacity`: Maximum available effective capacity
- `SubscribedCapacity`: Total allocated capacity (can exceed physical due to thin provisioning)
- `TotalUsableCapacity`: Total raw usable capacity

---

### 4.2 Storage Resource Pool (SRP) Capacity

**Method**: `get_srp_capacity(array_id: str) -> List[SrpCapacity]`

**API Type**: Legacy REST API (Two-Step Process)  
**Endpoints**: 
1. `/univmax/restapi/{version}/performance/StorageResourcePool/keys`
2. `/univmax/restapi/{version}/performance/StorageResourcePool/metrics`

**PyU4V Modules**: `conn.performance`, optionally `conn.provisioning`

**Implementation**:

```python
def get_srp_capacity(self, array_id: str) -> List[SrpCapacity]:
    srp_capacities = []
    
    # Step 1: Get list of all SRP IDs
    srp_keys = self.conn.performance.get_storage_resource_pool_keys(
        array_id=array_id
    )
    
    srp_list = srp_keys['storageResourcePoolInfo']
    
    # Step 2: Loop through each SRP and get metrics
    for srp_info in srp_list:
        srp_id = srp_info['storageResourcePoolId']
        
        # Define metrics to retrieve
        metrics = [
            'UsedCapacity',           # Actually consumed
            'SubscribedCapacity',     # Total allocated
            'TotalManagedSpace'       # Total pool size
        ]
        
        # Query performance stats for this SRP
        stats = self.conn.performance.get_storage_resource_pool_stats(
            array_id=array_id,
            storage_resource_pool_id=srp_id,
            metrics=metrics,
            data_format='Average'
        )
        
        result = stats['result'][0]
        
        srp_capacities.append(SrpCapacity(
            array_id=array_id,
            srp_id=srp_id,
            timestamp=datetime.now().isoformat(),
            used_capacity_gb=float(result['UsedCapacity']),
            subscribed_capacity_gb=float(result['SubscribedCapacity']),
            total_managed_space_gb=float(result['TotalManagedSpace'])
        ))
    
    return srp_capacities
```

**Alternative Approach** (using provisioning API):

```python
# Instead of performance API, use provisioning for current state
srp_details = self.conn.provisioning.get_srp(
    srp_id=srp_id,
    array_id=array_id
)

# Extract from srp_details:
# - total_used_cap_gb
# - total_subscribed_cap_gb
# - total_usable_cap_gb
```

**Key Metrics**:
- `UsedCapacity`: Actual space consumed in the SRP
- `SubscribedCapacity`: Total allocated to Storage Groups (thin provisioning awareness)
- `TotalManagedSpace`: Total capacity managed by this SRP

---

### 4.3 Storage Group Capacity

**Method**: `get_all_storage_groups(array_id: str) -> List[StorageGroupCapacity]`

**API Type**: Enhanced REST API  
**Endpoint**: `/univmax/rest/v1/sloprovisioning/symmetrix/{array_id}/storagegroup`  
**PyU4V Module**: `conn.provisioning`

**Implementation**:

```python
def get_all_storage_groups(self, array_id: str) -> List[StorageGroupCapacity]:
    storage_group_capacities = []
    
    # Step 1: Get list of all Storage Group IDs
    sg_list = self.conn.provisioning.get_storage_group_list(
        array_id=array_id
    )
    
    # Step 2: Get details for each Storage Group
    # Note: For true bulk efficiency, consider direct Enhanced API call
    for sg_id in sg_list:
        sg_details = self.conn.provisioning.get_storage_group(
            storage_group_id=sg_id,
            array_id=array_id
        )
        
        storage_group_capacities.append(StorageGroupCapacity(
            array_id=array_id,
            storage_group_id=sg_id,
            timestamp=datetime.now().isoformat(),
            capacity_gb=float(sg_details['cap_gb']),
            num_volumes=int(sg_details['num_of_vols']),
            service_level=sg_details.get('slo'),
            srp_name=sg_details.get('srp'),
            compression_enabled=sg_details.get('compression', False)
        ))
    
    return storage_group_capacities
```

**Performance Optimization**:

For production with many Storage Groups, consider direct REST call:

```python
# Direct Enhanced API call (more efficient for bulk)
import requests

response = requests.get(
    f"https://{host}:{port}/univmax/rest/v1/sloprovisioning/"
    f"symmetrix/{array_id}/storagegroup",
    auth=(username, password),
    verify=verify_ssl
)

# Response contains ALL storage groups in single call
all_storage_groups = response.json()['storageGroupId']
```

**Key Metrics**:
- `storageGroupId`: Unique identifier
- `cap_gb`: Total capacity allocated
- `num_of_vols`: Number of volumes in group
- `slo`: Service Level (Diamond, Platinum, Gold, Silver, Bronze, Optimized, None)
- `srp`: Associated Storage Resource Pool
- `compression`: Whether compression is enabled

---

### 4.4 Volume Capacity

**Method**: `get_all_volumes(array_id: str) -> List[VolumeCapacity]`

**API Type**: Enhanced REST API  
**Endpoint**: `/univmax/rest/v1/sloprovisioning/symmetrix/{array_id}/volume`  
**PyU4V Module**: `conn.provisioning`

**Implementation**:

```python
def get_all_volumes(self, array_id: str) -> List[VolumeCapacity]:
    volume_capacities = []
    
    # Step 1: Get list of all Volume IDs
    # Warning: Can return thousands of volumes on large arrays
    volume_list = self.conn.provisioning.get_volume_list(
        array_id=array_id,
        params=None  # Can filter by SG, SRP if needed
    )
    
    total_volumes = len(volume_list)
    batch_size = 100
    
    # Step 2: Get details for each volume
    for idx, volume_id in enumerate(volume_list, 1):
        vol_details = self.conn.provisioning.get_volume(
            device_id=volume_id,
            array_id=array_id
        )
        
        volume_capacities.append(VolumeCapacity(
            array_id=array_id,
            volume_id=volume_id,
            volume_identifier=vol_details.get('volume_identifier', ''),
            timestamp=datetime.now().isoformat(),
            capacity_gb=float(vol_details['cap_gb']),
            allocated_percent=float(vol_details.get('allocated_percent', 0)),
            storage_groups=vol_details.get('storageGroupId', []),
            wwn=vol_details.get('wwn'),
            emulation_type=vol_details.get('type')
        ))
        
        # Progress logging for large collections
        if idx % batch_size == 0:
            logger.info(f"Progress: {idx}/{total_volumes} volumes")
    
    return volume_capacities
```

**Performance Considerations**:

For arrays with 10,000+ volumes:

1. **Filtering**: Only collect volumes from specific Storage Groups
```python
volume_list = self.conn.provisioning.get_volume_list(
    array_id=array_id,
    params={'storageGroupId': 'Production_SG'}
)
```

2. **Parallel Processing**: Use ThreadPoolExecutor
```python
from concurrent.futures import ThreadPoolExecutor

def get_volume_details(volume_id):
    return self.conn.provisioning.get_volume(volume_id, array_id)

with ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(get_volume_details, volume_list)
```

3. **Caching**: Cache static metadata, only refresh capacity values

**Key Metrics**:
- `volume_id`: Device ID (e.g., "00001")
- `volume_identifier`: Human-readable name
- `cap_gb`: Volume capacity in GB
- `allocated_percent`: Percentage of allocated space actually written (thin provisioning metric)
- `storageGroupId`: List of parent Storage Groups
- `wwn`: World Wide Name (unique identifier for storage networking)
- `type`: Emulation type (e.g., FBA, CKD)

---

### 4.5 Aggregated Collection

**Method**: `get_all_capacity_data(array_id: str) -> CapacitySnapshot`

**Purpose**: Orchestrate collection across all four levels

**Implementation**:

```python
def get_all_capacity_data(self, array_id: str) -> CapacitySnapshot:
    collection_start = datetime.now()
    
    # Collect each level sequentially
    system_capacity = self.get_system_summary(array_id)
    srp_capacities = self.get_srp_capacity(array_id)
    storage_group_capacities = self.get_all_storage_groups(array_id)
    volume_capacities = self.get_all_volumes(array_id)
    
    # Aggregate into snapshot
    snapshot = CapacitySnapshot(
        array_id=array_id,
        collection_timestamp=collection_start.isoformat(),
        system_capacity=system_capacity,
        srp_capacities=srp_capacities,
        storage_group_capacities=storage_group_capacities,
        volume_capacities=volume_capacities
    )
    
    return snapshot
```

---

## 5. Data Models

### 5.1 Dataclass Definitions

```python
@dataclass
class SystemCapacity:
    array_id: str
    timestamp: str
    effective_used_capacity_gb: float
    max_effective_capacity_gb: float
    subscribed_capacity_gb: float
    total_usable_capacity_gb: float
    free_capacity_gb: float = 0.0          # Calculated
    utilization_percent: float = 0.0        # Calculated

@dataclass
class SrpCapacity:
    array_id: str
    srp_id: str
    timestamp: str
    used_capacity_gb: float
    subscribed_capacity_gb: float
    total_managed_space_gb: float
    free_capacity_gb: float = 0.0          # Calculated
    utilization_percent: float = 0.0        # Calculated
    subscription_percent: float = 0.0       # Calculated

@dataclass
class StorageGroupCapacity:
    array_id: str
    storage_group_id: str
    timestamp: str
    capacity_gb: float
    num_volumes: int = 0
    service_level: Optional[str] = None
    srp_name: Optional[str] = None
    compression_enabled: bool = False

@dataclass
class VolumeCapacity:
    array_id: str
    volume_id: str
    volume_identifier: str
    timestamp: str
    capacity_gb: float
    allocated_percent: float = 0.0
    storage_groups: List[str] = field(default_factory=list)
    wwn: Optional[str] = None
    emulation_type: Optional[str] = None

@dataclass
class CapacitySnapshot:
    array_id: str
    collection_timestamp: str
    system_capacity: SystemCapacity
    srp_capacities: List[SrpCapacity]
    storage_group_capacities: List[StorageGroupCapacity]
    volume_capacities: List[VolumeCapacity]
```

---

## 6. Error Handling Strategy

### 6.1 Exception Hierarchy

```python
class VmaxCapacityCollectorError(Exception):
    """Base exception for all collector errors."""
    pass

class ConnectionError(VmaxCapacityCollectorError):
    """Network or connectivity issues."""
    pass

class AuthenticationError(VmaxCapacityCollectorError):
    """Invalid credentials or insufficient permissions."""
    pass

class DataCollectionError(VmaxCapacityCollectorError):
    """API errors during data retrieval."""
    pass
```

### 6.2 Error Handling Patterns

#### Connection Initialization

```python
try:
    self.conn = PyU4V.U4VConn(...)
    arrays = self.conn.common.get_array_list()
except requests.exceptions.ConnectionError as e:
    raise ConnectionError(
        f"Cannot connect to Unisphere at {host}:{port}"
    ) from e
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise AuthenticationError("Invalid credentials") from e
    else:
        raise ConnectionError(f"HTTP error: {e}") from e
```

#### API Data Collection

```python
try:
    stats = self.conn.performance.get_array_stats(...)
except PyU4V.utils.exception.VolumeBackendAPIException as e:
    raise DataCollectionError(
        f"Failed to retrieve system summary: {e}"
    ) from e
except KeyError as e:
    raise DataCollectionError(
        f"API response missing required field: {e}"
    ) from e
except Exception as e:
    raise DataCollectionError(
        f"Unexpected error: {e}"
    ) from e
```

#### Graceful Degradation

For non-critical failures (e.g., one SRP fails), log and continue:

```python
for srp_id in srp_list:
    try:
        srp_data = self.get_srp_details(srp_id)
        srp_capacities.append(srp_data)
    except Exception as e:
        logger.error(f"Failed to collect SRP '{srp_id}': {e}")
        # Continue with other SRPs
        continue
```

---

## 7. Development Roadmap

### Phase 1: Core Framework (Completed)
- [x] Project structure
- [x] Configuration management
- [x] Data models
- [x] VmaxCapacityCollector skeleton
- [x] Error handling framework

### Phase 2: API Implementation (Completed)
- [x] System-level collection (Legacy API)
- [x] SRP collection (Legacy API)
- [x] Storage Group collection (Enhanced API)
- [x] Volume collection (Enhanced API)
- [x] Aggregated collection method

### Phase 3: User Interface (Completed)
- [x] CLI main.py
- [x] Console output formatting
- [x] JSON export
- [x] Progress indicators

### Phase 4: Documentation (Completed)
- [x] Comprehensive README.md
- [x] Development plan (this document)
- [x] Code comments and docstrings
- [x] Configuration examples

### Phase 5: Testing (Recommended Next)
- [ ] Unit tests for data models
- [ ] Integration tests with mock API
- [ ] End-to-end testing with real array
- [ ] Performance benchmarking

### Phase 6: Production Hardening (Future)
- [ ] Logging configuration
- [ ] Retry logic for transient failures
- [ ] Rate limiting for API calls
- [ ] Connection pooling
- [ ] Metrics and monitoring

### Phase 7: Advanced Features (Future)
- [ ] Multi-array support
- [ ] Database persistence
- [ ] Web dashboard
- [ ] Scheduled collection
- [ ] Alerting and thresholds

---

## 8. Best Practices & Recommendations

### 8.1 Security
1. **Never commit `config.json`** - Use `.gitignore`
2. **Use environment variables** in CI/CD pipelines
3. **Enable SSL verification** in production (`verify_ssl: true`)
4. **Rotate credentials** regularly
5. **Use least-privilege accounts** (Monitor role only)

### 8.2 Performance
1. **Batch volume collection** for large arrays (10,000+ volumes)
2. **Use filtering** to reduce data volume when possible
3. **Implement caching** for static metadata
4. **Consider parallel processing** with ThreadPoolExecutor
5. **Monitor API rate limits** and implement backoff

### 8.3 Reliability
1. **Implement retries** for transient network errors
2. **Log all API calls** for troubleshooting
3. **Validate data** before processing
4. **Handle partial failures** gracefully
5. **Test with production data volumes**

### 8.4 Maintainability
1. **Keep PyU4V updated** - Check for new versions regularly
2. **Document API version compatibility**
3. **Use type hints** throughout
4. **Write comprehensive tests**
5. **Follow PEP 8** style guidelines

---

## 9. Deployment Checklist

### Prerequisites
- [ ] Python 3.8+ installed
- [ ] Network access to Unisphere (port 8443)
- [ ] Valid credentials with Monitor role
- [ ] Array ID (12-digit serial number)

### Installation
- [ ] Clone/download project
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate: `venv\Scripts\activate` (Windows)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy `config.example.json` to `config.json`
- [ ] Edit `config.json` with connection details

### Verification
- [ ] Test connection: `python -c "import PyU4V; print(PyU4V.__version__)"`
- [ ] Run application: `python main.py`
- [ ] Verify output and JSON export
- [ ] Check logs for errors

### Production
- [ ] Enable SSL verification
- [ ] Set up scheduled execution (Task Scheduler)
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Document operational procedures

---

## 10. Troubleshooting Guide

### Issue: "Cannot connect to Unisphere"
**Symptoms**: `ConnectionError` on initialization  
**Causes**:
- Unisphere service not running
- Network firewall blocking port 8443
- Incorrect hostname/IP

**Resolution**:
```powershell
# Test connectivity
Test-NetConnection -ComputerName unisphere-host -Port 8443

# Test DNS resolution
Resolve-DnsName unisphere-host

# Disable SSL verification for testing
# Set verify_ssl: false in config.json
```

### Issue: "Authentication failed"
**Symptoms**: HTTP 401 error  
**Causes**:
- Incorrect username/password
- Account locked
- Insufficient permissions

**Resolution**:
- Verify credentials in Unisphere GUI
- Check user has "Monitor" role assigned
- Test with different account
- Include domain if using AD: `DOMAIN\username`

### Issue: "No data returned"
**Symptoms**: Empty lists for SRPs, SGs, or Volumes  
**Causes**:
- Wrong array ID
- User lacks permissions to view resources
- Array has no objects of that type

**Resolution**:
```python
# Verify array ID
arrays = conn.common.get_array_list()
print(f"Available arrays: {arrays}")

# Check array details
array_info = conn.common.get_array(array_id)
print(array_info)
```

### Issue: "Slow performance"
**Symptoms**: Collection takes > 30 minutes  
**Causes**:
- Large number of volumes (10,000+)
- Network latency
- Unisphere under load

**Resolution**:
- Implement filtering by Storage Group
- Use parallel processing
- Collect during off-peak hours
- Consider incremental updates

---

## 11. References

### Official Documentation
- PyU4V GitHub: https://github.com/dell/PyU4V
- PyU4V Docs: https://pyu4v.readthedocs.io/
- PowerMax REST API: https://developer.dell.com/apis/4494/
- Unisphere for PowerMax: Dell Support Portal

### Key API Endpoints

#### Legacy API (`/univmax/restapi/{version}/...`)
- `/performance/Array/keys` - System metrics
- `/performance/StorageResourcePool/keys` - SRP list
- `/performance/StorageResourcePool/metrics` - SRP metrics
- `/sloprovisioning/symmetrix/{id}/srp` - SRP details

#### Enhanced API (`/univmax/rest/v1/...`)
- `/sloprovisioning/symmetrix/{id}/storagegroup` - Storage Groups
- `/sloprovisioning/symmetrix/{id}/volume` - Volumes
- `/system/symmetrix` - Array list

---

## 12. Conclusion

This development plan provides a complete foundation for a production-ready capacity monitoring application. The hybrid API strategy maximizes efficiency while the modular architecture ensures maintainability and extensibility.

**Key Achievements**:
- ✅ Enterprise-grade architecture using official Dell SDK
- ✅ Efficient hybrid API strategy (Legacy + Enhanced)
- ✅ Comprehensive error handling
- ✅ Extensible data models
- ✅ Production-ready code structure
- ✅ Complete documentation

**Next Steps**:
1. Test with real PowerMax/VMAX environment
2. Implement unit and integration tests
3. Add database persistence for historical trending
4. Create web dashboard for visualization
5. Implement scheduling and automation

---

**Document Version**: 1.0  
**Last Updated**: October 24, 2025  
**Author**: Principal Software Architect  
**Technology**: Python 3.x + Dell PyU4V SDK
