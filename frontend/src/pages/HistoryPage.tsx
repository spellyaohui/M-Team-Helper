import { useState, useEffect } from 'react';
import { Table, Button, Select, Tag, message, Popconfirm } from 'antd';
import { DeleteOutlined, ClearOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { accountApi, historyApi } from '../api';

interface History {
  id: number;
  account_id: number;
  torrent_id: string;
  torrent_name: string;
  torrent_size: number;
  rule_id: number | null;
  downloader_id: number | null;
  status: string;
  discount_type: string | null;
  discount_end_time: string | null;
  created_at: string;
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const statusMap: Record<string, { text: string; color: string }> = {
  downloaded: { text: '已下载', color: 'green' },
  pushing: { text: '推送中', color: 'blue' },
  push_failed: { text: '推送失败', color: 'red' },
  pending: { text: '等待中', color: 'orange' },
  completed: { text: '已完成', color: 'green' },
  expired_deleted: { text: '过期已删', color: 'volcano' },
  failed: { text: '失败', color: 'red' },
};

const discountMap: Record<string, { text: string; color: string }> = {
  FREE: { text: '免费', color: 'green' },
  _2X_FREE: { text: '2x免费', color: 'cyan' },
  PERCENT_50: { text: '50%', color: 'blue' },
  _2X_PERCENT_50: { text: '2x50%', color: 'purple' },
  _2X: { text: '2x上传', color: 'gold' },
  NORMAL: { text: '无优惠', color: 'default' },
};

export default function HistoryPage() {
  const [history, setHistory] = useState<History[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [accountId, setAccountId] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  useEffect(() => {
    accountApi.list().then(res => setAccounts(res.data));
  }, []);

  const fetchHistory = async (p = page, accId = accountId) => {
    setLoading(true);
    try {
      const res = await historyApi.list({ account_id: accId, page: p, page_size: 20 });
      setHistory(res.data.data);
      setTotal(res.data.total);
    } catch (e) {
      message.error('获取历史记录失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleDelete = async (id: number) => {
    try {
      await historyApi.delete(id);
      message.success('删除成功');
      fetchHistory();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const handleClear = async () => {
    try {
      await historyApi.clear(accountId);
      message.success('清空成功');
      fetchHistory();
    } catch (e) {
      message.error('清空失败');
    }
  };

  const columns = [
    { 
      title: '种子名称', 
      dataIndex: 'torrent_name', 
      key: 'torrent_name',
      width: 300,
      ellipsis: true,
    },
    { title: '大小', dataIndex: 'torrent_size', key: 'torrent_size', render: formatBytes, width: 100 },
    { 
      title: '账号', 
      dataIndex: 'account_id', 
      key: 'account_id',
      width: 100,
      render: (v: number) => accounts.find(a => a.id === v)?.username || '-'
    },
    {
      title: '促销',
      dataIndex: 'discount_type',
      key: 'discount_type',
      width: 80,
      render: (v: string | null) => {
        if (!v) return '-';
        const d = discountMap[v] || { text: v, color: 'default' };
        return <Tag color={d.color}>{d.text}</Tag>;
      }
    },
    {
      title: '促销到期',
      dataIndex: 'discount_end_time',
      key: 'discount_end_time',
      width: 160,
      render: (v: string | null) => {
        if (!v) return '-';
        const endTime = dayjs(v);
        const isExpired = endTime.isBefore(dayjs());
        return (
          <span style={{ color: isExpired ? '#ff4d4f' : '#52c41a' }}>
            {endTime.format('MM-DD HH:mm')}
            {isExpired ? ' (已过期)' : ''}
          </span>
        );
      }
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      width: 100,
      render: (v: string) => {
        const s = statusMap[v] || { text: v, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      }
    },
    { 
      title: '添加时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      width: 160,
      render: (v: string) => dayjs(v).format('MM-DD HH:mm:ss')
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: any, r: History) => (
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
          <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <Select
          style={{ width: 150 }}
          placeholder="全部账号"
          allowClear
          value={accountId}
          onChange={(v) => { setAccountId(v); setPage(1); fetchHistory(1, v); }}
          options={accounts.map(a => ({ value: a.id, label: a.username }))}
        />
        <Popconfirm title="确定清空所有记录？" onConfirm={handleClear}>
          <Button danger icon={<ClearOutlined />}>清空历史</Button>
        </Popconfirm>
      </div>
      
      <Table
        columns={columns}
        dataSource={history}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: (p) => { setPage(p); fetchHistory(p); }
        }}
      />
    </>
  );
}
