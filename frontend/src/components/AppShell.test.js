import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AppShell from './AppShell.vue'

vi.mock('vue-router', () => ({
  RouterLink: {
    props: ['to'],
    emits: ['click'],
    template: '<a href="#" @click="$emit(\'click\')"><slot /></a>',
  },
  useRouter: () => ({ push: vi.fn() }),
}))

describe('AppShell mobile menu', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uses a dynamic accessible label and closes after navigation', async () => {
    const wrapper = mount(AppShell)
    const menu = wrapper.get('button.icon-button')

    expect(menu.attributes('aria-label')).toBe('Abrir menu')
    await menu.trigger('click')
    expect(menu.attributes('aria-label')).toBe('Fechar menu')
    expect(wrapper.find('aside').classes()).toContain('sidebar--open')

    await wrapper.find('nav a').trigger('click')
    expect(menu.attributes('aria-label')).toBe('Abrir menu')
    expect(wrapper.find('aside').classes()).not.toContain('sidebar--open')
  })
})
