import { useState, useEffect, lazy, Suspense } from 'react';
import { App as AntdApp, ConfigProvider, Layout, Menu, Avatar, Dropdown, Spin, Button } from 'antd';
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
  BellOutlined
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import { authApi } from './api';
import { lightTheme, darkTheme } from './theme';
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

// 检测系统主题偏好
const useSystemTheme = () => {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      setIsDark(mediaQuery.matches);
      
      const handleChange = (e: MediaQueryListEvent) => {
        setIsDark(e.matches);
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, []);

  return isDark;
};

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState<PageKey>('dashboard');
  const [collapsed, setCollapsed] = useState(false);
  
  const isDarkMode = useSystemTheme();
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
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
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

  if (loading) {
    return (
      <ConfigProvider locale={zhCN} theme={currentTheme}>
        <AntdApp>
          <div className="loading-container" style={{ 
            background: isDarkMode ? '#1f2937' : '#f3f4f6',
            height: '100vh',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}>
            <Spin size="large" />
          </div>
        </AntdApp>
      </ConfigProvider>
    );
  }

  if (!isLoggedIn) {
    return (
      <ConfigProvider locale={zhCN} theme={currentTheme}>
        <AntdApp>
          <LoginPage onLogin={handleLogin} />
        </AntdApp>
      </ConfigProvider>
    );
  }

  // 使用 Ant Design 的 useToken 获取当前主题的 token
  // 注意：这里不能直接用 useToken，因为 App 组件本身在 ConfigProvider 外面
  // 所以我们直接用 currentTheme.token 中的值，或者简单的硬编码一些依赖主题的值

  const headerStyle = {
    padding: '0 24px',
    background: isDarkMode ? '#1f2937' : '#ffffff', // 使用主题色
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    boxShadow: isDarkMode ? '0 1px 2px rgba(255,255,255,0.05)' : '0 1px 2px rgba(0,0,0,0.03)',
    zIndex: 10,
    height: 64,
  };

  return (
    <ConfigProvider locale={zhCN} theme={currentTheme}>
      <AntdApp>
        <Layout className="app-layout" style={{ minHeight: '100vh' }}>
          <Sider 
            trigger={null}
            collapsible 
            collapsed={collapsed} 
            className="app-sider"
            width={240}
            theme={isDarkMode ? 'dark' : 'light'}
            style={{
              boxShadow: '2px 0 8px 0 rgba(29,35,41,.05)',
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
          <Layout>
            <Header style={headerStyle}>
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
                <span style={{ fontSize: 18, fontWeight: 500, marginLeft: 16 }}>
                  {menuItems.find(m => m.key === currentPage)?.label}
                </span>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
                <Button type="text" icon={<BellOutlined />} style={{ fontSize: 18 }} />
                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
                  <div className="header-user" style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    padding: '4px 8px',
                    borderRadius: 6,
                    transition: 'all 0.3s'
                  }}>
                    <Avatar 
                      style={{ backgroundColor: '#3b82f6', marginRight: 8 }} 
                      icon={<UserOutlined />} 
                    />
                    <span className="user-name" style={{ fontWeight: 500 }}>{username}</span>
                  </div>
                </Dropdown>
              </div>
            </Header>
            <Content className="app-content" style={{
              margin: '24px 24px',
              minHeight: 280,
              borderRadius: 12,
              overflow: 'initial' // 防止内容被截断
            }}>
              {renderPage()}
            </Content>
          </Layout>
        </Layout>
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
