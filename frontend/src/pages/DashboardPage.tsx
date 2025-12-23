import { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, List, Avatar, Spin, message } from 'antd';
import { 
  UserOutlined, 
  CloudDownloadOutlined, 
  FilterOutlined, 
  HistoryOutlined,
  GiftOutlined,
  DownloadOutlined,
  UploadOutlined
} from '@ant-design/icons';
import { Line } from '@ant-design/plots';
import { dashboardApi } from '../api';
import dayjs from 'dayjs';

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

// 格式化数字
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const res = await dashboardApi.getDashboardData();
      setData(res.data);
    } catch (e) {
      message.error('获取仪表盘数据失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDashboardData();
    // 每30秒刷新一次数据
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  // 准备趋势图数据
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
    color: '#1668dc',
    point: {
      size: 4,
      shape: 'circle',
    },
    tooltip: {
      formatter: (datum: any) => ({
        name: '下载数量',
        value: datum.downloads
      })
    }
  };

  // 账号表格列
  const accountColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text: string, record: AccountStats) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Avatar icon={<UserOutlined />} size="small" />
          <span>{text}</span>
          {!record.is_active && <Tag color="red">已禁用</Tag>}
        </div>
      )
    },
    {
      title: '上传量',
      dataIndex: 'upload',
      key: 'upload',
      render: (value: number) => (
        <span style={{ color: '#52c41a' }}>
          <UploadOutlined /> {formatBytes(value)}
        </span>
      )
    },
    {
      title: '下载量',
      dataIndex: 'download',
      key: 'download',
      render: (value: number) => (
        <span style={{ color: '#1668dc' }}>
          <DownloadOutlined /> {formatBytes(value)}
        </span>
      )
    },
    {
      title: '分享率',
      dataIndex: 'ratio',
      key: 'ratio',
      render: (value: number) => (
        <Tag color={value >= 1 ? 'green' : value >= 0.5 ? 'orange' : 'red'}>
          {value.toFixed(2)}
        </Tag>
      )
    },
    {
      title: '魔力值',
      dataIndex: 'bonus',
      key: 'bonus',
      render: (value: number) => (
        <span style={{ color: '#722ed1' }}>
          <GiftOutlined /> {formatNumber(value)}
        </span>
      )
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (value: string | null) => 
        value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '从未登录'
    }
  ];

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      {/* 系统概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总账号数"
              value={data.system_stats.total_accounts}
              prefix={<UserOutlined />}
              suffix={`/ ${data.system_stats.active_accounts} 活跃`}
              valueStyle={{ color: '#1668dc' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="自动规则"
              value={data.system_stats.total_rules}
              prefix={<FilterOutlined />}
              suffix={`/ ${data.system_stats.active_rules} 启用`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="下载器"
              value={data.system_stats.total_downloaders}
              prefix={<CloudDownloadOutlined />}
              suffix={`/ ${data.system_stats.active_downloaders} 在线`}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总下载数"
              value={data.system_stats.total_downloads}
              prefix={<HistoryOutlined />}
              suffix={`/ ${data.system_stats.recent_downloads} 今日`}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 下载趋势图 */}
        <Col xs={24} lg={16}>
          <Card title="下载趋势（最近7天）" style={{ height: 400 }}>
            <Line {...trendConfig} height={300} />
          </Card>
        </Col>

        {/* 下载器状态 */}
        <Col xs={24} lg={8}>
          <Card title="下载器状态" style={{ height: 400 }}>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data.downloader_stats.map(downloader => (
                <Card 
                  key={downloader.id} 
                  size="small" 
                  style={{ marginBottom: 12 }}
                  bodyStyle={{ padding: 12 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Tag color={downloader.type === 'qbittorrent' ? 'blue' : 'green'}>
                        {downloader.type === 'qbittorrent' ? 'qB' : 'TR'}
                      </Tag>
                      <strong>{downloader.name}</strong>
                    </div>
                    <Tag color={downloader.is_active ? 'green' : 'red'}>
                      {downloader.is_active ? '在线' : '离线'}
                    </Tag>
                  </div>
                  
                  {downloader.is_active && (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span>下载中:</span>
                        <span style={{ color: '#1668dc', fontWeight: 'bold' }}>
                          {downloader.downloading_count}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span>做种中:</span>
                        <span style={{ color: '#52c41a', fontWeight: 'bold' }}>
                          {downloader.seeding_count}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>未完成:</span>
                        <span style={{ color: '#fa8c16', fontWeight: 'bold' }}>
                          {downloader.incomplete_torrents.length}
                        </span>
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </Card>
        </Col>

        {/* 账号统计 */}
        <Col xs={24}>
          <Card title="账号统计" style={{ marginBottom: 16 }}>
            <Table
              columns={accountColumns}
              dataSource={data.account_stats}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>

        {/* 最近活动 */}
        <Col xs={24}>
          <Card title="最近下载活动">
            <List
              itemLayout="horizontal"
              dataSource={data.recent_activities}
              renderItem={activity => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <Avatar 
                        style={{ 
                          backgroundColor: activity.status === 'completed' ? '#52c41a' : 
                                          activity.status === 'failed' ? '#ff4d4f' : '#1668dc' 
                        }}
                      >
                        {activity.status === 'completed' ? '✓' : 
                         activity.status === 'failed' ? '✗' : '↓'}
                      </Avatar>
                    }
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 'normal' }}>{activity.torrent_name}</span>
                        {activity.discount_type && (
                          <Tag color={activity.discount_type === 'FREE' ? 'green' : 'blue'}>
                            {activity.discount_type}
                          </Tag>
                        )}
                      </div>
                    }
                    description={
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>账号: {activity.account_username}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Tag color={
                            activity.status === 'completed' ? 'green' :
                            activity.status === 'failed' ? 'red' :
                            activity.status === 'expired_deleted' ? 'orange' : 'blue'
                          }>
                            {activity.status === 'completed' ? '已完成' :
                             activity.status === 'failed' ? '失败' :
                             activity.status === 'expired_deleted' ? '已删除' : '下载中'}
                          </Tag>
                          <span style={{ color: '#8c8c8c', fontSize: '12px' }}>
                            {dayjs(activity.created_at).format('MM-DD HH:mm')}
                          </span>
                        </div>
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