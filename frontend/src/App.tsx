import { useState, useEffect } from 'react';
import { ConfigProvider, Layout, Menu, theme, Avatar, Dropdown, Spin } from 'antd';
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
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import AccountPage from './pages/AccountPage';
import TorrentPage from './pages/TorrentPage';
import RulePage from './pages/RulePage';
import DownloaderPage from './pages/DownloaderPage';
import HistoryPage from './pages/HistoryPage';
import DashboardPage from './pages/DashboardPage';
import SettingsPage from './pages/SettingsPage';
// import TestSettingsPage from './pages/TestSettingsPage';
import { authApi } from './api';
import './App.css';

const { Header, Sider, Content } = Layout;

type PageKey = 'dashboard' | 'accounts' | 'torrents' | 'rules' | 'downloaders' | 'history' | 'settings';

// 检测系统主题偏好
const useSystemTheme = () => {
  const [isDark, setIsDark] = useState(() => {
    // 初始化时检查系统主题
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      // 设置初始值
      setIsDark(mediaQuery.matches);
      
      // 监听主题变化
      const handleChange = (e: MediaQueryListEvent) => {
        setIsDark(e.matches);
      };
      
      mediaQuery.addEventListener('change', handleChange);
      
      // 清理监听器
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
  
  // 使用系统主题
  const isDarkMode = useSystemTheme();

  useEffect(() => {
    // 检查登录状态
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
    switch (currentPage) {
      case 'dashboard': return <DashboardPage />;
      case 'accounts': return <AccountPage />;
      case 'torrents': return <TorrentPage />;
      case 'rules': return <RulePage />;
      case 'downloaders': return <DownloaderPage />;
      case 'history': return <HistoryPage />;
      case 'settings': return <SettingsPage />;
      default: return <DashboardPage />;
    }
  };

  // 根据系统主题选择算法
  const themeAlgorithm = isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm;
  
  // 主题配置
  const themeConfig = {
    algorithm: themeAlgorithm,
    token: {
      colorPrimary: '#1668dc',
      borderRadius: 8,
      // 根据主题调整一些颜色
      ...(isDarkMode ? {
        colorBgContainer: '#141414',
        colorBgElevated: '#1f1f1f',
      } : {
        colorBgContainer: '#ffffff',
        colorBgElevated: '#ffffff',
      })
    },
  };

  if (loading) {
    return (
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        <div className="loading-container">
          <Spin size="large" />
        </div>
      </ConfigProvider>
    );
  }

  if (!isLoggedIn) {
    return (
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        <LoginPage onLogin={handleLogin} />
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <Layout className="app-layout">
        <Sider 
          collapsible 
          collapsed={collapsed} 
          onCollapse={setCollapsed}
          className="app-sider"
          width={220}
          theme={isDarkMode ? 'dark' : 'light'}
        >
          <div className="logo">
            <span className="logo-icon">🚀</span>
            {!collapsed && <span className="logo-text">M-Team Helper</span>}
          </div>
          <Menu
            theme={isDarkMode ? 'dark' : 'light'}
            mode="inline"
            selectedKeys={[currentPage]}
            items={menuItems}
            onClick={({ key }) => setCurrentPage(key as PageKey)}
            className="app-menu"
          />
        </Sider>
        <Layout>
          <Header className="app-header" style={{
            backgroundColor: isDarkMode ? '#001529' : '#ffffff',
            borderBottom: isDarkMode ? '1px solid #303030' : '1px solid #f0f0f0'
          }}>
            <div className="header-title" style={{
              color: isDarkMode ? '#ffffff' : '#000000'
            }}>
              {menuItems.find(m => m.key === currentPage)?.label}
            </div>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div className="header-user">
                <Avatar icon={<UserOutlined />} className="user-avatar" />
                <span className="user-name" style={{
                  color: isDarkMode ? '#ffffff' : '#000000'
                }}>{username}</span>
              </div>
            </Dropdown>
          </Header>
          <Content className="app-content" style={{
            backgroundColor: isDarkMode ? '#000000' : '#f5f5f5'
          }}>
            <div className="content-wrapper">
              {renderPage()}
            </div>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
