import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import {
  makeStyles,
  tokens,
  Text,
  Button,
  Spinner,
} from '@fluentui/react-components';
import {
  Storage24Regular,
  DatabaseArrowRight24Regular,
  Box24Regular,
  DocumentBulletList24Regular,
  ArrowSync24Regular,
} from '@fluentui/react-icons';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import SRPView from './pages/SRPView';
import StorageGroupsView from './pages/StorageGroupsView';
import VolumesView from './pages/VolumesView';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './services/api';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    minHeight: '100vh',
    backgroundColor: tokens.colorNeutralBackground3,
  },
  sidebar: {
    width: '240px',
    backgroundColor: tokens.colorNeutralBackground1,
    borderRight: `1px solid ${tokens.colorNeutralStroke1}`,
    display: 'flex',
    flexDirection: 'column',
    padding: '16px',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px',
    marginBottom: '24px',
  },
  logoIcon: {
    fontSize: '32px',
    color: tokens.colorBrandForeground1,
  },
  logoText: {
    fontSize: '20px',
    fontWeight: '600',
    color: tokens.colorNeutralForeground1,
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    backgroundColor: tokens.colorNeutralBackground1,
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
    padding: '16px 32px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: '24px',
    fontWeight: '600',
    color: tokens.colorNeutralForeground1,
  },
  headerActions: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  content: {
    flex: 1,
    padding: '32px',
    overflowY: 'auto',
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    borderRadius: '4px',
    backgroundColor: tokens.colorNeutralBackground3,
  },
  loadingOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  loadingCard: {
    backgroundColor: tokens.colorNeutralBackground1,
    padding: '32px',
    borderRadius: '8px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
  },
});

export interface AppStatus {
  collection_in_progress: boolean;
  last_collection_time: string | null;
  has_data: boolean;
  error: string | null;
  array_id: string | null;
}

function App() {
  const styles = useStyles();
  const [status, setStatus] = useState<AppStatus | null>(null);
  const [currentPage, setCurrentPage] = useState('Dashboard');
  const { lastMessage, sendMessage } = useWebSocket('ws://localhost:8000/ws');

  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    if (lastMessage) {
      const data = JSON.parse(lastMessage.data);
      if (data.type === 'collection_completed' || data.type === 'collection_error') {
        loadStatus();
      }
    }
  }, [lastMessage]);

  const loadStatus = async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const handleRefresh = async () => {
    try {
      await api.triggerCollection();
      loadStatus();
    } catch (error: any) {
      console.error('Failed to trigger collection:', error);
      if (error.response?.status === 409) {
        alert('Collection already in progress');
      }
    }
  };

  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: <DatabaseArrowRight24Regular />, path: '/' },
    { key: 'srps', label: 'Storage Pools', icon: <Storage24Regular />, path: '/srps' },
    { key: 'storage-groups', label: 'Storage Groups', icon: <Box24Regular />, path: '/storage-groups' },
    { key: 'volumes', label: 'Volumes', icon: <DocumentBulletList24Regular />, path: '/volumes' },
  ];

  return (
    <Router>
      <div className={styles.root}>
        <div className={styles.sidebar}>
          <div className={styles.logo}>
            <Storage24Regular className={styles.logoIcon} />
            <Text className={styles.logoText}>VMAX Dashboard</Text>
          </div>
          <Navigation items={navItems} onItemClick={setCurrentPage} />
        </div>

        <div className={styles.main}>
          <div className={styles.header}>
            <Text className={styles.headerTitle}>{currentPage}</Text>
            <div className={styles.headerActions}>
              {status && (
                <div className={styles.statusBadge}>
                  <Text size={200}>
                    {status.array_id ? `Array: ${status.array_id}` : 'No data'}
                  </Text>
                </div>
              )}
              <Button
                appearance="primary"
                icon={<ArrowSync24Regular />}
                onClick={handleRefresh}
                disabled={status?.collection_in_progress}
              >
                {status?.collection_in_progress ? 'Collecting...' : 'Refresh Data'}
              </Button>
            </div>
          </div>

          <div className={styles.content}>
            <Routes>
              <Route path="/" element={<Dashboard status={status} />} />
              <Route path="/srps" element={<SRPView />} />
              <Route path="/storage-groups" element={<StorageGroupsView />} />
              <Route path="/volumes" element={<VolumesView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </div>

        {status?.collection_in_progress && (
          <div className={styles.loadingOverlay}>
            <div className={styles.loadingCard}>
              <Spinner size="huge" />
              <Text size={500} weight="semibold">Collecting Capacity Data</Text>
              <Text size={300}>This may take several minutes...</Text>
            </div>
          </div>
        )}
      </div>
    </Router>
  );
}

export default App;
