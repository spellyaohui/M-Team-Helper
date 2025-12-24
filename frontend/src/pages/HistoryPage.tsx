import { useState, useEffect } from 'react';
import { Table, Button, Select, Tag, message, Popconfirm, Space, Tooltip, Modal, Upload, Form, Input } from 'antd';
import { DeleteOutlined, ClearOutlined, SyncOutlined, InfoCircleOutlined, UploadOutlined, InboxOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { accountApi, historyApi, downloaderApi } from '../api';

const { Dragger } = Upload;

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
  pending: { text: '等待中', color: 'orange' },
  downloading: { text: '下载中', color: 'blue' },
  paused: { text: '已暂停', color: 'default' },
  queued: { text: '队列中', color: 'cyan' },
  completed: { text: '已完成', color: 'green' },
  seeding: { text: '做种中', color: 'lime' },
  deleted: { text: '已删除', color: 'red' },
  failed: { text: '失败', color: 'red' },
  expired_deleted: { text: '过期已删', color: 'volcano' },
  // 兼容旧状态
  downloaded: { text: '已下载', color: 'green' },
  pushing: { text: '推送中', color: 'blue' },
  push_failed: { text: '推送失败', color: 'red' },
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
  const [downloaders, setDownloaders] = useState<any[]>([]);
  const [accountId, setAccountId] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [clearingDeleted, setClearingDeleted] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [uploadForm] = Form.useForm();

  useEffect(() => {
    accountApi.list().then(res => setAccounts(res.data));
    downloaderApi.list().then(res => setDownloaders(res.data));
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

  // 自动刷新：每30秒同步状态（不导入新种子）
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        await historyApi.syncStatus(false);  // 自动同步不导入新种子
        fetchHistory(page, accountId);
      } catch (e) {
        console.error('自动同步状态失败:', e);
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, [page, accountId]);

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

  const handleClearDeleted = async () => {
    setClearingDeleted(true);
    try {
      const response = await historyApi.clearDeleted();
      if (response.data.success) {
        message.success(response.data.message);
        fetchHistory();
      } else {
        message.error('清空失败');
      }
    } catch (e) {
      message.error('清空失败');
    } finally {
      setClearingDeleted(false);
    }
  };

  const handleSyncStatus = async () => {
    setSyncing(true);
    try {
      // 手动点击时先导入新种子再同步状态
      const response = await historyApi.syncStatus(true);
      
      if (response.data.success) {
        message.success(response.data.message);
        fetchHistory(); // 刷新列表
      } else {
        message.error('同步失败');
      }
    } catch (e) {
      message.error('同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleUploadDownloaderChange = async (downloaderId: number) => {
    // 获取下载器的标签
    try {
      const response = await historyApi.getDownloaderTags(downloaderId);
      if (response.data.success) {
        setAvailableTags(response.data.tags);
      }
    } catch (e) {
      console.error('获取标签失败:', e);
      setAvailableTags([]);
    }
  };

  const handleUploadTorrent = async (values: any) => {
    const { file, downloader_id, account_id, save_path, tags } = values;
    
    console.log('上传表单数据:', values);
    
    if (!file || !file.fileList || file.fileList.length === 0) {
      message.error('请选择种子文件');
      return;
    }
    
    setUploading(true);
    try {
      const formData = new FormData();
      
      // 处理文件对象 - Ant Design Upload组件的文件结构
      const fileObj = file.fileList[0];
      const actualFile = fileObj.originFileObj || fileObj;
      
      console.log('文件对象:', fileObj);
      console.log('实际文件:', actualFile);
      
      formData.append('file', actualFile);
      formData.append('downloader_id', downloader_id.toString());
      
      if (account_id) formData.append('account_id', account_id.toString());
      if (save_path) formData.append('save_path', save_path);
      if (tags && Array.isArray(tags)) {
        formData.append('tags', tags.join(','));
      } else if (tags) {
        formData.append('tags', tags);
      }
      
      const response = await historyApi.uploadTorrent(formData);
      
      if (response.data.success) {
        const data = response.data.data;
        let successMsg = '种子上传成功';
        
        // 如果获取到了促销信息，显示在成功消息中
        if (data.discount_type && data.discount_type !== 'NORMAL') {
          const discountText = discountMap[data.discount_type]?.text || data.discount_type;
          successMsg += `，促销类型：${discountText}`;
          
          if (data.discount_end_time) {
            const endTime = dayjs(data.discount_end_time);
            successMsg += `，到期时间：${endTime.format('MM-DD HH:mm')}`;
          }
        }
        
        message.success(successMsg);
        setUploadModalVisible(false);
        uploadForm.resetFields();
        fetchHistory(); // 刷新列表
      } else {
        message.error('上传失败');
      }
    } catch (e: any) {
      console.error('上传错误:', e);
      message.error(e.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
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
      <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        <Select
          style={{ width: 150 }}
          placeholder="全部账号"
          allowClear
          value={accountId}
          onChange={(v) => { setAccountId(v); setPage(1); fetchHistory(1, v); }}
          options={accounts.map(a => ({ value: a.id, label: a.username }))}
        />
        
        <Space>
          <Tooltip title="从下载器导入新种子并同步状态">
            <Button 
              icon={<SyncOutlined />} 
              loading={syncing}
              onClick={handleSyncStatus}
            >
              同步状态
            </Button>
          </Tooltip>
          
          <Tooltip title="上传种子文件到下载器">
            <Button 
              icon={<UploadOutlined />} 
              onClick={() => setUploadModalVisible(true)}
            >
              上传种子
            </Button>
          </Tooltip>
          
          <Popconfirm title="确定清空已删除的记录？" onConfirm={handleClearDeleted}>
            <Tooltip title="清空下载器中已删除的种子记录">
              <Button 
                icon={<ClearOutlined />}
                loading={clearingDeleted}
              >
                清空已删除
              </Button>
            </Tooltip>
          </Popconfirm>
          
          <Popconfirm title="确定清空所有记录？" onConfirm={handleClear}>
            <Button danger icon={<ClearOutlined />}>清空历史</Button>
          </Popconfirm>
        </Space>
        
        <div style={{ marginLeft: 'auto', color: '#666', fontSize: '12px' }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          状态说明：下载中 → 已完成 → 做种中 / 已删除
        </div>
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
      
      {/* 上传种子模态框 */}
      <Modal
        title="上传种子文件"
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false);
          uploadForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={uploadForm}
          layout="vertical"
          onFinish={handleUploadTorrent}
        >
          <Form.Item
            label="种子文件"
            name="file"
            rules={[{ required: true, message: '请选择种子文件' }]}
            valuePropName="file"
          >
            <Dragger
              accept=".torrent"
              maxCount={1}
              beforeUpload={() => false}
              showUploadList={{ showRemoveIcon: true }}
              onChange={(info) => {
                // 确保表单能正确获取文件
                uploadForm.setFieldsValue({ file: info });
              }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽种子文件到此区域上传</p>
              <p className="ant-upload-hint">仅支持 .torrent 格式文件</p>
            </Dragger>
          </Form.Item>

          <Form.Item
            label="下载器"
            name="downloader_id"
            rules={[{ required: true, message: '请选择下载器' }]}
          >
            <Select
              placeholder="请选择下载器"
              onChange={handleUploadDownloaderChange}
              options={downloaders.map(d => ({ 
                value: d.id, 
                label: `${d.name} (${d.host}:${d.port})` 
              }))}
            />
          </Form.Item>

          <Form.Item
            label="关联账号"
            name="account_id"
          >
            <Select
              placeholder="可选，关联M-Team账号"
              allowClear
              options={accounts.map(a => ({ 
                value: a.id, 
                label: a.username 
              }))}
            />
          </Form.Item>

          <Form.Item
            label="保存路径"
            name="save_path"
          >
            <Input placeholder="可选，指定下载保存路径" />
          </Form.Item>

          <Form.Item
            label="标签"
            name="tags"
          >
            <Select
              mode="tags"
              placeholder="可选，添加标签（逗号分隔）"
              options={availableTags.map(tag => ({ value: tag, label: tag }))}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={uploading}>
                上传并添加到下载器
              </Button>
              <Button onClick={() => {
                setUploadModalVisible(false);
                uploadForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
        
        <div style={{ color: '#666', fontSize: '12px', marginTop: 16 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          上传的种子文件会自动添加到选择的下载器，并创建下载历史记录。
          如果关联了M-Team账号，系统会自动查询种子的促销信息。
          可以指定标签来更好地管理种子，系统会自动创建不存在的标签。
        </div>
      </Modal>
    </>
  );
}
