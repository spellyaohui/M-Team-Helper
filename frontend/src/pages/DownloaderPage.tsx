import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, InputNumber, message, Space, Tag, Popconfirm, Switch } from 'antd';
import { PlusOutlined, ApiOutlined, DeleteOutlined } from '@ant-design/icons';
import { downloaderApi } from '../api';

interface Downloader {
  id: number;
  name: string;
  type: string;
  host: string;
  port: number;
  username: string;
  use_ssl: boolean;
  is_active: boolean;
}

export default function DownloaderPage() {
  const [downloaders, setDownloaders] = useState<Downloader[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [testing, setTesting] = useState<number | null>(null);
  const [form] = Form.useForm();

  const fetchDownloaders = async () => {
    setLoading(true);
    try {
      const res = await downloaderApi.list();
      setDownloaders(res.data);
    } catch (e) {
      message.error('获取下载器列表失败');
    }
    setLoading(false);
  };

  useEffect(() => { 
    fetchDownloaders(); 
  }, []);

  const handleAdd = async (values: any) => {
    try {
      await downloaderApi.create(values);
      message.success('添加成功');
      setModalOpen(false);
      form.resetFields();
      fetchDownloaders();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '添加失败');
    }
  };

  const handleTest = async (id: number) => {
    setTesting(id);
    try {
      const res = await downloaderApi.test(id);
      if (res.data.success) {
        message.success(res.data.message);
      } else {
        message.error(res.data.message);
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || '测试失败');
    }
    setTesting(null);
  };

  const handleDelete = async (id: number) => {
    try {
      await downloaderApi.delete(id);
      message.success('删除成功');
      fetchDownloaders();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '类型', 
      dataIndex: 'type', 
      key: 'type',
      render: (v: string) => (
        <Tag color={v === 'qbittorrent' ? 'blue' : 'green'}>
          {v === 'qbittorrent' ? 'qBittorrent' : 'Transmission'}
        </Tag>
      )
    },
    { title: '地址', key: 'address', render: (_: any, r: Downloader) => `${r.use_ssl ? 'https' : 'http'}://${r.host}:${r.port}` },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { 
      title: '状态', 
      dataIndex: 'is_active', 
      key: 'is_active',
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '禁用'}</Tag>
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, r: Downloader) => (
        <Space>
          <Button 
            size="small" 
            icon={<ApiOutlined />} 
            loading={testing === r.id}
            onClick={() => handleTest(r.id)}
          >
            测试连接
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)} style={{ marginBottom: 16 }}>
        添加下载器
      </Button>

      <Table columns={columns} dataSource={downloaders} rowKey="id" loading={loading} />
      
      {/* 添加下载器弹窗 */}
      <Modal title="添加下载器" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：本地qBittorrent" />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={[
              { value: 'qbittorrent', label: 'qBittorrent' },
              { value: 'transmission', label: 'Transmission' },
            ]} />
          </Form.Item>
          <Form.Item name="host" label="地址" rules={[{ required: true }]}>
            <Input placeholder="如：192.168.1.100 或 localhost" />
          </Form.Item>
          <Form.Item name="port" label="端口" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} placeholder="如：8080" />
          </Form.Item>
          <Form.Item name="use_ssl" label="使用 HTTPS" valuePropName="checked" initialValue={false}>
            <Switch checkedChildren="HTTPS" unCheckedChildren="HTTP" />
          </Form.Item>
          <Form.Item name="username" label="用户名">
            <Input placeholder="下载器登录用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码">
            <Input.Password placeholder="下载器登录密码" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
