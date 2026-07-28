const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 获取应用版本
  getVersion: () => process.env.npm_package_version || '1.0.0',
  
  // 平台信息
  platform: process.platform,
  
  // 是否是打包后的应用
  isPackaged: process.env.NODE_ENV === 'production'
});
