/**
 * 生成应用图标
 * 使用 sharp 库创建一个 M-Team Helper 图标
 */

const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

// 创建 SVG 图标
function createIconSVG(size) {
  const center = size / 2;
  const radius = size * 0.45;
  
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#41D1FF"/>
      <stop offset="100%" stop-color="#BD34FE"/>
    </linearGradient>
  </defs>
  <!-- 圆形背景 -->
  <circle cx="${center}" cy="${center}" r="${radius}" fill="url(#bg)"/>
  <!-- M 字母 -->
  <text x="${center}" y="${center + size * 0.12}" 
        font-family="Arial, sans-serif" 
        font-size="${size * 0.5}" 
        font-weight="bold" 
        fill="white" 
        text-anchor="middle">M</text>
</svg>`;
}

// 主函数
async function main() {
  console.log('生成应用图标...');
  
  const outputDir = path.join(__dirname, '..');
  
  // 生成 SVG
  const svg = createIconSVG(256);
  const svgPath = path.join(outputDir, 'icon.svg');
  fs.writeFileSync(svgPath, svg);
  console.log('SVG 图标已生成:', svgPath);
  
  // 使用 sharp 转换为 PNG
  const pngPath = path.join(outputDir, 'icon.png');
  await sharp(Buffer.from(svg))
    .resize(256, 256)
    .png()
    .toFile(pngPath);
  console.log('PNG 图标已生成:', pngPath);
  
  // 生成多尺寸 PNG 用于 ICO
  const sizes = [16, 32, 48, 64, 128, 256];
  const pngBuffers = [];
  
  for (const size of sizes) {
    const buffer = await sharp(Buffer.from(createIconSVG(size)))
      .resize(size, size)
      .png()
      .toBuffer();
    pngBuffers.push({ size, buffer });
  }
  
  // 使用 to-ico 转换
  try {
    const toIco = require('to-ico');
    const ico = await toIco([fs.readFileSync(pngPath)]);
    const icoPath = path.join(outputDir, 'icon.ico');
    fs.writeFileSync(icoPath, ico);
    console.log('ICO 图标已生成:', icoPath);
  } catch (err) {
    console.error('ICO 转换失败:', err.message);
  }
  
  console.log('图标生成完成！');
}

main().catch(console.error);
