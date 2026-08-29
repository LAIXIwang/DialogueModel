#!/usr/bin/env bash
# DialogueModel 一键部署脚本（Linux 服务器，需已安装 Docker 与 Docker Compose）
# 兼容：docker compose (v2 插件) 与 docker-compose (v1 独立版)
set -euo pipefail

cd "$(dirname "$0")"

# 首次运行：生成环境变量文件（compose 会自动读取项目目录下的 .env）
if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "[deploy] 已生成 .env（请按需修改 JWT_SECRET / UPSTREAM_API_KEY 等）"
fi

# 自动探测可用的 Compose 命令
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif docker-compose --version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "[deploy] 未检测到 Docker Compose，请先安装：" >&2
  echo "         Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y docker-compose-plugin" >&2
  echo "         CentOS/RHEL:   sudo yum install -y docker-compose-plugin" >&2
  exit 1
fi

$COMPOSE up -d --build

echo ""
echo "=============================================="
echo " 部署完成 ✅"
echo "   对话平台:  http://<服务器IP>/           （默认端口 80）"
echo "   管理后台:  http://<服务器IP>/login"
echo "   默认管理员: admin / Admin@123456（登录后请立即修改密码）"
echo "=============================================="
