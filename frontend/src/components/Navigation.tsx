import { NavLink } from 'react-router-dom';
import { makeStyles, tokens, Text } from '@fluentui/react-components';

const useStyles = makeStyles({
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderRadius: '6px',
    textDecoration: 'none',
    color: tokens.colorNeutralForeground2,
    transition: 'all 0.2s ease',
    cursor: 'pointer',
    ':hover': {
      backgroundColor: tokens.colorNeutralBackground1Hover,
      color: tokens.colorNeutralForeground1,
    },
  },
  navItemActive: {
    backgroundColor: tokens.colorBrandBackground2,
    color: tokens.colorBrandForeground1,
    ':hover': {
      backgroundColor: tokens.colorBrandBackground2Hover,
    },
  },
  navItemIcon: {
    fontSize: '20px',
  },
  navItemText: {
    fontSize: '14px',
    fontWeight: '500',
  },
});

interface NavItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

interface NavigationProps {
  items: NavItem[];
  onItemClick: (label: string) => void;
}

export default function Navigation({ items, onItemClick }: NavigationProps) {
  const styles = useStyles();

  return (
    <nav className={styles.nav}>
      {items.map((item) => (
        <NavLink
          key={item.key}
          to={item.path}
          className={({ isActive }) =>
            isActive ? `${styles.navItem} ${styles.navItemActive}` : styles.navItem
          }
          onClick={() => onItemClick(item.label)}
        >
          <span className={styles.navItemIcon}>{item.icon}</span>
          <Text className={styles.navItemText}>{item.label}</Text>
        </NavLink>
      ))}
    </nav>
  );
}
