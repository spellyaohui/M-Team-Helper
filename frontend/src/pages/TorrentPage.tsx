import { useState, useEffect, useRef } from 'react';
import { App, Table, Button, Select, Input, Tag, Form, InputNumber, Card, Row, Col, theme, Tooltip, Modal, Space } from 'antd';
import { SearchOutlined, DownloadOutlined, CloudDownloadOutlined, FileTextOutlined, SendOutlined } from '@ant-design/icons';
import { accountApi, torrentApi, downloaderApi } from '../api';

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

interface Downloader {
  id: number;
  name: string;
  type: string;
  is_active: boolean;
}

const discountOptions = [
  { value: '', label: '全部' },
  { value: 'FREE', label: '免费' },
  { value: 'PERCENT_50', label: '50%' },
];

const modeOptions = [
  { value: 'normal', label: '普通' },
  { value: 'adult', label: '成人' },
];

export default function TorrentPage() {
  const { message } = App.useApp();
  const { token } = useToken();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [torrents, setTorrents] = useState<Torrent[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [form] = Form.useForm();

  // 动态计算表格高度
  const [tableHeight, setTableHeight] = useState(500);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 使用 ResizeObserver 监听容器高度变化
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        // 减去表头高度 (~55px) 和分页器高度 (~64px) 及预留缓冲
        const height = entry.contentRect.height - 130;
        setTableHeight(Math.max(200, height));
      }
    });

    if (tableContainerRef.current) {
      resizeObserver.observe(tableContainerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // 批量选择和推送相关状态
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [downloaders, setDownloaders] = useState<Downloader[]>([]);
  const [pushModalVisible, setPushModalVisible] = useState(false);
  const [selectedDownloaderId, setSelectedDownloaderId] = useState<number | null>(null);
  const [pushing, setPushing] = useState(false);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [savePath, setSavePath] = useState<string>('');

  useEffect(() => {
    // 加载账号列表
    accountApi.list().then(res => {
      setAccounts(res.data);
      if (res.data.length > 0) setAccountId(res.data[0].id);
    });
    // 加载下载器列表
    downloaderApi.list().then(res => {
      const activeDownloaders = res.data.filter((d: Downloader) => d.is_active);
      setDownloaders(activeDownloaders);
      if (activeDownloaders.length > 0) {
        setSelectedDownloaderId(activeDownloaders[0].id);
      }
    });
  }, []);

  // 当选择的下载器变化时，加载其标签
  useEffect(() => {
    if (selectedDownloaderId) {
      downloaderApi.getTags(selectedDownloaderId).then(res => {
        setAvailableTags(res.data.tags || []);
      }).catch(() => {
        setAvailableTags([]);
      });
    }
  }, [selectedDownloaderId]);

  const handleSearch = async (values?: any) => {
    if (!accountId) {
      message.warning('请先选择账号');
      return;
    }
    setLoading(true);
    setSelectedRowKeys([]); // 搜索时清空选择
    try {
      const formValues = form.getFieldsValue();
      const params = {
        account_id: accountId,
        page: values?.page || 1,
        page_size: 20,
        ...formValues,
        ...values,
      };
      
      if (!values?.page) {
        setPage(1);
        params.page = 1;
      } else {
        setPage(values.page);
      }

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

  // 打开推送弹窗
  const handleOpenPushModal = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要推送的种子');
      return;
    }
    if (downloaders.length === 0) {
      message.warning('没有可用的下载器，请先添加下载器');
      return;
    }
    setPushModalVisible(true);
  };

  // 单个种子推送
  const handlePushSingle = async (torrentId: string) => {
    if (!accountId) return;
    if (downloaders.length === 0) {
      message.warning('没有可用的下载器，请先添加下载器');
      return;
    }
    setSelectedRowKeys([torrentId]);
    setPushModalVisible(true);
  };

  // 执行推送
  const handlePush = async () => {
    if (!accountId || !selectedDownloaderId) {
      message.warning('请选择下载器');
      return;
    }
    
    setPushing(true);
    const results = { success: 0, failed: 0 };
    
    for (const torrentId of selectedRowKeys) {
      try {
        await torrentApi.push({
          torrent_id: torrentId as string,
          downloader_id: selectedDownloaderId,
          account_id: accountId,
          save_path: savePath || undefined,
          tags: selectedTags.length > 0 ? selectedTags : undefined,
        });
        results.success++;
      } catch (e: any) {
        results.failed++;
        console.error(`推送种子 ${torrentId} 失败:`, e);
      }
    }
    
    setPushing(false);
    setPushModalVisible(false);
    setSelectedRowKeys([]);
    setSelectedTags([]);
    setSavePath('');
    
    if (results.failed === 0) {
      message.success(`成功推送 ${results.success} 个种子到下载器`);
    } else {
      message.warning(`推送完成：成功 ${results.success} 个，失败 ${results.failed} 个`);
    }
  };

  const columns = [
    {
      title: '种子名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string, r: Torrent) => (
        <div>
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
      width: 160,
      render: (_: any, r: Torrent) => (
        <Space size="small">
          <Button 
            type="primary" 
            ghost 
            size="small" 
            icon={<DownloadOutlined />} 
            onClick={() => handleDownload(r.id)}
          >
            下载
          </Button>
          <Button
            size="small"
            icon={<SendOutlined />}
            onClick={() => handlePushSingle(r.id)}
            title="推送到下载器"
          >
            推送
          </Button>
        </Space>
      ),
    },
  ];

  // 表格行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
    // virtual + tableLayout=fixed 时，未指定宽度会导致勾选列被均分到大量剩余空间
    columnWidth: 48,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, height: '100%' }}>
      <Card variant="borderless" className="modern-card">
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
        variant="borderless"
        className="modern-card"
        style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { padding: 0, flex: 1, overflow: 'hidden' } }}
        title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CloudDownloadOutlined style={{ color: token.colorPrimary }} />
                <span>种子列表</span>
                {total > 0 && <Tag color="blue">{total}</Tag>}
            </div>
        }
        extra={
          selectedRowKeys.length > 0 && (
            <Button 
              type="primary" 
              icon={<SendOutlined />} 
              onClick={handleOpenPushModal}
            >
              推送选中 ({selectedRowKeys.length})
            </Button>
          )
        }
      >
        <div ref={tableContainerRef} style={{ height: '100%' }}>
          <Table
            virtual
            tableLayout="fixed"
            scroll={{ y: tableHeight }}
            columns={columns}
            dataSource={torrents}
            rowKey="id"
            loading={loading}
            rowSelection={rowSelection}
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
        </div>
      </Card>

      {/* 推送到下载器弹窗 */}
      <Modal
        title="推送到下载器"
        open={pushModalVisible}
        onCancel={() => {
          setPushModalVisible(false);
          setSelectedTags([]);
          setSavePath('');
        }}
        onOk={handlePush}
        confirmLoading={pushing}
        okText="推送"
        cancelText="取消"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>已选择 {selectedRowKeys.length} 个种子</div>
          </div>
          
          <div>
            <div style={{ marginBottom: 8 }}>选择下载器</div>
            <Select
              style={{ width: '100%' }}
              value={selectedDownloaderId}
              onChange={setSelectedDownloaderId}
              options={downloaders.map(d => ({ 
                value: d.id, 
                label: `${d.name} (${d.type})` 
              }))}
              placeholder="请选择下载器"
            />
          </div>
          
          <div>
            <div style={{ marginBottom: 8 }}>保存路径（可选）</div>
            <Input
              value={savePath}
              onChange={e => setSavePath(e.target.value)}
              placeholder="留空使用下载器默认路径"
            />
          </div>
          
          <div>
            <div style={{ marginBottom: 8 }}>标签（可选）</div>
            <Select
              mode="tags"
              style={{ width: '100%' }}
              value={selectedTags}
              onChange={setSelectedTags}
              options={availableTags.map(t => ({ value: t, label: t }))}
              placeholder="选择或输入标签"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
