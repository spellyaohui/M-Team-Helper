/**
 * 构建前端 - 重新构建并复制前端产物
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const frontendSrc = path.join(__dirname, '..', '..', 'mteam-helper', 'frontend');
const frontendDist = path.join(frontendSrc, 'dist');
const outputDir = path.join(__dirname, '..', 'frontend');

console.log('========================================');
console.log('构建前端');
console.log('========================================');

// 总是重新构建前端
console.log('1. 安装前端依赖...');
execSync('npm install', { cwd: frontendSrc, stdio: 'inherit' });

// 删除旧的构建产物
if (fs.existsSync(frontendDist)) {
  console.log('2. 清理旧的构建产物...');
  fs.rmSync(frontendDist, { recursive: true });
}

console.log('3. 构建前端...');
execSync('npm run build', { cwd: frontendSrc, stdio: 'inherit' });

// 复制构建产物
console.log('4. 复制前端文件...');

// 删除旧的输出目录
if (fs.existsSync(outputDir)) {
  fs.rmSync(outputDir, { recursive: true });
}

// 递归复制目录
function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

copyDir(frontendDist, outputDir);

// 修改 index.html 中的 API 地址（如果需要）
const indexPath = path.join(outputDir, 'index.html');
if (fs.existsSync(indexPath)) {
  let content = fs.readFileSync(indexPath, 'utf-8');
  // 确保 API 请求指向本地后端
  // 前端已经配置为相对路径，不需要修改
  fs.writeFileSync(indexPath, content);
}

console.log('前端构建完成！');
