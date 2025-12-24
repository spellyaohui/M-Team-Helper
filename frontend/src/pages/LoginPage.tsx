import { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Typography, theme, ConfigProvider } from 'antd';
import { UserOutlined, LockOutlined, RocketOutlined } from '@ant-design/icons';
import { authApi } from '../api';

const { Text } = Typography;

interface LoginPageProps {
  onLogin: (token: string, username: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [needInit, setNeedInit] = useState(false);
  const [form] = Form.useForm();
  
  // 使用 Ant Design Token
  const { token } = theme.useToken();

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
      {/* 背景装饰图形 */}
      <div className="login-bg-shape-1" />
      <div className="login-bg-shape-2" />
      
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <div className="login-logo-wrapper">
            <RocketOutlined className="login-logo" />
          </div>
          <div className="login-title">M-Team Helper</div>
          <Text type="secondary" style={{ fontSize: 16 }}>
            PT 种子自动化管理助手
          </Text>
        </div>
        
        <ConfigProvider
          theme={{
            components: {
              Input: {
                controlHeight: 48,
                borderRadius: 12,
                colorBgContainer: 'rgba(255,255,255,0.6)',
              },
              Button: {
                controlHeight: 48,
                borderRadius: 12,
                fontSize: 16,
                fontWeight: 600,
              }
            }
          }}
        >
          <Form 
            form={form} 
            onFinish={handleSubmit} 
            size="large" 
            className="login-form"
            layout="vertical"
          >
            <Form.Item 
              name="username" 
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input 
                prefix={<UserOutlined style={{ color: token.colorTextSecondary }} />} 
                placeholder="用户名" 
                bordered={false}
                style={{ background: 'rgba(0,0,0,0.04)' }}
              />
            </Form.Item>
            
            <Form.Item 
              name="password" 
              rules={[{ required: true, message: '请输入密码' }]}
              style={{ marginBottom: 32 }}
            >
              <Input.Password 
                prefix={<LockOutlined style={{ color: token.colorTextSecondary }} />} 
                placeholder="密码" 
                bordered={false}
                style={{ background: 'rgba(0,0,0,0.04)' }}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading} 
                block 
                style={{ 
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                  border: 'none',
                  boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.39)'
                }}
              >
                {isRegister ? '初始化并创建管理员' : '登录'}
              </Button>
            </Form.Item>
          </Form>
        </ConfigProvider>
        
        {needInit && (
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Text type="warning" style={{ fontSize: 13 }}>
              * 首次运行，请创建管理员账号
            </Text>
          </div>
        )}
        
        <div style={{ textAlign: 'center', marginTop: 32 }}>
          <Text type="secondary" style={{ fontSize: 12, opacity: 0.8 }}>
            © {new Date().getFullYear()} M-Team Helper. All rights reserved.
          </Text>
        </div>
      </Card>
    </div>
  );
}
