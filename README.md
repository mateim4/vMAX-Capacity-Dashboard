# VMAX/PowerMax Capacity Dashboard

A comprehensive Python application for monitoring and reporting capacity metrics from Dell PowerMax and VMAX storage arrays via the Unisphere for PowerMax REST API.

## 📋 Overview

This application collects capacity information at four distinct hierarchical levels:

1. **System Level** - Array-wide capacity summary
2. **Storage Resource Pool (SRP)** - Pool-level utilization and subscription
3. **Storage Group** - Logical grouping capacity
4. **Volume** - Individual volume capacity and allocation

## 🏗️ Architecture

### Hybrid API Strategy

The application implements a strategic dual-API approach to maximize efficiency:

#### Enhanced REST API (`/univmax/rest/v1/...`)
- **Purpose**: Bulk object-level data collection
- **Used For**: Storage Groups and Volumes
- **Benefit**: Single API call returns all objects, eliminating inefficient loops
- **PyU4V Modules**: `volumes`, `storage_groups`

#### Legacy REST API (`/univmax/restapi/{version}/...`)
- **Purpose**: System summaries and detailed pool metrics
- **Used For**: System-level capacity and SRP metrics
- **Benefit**: Access to performance metrics and subscription data not in Enhanced API
- **PyU4V Modules**: `performance`, `provisioning`

### Why This Architecture?

**Deprecated Technologies NOT Used:**
- ❌ **SMI-S Protocol** - Deprecated by Dell, superseded by REST API
- ❌ **Dell.PowerMax PowerShell Module** - End-of-Support as of January 31, 2024

**Selected Technology:**
- ✅ **PyU4V SDK** - Official Dell-maintained Python library
  - Actively supported
  - Abstracts HTTP complexity
  - Supports both Legacy and Enhanced REST APIs
  - Production-ready and enterprise-tested

## 📁 Project Structure

```
VMAX Capacity Dashboard/
│
├── main.py                    # Application entry point
├── vmax_collector.py          # Core VmaxCapacityCollector class
├── data_models.py             # Data structures (dataclasses)
├── config.py                  # Configuration management
│
├── requirements.txt           # Python dependencies
├── config.example.json        # Configuration template
└── README.md                  # This file
```

## 🔧 Prerequisites

### Network Requirements
- Network connectivity to Unisphere management server
- HTTPS access on **TCP port 8443**

### Authentication Requirements
- Valid Unisphere username and password
- Account with minimum **"Monitor" role** assigned
- HTTP Basic Authentication credentials

### Software Requirements
- Python 3.8 or higher
- pip (Python package manager)
- Access to PyPI or local package repository

## 🚀 Installation

### 1. Clone or Download Project

```powershell
cd "c:\DevApps\VMAX Capacity Dashboard"
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

This installs:
- `PyU4V` - Dell's official PowerMax/VMAX Python SDK
- `requests` - HTTP library
- `pydantic` - Data validation

### 3. Configure Connection

#### Option A: Configuration File (Recommended)

Copy the example configuration:

```powershell
Copy-Item config.example.json config.json
```

Edit `config.json`:

```json
{
  "unisphere_host": "your-unisphere-server.example.com",
  "unisphere_port": 8443,
  "username": "monitor_user",
  "password": "SecurePassword123",
  "array_id": "000123456789",
  "verify_ssl": false
}
```

#### Option B: Environment Variables

```powershell
$env:UNISPHERE_HOST = "your-unisphere-server.example.com"
$env:UNISPHERE_PORT = "8443"
$env:UNISPHERE_USER = "monitor_user"
$env:UNISPHERE_PASSWORD = "SecurePassword123"
$env:VMAX_ARRAY_ID = "000123456789"
$env:UNISPHERE_VERIFY_SSL = "false"
```

## 💻 Usage

### Basic Usage

Run the complete capacity collection:

```powershell
python main.py
```

This will:
1. Connect to Unisphere
2. Collect capacity data at all four levels
3. Display a formatted summary
4. Export results to JSON file

### Example Output

```
VMAX/PowerMax Capacity Dashboard
================================================================================
✅ Configuration loaded
   Unisphere: unisphere.example.com:8443
   Array ID:  000123456789
   User:      monitor_user

🔌 Connecting to Unisphere...
✅ Connected successfully

📊 Collecting capacity data (this may take several minutes)...

================================================================================
CAPACITY DASHBOARD - Array: 000123456789
Collection Time: 2025-10-24T10:30:00
================================================================================

📊 SYSTEM CAPACITY
  Total Usable:     1,000,000.00 GB
  Used:             650,000.00 GB
  Free:             350,000.00 GB
  Utilization:      65.00%
  Subscribed:       800,000.00 GB

💾 STORAGE RESOURCE POOLS (2)
  SRP_1:
    Total:          500,000.00 GB
    Used:           325,000.00 GB (65.00%)
    Subscription:   80.00%

