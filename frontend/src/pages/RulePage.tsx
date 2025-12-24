import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Switch, InputNumber, Select, message, Space, Tag, Popconfirm, Checkbox, Card, theme, Row, Col } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FilterOutlined } from '@ant-design/icons';
import { accountApi, ruleApi, downloaderApi, torrentApi } from '../api';

const { useToken } = theme;

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
  categories: string[] | null;
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
  const { token } = useToken();
  const [rules, setRules] = useState<Rule[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [downloaders, setDownloaders] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [tagsLoading, setTagsLoading] = useState(false);
  const [categories, setCategories] = useState<any[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [enableCategoryFilter, setEnableCategoryFilter] = useState(false);
  const [form] = Form.useForm();

  // 监听下载器选择变化，获取对应的标签列表
  const selectedDownloaderId = Form.useWatch('downloader_id', form);
  // 监听账号和模式变化，获取对应的分类列表
  const selectedAccountId = Form.useWatch('account_id', form);
  const selectedMode = Form.useWatch('mode', form);

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

  // 获取分类列表
  useEffect(() => {
    if (selectedAccountId && enableCategoryFilter) {
      setCategoriesLoading(true);
      torrentApi.getCategories(selectedAccountId)
        .then(res => {
          if (res.data.success) {
            const categoryData = res.data.data;
            const categoryList = categoryData.list || [];
            
            // 只保留二级分类（有 parent 的分类）
            const secondLevelCategories = categoryList.filter((cat: any) => cat.parent !== null);
            
            // 用 API 返回的 adult 数组判断成人分类
            const adultCategoryIds = new Set((categoryData.adult || []).map((id: any) => String(id)));
            
            let filteredCategories = secondLevelCategories;
            
            if (selectedMode === 'normal') {
              // 综合区：排除成人分类
              filteredCategories = secondLevelCategories.filter((cat: any) => 
                !adultCategoryIds.has(String(cat.id))
              );
            } else if (selectedMode === 'adult') {
              // 成人区：只显示成人分类
              filteredCategories = secondLevelCategories.filter((cat: any) => 
                adultCategoryIds.has(String(cat.id))
              );
            }
            
            // 按 parent 和 order 排序
            filteredCategories.sort((a: any, b: any) => {
              if (a.parent !== b.parent) {
                return String(a.parent).localeCompare(String(b.parent));
              }
              return parseInt(a.order || '0') - parseInt(b.order || '0');
            });
            
            setCategories(filteredCategories);
          }
        })
        .catch(err => {
          console.error('获取分类失败:', err);
          message.error('获取分类失败');
          setCategories([]);
        })
        .finally(() => {
          setCategoriesLoading(false);
        });
    } else {
      setCategories([]);
    }
  }, [selectedAccountId, selectedMode, enableCategoryFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [rulesRes, accountsRes, downloadersRes] = await Promise.all([
        ruleApi.list(),
        accountApi.list(),
        downloaderApi.list(),
      ]);
      setRules(Array.isArray(rulesRes.data) ? rulesRes.data : []);
      setAccounts(Array.isArray(accountsRes.data) ? accountsRes.data : []);
      setDownloaders(Array.isArray(downloadersRes.data) ? downloadersRes.data : []);
    } catch (e: any) {
      message.error('获取数据失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const handleSubmit = async (values: any) => {
    try {
      // 处理分类数据：如果未启用分类筛选，则清空categories字段
      const submitData = {
        ...values,
        categories: enableCategoryFilter ? values.categories : null
      };
      
      if (editingRule) {
        await ruleApi.update(editingRule.id, submitData);
        message.success('更新成功');
      } else {
        await ruleApi.create(submitData);
        message.success('创建成功');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingRule(null);
      setEnableCategoryFilter(false);
      fetchData();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '操作失败');
    }
  };

  const handleEdit = (rule: Rule) => {
    setEditingRule(rule);
    // 设置分类过滤器状态
    setEnableCategoryFilter(!!(rule.categories && rule.categories.length > 0));
    form.setFieldsValue({
      ...rule,
      enable_category_filter: rule.categories && rule.categories.length > 0
    });
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
    { 
      title: '规则名称', 
      dataIndex: 'name', 
      key: 'name',
      render: (text: string) => (
         <div style={{ fontWeight: 500 }}>{text}</div>
      )
    },
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
        <Switch checked={v} onChange={() => handleToggle(r.id)} size="small" />
      )
    },
    { 
      title: '条件', 
      key: 'conditions',
      render: (_: any, r: Rule) => (
        <Space wrap size={[4, 4]}>
          <Tag color={r.mode === 'adult' ? 'magenta' : 'blue'} bordered={false}>{r.mode === 'adult' ? '成人' : '普通'}</Tag>
          {r.free_only && <Tag color="green" bordered={false}>免费</Tag>}
          {r.double_upload && <Tag color="cyan" bordered={false}>2x上传</Tag>}
          {r.min_size && <Tag bordered={false}>≥{r.min_size}GB</Tag>}
          {r.max_size && <Tag bordered={false}>≤{r.max_size}GB</Tag>}
          {r.keywords && <Tag bordered={false} icon={<FilterOutlined />}>{r.keywords}</Tag>}
          {r.categories && r.categories.length > 0 && (
            <Tag color="orange" bordered={false}>分类: {r.categories.length}个</Tag>
          )}
          {r.tags && r.tags.length > 0 && <Tag color="purple" bordered={false}>标签: {r.tags.join(', ')}</Tag>}
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
        return (
           <span style={{ color: v ? token.colorText : token.colorTextDisabled }}>
              {name + limit}
           </span>
        );
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, r: Rule) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} style={{ color: token.colorPrimary }}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card 
         bordered={false} 
         className="modern-card" 
         title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <FilterOutlined style={{ color: token.colorSuccess }} />
                <span>自动下载规则</span>
            </div>
         }
         extra={
             <Button type="primary" icon={<PlusOutlined />} onClick={() => { 
                setEditingRule(null); 
                setEnableCategoryFilter(false);
                form.resetFields(); 
                setModalOpen(true); 
              }}>
                添加规则
              </Button>
         }
         bodyStyle={{ padding: 0 }}
      >
        <Table 
           columns={columns} 
           dataSource={rules} 
           rowKey="id" 
           loading={loading} 
           pagination={{ pageSize: 10 }}
        />
      </Card>
      
      <Modal 
        title={editingRule ? '编辑规则' : '添加规则'} 
        open={modalOpen} 
        onCancel={() => { 
          setModalOpen(false); 
          setEditingRule(null); 
          setEnableCategoryFilter(false);
        }} 
        onOk={() => form.submit()}
        width={700}
        centered
        maskClosable={false}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} size="middle" style={{ marginTop: 24 }}>
          <Row gutter={16}>
             <Col span={12}>
                <Form.Item name="account_id" label="账号" rules={[{ required: true }]}>
                   <Select options={accounts.map(a => ({ value: a.id, label: a.username }))} />
                </Form.Item>
             </Col>
             <Col span={12}>
                <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
                   <Input placeholder="如：免费电影" />
                </Form.Item>
             </Col>
          </Row>
          
          <Row gutter={16}>
             <Col span={6}>
                <Form.Item name="mode" label="模式" initialValue="normal">
                   <Select options={modeOptions} />
                </Form.Item>
             </Col>
             <Col span={6}>
                <Form.Item name="is_enabled" label="启用" valuePropName="checked" initialValue={true}>
                   <Switch />
                </Form.Item>
             </Col>
             <Col span={6}>
                <Form.Item name="free_only" label="仅免费" valuePropName="checked">
                   <Switch />
                </Form.Item>
             </Col>
             <Col span={6}>
                <Form.Item name="double_upload" label="2x上传" valuePropName="checked">
                   <Switch />
                </Form.Item>
             </Col>
          </Row>
          
          <Row gutter={16}>
             <Col span={6}>
                <Form.Item name="min_size" label="最小(GB)">
                   <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
             </Col>
             <Col span={6}>
                <Form.Item name="max_size" label="最大(GB)">
                   <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
             </Col>
             <Col span={6}>
                <Form.Item name="min_seeders" label="最小做种">
                   <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
             </Col>
             <Col span={6}>
                <Form.Item name="max_seeders" label="最大做种">
                   <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
             </Col>
          </Row>
          
          <Row gutter={16}>
             <Col span={12}>
                <Form.Item name="keywords" label="关键词（逗号分隔）">
                   <Input placeholder="如：4K,HDR,REMUX" />
                </Form.Item>
             </Col>
             <Col span={12}>
                <Form.Item name="exclude_keywords" label="排除关键词">
                   <Input placeholder="如：CAM,TS" />
                </Form.Item>
             </Col>
          </Row>
          
          {/* 分类选择 */}
          <Form.Item label="分类筛选" style={{ marginBottom: 0 }}>
            <Checkbox 
              checked={enableCategoryFilter}
              onChange={(e) => {
                setEnableCategoryFilter(e.target.checked);
                if (!e.target.checked) {
                  form.setFieldValue('categories', []);
                }
              }}
            >
              启用指定分类筛选
            </Checkbox>
          </Form.Item>
          
          {enableCategoryFilter && (
            <Form.Item 
              name="categories" 
              label="选择分类"
              tooltip="只下载选中分类的种子。如果不选择任何分类，则下载该模式下的所有分类"
              style={{ marginTop: 8 }}
            >
              <Select
                mode="multiple"
                placeholder={selectedAccountId ? "选择要筛选的分类" : "请先选择账号"}
                disabled={!selectedAccountId || categoriesLoading}
                loading={categoriesLoading}
                options={categories.map(cat => ({
                  value: cat.id,
                  label: `${cat.nameChs} (${cat.nameEng})`,
                  title: cat.nameChs
                }))}
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              />
            </Form.Item>
          )}
          
          <Row gutter={16} style={{ marginTop: 16 }}>
             <Col span={12}>
                <Form.Item name="downloader_id" label="推送到下载器">
                   <Select allowClear options={downloaders.map(d => ({ value: d.id, label: d.name }))} placeholder="不推送" />
                </Form.Item>
             </Col>
             <Col span={12}>
                <Form.Item name="max_downloading" label="最大同时下载" tooltip="超过此数量时暂停添加新种子">
                   <InputNumber min={1} style={{ width: '100%' }} placeholder="不限制" />
                </Form.Item>
             </Col>
          </Row>
          
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
