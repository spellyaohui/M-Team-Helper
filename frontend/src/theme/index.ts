import { ThemeConfig, theme } from 'antd';

// 亮色主题配置
export const lightTheme: ThemeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#3b82f6', // 更现代的蓝色 (Tailwind Blue 500)
    borderRadius: 12,
    wireframe: false,
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f3f4f6', // 浅灰色背景
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  },
  components: {
    Card: {
      boxShadowTertiary: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      paddingLG: 24,
    },
    Button: {
      controlHeight: 36,
      boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    },
    Table: {
      borderRadiusLG: 12,
    },
    Menu: {
      itemBorderRadius: 8,
      itemMarginInline: 8,
    }
  },
};

// 暗色主题配置
export const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#60a5fa', // Tailwind Blue 400
    borderRadius: 12,
    colorBgContainer: '#1f2937', // Tailwind Gray 800
    colorBgLayout: '#111827', // Tailwind Gray 900
    colorBgElevated: '#374151', // Tailwind Gray 700
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
  },
  components: {
    Menu: {
      itemBorderRadius: 8,
      itemMarginInline: 8,
    }
  },
};

export const customColors = {
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
};
