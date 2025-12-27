import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import viteCompression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    react(),
    // 启用 Gzip 压缩
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 1024, // 只压缩大于 1KB 的文件
    })
  ],
  // Electron 打包需要使用相对路径
  base: './',
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
    // 启用压缩和优化
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // 生产环境移除 console.log
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug']
      }
    },
    rollupOptions: {
      output: {
        // 更细粒度的代码分割
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'react-router': ['react-router-dom'],
          'antd-core': ['antd'],
          'antd-icons': ['@ant-design/icons'],
          'http-utils': ['axios'],
          'date-utils': ['dayjs'],
          // 将图表组件单独分离，实现真正的按需加载
          'charts': ['@ant-design/plots'],
        },
        // 为静态资源添加哈希，启用长期缓存
        assetFileNames: 'assets/[name].[hash].[ext]',
        chunkFileNames: 'assets/[name].[hash].js',
        entryFileNames: 'assets/[name].[hash].js'
      },
    },
  },
});
