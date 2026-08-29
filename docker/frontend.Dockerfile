# 前端镜像：Vite 构建 + Nginx 静态托管 + 反代两个后端
FROM node:24-alpine AS build

WORKDIR /app

COPY vue-project/package.json vue-project/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY vue-project/ .
RUN npm run build

FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
