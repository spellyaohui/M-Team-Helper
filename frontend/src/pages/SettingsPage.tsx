import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  InputNumber,
  Button,
  Switch,
  Select,
  Statistic,
  Row,
  Col,
  message,
  Divider,
  Tag,
  Space,
  Alert,
  Tooltip,
  Typography,
  TimePicker,
  Table,
  Popconfirm,
} from 'antd';
import {
  ClockCircleOutlined,
  SettingOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { settingsApi } from '../api';

const { Title, Text } = Typography;
const { Option } = Select;

interface RefreshIntervals {
  account_refresh_interval: number;
  torrent_check_interval: number;
  expired_check_interval: number;
}

interface AutoDeleteSettings {
  enabled: boolean;
  delete_scope: 'all' | 'normal' | 'adult';
  check_tags: boolean;
}

interface SchedulerJob {
  id: string;
  name: string;
  next_run: string | null;
  last_run: string | null;
  trigger: string;
}

interface SchedulerStatus {
  running: boolean;
  jobs: SchedulerJob[];
  current_intervals: RefreshIntervals;
  schedule_control: {
    enabled: boolean;
    current_status: {
      auto_download: boolean;
      expired_check: boolean;
      account_refresh: boolean;
      current_time: string;
      current_time_range: {
        in_range: boolean;
        description: string;
        start?: string;
        end?: string;
        settings?: {
          auto_download: boolean;
          expired_check: boolean;
          account_refresh: boolean;
        };
      };
    };
    time_ranges: TimeRange[];
  };
}

interface ScheduleSettings {
  enabled: boolean;
  time_ranges: TimeRange[];
}

interface TimeRange {
  start: string;
  end: string;
  auto_download: boolean;
  expired_check: boolean;
  account_refresh: boolean;
}

// 定时运行控制组件
const ScheduleControlForm: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [scheduleSettings, setScheduleSettings] = useState<ScheduleSettings>({
    enabled: false,
    time_ranges: []
  });
  const [showAddForm, setShowAddForm] = useState(false);

  // 获取定时控制设置
  const fetchScheduleSettings = async () => {
    try {
      const response = await settingsApi.getScheduleControl();
      const settings = response.data.value;
      setScheduleSettings(settings);
      form.setFieldsValue({ enabled: settings.enabled });
    } catch (error) {
      console.error('获取定时控制设置失败:', error);
    }
  };

  // 更新定时控制设置
  const handleUpdateScheduleSettings = async (values: { enabled: boolean }) => {
    setLoading(true);
    try {
      const newSettings = {
        ...scheduleSettings,
        enabled: values.enabled
      };
      await settingsApi.updateScheduleControl(newSettings);
      setScheduleSettings(newSettings);
      message.success('定时控制设置已更新');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  // 添加时间段
  const handleAddTimeRange = (range: TimeRange) => {
    const newRanges = [...scheduleSettings.time_ranges, range];
    updateTimeRanges(newRanges);
    setShowAddForm(false);
  };

  // 删除时间段
  const handleDeleteTimeRange = (index: number) => {
    const newRanges = scheduleSettings.time_ranges.filter((_, i) => i !== index);
    updateTimeRanges(newRanges);
  };

  // 更新时间段列表
  const updateTimeRanges = async (ranges: TimeRange[]) => {
    setLoading(true);
    try {
      const newSettings = {
        ...scheduleSettings,
        time_ranges: ranges
      };
      await settingsApi.updateScheduleControl(newSettings);
      setScheduleSettings(newSettings);
      message.success('时间段设置已更新');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  // 时间段表格列定义
  const columns = [
    {
      title: '时间段',
      key: 'time',
      render: (record: TimeRange) => `${record.start} - ${record.end}`,
    },
    {
      title: '自动下载',
      dataIndex: 'auto_download',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '过期检查',
      dataIndex: 'expired_check',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '账号刷新',
      dataIndex: 'account_refresh',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, __: TimeRange, index: number) => (
        <Space>
          <Popconfirm
            title="确定删除这个时间段吗？"
            onConfirm={() => handleDeleteTimeRange(index)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  useEffect(() => {
    fetchScheduleSettings();
  }, []);

  return (
    <div>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleUpdateScheduleSettings}
        initialValues={{ enabled: false }}
      >
        <Form.Item
          label="启用定时运行控制"
          name="enabled"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            保存设置
          </Button>
        </Form.Item>
      </Form>

      {scheduleSettings.enabled && (
        <>
          <Divider>时间段配置</Divider>
          
          <div style={{ marginBottom: 16 }}>
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={() => setShowAddForm(true)}
              disabled={showAddForm}
            >
              添加时间段
            </Button>
          </div>

          {showAddForm && (
            <TimeRangeForm
              onSubmit={handleAddTimeRange}
              onCancel={() => setShowAddForm(false)}
            />
          )}

          <Table
            columns={columns}
            dataSource={scheduleSettings.time_ranges}
            rowKey={(record, index) => `${record.start}-${record.end}-${index}`}
            pagination={false}
            size="small"
          />

          {scheduleSettings.time_ranges.length === 0 && (
            <Alert
              message="未配置时间段"
              description="请添加时间段来控制任务的运行时间。如果不配置时间段，所有任务将正常运行。"
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </>
      )}
    </div>
  );
};

// 时间段表单组件
const TimeRangeForm: React.FC<{
  onSubmit: (range: TimeRange) => void;
  onCancel: () => void;
}> = ({ onSubmit, onCancel }) => {
  const [form] = Form.useForm();

  const handleSubmit = (values: any) => {
    const range: TimeRange = {
      start: values.start.format('HH:mm'),
      end: values.end.format('HH:mm'),
      auto_download: values.auto_download,
      expired_check: values.expired_check,
      account_refresh: values.account_refresh,
    };
    onSubmit(range);
    form.resetFields();
  };

  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Form
        form={form}
        layout="inline"
        onFinish={handleSubmit}
        initialValues={{
          auto_download: true,
          expired_check: true,
          account_refresh: true,
        }}
      >
        <Form.Item
          label="开始时间"
          name="start"
          rules={[{ required: true, message: '请选择开始时间' }]}
        >
          <TimePicker format="HH:mm" />
        </Form.Item>

        <Form.Item
          label="结束时间"
          name="end"
          rules={[{ required: true, message: '请选择结束时间' }]}
        >
          <TimePicker format="HH:mm" />
        </Form.Item>

        <Form.Item
          label="自动下载"
          name="auto_download"
          valuePropName="checked"
        >
          <Switch size="small" />
        </Form.Item>

        <Form.Item
          label="过期检查"
          name="expired_check"
          valuePropName="checked"
        >
          <Switch size="small" />
        </Form.Item>

        <Form.Item
          label="账号刷新"
          name="account_refresh"
          valuePropName="checked"
        >
          <Switch size="small" />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" size="small">
              添加
            </Button>
            <Button onClick={onCancel} size="small">
              取消
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

const SettingsPage: React.FC = () => {
  const [refreshForm] = Form.useForm();
  const [autoDeleteForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);

  // 获取刷新间隔设置
  const fetchRefreshIntervals = async () => {
    try {
      const response = await settingsApi.getRefreshIntervals();
      const intervals = response.data.value;
      refreshForm.setFieldsValue(intervals);
    } catch (error) {
      console.error('获取刷新间隔设置失败:', error);
    }
  };

  // 获取自动删种设置
  const fetchAutoDeleteSettings = async () => {
    try {
      const response = await settingsApi.getAutoDelete();
      const settings = response.data.value;
      autoDeleteForm.setFieldsValue(settings);
    } catch (error) {
      console.error('获取自动删种设置失败:', error);
    }
  };

  // 获取调度器状态
  const fetchSchedulerStatus = async () => {
    try {
      const response = await settingsApi.getSchedulerStatus();
      setSchedulerStatus(response.data);
    } catch (error) {
      console.error('获取调度器状态失败:', error);
    }
  };

  // 更新刷新间隔设置
  const handleUpdateRefreshIntervals = async (values: RefreshIntervals) => {
    setLoading(true);
    try {
      await settingsApi.updateRefreshIntervals(values);
      message.success('刷新间隔设置已更新，调度器已重启');
      fetchSchedulerStatus(); // 刷新调度器状态
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  // 更新自动删种设置
  const handleUpdateAutoDelete = async (values: AutoDeleteSettings) => {
    setLoading(true);
    try {
      await settingsApi.updateAutoDelete(values);
      message.success('自动删种设置已更新');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  // 重启调度器
  const handleRestartScheduler = async () => {
    try {
      await settingsApi.restartScheduler();
      message.success('调度器已重启');
      fetchSchedulerStatus();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重启失败');
    }
  };

  // 格式化时间间隔显示
  const formatInterval = (seconds: number): string => {
    if (seconds < 60) return `${seconds}秒`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
    return `${Math.floor(seconds / 3600)}小时${Math.floor((seconds % 3600) / 60)}分钟`;
  };

  // 格式化下次运行时间
  const formatNextRun = (nextRun: string | null): string => {
    if (!nextRun) return '未知';
    const date = new Date(nextRun);
    return date.toLocaleString('zh-CN');
  };

  // 获取任务状态标签
  const getJobStatusTag = (job: SchedulerJob) => {
    if (!job.next_run) {
      return <Tag color="red">未调度</Tag>;
    }
    
    const nextRun = new Date(job.next_run);
    const now = new Date();
    const diff = nextRun.getTime() - now.getTime();
    
    if (diff < 0) {
      return <Tag color="orange">已过期</Tag>;
    } else if (diff < 60000) { // 1分钟内
      return <Tag color="green">即将运行</Tag>;
    } else {
      return <Tag color="blue">已调度</Tag>;
    }
  };

  useEffect(() => {
    fetchRefreshIntervals();
    fetchAutoDeleteSettings();
    fetchSchedulerStatus();
    
    // 每30秒刷新调度器状态
    const interval = setInterval(fetchSchedulerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <SettingOutlined /> 系统设置
      </Title>

      {/* 定时运行控制 */}
      <Card 
        title={
          <Space>
            <ClockCircleOutlined />
            定时运行控制
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Alert
          message="功能说明"
          description="可以设置不同时间段内允许或禁用特定任务。例如：夜间关闭自动下载但保持过期检查，白天全部开启等。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <ScheduleControlForm />
      </Card>

      {/* 刷新间隔设置 */}
      <Card 
        title={
          <Space>
            <ClockCircleOutlined />
            刷新间隔设置
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Alert
          message="设置说明"
          description="调整系统各项任务的执行频率。设置过短可能导致网站访问频率过高，设置过长可能影响及时性。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Form
          form={refreshForm}
          layout="vertical"
          onFinish={handleUpdateRefreshIntervals}
          initialValues={{
            account_refresh_interval: 300,
            torrent_check_interval: 180,
            expired_check_interval: 60,
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label={
                  <Space>
                    账号刷新间隔（秒）
                    <Tooltip title="获取账号信息（上传量、下载量、分享率等）的频率，建议不少于2分钟">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </Space>
                }
                name="account_refresh_interval"
                rules={[
                  { required: true, message: '请输入账号刷新间隔' },
                  { type: 'number', min: 30, max: 86400, message: '间隔必须在30秒到24小时之间' }
                ]}
                help="例如：300 = 5分钟，600 = 10分钟"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={30}
                  max={86400}
                  placeholder="输入秒数，如 300 表示 5分钟"
                />
              </Form.Item>
            </Col>
            
            <Col span={8}>
              <Form.Item
                label={
                  <Space>
                    种子检查间隔（秒）
                    <Tooltip title="自动下载种子检查的频率，影响抢种及时性">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </Space>
                }
                name="torrent_check_interval"
                rules={[
                  { required: true, message: '请输入种子检查间隔' },
                  { type: 'number', min: 30, max: 86400, message: '间隔必须在30秒到24小时之间' }
                ]}
                help="例如：180 = 3分钟，300 = 5分钟"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={30}
                  max={86400}
                  placeholder="输入秒数，如 180 表示 3分钟"
                />
              </Form.Item>
            </Col>
            
            <Col span={8}>
              <Form.Item
                label={
                  <Space>
                    过期检查间隔（秒）
                    <Tooltip title="检查促销过期种子的频率，用于及时清理过期种子">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </Space>
                }
                name="expired_check_interval"
                rules={[
                  { required: true, message: '请输入过期检查间隔' },
                  { type: 'number', min: 30, max: 3600, message: '间隔必须在30秒到1小时之间' }
                ]}
                help="例如：60 = 1分钟，300 = 5分钟"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={30}
                  max={3600}
                  placeholder="输入秒数，如 60 表示 1分钟"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                保存设置
              </Button>
              <Button onClick={handleRestartScheduler} icon={<ReloadOutlined />}>
                重启调度器
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 推荐设置 */}
        <Divider>推荐设置</Divider>
        <Row gutter={16}>
          <Col span={8}>
            <Card size="small" title="轻度使用">
              <Text type="secondary">个人用户，偶尔使用</Text>
              <div style={{ marginTop: 8 }}>
                <div>账号刷新: 10分钟</div>
                <div>种子检查: 5分钟</div>
                <div>过期检查: 2分钟</div>
              </div>
              <Button 
                size="small" 
                style={{ marginTop: 8 }}
                onClick={() => refreshForm.setFieldsValue({
                  account_refresh_interval: 600,
                  torrent_check_interval: 300,
                  expired_check_interval: 120,
                })}
              >
                应用此设置
              </Button>
            </Card>
          </Col>
          
          <Col span={8}>
            <Card size="small" title="中度使用">
              <Text type="secondary">活跃用户，日常使用</Text>
              <div style={{ marginTop: 8 }}>
                <div>账号刷新: 5分钟</div>
                <div>种子检查: 3分钟</div>
                <div>过期检查: 1分钟</div>
              </div>
              <Button 
                size="small" 
                style={{ marginTop: 8 }}
                onClick={() => refreshForm.setFieldsValue({
                  account_refresh_interval: 300,
                  torrent_check_interval: 180,
                  expired_check_interval: 60,
                })}
              >
                应用此设置
              </Button>
            </Card>
          </Col>
          
          <Col span={8}>
            <Card size="small" title="重度使用">
              <Text type="secondary">抢种用户，高频使用</Text>
              <div style={{ marginTop: 8 }}>
                <div>账号刷新: 3分钟</div>
                <div>种子检查: 1分钟</div>
                <div>过期检查: 30秒</div>
              </div>
              <Button 
                size="small" 
                style={{ marginTop: 8 }}
                onClick={() => refreshForm.setFieldsValue({
                  account_refresh_interval: 180,
                  torrent_check_interval: 60,
                  expired_check_interval: 30,
                })}
              >
                应用此设置
              </Button>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 调度器状态 */}
      <Card 
        title={
          <Space>
            <CheckCircleOutlined />
            调度器状态
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {schedulerStatus && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic
                  title="运行状态"
                  value={schedulerStatus.running ? '运行中' : '已停止'}
                  valueStyle={{ 
                    color: schedulerStatus.running ? '#3f8600' : '#cf1322' 
                  }}
                  prefix={schedulerStatus.running ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="任务数量"
                  value={schedulerStatus.jobs.length}
                  suffix="个"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="账号刷新间隔"
                  value={formatInterval(schedulerStatus.current_intervals.account_refresh_interval)}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="种子检查间隔"
                  value={formatInterval(schedulerStatus.current_intervals.torrent_check_interval)}
                />
              </Col>
            </Row>

            {/* 时间段控制状态 */}
            {schedulerStatus.schedule_control.enabled && (
              <>
                <Divider>时间段控制状态</Divider>
                <Alert
                  message={`当前时间: ${schedulerStatus.schedule_control.current_status.current_time}`}
                  description={schedulerStatus.schedule_control.current_status.current_time_range.description}
                  type={schedulerStatus.schedule_control.current_status.current_time_range.in_range ? "info" : "warning"}
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="自动下载"
                        value={schedulerStatus.schedule_control.current_status.auto_download ? '允许' : '禁用'}
                        valueStyle={{ 
                          color: schedulerStatus.schedule_control.current_status.auto_download ? '#3f8600' : '#cf1322' 
                        }}
                        prefix={schedulerStatus.schedule_control.current_status.auto_download ? 
                          <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="过期检查"
                        value={schedulerStatus.schedule_control.current_status.expired_check ? '允许' : '禁用'}
                        valueStyle={{ 
                          color: schedulerStatus.schedule_control.current_status.expired_check ? '#3f8600' : '#cf1322' 
                        }}
                        prefix={schedulerStatus.schedule_control.current_status.expired_check ? 
                          <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="账号刷新"
                        value={schedulerStatus.schedule_control.current_status.account_refresh ? '允许' : '禁用'}
                        valueStyle={{ 
                          color: schedulerStatus.schedule_control.current_status.account_refresh ? '#3f8600' : '#cf1322' 
                        }}
                        prefix={schedulerStatus.schedule_control.current_status.account_refresh ? 
                          <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>
              </>
            )}

            <Divider>任务列表</Divider>
            <div>
              {schedulerStatus.jobs.map((job: SchedulerJob) => (
                <Card key={job.id} size="small" style={{ marginBottom: 8 }}>
                  <Row align="middle">
                    <Col span={4}>
                      <strong>{job.name}</strong>
                    </Col>
                    <Col span={4}>
                      {getJobStatusTag(job)}
                    </Col>
                    <Col span={8}>
                      <Text type="secondary">
                        下次运行: {formatNextRun(job.next_run)}
                      </Text>
                    </Col>
                    <Col span={8}>
                      <Text type="secondary">
                        上次运行: {formatNextRun(job.last_run)}
                      </Text>
                    </Col>
                  </Row>
                </Card>
              ))}
            </div>
          </>
        )}
      </Card>

      {/* 自动删种设置 */}
      <Card 
        title={
          <Space>
            <ExclamationCircleOutlined />
            自动删种设置
          </Space>
        }
      >
        <Alert
          message="重要提示"
          description="自动删种功能会在促销过期后自动删除未完成的种子，避免影响分享率。请谨慎配置。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Form
          form={autoDeleteForm}
          layout="vertical"
          onFinish={handleUpdateAutoDelete}
          initialValues={{
            enabled: true,
            delete_scope: 'all',
            check_tags: true,
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="启用自动删种"
                name="enabled"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            
            <Col span={8}>
              <Form.Item
                label="删种范围"
                name="delete_scope"
              >
                <Select>
                  <Option value="all">全部种子</Option>
                  <Option value="normal">仅正常种子</Option>
                  <Option value="adult">仅成人种子</Option>
                </Select>
              </Form.Item>
            </Col>
            
            <Col span={8}>
              <Form.Item
                label="检查标签匹配"
                name="check_tags"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              保存设置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default SettingsPage;