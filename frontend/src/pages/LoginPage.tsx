import { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, RocketOutlined } from '@ant-design/icons';
import { authApi } from '../api';

const { Title, Text } = Typography;

interface LoginPageProps {
  onLogin: (token: string, username: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [needInit, setNeedInit] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    // 检查是否需要初始化
    authApi.checkInit().then(res => {
      setNeedInit(res.data.need_init);
      if (res.data.need_init) {
        setIsRegister(true);
      }
    });
  }, []);

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const api = isRegister ? authApi.register : authApi.login;
      const res = await api(values);
      
      if (res.data.success) {
        message.success(res.data.message);
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('username', res.data.username);
        onLogin(res.data.token, res.data.username);
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || '操作失败');
    }
    setLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-bg" />
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <RocketOutlined className="login-logo" />
          <Title level={2} className="login-title">M-Team Helper</Title>
          <Text type="secondary">PT 种子自动化助手</Text>
        </div>
        
        <Form form={form} onFinish={handleSubmit} size="large" className="login-form">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block className="login-btn">
              {isRegister ? '注册并登录' : '登录'}
            </Button>
          </Form.Item>
        </Form>
        
        {needInit && (
          <Text type="secondary" className="login-hint">
            首次使用，请创建管理员账号
          </Text>
        )}
      </Card>
    </div>
  );
}
