/**
 * 构建后端 - 使用 PyInstaller 打包 Python 后端
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const backendDir = path.join(__dirname, '..', '..', 'mteam-helper', 'backend');
const outputDir = path.join(__dirname, '..', 'backend-dist');

console.log('========================================');
console.log('构建 Python 后端');
console.log('========================================');

// 确保输出目录存在
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// 创建 PyInstaller spec 文件
const specContent = `
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['${backendDir.replace(/\\/g, '\\\\')}'],
    binaries=[],
    datas=[
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'httptools',
        'dotenv',
        'sqlalchemy.dialects.sqlite',
        'pydantic',
        'pydantic_settings',
        'apscheduler',
        'apscheduler.schedulers.asyncio',
        'apscheduler.triggers.interval',
        'httpx',
        'qbittorrentapi',
        'transmission_rpc',
        'bencodepy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mteam-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
`;

const specPath = path.join(backendDir, 'mteam-backend.spec');
fs.writeFileSync(specPath, specContent);

console.log('1. 安装 PyInstaller...');
try {
  execSync('pip install pyinstaller', { stdio: 'inherit' });
} catch (e) {
  console.log('PyInstaller 可能已安装');
}

console.log('2. 打包后端...');
try {
  execSync(`pyinstaller --clean --noconfirm "${specPath}"`, {
    cwd: backendDir,
    stdio: 'inherit'
  });
} catch (e) {
  console.error('打包失败:', e.message);
  process.exit(1);
}

console.log('3. 复制输出文件...');
const distExe = path.join(backendDir, 'dist', 'mteam-backend.exe');
const targetExe = path.join(outputDir, 'mteam-backend.exe');

if (fs.existsSync(distExe)) {
  fs.copyFileSync(distExe, targetExe);
  console.log('后端构建完成:', targetExe);
} else {
  console.error('找不到构建输出文件');
  process.exit(1);
}

// 清理临时文件
console.log('4. 清理临时文件...');
const buildDir = path.join(backendDir, 'build');
const distDir = path.join(backendDir, 'dist');
if (fs.existsSync(buildDir)) {
  fs.rmSync(buildDir, { recursive: true });
}
if (fs.existsSync(distDir)) {
  fs.rmSync(distDir, { recursive: true });
}
fs.unlinkSync(specPath);

console.log('后端构建完成！');
