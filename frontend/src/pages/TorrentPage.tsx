import { useState, useEffect } from 'react';
import { Table, Button, Select, Input, Tag, message, Form, InputNumber, Card, Row, Col, theme, Tooltip } from 'antd';
import { SearchOutlined, DownloadOutlined, CloudDownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { accountApi, torrentApi } from '../api';

const { useToken } = theme;

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
  const { token } = useToken();
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
      const formValues = form.getFieldsValue();
      const params = {
        account_id: accountId,
        page: values?.page || 1, // 优先使用传入的 page
        page_size: 20,
        ...formValues,
        ...values,
      };
      
      // 如果不是翻页操作，重置页码
      if (!values?.page) {
        setPage(1);
        params.page = 1;
      } else {
        setPage(values.page);
      }

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
      title: '种子名称', 
      dataIndex: 'name', 
      key: 'name',
      render: (v: string, r: Torrent) => (
        <div style={{ maxWidth: 400 }}>
          <Tooltip title={v}>
            <div style={{ 
              fontWeight: 500, 
              color: token.colorPrimary, 
              marginBottom: 4,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {v}
            </div>
          </Tooltip>
          <div style={{ fontSize: 12, color: token.colorTextSecondary, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <FileTextOutlined /> {r.small_descr || '无描述'}
            </span>
            <span style={{ color: token.colorTextTertiary }}>|</span>
            <span>{r.created_date}</span>
          </div>
        </div>
      )
    },
    { 
      title: '大小', 
      dataIndex: 'size_gb', 
      key: 'size_gb', 
      width: 100,
      render: (v: number) => (
        <span style={{ fontFamily: 'monospace' }}>{v} GB</span>
      )
    },
    { 
      title: '做种/下载', 
      key: 'stats',
      width: 120,
      render: (_: any, r: Torrent) => (
        <div style={{ display: 'flex', gap: 8, fontSize: 13 }}>
          <span style={{ color: token.colorSuccess }}>↑ {r.seeders}</span>
          <span style={{ color: token.colorError }}>↓ {r.leechers}</span>
        </div>
      )
    },
    { 
      title: '优惠信息', 
      key: 'discount',
      width: 120,
      render: (_: any, r: Torrent) => {
        let color = 'default';
        
        if (r.is_free) {
            color = 'success';
        } else if (r.is_2x) {
            color = 'processing';
        } else if (r.discount === 'PERCENT_50') {
            color = 'warning';
        }
        
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
             {r.discount_text !== '普通' && (
                <Tag color={color} style={{ margin: 0, textAlign: 'center' }}>
                    {r.discount_text}
                </Tag>
             )}
          </div>
        );
      }
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      width: 150,
      render: (v: string[]) => (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {v?.map(l => <Tag key={l} style={{ margin: 0, fontSize: 12 }}>{l}</Tag>)}
        </div>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, r: Torrent) => (
        <Button 
          type="primary" 
          ghost 
          size="small" 
          icon={<DownloadOutlined />} 
          onClick={() => handleDownload(r.id)}
        >
          下载
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Card bordered={false} className="modern-card">
        <Form 
          form={form} 
          layout="vertical" 
          onFinish={() => handleSearch({ page: 1 })}
          initialValues={{ mode: 'normal' }}
        >
          <Row gutter={[16, 16]} align="bottom">
            <Col xs={24} sm={12} md={6} lg={4}>
              <Form.Item label="选择账号" style={{ marginBottom: 0 }}>
                <Select
                  value={accountId}
                  onChange={setAccountId}
                  options={accounts.map(a => ({ value: a.id, label: a.username }))}
                  placeholder="请选择账号"
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6} lg={3}>
              <Form.Item name="mode" label="模式" style={{ marginBottom: 0 }}>
                <Select options={modeOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Form.Item name="keyword" label="关键词" style={{ marginBottom: 0 }}>
                <Input placeholder="搜索种子名称/描述" prefix={<SearchOutlined style={{ color: token.colorTextQuaternary }} />} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={4} lg={3}>
              <Form.Item name="discount" label="优惠类型" style={{ marginBottom: 0 }}>
                <Select options={discountOptions} allowClear placeholder="全部" />
              </Form.Item>
            </Col>
            <Col xs={12} sm={6} md={4} lg={2}>
               <Form.Item name="min_size_gb" label="最小(GB)" style={{ marginBottom: 0 }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
               </Form.Item>
            </Col>
            <Col xs={12} sm={6} md={4} lg={2}>
               <Form.Item name="max_size_gb" label="最大(GB)" style={{ marginBottom: 0 }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
               </Form.Item>
            </Col>
            <Col xs={24} sm={24} md={4} lg={4} style={{ textAlign: 'right' }}>
              <Button type="primary" icon={<SearchOutlined />} htmlType="submit" loading={loading} block>
                搜索
              </Button>
            </Col>
          </Row>
        </Form>
      </Card>

      <Card 
        bordered={false} 
        className="modern-card" 
        bodyStyle={{ padding: 0 }}
        title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CloudDownloadOutlined style={{ color: token.colorPrimary }} />
                <span>种子列表</span>
                {total > 0 && <Tag color="blue">{total}</Tag>}
            </div>
        }
      >
        <Table
          columns={columns}
          dataSource={torrents}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            showSizeChanger: false,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p) => handleSearch({ page: p })
          }}
        />
      </Card>
    </div>
  );
}
