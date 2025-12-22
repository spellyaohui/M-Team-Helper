import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Switch, InputNumber, Select, message, Space, Tag, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { accountApi, ruleApi, downloaderApi } from '../api';

interface Rule {
  id: number;
  account_id: number;
  name: string;
  is_enabled: boolean;
  mode: string;
  free_only: boolean;
  double_upload: boolean;
  min_size: number | null;
  max_size: number | null;
  min_seeders: number | null;
  max_seeders: number | null;
  keywords: string | null;
  exclude_keywords: string | null;
  downloader_id: number | null;
  save_path: string | null;
  tags: string[] | null;
  max_downloading: number | null;
}

const modeOptions = [
  { value: 'normal', label: '普通' },
  { value: 'adult', label: '成人' },
];

export default function RulePage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [downloaders, setDownloaders] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [tagsLoading, setTagsLoading] = useState(false);
  const [form] = Form.useForm();

  // 监听下载器选择变化，获取对应的标签列表
  const selectedDownloaderId = Form.useWatch('downloader_id', form);

  useEffect(() => {
    if (selectedDownloaderId) {
      setTagsLoading(true);
      downloaderApi.getTags(selectedDownloaderId)
        .then(res => {
          setAvailableTags(res.data.tags || []);
        })
        .catch(() => {
          setAvailableTags([]);
        })
        .finally(() => {
          setTagsLoading(false);
        });
    } else {
      setAvailableTags([]);
    }
  }, [selectedDownloaderId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      console.log('开始获取数据...');
      const [rulesRes, accountsRes, downloadersRes] = await Promise.all([
        ruleApi.list(),
        accountApi.list(),
        downloaderApi.list(),
      ]);
      console.log('账号响应:', accountsRes);
      console.log('规则响应:', rulesRes);
      console.log('下载器响应:', downloadersRes);
      setRules(Array.isArray(rulesRes.data) ? rulesRes.data : []);
      setAccounts(Array.isArray(accountsRes.data) ? accountsRes.data : []);
      setDownloaders(Array.isArray(downloadersRes.data) ? downloadersRes.data : []);
    } catch (e: any) {
      message.error('获取数据失败');
      console.error('获取数据失败:', e);
      console.error('错误详情:', e.response?.status, e.response?.data);
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const handleSubmit = async (values: any) => {
    try {
      if (editingRule) {
        await ruleApi.update(editingRule.id, values);
        message.success('更新成功');
      } else {
        await ruleApi.create(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingRule(null);
      fetchData();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '操作失败');
    }
  };

  const handleEdit = (rule: Rule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await ruleApi.delete(id);
      message.success('删除成功');
      fetchData();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const handleToggle = async (id: number) => {
    try {
      await ruleApi.toggle(id);
      fetchData();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const columns = [
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { 
      title: '账号', 
      dataIndex: 'account_id', 
      key: 'account_id',
      render: (v: number) => accounts.find(a => a.id === v)?.username || '-'
    },
    { 
      title: '状态', 
      dataIndex: 'is_enabled', 
      key: 'is_enabled',
      render: (v: boolean, r: Rule) => (
        <Switch checked={v} onChange={() => handleToggle(r.id)} />
      )
    },
    { 
      title: '条件', 
      key: 'conditions',
      render: (_: any, r: Rule) => (
        <Space wrap>
          <Tag color={r.mode === 'adult' ? 'magenta' : 'default'}>{r.mode === 'adult' ? '成人' : '普通'}</Tag>
          {r.free_only && <Tag color="green">免费</Tag>}
          {r.double_upload && <Tag color="blue">2x上传</Tag>}
          {r.min_size && <Tag>≥{r.min_size}GB</Tag>}
          {r.max_size && <Tag>≤{r.max_size}GB</Tag>}
          {r.keywords && <Tag>关键词: {r.keywords}</Tag>}
          {r.tags && r.tags.length > 0 && <Tag color="purple">标签: {r.tags.join(', ')}</Tag>}
        </Space>
      )
    },
    { 
      title: '下载器', 
      dataIndex: 'downloader_id', 
      key: 'downloader_id',
      render: (v: number, r: Rule) => {
        const name = downloaders.find(d => d.id === v)?.name || '不推送';
        const limit = r.max_downloading ? ` (≤${r.max_downloading})` : '';
        return name + limit;
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, r: Rule) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRule(null); form.resetFields(); setModalOpen(true); }}>
          添加规则
        </Button>
      </div>
      <Table columns={columns} dataSource={rules} rowKey="id" loading={loading} />
      
      <Modal 
        title={editingRule ? '编辑规则' : '添加规则'} 
        open={modalOpen} 
        onCancel={() => { setModalOpen(false); setEditingRule(null); }} 
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} size="small">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item name="account_id" label="账号" rules={[{ required: true }]}>
              <Select options={accounts.map(a => ({ value: a.id, label: a.username }))} />
            </Form.Item>
            <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
              <Input placeholder="如：免费电影" />
            </Form.Item>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0 16px' }}>
            <Form.Item name="mode" label="模式" initialValue="normal">
              <Select options={modeOptions} />
            </Form.Item>
            <Form.Item name="is_enabled" label="启用" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
            <Form.Item name="free_only" label="仅免费" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="double_upload" label="2x上传" valuePropName="checked">
              <Switch />
            </Form.Item>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0 16px' }}>
            <Form.Item name="min_size" label="最小(GB)">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="max_size" label="最大(GB)">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="min_seeders" label="最小做种">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="max_seeders" label="最大做种">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item name="keywords" label="关键词（逗号分隔）">
              <Input placeholder="如：4K,HDR,REMUX" />
            </Form.Item>
            <Form.Item name="exclude_keywords" label="排除关键词">
              <Input placeholder="如：CAM,TS" />
            </Form.Item>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item name="downloader_id" label="推送到下载器">
              <Select allowClear options={downloaders.map(d => ({ value: d.id, label: d.name }))} placeholder="不推送" />
            </Form.Item>
            <Form.Item name="max_downloading" label="最大同时下载" tooltip="超过此数量时暂停添加新种子">
              <InputNumber min={1} style={{ width: '100%' }} placeholder="不限制" />
            </Form.Item>
          </div>
          
          <Form.Item name="save_path" label="保存路径">
            <Input placeholder="如：/downloads/movies" />
          </Form.Item>
          
          <Form.Item 
            name="tags" 
            label="标签" 
            tooltip="选择已有标签或输入新标签。注意：只有带这些标签的种子才会在促销过期时被自动删除"
          >
            <Select
              mode="tags"
              placeholder={selectedDownloaderId ? "选择或输入标签" : "请先选择下载器"}
              disabled={!selectedDownloaderId}
              loading={tagsLoading}
              options={availableTags.map(tag => ({ value: tag, label: tag }))}
              tokenSeparators={[',']}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
