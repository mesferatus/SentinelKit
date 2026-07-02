import { describe, expect, it } from 'vitest'

import { resolveAuthNavigation } from './guards'

describe('route guards', () => {
  it('redirects guests from private routes to login', () => {
    expect(resolveAuthNavigation({ requiresAuth: true }, false)).toEqual({
      name: 'login',
      query: { redirect: '/' },
    })
  })

  it('redirects authenticated users away from guest routes', () => {
    expect(resolveAuthNavigation({ guestOnly: true }, true)).toEqual({ name: 'dashboard' })
  })

  it('allows navigation when the route matches the session state', () => {
    expect(resolveAuthNavigation({ requiresAuth: true }, true)).toBe(true)
  })
})
