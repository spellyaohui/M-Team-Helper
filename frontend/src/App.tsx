import { useState, useEffect, lazy, Suspense } from 'react';
import { App as AntdApp, ConfigProvider, Layout, Menu, Avatar, Dropdown, Spin, Button, theme } from 'antd';
import {
  UserOutlined,
  SearchOutlined,
  FilterOutlined,
  CloudDownloadOutlined,
  HistoryOutlined,
  LogoutOutlined,
  SettingOutlined,
  DashboardOutlined,
  ControlOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  BellOutlined,
  SunOutlined,
  MoonOutlined,
  DesktopOutlined
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import { authApi } from './api';
import { lightTheme, darkTheme } from './theme';
import { useTheme } from './context/ThemeContext';
import './App.css';

// 懒加载页面组件
const AccountPage = lazy(() => import('./pages/AccountPage'));
const TorrentPage = lazy(() => import('./pages/TorrentPage'));
const RulePage = lazy(() => import('./pages/RulePage'));
const DownloaderPage = lazy(() => import('./pages/DownloaderPage'));
const HistoryPage = lazy(() => import('./pages/HistoryPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

const { Header, Sider, Content } = Layout;

type PageKey = 'dashboard' | 'accounts' | 'torrents' | 'rules' | 'downloaders' | 'history' | 'settings';

const MainLayout = ({
  username,
  onLogout
}: {
  username: string;
  onLogout: () => void;
}) => {
  const { token } = theme.useToken();
  const { mode, setMode, isDarkMode } = useTheme();
  const [currentPage, setCurrentPage] = useState<PageKey>('dashboard');
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: 'torrents', icon: <SearchOutlined />, label: '种子搜索' },
    { key: 'rules', icon: <FilterOutlined />, label: '自动下载' },
    { key: 'history', icon: <HistoryOutlined />, label: '下载历史' },
    { key: 'downloaders', icon: <CloudDownloadOutlined />, label: '下载器' },
    { key: 'accounts', icon: <SettingOutlined />, label: 'PT 账号' },
    { key: 'settings', icon: <ControlOutlined />, label: '系统设置' },
  ];

  const userMenuItems = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: onLogout },
  ];

  const themeMenuItems = [
    {
      key: 'light',
      icon: <SunOutlined />,
      label: '亮色模式',
      onClick: () => setMode('light')
    },
    {
      key: 'dark',
      icon: <MoonOutlined />,
      label: '暗黑模式',
      onClick: () => setMode('dark')
    },
    {
      key: 'system',
      icon: <DesktopOutlined />,
      label: '跟随系统',
      onClick: () => setMode('system')
    },
  ];

  const renderPage = () => {
    const PageComponent = (() => {
      switch (currentPage) {
        case 'dashboard': return DashboardPage;
        case 'accounts': return AccountPage;
        case 'torrents': return TorrentPage;
        case 'rules': return RulePage;
        case 'downloaders': return DownloaderPage;
        case 'history': return HistoryPage;
        case 'settings': return SettingsPage;
        default: return DashboardPage;
      }
    })();

    return (
      <Suspense fallback={
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px'
        }}>
          <Spin size="large" />
        </div>
      }>
        <PageComponent />
      </Suspense>
    );
  };

  return (
    <Layout className="app-layout" style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className="app-sider"
        width={240}
        theme={isDarkMode ? 'dark' : 'light'}
        style={{
          boxShadow: isDarkMode ? '2px 0 8px 0 rgba(0,0,0,0.2)' : '2px 0 8px 0 rgba(29,35,41,.05)',
          zIndex: 20
        }}
      >
        <div className="logo" style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: isDarkMode ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.06)',
          margin: '0 16px 16px 16px'
        }}>
          <span className="logo-icon" style={{ fontSize: 24, marginRight: collapsed ? 0 : 8 }}>🚀</span>
          {!collapsed && <span className="logo-text" style={{
            fontSize: 18,
            fontWeight: 600,
            color: isDarkMode ? '#fff' : '#1f2937'
          }}>M-Team Helper</span>}
        </div>
        <Menu
          theme={isDarkMode ? 'dark' : 'light'}
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems}
          onClick={({ key }) => setCurrentPage(key as PageKey)}
          className="app-menu"
          style={{ borderRight: 'none' }}
        />
      </Sider>
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        <Header style={{
          padding: '0 24px',
          background: token.colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: isDarkMode ? '0 1px 2px rgba(255,255,255,0.05)' : '0 1px 2px rgba(0,0,0,0.03)',
          zIndex: 10,
          height: 64,
          flexShrink: 0,
          transition: 'all 0.2s'
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '16px',
                width: 64,
                height: 64,
              }}
            />
            <span style={{ fontSize: 18, fontWeight: 500, marginLeft: 16, color: token.colorText }}>
              {menuItems.find(m => m.key === currentPage)?.label}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Dropdown menu={{ items: themeMenuItems }} placement="bottomRight" arrow>
              <Button type="text" icon={
                mode === 'light' ? <SunOutlined /> :
                mode === 'dark' ? <MoonOutlined /> :
                <DesktopOutlined />
              } style={{ fontSize: 18 }} />
            </Dropdown>

            <Button type="text" icon={<BellOutlined />} style={{ fontSize: 18 }} />

            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <div className="header-user" style={{
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: 6,
                transition: 'all 0.3s',
                border: `1px solid ${token.colorBorderSecondary}`
              }}>
                <Avatar
                  style={{ backgroundColor: token.colorPrimary, marginRight: 8 }}
                  icon={<UserOutlined />}
                  size="small"
                />
                <span className="user-name" style={{ fontWeight: 500, color: token.colorText }}>{username}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content className="app-content" style={{
          margin: '24px 24px',
          minHeight: 280,
          borderRadius: 12,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          flex: 1
        }}>
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
};

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(true);

  const { isDarkMode } = useTheme();
  const currentTheme = isDarkMode ? darkTheme : lightTheme;

  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUsername = localStorage.getItem('username');

    if (token && savedUsername) {
      authApi.verify(token)
        .then(() => {
          setIsLoggedIn(true);
          setUsername(savedUsername);
        })
        .catch(() => {
          localStorage.removeItem('token');
          localStorage.removeItem('username');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (_token: string, user: string) => {
    setIsLoggedIn(true);
    setUsername(user);
  };

  const handleLogout = () => {
    const token = localStorage.getItem('token');
    if (token) {
      authApi.logout(token);
    }
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setIsLoggedIn(false);
    setUsername('');
  };

  return (
    <ConfigProvider locale={zhCN} theme={currentTheme}>
      <AntdApp>
        {loading ? (
          <div className="loading-container" style={{
            background: isDarkMode ? '#1f2937' : '#f3f4f6',
            height: '100vh',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}>
            <Spin size="large" />
          </div>
        ) : !isLoggedIn ? (
          <LoginPage onLogin={handleLogin} />
        ) : (
          <MainLayout username={username} onLogout={handleLogout} />
        )}
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