📦 STORAGE GROUPS (150)
  Total Allocated:  780,000.00 GB
  Top 10 by Size:
    1. Production_DB: 50,000.00 GB (100 vols)
    2. SAP_Storage: 45,000.00 GB (75 vols)
    ...

💿 VOLUMES (2500)
  Total Capacity:   780,000.00 GB
  Average Size:     312.00 GB

================================================================================
✅ Data exported to: capacity_report_000123456789_2025-10-24T10-30-00.json
```

### Programmatic Usage

```python
from config import load_config
from vmax_collector import VmaxCapacityCollector

# Load configuration
config = load_config("config.json")

# Create collector (use context manager for auto-cleanup)
with VmaxCapacityCollector(
    host=config.host,
    port=config.port,
    username=config.username,
    password=config.password,
    array_id=config.array_id
) as collector:
    
    # Collect all capacity data
    snapshot = collector.get_all_capacity_data(config.array_id)
    
    # Access specific levels
    print(f"System utilization: {snapshot.system_capacity.utilization_percent}%")
    print(f"Number of SRPs: {snapshot.total_srps}")
    print(f"Number of volumes: {snapshot.total_volumes}")
    
    # Or collect individual levels
    system_cap = collector.get_system_summary(config.array_id)
    srp_caps = collector.get_srp_capacity(config.array_id)
    sg_caps = collector.get_all_storage_groups(config.array_id)
    vol_caps = collector.get_all_volumes(config.array_id)
```

## 📊 Data Models

### SystemCapacity
- `effective_used_capacity_gb` - Actual consumed capacity
- `max_effective_capacity_gb` - Maximum available capacity
- `subscribed_capacity_gb` - Total allocated (may exceed physical)
- `total_usable_capacity_gb` - Total raw capacity
- `utilization_percent` - Calculated usage percentage

### SrpCapacity
- `srp_id` - Storage Resource Pool identifier
- `used_capacity_gb` - Actual consumed in pool
- `subscribed_capacity_gb` - Total allocated to pool
- `total_managed_space_gb` - Total pool capacity
- `utilization_percent` - Pool usage percentage
- `subscription_percent` - Over/under-subscription ratio

### StorageGroupCapacity
- `storage_group_id` - Unique identifier
- `capacity_gb` - Total allocated capacity
- `num_volumes` - Count of volumes in group
- `service_level` - Performance tier (Diamond, Platinum, Gold, etc.)
- `srp_name` - Associated SRP

### VolumeCapacity
- `volume_id` - Device ID
- `volume_identifier` - Human-readable name
- `capacity_gb` - Volume size
- `allocated_percent` - Actual data written vs allocated
- `storage_groups` - List of parent storage groups
- `wwn` - World Wide Name

## 🔍 Implementation Details

### VmaxCapacityCollector Class

#### Core Methods

##### `get_system_summary(array_id: str) -> SystemCapacity`
**API Strategy**: Legacy REST API  
**Endpoint**: `/univmax/restapi/{version}/performance/Array/keys`  
**PyU4V Functions**:
```python
conn.performance.get_array_keys()
conn.performance.get_array_stats(
    array_id=array_id,
    metrics=['EffectiveUsedCapacity', 'MaxEffectiveCapacity', 
             'SubscribedCapacity', 'TotalUsableCapacity']
)
```

##### `get_srp_capacity(array_id: str) -> List[SrpCapacity]`
**API Strategy**: Legacy REST API (two-step process)  
**Step 1**: Get SRP list
```python
conn.performance.get_storage_resource_pool_keys(array_id=array_id)
```
**Step 2**: Query each SRP
```python
conn.performance.get_storage_resource_pool_stats(
    array_id=array_id,
    storage_resource_pool_id=srp_id,
    metrics=['UsedCapacity', 'SubscribedCapacity', 'TotalManagedSpace']
)
```

##### `get_all_storage_groups(array_id: str) -> List[StorageGroupCapacity]`
**API Strategy**: Enhanced REST API  
**Endpoint**: `/univmax/rest/v1/sloprovisioning/symmetrix/{array_id}/storagegroup`  
**PyU4V Functions**:
```python
conn.provisioning.get_storage_group_list(array_id=array_id)
conn.provisioning.get_storage_group(storage_group_id=sg_id, array_id=array_id)
```
**Key Metrics**: `storageGroupId`, `cap_gb`, `num_of_vols`, `slo`, `srp`

##### `get_all_volumes(array_id: str) -> List[VolumeCapacity]`
**API Strategy**: Enhanced REST API  
**Endpoint**: `/univmax/rest/v1/sloprovisioning/symmetrix/{array_id}/volume`  
**PyU4V Functions**:
```python
conn.provisioning.get_volume_list(array_id=array_id)
conn.provisioning.get_volume(device_id=volume_id, array_id=array_id)
```
**Key Metrics**: `volume_identifier`, `cap_gb`, `allocated_percent`, `storageGroupId`

##### `get_all_capacity_data(array_id: str) -> CapacitySnapshot`
**Purpose**: Orchestrates complete collection across all four levels  
**Returns**: Aggregated `CapacitySnapshot` object with all data

### Error Handling

The application implements comprehensive exception handling:

#### Custom Exceptions
- `ConnectionError` - Network/connectivity issues
- `AuthenticationError` - Invalid credentials or insufficient permissions
- `DataCollectionError` - API errors during data retrieval

#### Try-Except Patterns

```python
try:
    # PyU4V API calls
    data = conn.performance.get_array_stats(...)
