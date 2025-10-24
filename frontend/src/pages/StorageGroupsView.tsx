import { useEffect, useState } from 'react';
import {
  makeStyles,
  tokens,
  Card,
  Text,
  Spinner,
  Input,
  Select,
  Button,
  Badge,
} from '@fluentui/react-components';
import {
  Box24Regular,
  Search24Regular,
  Filter24Regular,
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
    gridTemplateColumns: '2fr 1.5fr 1fr 1fr 1fr 1fr',
    padding: '16px',
    backgroundColor: tokens.colorNeutralBackground3,
    fontWeight: '600',
    fontSize: '14px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  tableRow: {
    display: 'grid',
    gridTemplateColumns: '2fr 1.5fr 1fr 1fr 1fr 1fr',
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
});

interface StorageGroup {
  array_id: string;
  storage_group_id: string;
  timestamp: string;
  capacity_gb: number;
  num_volumes: number;
  service_level: string | null;
  srp_name: string | null;
  compression_enabled: boolean;
}

export default function StorageGroupsView() {
  const styles = useStyles();
  const [storageGroups, setStorageGroups] = useState<StorageGroup[]>([]);
  const [filteredGroups, setFilteredGroups] = useState<StorageGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [serviceLevelFilter, setServiceLevelFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    loadStorageGroups();
  }, []);

  useEffect(() => {
    filterStorageGroups();
  }, [storageGroups, searchTerm, serviceLevelFilter]);

  const loadStorageGroups = async () => {
    setLoading(true);
    try {
      const data = await api.getStorageGroups();
      setStorageGroups(data);
    } catch (error) {
      console.error('Failed to load storage groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterStorageGroups = () => {
    let filtered = [...storageGroups];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter((sg) =>
        sg.storage_group_id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Service level filter
    if (serviceLevelFilter !== 'all') {
      filtered = filtered.filter((sg) => sg.service_level === serviceLevelFilter);
    }

    setFilteredGroups(filtered);
    setCurrentPage(1);
  };

  const formatCapacity = (gb: number) => {
    if (gb >= 1000) {
      return `${(gb / 1000).toFixed(2)} TB`;
    }
    return `${gb.toFixed(2)} GB`;
  };

  const getServiceLevels = () => {
    const levels = new Set(storageGroups.map((sg) => sg.service_level).filter((sl) => sl !== null));
    return ['all', ...Array.from(levels)];
  };

  const paginatedGroups = filteredGroups.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const totalPages = Math.ceil(filteredGroups.length / itemsPerPage);

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spinner size="huge" />
        <Text size={500}>Loading Storage Groups...</Text>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Box24Regular className={styles.headerIcon} />
          <div>
            <Text size={600} weight="semibold">Storage Groups</Text>
            <Text size={300} style={{ color: tokens.colorNeutralForeground3 }}>
              {filteredGroups.length} of {storageGroups.length} groups
            </Text>
          </div>
        </div>
      </div>

      <div className={styles.filters}>
        <Input
          className={styles.searchInput}
          placeholder="Search storage groups..."
          contentBefore={<Search24Regular />}
          value={searchTerm}
          onChange={(_, data) => setSearchTerm(data.value)}
        />
        <Select
          value={serviceLevelFilter}
          onChange={(_, data) => setServiceLevelFilter(data.value)}
        >
          {getServiceLevels().map((level) => (
            <option key={level} value={level}>
              {level === 'all' ? 'All Service Levels' : level}
            </option>
          ))}
        </Select>
      </div>

      <Card className={styles.table}>
        <div className={styles.tableHeader}>
          <div>Storage Group</div>
          <div>Service Level</div>
          <div>SRP</div>
          <div>Capacity</div>
          <div>Volumes</div>
          <div>Compression</div>
        </div>
        {paginatedGroups.map((sg) => (
          <div key={sg.storage_group_id} className={styles.tableRow}>
            <Text weight="semibold">{sg.storage_group_id}</Text>
            <Badge appearance="tint" color={sg.service_level ? 'brand' : 'subtle'}>
              {sg.service_level || 'None'}
            </Badge>
            <Text>{sg.srp_name || '-'}</Text>
            <Text>{formatCapacity(sg.capacity_gb)}</Text>
            <Text>{sg.num_volumes}</Text>
            <Badge appearance="outline" color={sg.compression_enabled ? 'success' : 'subtle'}>
              {sg.compression_enabled ? 'Enabled' : 'Disabled'}
            </Badge>
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
