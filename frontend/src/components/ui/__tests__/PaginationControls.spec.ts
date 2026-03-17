import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PaginationControls from '../PaginationControls.vue'

describe('PaginationControls — visibility', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders nothing when totalPages is 0', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 1, totalPages: 0, pageSize: 20 },
    })
    expect(wrapper.find('[role="navigation"]').exists()).toBe(false)
  })

  it('renders nothing when totalPages is 1', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 1, totalPages: 1, pageSize: 20 },
    })
    expect(wrapper.find('[role="navigation"]').exists()).toBe(false)
  })

  it('renders when totalPages is 2', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 1, totalPages: 2, pageSize: 20 },
    })
    expect(wrapper.find('[role="navigation"]').exists()).toBe(true)
  })
})

describe('PaginationControls — page info display', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows "Página 2 de 5" when currentPage=2 and totalPages=5', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 2, totalPages: 5, pageSize: 20 },
    })
    expect(wrapper.text()).toMatch(/Página\s+2\s+de\s+5/)
  })
})

describe('PaginationControls — button states', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('previous button is disabled on page 1', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 1, totalPages: 3, pageSize: 20 },
    })
    const prevBtn = wrapper.find('[data-testid="pagination-prev"]')
    expect(prevBtn.attributes('disabled')).toBeDefined()
  })

  it('next button is disabled on last page', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 3, totalPages: 3, pageSize: 20 },
    })
    const nextBtn = wrapper.find('[data-testid="pagination-next"]')
    expect(nextBtn.attributes('disabled')).toBeDefined()
  })

  it('both buttons are enabled on a middle page', () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 2, totalPages: 5, pageSize: 20 },
    })
    const prevBtn = wrapper.find('[data-testid="pagination-prev"]')
    const nextBtn = wrapper.find('[data-testid="pagination-next"]')
    expect(prevBtn.attributes('disabled')).toBeUndefined()
    expect(nextBtn.attributes('disabled')).toBeUndefined()
  })
})

describe('PaginationControls — emit events', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('emits page-change with currentPage-1 when previous is clicked', async () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 2, totalPages: 5, pageSize: 20 },
    })
    await wrapper.find('[data-testid="pagination-prev"]').trigger('click')
    expect(wrapper.emitted('page-change')).toBeTruthy()
    expect(wrapper.emitted('page-change')![0]).toEqual([1])
  })

  it('emits page-change with currentPage+1 when next is clicked', async () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 2, totalPages: 5, pageSize: 20 },
    })
    await wrapper.find('[data-testid="pagination-next"]').trigger('click')
    expect(wrapper.emitted('page-change')).toBeTruthy()
    expect(wrapper.emitted('page-change')![0]).toEqual([3])
  })

  it('does not emit when previous is clicked on page 1', async () => {
    const wrapper = mount(PaginationControls, {
      props: { currentPage: 1, totalPages: 3, pageSize: 20 },
    })
    await wrapper.find('[data-testid="pagination-prev"]').trigger('click')
    expect(wrapper.emitted('page-change')).toBeFalsy()
  })
})
