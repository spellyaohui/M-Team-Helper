import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4000,
    host: 'localhost',
    // 开发时代理 API 请求到后端
    proxy: {
      '/auth': 'http://localhost:8001',
      '/accounts': 'http://localhost:8001',
      '/downloaders': 'http://localhost:8001',
      '/torrents': 'http://localhost:8001',
      '/rules': 'http://localhost:8001',
      '/history': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd': ['antd', '@ant-design/icons'],
          'charts': ['@ant-design/plots'],
          'utils': ['axios', 'dayjs'],
        },
      },
    },
  },
});
