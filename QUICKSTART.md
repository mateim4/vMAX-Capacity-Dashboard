# Quick Start Guide - VMAX Capacity Dashboard

## 🚀 5-Minute Setup

### Step 1: Install Python Dependencies

```powershell
# Navigate to project directory
cd "c:\DevApps\VMAX Capacity Dashboard"

# Install required packages
pip install -r requirements.txt
```

### Step 2: Configure Connection

```powershell
# Copy example configuration
Copy-Item config.example.json config.json

# Edit config.json with your details
notepad config.json
```

**Required Configuration:**
```json
{
  "unisphere_host": "10.0.0.100",
  "unisphere_port": 8443,
  "username": "your_username",
  "password": "your_password",
  "array_id": "000123456789",
  "verify_ssl": false
}
```

### Step 3: Run the Application

```powershell
python main.py
```

## 📊 What You'll Get

### Console Output
- ✅ System-level capacity summary
- 💾 Storage Resource Pool (SRP) details
- 📦 Storage Group statistics
- 💿 Volume count and capacity

### JSON Export
- Complete capacity data in structured JSON format
- Filename: `capacity_report_{array_id}_{timestamp}.json`
- Suitable for importing into databases or analytics tools

## 🔧 Troubleshooting

### "Cannot connect to Unisphere"
```powershell
# Test connectivity
Test-NetConnection -ComputerName your-unisphere-host -Port 8443
```
**Fix**: Check firewall rules, verify Unisphere is running

### "Authentication failed"
**Fix**: Verify credentials, ensure user has "Monitor" role in Unisphere

### "No volumes found"
**Fix**: Check array_id is correct (12-digit serial number)

## 📝 Common Tasks

### Collect Only System Summary
```python
from config import load_config
from vmax_collector import VmaxCapacityCollector

config = load_config("config.json")
with VmaxCapacityCollector(
    host=config.host,
    port=config.port,
    username=config.username,
    password=config.password
) as collector:
    system = collector.get_system_summary(config.array_id)
    print(f"Utilization: {system.utilization_percent}%")
```

### Filter by Storage Group
```python
storage_groups = collector.get_all_storage_groups(config.array_id)
production_sgs = [sg for sg in storage_groups if 'PROD' in sg.storage_group_id]
```

### Export to CSV (requires pandas)
```python
import pandas as pd

snapshot = collector.get_all_capacity_data(config.array_id)

# Convert volumes to DataFrame
volumes_data = [{
    'Volume ID': v.volume_id,
    'Name': v.volume_identifier,
    'Capacity GB': v.capacity_gb,
    'Storage Groups': ','.join(v.storage_groups)
} for v in snapshot.volume_capacities]

df = pd.DataFrame(volumes_data)
df.to_csv('volumes_report.csv', index=False)
```

## 📚 Next Steps

1. **Review Output**: Check JSON export for completeness
2. **Schedule Collection**: Set up Windows Task Scheduler for regular runs
3. **Customize**: Modify `examples.py` for specific use cases
4. **Integrate**: Import JSON into your monitoring/reporting tools

## 🆘 Need Help?

- Review `README.md` for complete documentation
- Check `DEVELOPMENT_PLAN.md` for architecture details
- Review `examples.py` for code samples
- Enable debug logging: Set `level=logging.DEBUG` in code

---

**Estimated First Run Time:**
- Small array (< 1000 volumes): 1-2 minutes
- Medium array (1000-5000 volumes): 5-10 minutes  
- Large array (> 10000 volumes): 20-30 minutes
