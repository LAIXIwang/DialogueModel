import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

import App from '../App.vue'

let pinia

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  // 预置登录态，避免 App 挂载后跳转登录页
  localStorage.setItem('dialogue.admin.access', 'test-token')
  localStorage.setItem('dialogue.admin.refresh', 'test-refresh')
  localStorage.setItem(
    'dialogue.admin.user',
    JSON.stringify({ id: 1, username: 'admin', role_name: '超级管理员', role_code: 'super_admin', permissions: [] }),
  )
})

afterEach(() => {
  localStorage.clear()
})

describe('App', () => {
  it('渲染黑色主题对话界面', () => {
    const wrapper = mount(App, { global: { plugins: [pinia] } })
    expect(wrapper.text()).toContain('Dialogue')
    expect(wrapper.text()).toContain('新对话')
  })

  it('渲染输入框与登录用户信息', () => {
    const wrapper = mount(App, { global: { plugins: [pinia] } })
    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.find('textarea').attributes('placeholder')).toContain('输入消息')
    expect(wrapper.text()).toContain('admin')
  })
})