except PyU4V.utils.exception.VolumeBackendAPIException as e:
    # Handle PyU4V-specific errors
    raise DataCollectionError(f"API error: {e}") from e
except requests.exceptions.ConnectionError as e:
    # Handle network errors
    raise ConnectionError(f"Cannot connect: {e}") from e
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise AuthenticationError("Invalid credentials") from e
    else:
        raise DataCollectionError(f"HTTP error: {e}") from e
```

## 🛠️ Troubleshooting

### Connection Issues
- Verify Unisphere is running: `Test-NetConnection -ComputerName unisphere-host -Port 8443`
- Check firewall rules for port 8443
- Verify hostname resolution
- Test with SSL verification disabled (`verify_ssl: false`)

### Authentication Failures
- Confirm username and password
- Verify user has "Monitor" role in Unisphere
- Check if account is locked or expired
- Ensure domain is included if using AD: `DOMAIN\username`

### Data Collection Errors
- Verify array ID is correct (12-digit serial number)
- Check user has permissions to view all resources
- Review Unisphere logs for API errors
- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

### Performance Optimization

For large arrays with thousands of volumes:

1. **Batch Processing**: Modify volume collection to process in batches
2. **Parallel Requests**: Use threading for concurrent API calls
3. **Filtering**: Only collect data for specific SRPs or Storage Groups
4. **Caching**: Cache array metadata that doesn't change frequently

## 📈 Future Enhancements

Potential improvements for production deployment:

- [ ] **Database Integration** - Store time-series data in PostgreSQL/InfluxDB
- [ ] **Scheduling** - Automated periodic collection with cron/Task Scheduler
- [ ] **Web Dashboard** - Flask/Django web interface with charts
- [ ] **Alerting** - Threshold-based notifications (email, Slack)
- [ ] **Multi-Array Support** - Concurrent monitoring of multiple arrays
- [ ] **Trend Analysis** - Historical capacity growth predictions
- [ ] **Excel Reporting** - Formatted XLSX reports with charts
- [ ] **REST API** - Expose collected data via RESTful endpoints

## 📚 References

### Official Documentation
- [Dell PyU4V GitHub](https://github.com/dell/PyU4V)
- [PyU4V Documentation](https://pyu4v.readthedocs.io/)
- [PowerMax REST API Documentation](https://developer.dell.com/apis/4494/versions/10.0.0/docs/overview.md)
- [Unisphere for PowerMax](https://www.dell.com/support/home/en-us/product-support/product/powermax-unisphere/docs)

### Key Decisions
1. **PyU4V over SMI-S**: SMI-S is deprecated; REST API is the modern standard
2. **PyU4V over PowerShell**: PowerShell module EOL Jan 31, 2024
3. **Hybrid API Strategy**: Leverage strengths of both Legacy and Enhanced APIs
4. **Bulk Collection**: Use Enhanced API for efficient multi-object retrieval

## 📝 License

This project is provided as-is for educational and operational purposes.

## 🤝 Contributing

To extend this project:

1. Add new metrics to data models
2. Implement additional collection methods
3. Create visualization components
4. Add export formats (CSV, Excel, etc.)
5. Implement scheduling and automation

## ⚙️ System Requirements

- **OS**: Windows, Linux, or macOS
- **Python**: 3.8+
- **Network**: HTTPS (TCP 8443) to Unisphere
- **Permissions**: Unisphere "Monitor" role minimum
- **Memory**: ~500MB for large arrays (10,000+ volumes)
- **Disk**: Minimal (JSON exports ~1-10MB per snapshot)

## 🔐 Security Considerations

1. **Credentials**: Store `config.json` securely, exclude from version control
2. **SSL**: Enable `verify_ssl: true` in production environments
3. **Permissions**: Use least-privilege accounts (Monitor role only)
4. **Logs**: Review logs for sensitive data before sharing
5. **Network**: Use VPN or secure network for Unisphere access

---

**Created**: October 2025  
**Technology**: Python 3.x + Dell PyU4V SDK  
**Target Platform**: Dell PowerMax & VMAX Arrays  
**API Version**: Unisphere REST API v10.0+
