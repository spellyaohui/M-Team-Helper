import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, message, Space, Tag, Popconfirm } from 'antd';
import { PlusOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { accountApi } from '../api';

interface Account {
  id: number;
  username: string;
  uid: string;
  is_active: boolean;
  last_login: string;
  upload: number;
  download: number;
  ratio: number;
  bonus: number;
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export default function AccountPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const res = await accountApi.list();
      setAccounts(res.data);
    } catch (e) {
      message.error('获取账号列表失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchAccounts(); }, []);

  const handleAdd = async (values: { username: string; api_key: string }) => {
    try {
      await accountApi.create(values);
      message.success('添加成功');
      setModalOpen(false);
      form.resetFields();
      fetchAccounts();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '添加失败');
    }
  };

  const handleRefresh = async (id: number) => {
    try {
      await accountApi.refresh(id);
      message.success('刷新成功');
      fetchAccounts();
    } catch (e) {
      message.error('刷新失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await accountApi.delete(id);
      message.success('删除成功');
      fetchAccounts();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: 'UID', dataIndex: 'uid', key: 'uid' },
    { 
      title: '状态', 
      dataIndex: 'is_active', 
      key: 'is_active',
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '正常' : '禁用'}</Tag>
    },
    { title: '上传量', dataIndex: 'upload', key: 'upload', render: formatBytes },
    { title: '下载量', dataIndex: 'download', key: 'download', render: formatBytes },
    { title: '分享率', dataIndex: 'ratio', key: 'ratio', render: (v: number) => v.toFixed(2) },
    { title: '魔力值', dataIndex: 'bonus', key: 'bonus', render: (v: number) => v.toFixed(1) },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Account) => (
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRefresh(record.id)}>刷新</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          添加账号
        </Button>
      </div>
      <Table columns={columns} dataSource={accounts} rowKey="id" loading={loading} />
      
      <Modal title="添加账号" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input placeholder="M-Team 用户名" />
          </Form.Item>
          <Form.Item name="api_key" label="API Token" rules={[{ required: true }]}>
            <Input.TextArea placeholder="从 控制台->实验室->存取令牌 获取" rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
