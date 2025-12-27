import { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Tag, List, Avatar, Spin, message, theme, Tooltip, Progress } from 'antd';
import { 
  UserOutlined, 
  CloudDownloadOutlined, 
  FilterOutlined, 
  HistoryOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { Line } from '@ant-design/plots';
import { dashboardApi } from '../api';
import dayjs from 'dayjs';

const { useToken } = theme;

interface AccountStats {
  id: number;
  username: string;
  upload: number;
  download: number;
  ratio: number;
  bonus: number;
  last_login: string | null;
  is_active: boolean;
}

interface DownloaderStats {
  id: number;
  name: string;
  type: string;
  downloading_count: number;
  seeding_count: number;
  incomplete_torrents: any[];
  is_active: boolean;
  download_speed: number;
  upload_speed: number;
  connection_status: string;
  free_space_gb: number;
  free_space_bytes: number;
}

interface SystemStats {
  total_accounts: number;
  active_accounts: number;
  total_rules: number;
  active_rules: number;
  total_downloaders: number;
  active_downloaders: number;
  total_downloads: number;
  recent_downloads: number;
}

interface RecentActivity {
  id: number;
  torrent_name: string;
  account_username: string;
  status: string;
  created_at: string;
  discount_type: string | null;
}

interface DashboardData {
  system_stats: SystemStats;
  account_stats: AccountStats[];
  downloader_stats: DownloaderStats[];
  recent_activities: RecentActivity[];
  download_trends: Record<string, number>;
}

// 格式化文件大小
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化速度
const formatSpeed = (bytesPerSecond: number): string => {
  if (bytesPerSecond === 0) return '0 B/s';
  const k = 1024;
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
  const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k));
  return parseFloat((bytesPerSecond / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

// 格式化数字
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

const StatCard = ({ title, value, suffix, icon, color, loading }: any) => {
  const { token } = useToken();
  
  return (
    <Card className="modern-card" bordered={false} bodyStyle={{ padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ color: token.colorTextSecondary, fontSize: 14, marginBottom: 4 }}>{title}</div>
          <div style={{ fontSize: 28, fontWeight: 600, lineHeight: 1.2, color: token.colorTextHeading }}>
            {loading ? <Spin size="small" /> : value}
          </div>
          {suffix && (
            <div style={{ marginTop: 8, fontSize: 13, color: token.colorTextSecondary }}>
              {suffix}
            </div>
          )}
        </div>
        <div 
          className="stat-icon-wrapper"
          style={{ 
            background: `${color}15`, // 15 is approx 8% opacity in hex
            color: color,
            marginBottom: 0
          }}
        >
          {icon}
        </div>
      </div>
    </Card>
  );
};

export default function DashboardPage() {
  const { token } = useToken();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadersLoading, setDownloadersLoading] = useState(false);

  const fetchDashboardData = async () => {
    // 首次加载显示 loading，后续静默更新
    if (!data) setLoading(true);
    try {
      const res = await dashboardApi.getDashboardData();
      setData(res.data);
    } catch (e) {
      message.error('获取仪表盘数据失败');
    }
    setLoading(false);
  };

  const fetchDownloaderStats = async () => {
    if (!data) return;
    
    setDownloadersLoading(true);
    try {
      const res = await dashboardApi.getDownloaderStats();
      setData(prevData => ({
        ...prevData!,
        downloader_stats: res.data.downloader_stats
      }));
    } catch (e) {
      console.error('获取下载器状态失败', e);
    }
    setDownloadersLoading(false);
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (!data) return;

    let downloaderInterval: number;
    let dashboardInterval: number;
    
    const startAutoRefresh = () => {
      // 优化：增加下载器状态刷新间隔，从 15 秒改为 30 秒
      downloaderInterval = setInterval(() => {
        if (!document.hidden) {  // 仅在页面可见时刷新
          fetchDownloaderStats();
        }
      }, 30000);
      
      // 仪表板数据刷新间隔从 60 秒改为 120 秒
      dashboardInterval = setInterval(() => {
        if (!document.hidden) {  // 仅在页面可见时刷新
          fetchDashboardData();
        }
      }, 120000);
    };
    
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 页面不可见时清除定时器
        if (downloaderInterval) clearInterval(downloaderInterval);
        if (dashboardInterval) clearInterval(dashboardInterval);
      } else {
        // 页面可见时重新开始刷新
        startAutoRefresh();
      }
    };
    
    // 监听页面可见性变化
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // 初始启动
    startAutoRefresh();
    
    return () => {
      if (downloaderInterval) clearInterval(downloaderInterval);
      if (dashboardInterval) clearInterval(dashboardInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [data]);

  if (loading && !data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) return null;

  const trendData = Object.entries(data.download_trends)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({
      date: dayjs(date).format('MM-DD'),
      downloads: count
    }));

  const trendConfig = {
    data: trendData,
    xField: 'date',
    yField: 'downloads',
    smooth: true,
    color: token.colorPrimary,
    point: {
      size: 4,
      shape: 'circle',
      style: {
        fill: '#fff',
        stroke: token.colorPrimary,
        lineWidth: 2,
      },
    },
    tooltip: {
      showMarkers: false,
    },
    areaStyle: () => {
      return {
        fill: `l(270) 0:#ffffff 0.5:${token.colorPrimary}20 1:${token.colorPrimary}40`,
      };
    },
  };

  const accountColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text: string, record: AccountStats) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Avatar 
            icon={<UserOutlined />} 
            size="small" 
            style={{ backgroundColor: record.is_active ? token.colorPrimary : token.colorTextDisabled }} 
          />
          <div>
            <div style={{ fontWeight: 500 }}>{text}</div>
            {!record.is_active && <Tag color="red" style={{ margin: 0, fontSize: 10, lineHeight: '16px' }}>已禁用</Tag>}
          </div>
        </div>
      )
    },
    {
      title: '数据量',
      key: 'data',
      render: (_: any, record: AccountStats) => (
        <div style={{ fontSize: 13 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: token.colorSuccess }}>
            <ArrowUpOutlined style={{ fontSize: 12 }} /> {formatBytes(record.upload)}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: token.colorPrimary }}>
            <ArrowDownOutlined style={{ fontSize: 12 }} /> {formatBytes(record.download)}
          </div>
        </div>
      )
    },
    {
      title: '分享率',
      dataIndex: 'ratio',
      key: 'ratio',
      render: (value: number) => {
        let color = token.colorError;
        if (value >= 1) color = token.colorSuccess;
        else if (value >= 0.5) color = token.colorWarning;
        
        return (
          <div style={{ fontWeight: 600, color }}>
            {value.toFixed(2)}
          </div>
        );
      }
    },
    {
      title: '魔力值',
      dataIndex: 'bonus',
      key: 'bonus',
      render: (value: number) => (
        <span style={{ color: '#722ed1', fontWeight: 500 }}>
          {formatNumber(value)}
        </span>
      )
    }
  ];

  return (
    <div style={{ paddingBottom: 24 }}>
      {/* 顶部统计卡片 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="总账号数"
            value={data.system_stats.total_accounts}
            suffix={<span style={{ color: token.colorSuccess }}>{data.system_stats.active_accounts} 个活跃中</span>}
            icon={<UserOutlined />}
            color={token.colorPrimary}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="自动规则"
            value={data.system_stats.total_rules}
            suffix={<span style={{ color: token.colorSuccess }}>{data.system_stats.active_rules} 个启用中</span>}
            icon={<FilterOutlined />}
            color={token.colorSuccess}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="下载器"
            value={data.system_stats.total_downloaders}
            suffix={<span style={{ color: token.colorSuccess }}>{data.system_stats.active_downloaders} 个在线</span>}
            icon={<CloudDownloadOutlined />}
            color="#722ed1"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="今日下载"
            value={data.system_stats.recent_downloads}
            suffix={`总计 ${data.system_stats.total_downloads} 个种子`}
            icon={<HistoryOutlined />}
            color={token.colorWarning}
          />
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        {/* 左侧主要内容 */}
        <Col xs={24} lg={16}>
          {/* 下载趋势 */}
          <Card 
            title="下载趋势 (近7天)" 
            className="modern-card" 
            bordered={false}
            style={{ marginBottom: 24 }}
          >
            <div style={{ height: 300 }}>
              <Line {...trendConfig} />
            </div>
          </Card>

          {/* 账号列表 */}
          <Card 
            title="账号状态" 
            className="modern-card" 
            bordered={false}
          >
            <Table
              columns={accountColumns}
              dataSource={data.account_stats}
              rowKey="id"
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>

        {/* 右侧边栏 */}
        <Col xs={24} lg={8}>
          {/* 下载器状态 */}
          <Card 
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>下载器状态</span>
                {downloadersLoading && <Spin size="small" />}
              </div>
            }
            className="modern-card" 
            bordered={false}
            style={{ marginBottom: 24 }}
            bodyStyle={{ padding: '12px 12px' }}
          >
            <div style={{ maxHeight: 600, overflowY: 'auto' }}>
              {data.downloader_stats.map(downloader => (
                <Card 
                  key={downloader.id} 
                  size="small"
                  bordered={false}
                  style={{ 
                    marginBottom: 12,
                    background: token.colorBgLayout,
                    borderRadius: token.borderRadiusLG
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Avatar 
                        size="small" 
                        shape="square"
                        style={{ 
                          backgroundColor: downloader.type === 'qbittorrent' ? '#2f6eb5' : '#1e6823' 
                        }}
                      >
                        {downloader.type === 'qbittorrent' ? 'qB' : 'TR'}
                      </Avatar>
                      <span style={{ fontWeight: 600 }}>{downloader.name}</span>
                    </div>
                    <Tag color={downloader.is_active ? 'success' : 'error'} style={{ margin: 0 }}>
                      {downloader.is_active ? '在线' : '离线'}
                    </Tag>
                  </div>

                  {downloader.is_active && (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                        <div style={{ background: token.colorBgContainer, padding: 8, borderRadius: 6 }}>
                          <div style={{ fontSize: 12, color: token.colorTextSecondary }}>下载速度</div>
                          <div style={{ color: token.colorPrimary, fontWeight: 600 }}>
                            {formatSpeed(downloader.download_speed)}
                          </div>
                        </div>
                        <div style={{ background: token.colorBgContainer, padding: 8, borderRadius: 6 }}>
                          <div style={{ fontSize: 12, color: token.colorTextSecondary }}>上传速度</div>
                          <div style={{ color: token.colorSuccess, fontWeight: 600 }}>
                            {formatSpeed(downloader.upload_speed)}
                          </div>
                        </div>
                      </div>

                      <div style={{ marginBottom: 8 }}>
                         <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                            <span>剩余空间</span>
                            <span>{formatBytes(downloader.free_space_bytes)}</span>
                         </div>
                         <Progress 
                            percent={Math.min(100, Math.max(0, 100 - (downloader.free_space_bytes / (downloader.free_space_bytes + 1000000000000)) * 100))} // 这里只是个模拟，因为不知道总空间
                            showInfo={false} 
                            size="small"
                            status="active"
                            strokeColor={token.colorPrimary}
                         />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: token.colorTextSecondary }}>
                        <span>下载: {downloader.downloading_count}</span>
                        <span>做种: {downloader.seeding_count}</span>
                        <span>未完成: {downloader.incomplete_torrents.length}</span>
                      </div>
                    </>
                  )}
                </Card>
              ))}
            </div>
          </Card>

          {/* 最近活动 */}
          <Card 
            title="最近活动" 
            className="modern-card" 
            bordered={false}
            bodyStyle={{ padding: '0 24px' }}
          >
            <List
              itemLayout="horizontal"
              dataSource={data.recent_activities.slice(0, 5)}
              renderItem={activity => (
                <List.Item style={{ padding: '16px 0' }}>
                  <List.Item.Meta
                    avatar={
                      <div style={{ 
                        width: 36, 
                        height: 36, 
                        borderRadius: '50%', 
                        background: activity.status === 'completed' ? '#f6ffed' : '#e6f7ff',
                        border: `1px solid ${activity.status === 'completed' ? '#b7eb8f' : '#91caff'}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: activity.status === 'completed' ? '#52c41a' : '#1890ff'
                      }}>
                        {activity.status === 'completed' ? <CheckCircleOutlined /> : <CloudDownloadOutlined />}
                      </div>
                    }
                    title={
                      <Tooltip title={activity.torrent_name}>
                        <div style={{ 
                          width: '100%', 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis', 
                          whiteSpace: 'nowrap',
                          fontSize: 14 
                        }}>
                          {activity.torrent_name}
                        </div>
                      </Tooltip>
                    }
                    description={
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginTop: 4 }}>
                        <span>{activity.account_username}</span>
                        <span>{dayjs(activity.created_at).format('MM-DD HH:mm')}</span>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
