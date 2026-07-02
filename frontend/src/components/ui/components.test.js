import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import EmptyState from './EmptyState.vue'
import MetricCard from './MetricCard.vue'
import TaskStatus from './TaskStatus.vue'

describe('design system components', () => {
  it('announces metric values with a clear accessible label', () => {
    render(MetricCard, {
      props: { label: 'Scans', value: 24, tone: 'teal', hint: '+ 3 esta semana' },
    })
    expect(screen.getByRole('group', { name: 'Scans: 24' })).toBeTruthy()
  })

  it('renders task status as readable text instead of color alone', () => {
    render(TaskStatus, { props: { status: 'completed' } })
    expect(screen.getByText('Concluído')).toBeTruthy()
  })

  it('provides an optional empty-state action', () => {
    render(EmptyState, {
      props: { title: 'Nada por aqui', description: 'Crie seu primeiro scan.', actionLabel: 'Novo scan' },
    })
    expect(screen.getByRole('button', { name: 'Novo scan' })).toBeTruthy()
  })
})
