import { useEffect, useState } from 'react';
import {
  makeStyles,
  tokens,
  Card,
  Text,
  ProgressBar,
  Spinner,
  DataGrid,
  DataGridHeader,
  DataGridRow,
  DataGridHeaderCell,
  DataGridBody,
  DataGridCell,
  TableColumnDefinition,
  createTableColumn,
} from '@fluentui/react-components';
import { Storage24Regular } from '@fluentui/react-icons';
import { api } from '../services/api';

const useStyles = makeStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  headerIcon: {
    fontSize: '32px',
    color: tokens.colorBrandForeground1,
  },
  srpGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
    gap: '20px',
  },
  srpCard: {
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  srpHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  srpName: {
    fontSize: '20px',
    fontWeight: '600',
    color: tokens.colorNeutralForeground1,
  },
  metric: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '14px',
  },
  metricLabel: {
    color: tokens.colorNeutralForeground2,
  },
  metricValue: {
    fontWeight: '600',
    color: tokens.colorNeutralForeground1,
  },
  progressSection: {
    marginTop: '8px',
  },
  loading: {
    padding: '64px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
  },
});

interface SRP {
  array_id: string;
  srp_id: string;
  timestamp: string;
  used_capacity_gb: number;
  subscribed_capacity_gb: number;
  total_managed_space_gb: number;
  free_capacity_gb: number;
  utilization_percent: number;
  subscription_percent: number;
}

export default function SRPView() {
  const styles = useStyles();
  const [srps, setSrps] = useState<SRP[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSRPs();
  }, []);

  const loadSRPs = async () => {
    setLoading(true);
    try {
      const data = await api.getSRPs();
      setSrps(data);
    } catch (error) {
      console.error('Failed to load SRPs:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCapacity = (gb: number) => {
    if (gb >= 1000) {
      return `${(gb / 1000).toFixed(2)} TB`;
    }
    return `${gb.toFixed(2)} GB`;
  };

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spinner size="huge" />
        <Text size={500}>Loading Storage Pools...</Text>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Storage24Regular className={styles.headerIcon} />
        <div>
          <Text size={600} weight="semibold">Storage Resource Pools</Text>
          <Text size={300} style={{ color: tokens.colorNeutralForeground3 }}>
            {srps.length} SRP{srps.length !== 1 ? 's' : ''} configured
          </Text>
        </div>
      </div>

      <div className={styles.srpGrid}>
        {srps.map((srp) => (
          <Card key={srp.srp_id} className={styles.srpCard}>
            <div className={styles.srpHeader}>
              <Text className={styles.srpName}>{srp.srp_id}</Text>
              <Storage24Regular style={{ fontSize: '24px', color: tokens.colorBrandForeground1 }} />
            </div>

            <div className={styles.metric}>
              <span className={styles.metricLabel}>Total Capacity</span>
              <span className={styles.metricValue}>{formatCapacity(srp.total_managed_space_gb)}</span>
            </div>

            <div className={styles.metric}>
              <span className={styles.metricLabel}>Used</span>
              <span className={styles.metricValue}>{formatCapacity(srp.used_capacity_gb)}</span>
            </div>

            <div className={styles.metric}>
              <span className={styles.metricLabel}>Free</span>
              <span className={styles.metricValue}>{formatCapacity(srp.free_capacity_gb)}</span>
            </div>

            <div className={styles.progressSection}>
              <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <Text size={300}>Utilization</Text>
                <Text size={300} weight="semibold">{srp.utilization_percent.toFixed(1)}%</Text>
              </div>
              <ProgressBar
                value={srp.utilization_percent / 100}
                color={srp.utilization_percent > 80 ? 'error' : srp.utilization_percent > 60 ? 'warning' : 'success'}
              />
            </div>

            <div className={styles.progressSection}>
              <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <Text size={300}>Subscription</Text>
                <Text size={300} weight="semibold">{srp.subscription_percent.toFixed(1)}%</Text>
              </div>
              <ProgressBar
                value={Math.min(srp.subscription_percent / 100, 1)}
                color={srp.subscription_percent > 100 ? 'error' : srp.subscription_percent > 80 ? 'warning' : 'success'}
              />
            </div>

            <div className={styles.metric}>
              <span className={styles.metricLabel}>Subscribed</span>
              <span className={styles.metricValue}>{formatCapacity(srp.subscribed_capacity_gb)}</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
