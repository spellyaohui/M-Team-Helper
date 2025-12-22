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
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import AccountPage from './pages/AccountPage';
import TorrentPage from './pages/TorrentPage';
import RulePage from './pages/RulePage';
import DownloaderPage from './pages/DownloaderPage';
import HistoryPage from './pages/HistoryPage';
import { authApi } from './api';
import './App.css';

const { Header, Sider, Content } = Layout;

type PageKey = 'accounts' | 'torrents' | 'rules' | 'downloaders' | 'history';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState<PageKey>('torrents');
  const [collapsed, setCollapsed] = useState(false);

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
    { key: 'torrents', icon: <SearchOutlined />, label: '种子搜索' },
    { key: 'rules', icon: <FilterOutlined />, label: '自动下载' },
    { key: 'history', icon: <HistoryOutlined />, label: '下载历史' },
    { key: 'downloaders', icon: <CloudDownloadOutlined />, label: '下载器' },
    { key: 'accounts', icon: <SettingOutlined />, label: 'PT 账号' },
  ];

  const userMenuItems = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
  ];

  const renderPage = () => {
    switch (currentPage) {
      case 'accounts': return <AccountPage />;
      case 'torrents': return <TorrentPage />;
      case 'rules': return <RulePage />;
      case 'downloaders': return <DownloaderPage />;
      case 'history': return <HistoryPage />;
      default: return <TorrentPage />;
    }
  };

  if (loading) {
    return (
      <ConfigProvider locale={zhCN} theme={{ algorithm: theme.darkAlgorithm }}>
        <div className="loading-container">
          <Spin size="large" />
        </div>
      </ConfigProvider>
    );
  }

  if (!isLoggedIn) {
    return (
      <ConfigProvider locale={zhCN} theme={{ algorithm: theme.darkAlgorithm }}>
        <LoginPage onLogin={handleLogin} />
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider 
      locale={zhCN} 
      theme={{ 
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#1668dc',
          borderRadius: 8,
        },
      }}
    >
      <Layout className="app-layout">
        <Sider 
          collapsible 
          collapsed={collapsed} 
          onCollapse={setCollapsed}
          className="app-sider"
          width={220}
        >
          <div className="logo">
            <span className="logo-icon">🚀</span>
            {!collapsed && <span className="logo-text">M-Team Helper</span>}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[currentPage]}
            items={menuItems}
            onClick={({ key }) => setCurrentPage(key as PageKey)}
            className="app-menu"
          />
        </Sider>
        <Layout>
          <Header className="app-header">
            <div className="header-title">
              {menuItems.find(m => m.key === currentPage)?.label}
            </div>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div className="header-user">
                <Avatar icon={<UserOutlined />} className="user-avatar" />
                <span className="user-name">{username}</span>
              </div>
            </Dropdown>
          </Header>
          <Content className="app-content">
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
