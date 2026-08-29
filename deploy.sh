#!/usr/bin/env bash
# DialogueModel 一键部署脚本（Linux 服务器，需已安装 Docker + Docker Compose）
set -euo pipefail

cd "$(dirname "$0")"

# 首次运行：生成环境变量文件
if [ ! -f .env.docker ]; then
  cp .env.docker.example .env.docker
  echo "[deploy] 已生成 .env.docker（请按需修改 JWT_SECRET / UPSTREAM_API_KEY 等）"
fi

docker compose --env-file .env.docker up -d --build

echo ""
echo "=============================================="
echo " 部署完成 ✅"
echo "   对话平台:  http://<服务器IP>/           （默认端口 80）"
echo "   管理后台:  http://<服务器IP>/login"
echo "   默认管理员: admin / Admin@123456（登录后请立即修改密码）"
echo "=============================================="
