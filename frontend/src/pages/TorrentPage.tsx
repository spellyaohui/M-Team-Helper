import { useState, useEffect } from 'react';
import { Table, Button, Select, Input, Tag, message, Form, InputNumber } from 'antd';
import { SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import { accountApi, torrentApi } from '../api';

interface Torrent {
  id: string;
  name: string;
  small_descr: string;
  size_gb: number;
  seeders: number;
  leechers: number;
  discount: string;
  discount_text: string;
  is_free: boolean;
  is_2x: boolean;
  created_date: string;
  labels: string[];
}

interface Account {
  id: number;
  username: string;
}

const discountOptions = [
  { value: '', label: '全部' },
  { value: 'FREE', label: '免费' },
  { value: '_2X_FREE', label: '2x免费' },
  { value: 'PERCENT_50', label: '50%' },
  { value: '_2X', label: '2x上传' },
];

const modeOptions = [
  { value: 'normal', label: '普通' },
  { value: 'adult', label: '成人' },
];

export default function TorrentPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [torrents, setTorrents] = useState<Torrent[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [form] = Form.useForm();

  useEffect(() => {
    accountApi.list().then(res => {
      setAccounts(res.data);
      if (res.data.length > 0) setAccountId(res.data[0].id);
    });
  }, []);

  const handleSearch = async (values?: any) => {
    if (!accountId) {
      message.warning('请先选择账号');
      return;
    }
    setLoading(true);
    try {
      const params = {
        account_id: accountId,
        page,
        page_size: 20,
        ...form.getFieldsValue(),
        ...values,
      };
      // 清理空值
      Object.keys(params).forEach(k => {
        if (params[k] === '' || params[k] === undefined) delete params[k];
      });
      const res = await torrentApi.search(params);
      setTorrents(res.data.data);
      setTotal(res.data.total);
    } catch (e: any) {
      message.error(e.response?.data?.detail || '搜索失败');
    }
    setLoading(false);
  };

  const handleDownload = async (torrentId: string) => {
    if (!accountId) return;
    try {
      const res = await torrentApi.getDownloadUrl(torrentId, accountId);
      window.open(res.data.url, '_blank');
      message.success('已获取下载链接');
    } catch (e) {
      message.error('获取下载链接失败');
    }
  };

  const columns = [
    { 
      title: '名称', 
      dataIndex: 'name', 
      key: 'name',
      width: 400,
      render: (v: string, r: Torrent) => (
        <div>
          <div>{v}</div>
          <div style={{ fontSize: 12, color: '#888' }}>{r.small_descr}</div>
        </div>
      )
    },
    { title: '大小', dataIndex: 'size_gb', key: 'size_gb', render: (v: number) => `${v} GB` },
    { title: '做种', dataIndex: 'seeders', key: 'seeders' },
    { title: '下载', dataIndex: 'leechers', key: 'leechers' },
    { 
      title: '优惠', 
      dataIndex: 'discount_text', 
      key: 'discount',
      render: (v: string, r: Torrent) => {
        let color = 'default';
        if (r.is_free) color = 'green';
        else if (r.is_2x) color = 'blue';
        else if (r.discount === 'PERCENT_50') color = 'orange';
        return <Tag color={color}>{v}</Tag>;
      }
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      render: (v: string[]) => v?.map(l => <Tag key={l}>{l}</Tag>)
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, r: Torrent) => (
        <Button size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(r.id)}>
          下载
        </Button>
      ),
    },
  ];

  return (
    <>
      <Form form={form} layout="inline" style={{ marginBottom: 16, flexWrap: 'wrap', gap: 8 }} onFinish={handleSearch}>
        <Form.Item label="账号">
          <Select
            style={{ width: 150 }}
            value={accountId}
            onChange={setAccountId}
            options={accounts.map(a => ({ value: a.id, label: a.username }))}
          />
        </Form.Item>
        <Form.Item name="mode" label="模式" initialValue="normal">
          <Select style={{ width: 100 }} options={modeOptions} />
        </Form.Item>
        <Form.Item name="keyword" label="关键词">
          <Input placeholder="搜索关键词" style={{ width: 200 }} />
        </Form.Item>
        <Form.Item name="discount" label="优惠">
          <Select style={{ width: 120 }} options={discountOptions} allowClear />
        </Form.Item>
        <Form.Item name="min_size_gb" label="最小">
          <InputNumber placeholder="GB" style={{ width: 80 }} />
        </Form.Item>
        <Form.Item name="max_size_gb" label="最大">
          <InputNumber placeholder="GB" style={{ width: 80 }} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" icon={<SearchOutlined />} htmlType="submit">搜索</Button>
        </Form.Item>
      </Form>

      <Table
        columns={columns}
        dataSource={torrents}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: (p) => { setPage(p); handleSearch({ page: p }); }
        }}
      />
    </>
  );
}
