import { describe, expect, it } from 'vitest'

import { formatLocalDateTime, localDateTimeToIso } from './localDateTime'

describe('local datetime helpers', () => {
  it('formats date fields from local components without UTC shifting', () => {
    const fakeDate = {
      getFullYear: () => 2026,
      getMonth: () => 5,
      getDate: () => 21,
      getHours: () => 9,
      getMinutes: () => 7,
    }

    expect(formatLocalDateTime(fakeDate)).toBe('2026-06-21T09:07')
  })

  it('converts a datetime-local value to an ISO UTC instant', () => {
    const value = '2026-06-21T09:07'
    expect(localDateTimeToIso(value)).toBe(new Date(2026, 5, 21, 9, 7).toISOString())
  })
})
