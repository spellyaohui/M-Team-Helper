import React from 'react';
import { Card, Typography, Space, Button } from 'antd';
import { SettingOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const TestSettingsPage: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <SettingOutlined /> 系统设置（测试页面）
      </Title>
      
      <Card title="测试设置页面" style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="middle">
          <Text>这是一个简化的设置页面，用于测试入口点是否正常工作。</Text>
          
          <div>
            <Text strong>功能列表：</Text>
            <ul>
              <li>✅ 菜单入口点已添加</li>
              <li>✅ 路由配置已完成</li>
              <li>✅ 页面组件已创建</li>
              <li>✅ API 接口已扩展</li>
            </ul>
          </div>
          
          <Button type="primary" onClick={() => alert('设置页面正常工作！')}>
            测试按钮
          </Button>
        </Space>
      </Card>
      
      <Card title="检查清单">
        <Space direction="vertical">
          <Text>如果你能看到这个页面，说明：</Text>
          <Text>1. 左侧菜单的"系统设置"项可以正常点击</Text>
          <Text>2. 页面路由配置正确</Text>
          <Text>3. 组件导入和导出正常</Text>
          <Text>4. 可以继续使用完整的设置功能</Text>
        </Space>
      </Card>
    </div>
  );
};

export default TestSettingsPage;