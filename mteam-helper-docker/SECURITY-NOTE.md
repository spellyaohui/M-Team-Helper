# 安全/扫描说明

记录最近对 `spellyaohui/mteam-helper` Docker 镜像的加固与扫描情况。

## 时间线
- 2026-01-27：在 Dockerfile 固定 `wheel==0.46.2`，修复 CVE-2026-24049。
- 2026-01-27：将 `python-multipart` 升级到 0.0.22 并强制安装，修复 CVE-2026-24486。
- 2026-01-27：新增根级 `.dockerignore`，排除本地 venv/data 出构建上下文，重建并推送镜像。

## 当前镜像标签
- `spellyaohui/mteam-helper:2.0.4`
- `spellyaohui/mteam-helper:latest`

两个标签当前指向的 digest：
```
sha256:e8d450440cc4c76cceb30286635abb1d7bfb75858064c2b1e56c2b2e90d4ba17
```

## 尚存漏洞
- Debian 基础镜像 glibc CVE-2026-0861（HIGH）。上游暂无修复版，需等待 Debian/`python:3.11-slim` 发布补丁后重建。

## 扫描命令（本地，Docker 方式 Trivy）
- 清理扫描缓存：
```
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy clean --scan-cache
```
- 仅扫 HIGH/CRITICAL：
```
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --no-progress --scanners vuln --severity HIGH,CRITICAL spellyaohui/mteam-helper:2.0.4
```

## 构建/推送步骤
- 从仓库根目录构建（带 dockerignore，且无缓存）：
```
docker build --no-cache -f mteam-helper-docker/Dockerfile -t spellyaohui/mteam-helper:2.0.4 .
```
- 打 latest 标签：
```
docker tag spellyaohui/mteam-helper:2.0.4 spellyaohui/mteam-helper:latest
```
- 推送：
```
docker push spellyaohui/mteam-helper:2.0.4
docker push spellyaohui/mteam-helper:latest
```

## Dockerfile 加固要点
- 固定 wheel 到 0.46.2。
- 在安装依赖后强制 `python-multipart==0.0.22`。
- pip 使用清华镜像加速。

## dockerignore 说明
- 根 `.dockerignore` 排除：venv/.venv、**/__pycache__、data、node_modules、dist/build 产物、env 文件、日志，避免把本地 venv 旧依赖打进镜像。

## 后续动作
- 关注 Debian/`python:3.11-slim` 的 glibc 修复，发布后重建并推送。
- 重建后再次运行上述 Trivy 命令确认 glibc CVE 是否清除。
