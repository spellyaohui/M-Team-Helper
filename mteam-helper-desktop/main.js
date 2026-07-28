const { app, BrowserWindow, Tray, Menu, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// 保持对窗口和托盘的引用，防止被垃圾回收
let mainWindow = null;
let tray = null;
let backendProcess = null;
let isQuitting = false;

// 后端端口
const BACKEND_PORT = 8001;

// 获取资源路径
function getResourcePath(relativePath) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, relativePath);
  }
  return path.join(__dirname, relativePath);
}

// 获取用户数据目录
function getUserDataPath() {
  return app.getPath('userData');
}

// 确保数据目录存在
function ensureDataDir() {
  const dataDir = path.join(getUserDataPath(), 'data');
  const torrentsDir = path.join(dataDir, 'torrents');
  
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  if (!fs.existsSync(torrentsDir)) {
    fs.mkdirSync(torrentsDir, { recursive: true });
  }
  
  return dataDir;
}

// 启动后端服务
function startBackend() {
  return new Promise((resolve, reject) => {
    const dataDir = ensureDataDir();
    
    let backendPath;
    if (app.isPackaged) {
      // 打包后使用 PyInstaller 生成的可执行文件
      backendPath = path.join(process.resourcesPath, 'backend', 'mteam-backend.exe');
    } else {
      // 开发模式使用 Python
      backendPath = 'python';
    }
    
    console.log('启动后端服务:', backendPath);
    console.log('数据目录:', dataDir);
    
    const env = {
      ...process.env,
      MTEAM_DATA_DIR: dataDir,
    };
    
    if (app.isPackaged) {
      backendProcess = spawn(backendPath, [], {
        cwd: path.dirname(backendPath),
        env: env,
        stdio: ['pipe', 'pipe', 'pipe']
      });
    } else {
      // 开发模式
      const mainPy = path.join(__dirname, '..', 'mteam-helper', 'backend', 'main.py');
      backendProcess = spawn(backendPath, [mainPy], {
        cwd: path.join(__dirname, '..', 'mteam-helper', 'backend'),
        env: env,
        stdio: ['pipe', 'pipe', 'pipe']
      });
    }
    
    backendProcess.stdout.on('data', (data) => {
      console.log(`[Backend] ${data}`);
      // 检测服务启动成功
      if (data.toString().includes('Uvicorn running') || data.toString().includes('Application startup complete')) {
        resolve();
      }
    });
    
    backendProcess.stderr.on('data', (data) => {
      console.error(`[Backend Error] ${data}`);
    });
    
    backendProcess.on('error', (err) => {
      console.error('后端启动失败:', err);
      reject(err);
    });
    
    backendProcess.on('close', (code) => {
      console.log(`后端进程退出，代码: ${code}`);
      if (!isQuitting) {
        // 非正常退出，尝试重启
        setTimeout(() => {
          console.log('尝试重启后端...');
          startBackend();
        }, 3000);
      }
    });
    
    // 设置超时，如果10秒内没有启动成功也继续
    setTimeout(() => {
      resolve();
    }, 10000);
  });
}

// 停止后端服务
function stopBackend() {
  if (backendProcess) {
    console.log('停止后端服务...');
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    icon: path.join(__dirname, 'icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false,
    title: 'M-Team Helper'
  });
  
  // 加载前端页面
  if (app.isPackaged) {
    // 打包后加载本地文件
    mainWindow.loadFile(path.join(__dirname, 'frontend', 'index.html'));
  } else {
    // 开发模式加载后端服务
    mainWindow.loadURL(`http://localhost:${BACKEND_PORT}`);
  }
  
  // 窗口准备好后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
  
  // 点击关闭按钮时最小化到托盘
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  
  // 打开外部链接
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// 创建系统托盘
function createTray() {
  const iconPath = path.join(__dirname, 'icon.ico');
  
  // 如果图标不存在，使用默认图标
  if (!fs.existsSync(iconPath)) {
    console.log('托盘图标不存在，跳过创建托盘');
    return;
  }
  
  tray = new Tray(iconPath);
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: '打开数据目录',
      click: () => {
        shell.openPath(getUserDataPath());
      }
    },
    { type: 'separator' },
    {
      label: '重启后端服务',
      click: async () => {
        stopBackend();
        await startBackend();
        dialog.showMessageBox({
          type: 'info',
          title: '提示',
          message: '后端服务已重启'
        });
      }
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);
  
  tray.setToolTip('M-Team Helper');
  tray.setContextMenu(contextMenu);
  
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// 应用准备就绪
app.whenReady().then(async () => {
  console.log('M-Team Helper 启动中...');
  
  // 启动后端服务
  try {
    await startBackend();
    console.log('后端服务已启动');
  } catch (err) {
    console.error('后端启动失败:', err);
    dialog.showErrorBox('启动失败', '后端服务启动失败，请检查日志');
  }
  
  // 创建窗口和托盘
  createWindow();
  createTray();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 所有窗口关闭时
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // 不退出，保持托盘运行
  }
});

// 应用退出前
app.on('before-quit', () => {
  isQuitting = true;
  stopBackend();
});

// 应用退出
app.on('quit', () => {
  stopBackend();
});

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  console.error('未捕获的异常:', error);
});
