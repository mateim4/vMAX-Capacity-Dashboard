import { useEffect, useState } from 'react';
import {
  makeStyles,
  tokens,
  Card,
  Text,
  Spinner,
  Input,
  Button,
  Badge,
} from '@fluentui/react-components';
import {
  Document24Regular,
  Search24Regular,
} from '@fluentui/react-icons';
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
    justifyContent: 'space-between',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  headerIcon: {
    fontSize: '32px',
    color: tokens.colorBrandForeground1,
  },
  filters: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
  },
  searchInput: {
    minWidth: '300px',
  },
  table: {
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: '8px',
    overflow: 'hidden',
  },
  tableHeader: {
    display: 'grid',
    gridTemplateColumns: '1.5fr 2fr 1fr 1fr 2fr',
    padding: '16px',
    backgroundColor: tokens.colorNeutralBackground3,
    fontWeight: '600',
    fontSize: '14px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  tableRow: {
    display: 'grid',
    gridTemplateColumns: '1.5fr 2fr 1fr 1fr 2fr',
    padding: '16px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
    ':hover': {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  loading: {
    padding: '64px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px',
  },
  storageGroupBadges: {
    display: 'flex',
    gap: '4px',
    flexWrap: 'wrap',
  },
});

interface Volume {
  array_id: string;
  volume_id: string;
  volume_identifier: string;
  timestamp: string;
  capacity_gb: number;
  allocated_percent: number;
  storage_groups: string[];
  wwn: string | null;
  emulation_type: string | null;
}

export default function VolumesView() {
  const styles = useStyles();
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [filteredVolumes, setFilteredVolumes] = useState<Volume[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const itemsPerPage = 100;

  useEffect(() => {
    loadVolumes();
  }, [currentPage]);

  useEffect(() => {
    filterVolumes();
  }, [volumes, searchTerm]);

  const loadVolumes = async () => {
    setLoading(true);
    try {
      const response = await api.getVolumes({
        limit: itemsPerPage,
        offset: (currentPage - 1) * itemsPerPage,
      });
      
      if (response.items) {
        setVolumes(response.items);
        setTotalCount(response.total);
      } else {
        setVolumes(response);
        setTotalCount(response.length);
      }
    } catch (error) {
      console.error('Failed to load volumes:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterVolumes = () => {
    if (!searchTerm) {
      setFilteredVolumes(volumes);
      return;
    }

    const filtered = volumes.filter(
      (vol) =>
        vol.volume_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        vol.volume_identifier.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredVolumes(filtered);
  };

  const formatCapacity = (gb: number) => {
    if (gb >= 1000) {
      return `${(gb / 1000).toFixed(2)} TB`;
    }
    return `${gb.toFixed(2)} GB`;
  };

  const totalPages = Math.ceil(totalCount / itemsPerPage);

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spinner size="huge" />
        <Text size={500}>Loading Volumes...</Text>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Document24Regular className={styles.headerIcon} />
          <div>
            <Text size={600} weight="semibold">Volumes</Text>
            <Text size={300} style={{ color: tokens.colorNeutralForeground3 }}>
              {totalCount} total volumes
            </Text>
          </div>
        </div>
      </div>

      <div className={styles.filters}>
        <Input
          className={styles.searchInput}
          placeholder="Search by volume ID or name..."
          contentBefore={<Search24Regular />}
          value={searchTerm}
          onChange={(_, data) => setSearchTerm(data.value)}
        />
      </div>

      <Card className={styles.table}>
        <div className={styles.tableHeader}>
          <div>Volume ID</div>
          <div>Identifier</div>
          <div>Capacity</div>
          <div>Allocated</div>
          <div>Storage Groups</div>
        </div>
        {filteredVolumes.map((vol) => (
          <div key={vol.volume_id} className={styles.tableRow}>
            <Text weight="semibold">{vol.volume_id}</Text>
            <Text>{vol.volume_identifier || '-'}</Text>
            <Text>{formatCapacity(vol.capacity_gb)}</Text>
            <Text>{vol.allocated_percent.toFixed(1)}%</Text>
            <div className={styles.storageGroupBadges}>
              {vol.storage_groups.length > 0 ? (
                vol.storage_groups.map((sg, idx) => (
                  <Badge key={idx} appearance="tint" size="small">
                    {sg}
                  </Badge>
                ))
              ) : (
                <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
                  No storage groups
                </Text>
              )}
            </div>
          </div>
        ))}
      </Card>

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <Text size={300}>
            Page {currentPage} of {totalPages}
          </Text>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
