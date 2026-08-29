// 前端连接配置（部署时只需修改本文件）
// 开发环境走 Vite 代理：/api → http://127.0.0.1:8000
export const API_BASE = '/api'

// 客户端密钥回退（仅无平台登录的调试场景使用；留空 = 只用平台 JWT）
// 正式环境请保持为空，登录后由 JWT 鉴权
export const API_KEY = ''

// 留空则使用 BFF 默认模型（管理平台「模型接入」可在线修改）
export const DEFAULT_MODEL = ''
