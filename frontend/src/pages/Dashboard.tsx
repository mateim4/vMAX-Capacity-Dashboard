import { useEffect, useState } from 'react';
import {
  makeStyles,
  tokens,
  Card,
  Text,
  ProgressBar,
  Spinner,
  Button,
} from '@fluentui/react-components';
import {
  ArrowSync24Regular,
  Database24Regular,
  Storage24Regular,
  Box24Regular,
  Document24Regular,
} from '@fluentui/react-icons';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../services/api';
import type { AppStatus } from '../App';

const useStyles = makeStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '20px',
  },
  statCard: {
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  statHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  statIcon: {
    fontSize: '32px',
    color: tokens.colorBrandForeground1,
  },
  statValue: {
    fontSize: '36px',
    fontWeight: '600',
    color: tokens.colorNeutralForeground1,
  },
  statLabel: {
    fontSize: '14px',
    color: tokens.colorNeutralForeground3,
  },
  chartCard: {
    padding: '24px',
  },
  chartTitle: {
    fontSize: '18px',
    fontWeight: '600',
    marginBottom: '16px',
  },
  capacityBar: {
    marginTop: '8px',
  },
  noData: {
    padding: '64px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
    gap: '20px',
  },
});

interface DashboardProps {
  status: AppStatus | null;
}

const COLORS = ['#0078D4', '#00B7C3', '#8764B8', '#498205', '#EAA300', '#E3008C'];

export default function Dashboard({ status }: DashboardProps) {
  const styles = useStyles();
  const [summary, setSummary] = useState<any>(null);
  const [srpData, setSrpData] = useState<any[]>([]);
  const [serviceLevelData, setServiceLevelData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status?.has_data) {
      loadDashboardData();
    }
  }, [status]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [summaryRes, systemRes, srpsRes, serviceLevels] = await Promise.all([
        api.getSummary(),
        api.getSystemCapacity(),
        api.getSRPs(),
        api.getServiceLevelBreakdown(),
      ]);

      setSummary({ ...summaryRes, system: systemRes });
      setSrpData(srpsRes);
      setServiceLevelData(serviceLevels);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!status?.has_data) {
    return (
      <Card className={styles.noData}>
        <Database24Regular style={{ fontSize: '64px', color: tokens.colorNeutralForeground3 }} />
        <Text size={600} weight="semibold">No Capacity Data Available</Text>
        <Text size={400}>Click "Refresh Data" to collect capacity information from your VMAX array</Text>
        <Button
          appearance="primary"
          icon={<ArrowSync24Regular />}
          onClick={() => window.location.reload()}
        >
          Refresh Data
        </Button>
      </Card>
    );
  }

  if (loading) {
    return (
      <div className={styles.noData}>
        <Spinner size="huge" />
        <Text size={500}>Loading dashboard data...</Text>
      </div>
    );
  }

  const formatCapacity = (gb: number) => {
    if (gb >= 1000) {
      return `${(gb / 1000).toFixed(2)} TB`;
    }
    return `${gb.toFixed(2)} GB`;
  };

  const systemData = summary?.system;
  const utilizationPercent = systemData?.utilization_percent || 0;

  return (
    <div className={styles.container}>
      {/* Key Metrics Cards */}
      <div className={styles.statsGrid}>
        <Card className={styles.statCard}>
          <div className={styles.statHeader}>
            <Database24Regular className={styles.statIcon} />
            <div>
              <Text className={styles.statLabel}>System Capacity</Text>
              <Text className={styles.statValue}>
                {formatCapacity(systemData?.total_usable_capacity_gb || 0)}
              </Text>
            </div>
          </div>
          <div>
            <Text size={300} style={{ color: tokens.colorNeutralForeground2 }}>
              Used: {formatCapacity(systemData?.effective_used_capacity_gb || 0)}
            </Text>
            <ProgressBar
              className={styles.capacityBar}
              value={utilizationPercent / 100}
              color={utilizationPercent > 80 ? 'error' : utilizationPercent > 60 ? 'warning' : 'success'}
            />
            <Text size={200} style={{ marginTop: '8px', color: tokens.colorNeutralForeground3 }}>
              {utilizationPercent.toFixed(1)}% Utilized
            </Text>
          </div>
        </Card>

        <Card className={styles.statCard}>
          <div className={styles.statHeader}>
            <Storage24Regular className={styles.statIcon} />
            <div>
              <Text className={styles.statLabel}>Storage Pools</Text>
              <Text className={styles.statValue}>{summary?.counts?.srps || 0}</Text>
            </div>
          </div>
          <Text size={300} style={{ color: tokens.colorNeutralForeground2 }}>
            {srpData.length} SRPs configured
          </Text>
        </Card>

        <Card className={styles.statCard}>
          <div className={styles.statHeader}>
            <Box24Regular className={styles.statIcon} />
            <div>
              <Text className={styles.statLabel}>Storage Groups</Text>
              <Text className={styles.statValue}>{summary?.counts?.storage_groups || 0}</Text>
            </div>
          </div>
          <Text size={300} style={{ color: tokens.colorNeutralForeground2 }}>
            Organized capacity allocation
          </Text>
        </Card>

        <Card className={styles.statCard}>
          <div className={styles.statHeader}>
            <Document24Regular className={styles.statIcon} />
            <div>
              <Text className={styles.statLabel}>Volumes</Text>
              <Text className={styles.statValue}>{summary?.counts?.volumes || 0}</Text>
            </div>
          </div>
          <Text size={300} style={{ color: tokens.colorNeutralForeground2 }}>
            Individual storage volumes
          </Text>
        </Card>
      </div>

      {/* Charts */}
      <div className={styles.chartsGrid}>
        {/* SRP Utilization Chart */}
        <Card className={styles.chartCard}>
          <Text className={styles.chartTitle}>Storage Pool Utilization</Text>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={srpData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="srp_id" />
              <YAxis />
              <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
              <Legend />
              <Bar dataKey="utilization_percent" fill={tokens.colorBrandBackground} name="Utilization %" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Service Level Distribution */}
        <Card className={styles.chartCard}>
          <Text className={styles.chartTitle}>Capacity by Service Level</Text>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={serviceLevelData}
                dataKey="total_capacity_gb"
                nameKey="service_level"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={(entry) => `${entry.service_level}: ${(entry.total_capacity_gb / 1000).toFixed(1)} TB`}
              >
                {serviceLevelData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => formatCapacity(value)} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
