/**
 * Vue Router Configuration
 *
 * Why Vue Router?
 * - Native Vue.js routing solution
 * - SPA navigation without page reloads
 * - Route guards for future auth
 * - Lazy loading for better performance
 *
 * Mobile-first considerations:
 * - Bottom navigation for primary routes
 * - Back button behavior matches native apps
 * - Smooth transitions between views
 */

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: {
        title: 'Wallet',
        showInBottomNav: true,
        icon: 'home'
      }
    },
    {
      path: '/accounts',
      name: 'accounts',
      component: () => import('@/views/accounts/AccountsListView.vue'),
      meta: {
        title: 'Cuentas',
        showInBottomNav: true,
        icon: 'wallet'
      }
    },
    {
      path: '/accounts/new',
      name: 'account-create',
      component: () => import('@/views/accounts/AccountCreateView.vue'),
      meta: {
        title: 'Nueva Cuenta',
        showBackButton: true
      }
    },
    {
      path: '/accounts/:id',
      name: 'account-detail',
      component: () => import('@/views/accounts/AccountDetailView.vue'),
      meta: {
        title: 'Detalle de Cuenta',
        showBackButton: true
      }
    },
    {
      path: '/accounts/:id/edit',
      name: 'account-edit',
      component: () => import('@/views/accounts/AccountEditView.vue'),
      meta: {
        title: 'Editar Cuenta',
        showBackButton: true
      }
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('@/views/transactions/TransactionsListView.vue'),
      meta: {
        title: 'Transacciones',
        showInBottomNav: true,
        icon: 'list'
      }
    },
    {
      path: '/transactions/new',
      name: 'transaction-create',
      component: () => import('@/views/transactions/TransactionCreateView.vue'),
      meta: {
        title: 'Nueva Transacción',
        showBackButton: true
      }
    },
    {
      path: '/transactions/:id/edit',
      name: 'transaction-edit',
      component: () => import('@/views/transactions/TransactionEditView.vue'),
      meta: {
        title: 'Editar Transacción',
        showBackButton: true
      }
    },
    {
      path: '/transfers',
      name: 'transfers',
      component: () => import('@/views/transfers/TransfersListView.vue'),
      meta: {
        title: 'Transferencias',
        showInBottomNav: true,
        icon: 'transfer'
      }
    },
    {
      path: '/transfers/new',
      name: 'transfer-create',
      component: () => import('@/views/transfers/TransferCreateView.vue'),
      meta: {
        title: 'Nueva Transferencia',
        showBackButton: true
      }
    },
    {
      path: '/transfers/:id/edit',
      name: 'transfer-edit',
      component: () => import('@/views/transfers/TransferEditView.vue'),
      meta: {
        title: 'Editar Transferencia',
        showBackButton: true
      }
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: () => import('@/views/AnalyticsView.vue'),
      meta: {
        title: 'Analytics',
        showInBottomNav: true,
        icon: 'chart-bar'
      }
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('@/views/categories/CategoriesListView.vue'),
      meta: {
        title: 'Categorías',
        showBackButton: false
      }
    },
    {
      path: '/categories/new',
      name: 'category-create',
      component: () => import('@/views/categories/CategoryCreateView.vue'),
      meta: {
        title: 'Nueva Categoría',
        showBackButton: true
      }
    },
    {
      path: '/categories/:id/edit',
      name: 'category-edit',
      component: () => import('@/views/categories/CategoryEditView.vue'),
      meta: {
        title: 'Editar Categoría',
        showBackButton: true
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/settings/SettingsView.vue'),
      meta: {
        title: 'Configuración',
        showBackButton: true
      }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: {
        title: 'Iniciar sesión',
        // Esta ruta NO usa AppLayout — tiene su propio layout centrado
        noLayout: true,
      }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: {
        title: 'Página no encontrada'
      }
    }
  ],
  scrollBehavior(to, from, savedPosition) {
    // Scroll to top on route change (mobile-friendly)
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Navigation guard for setting page title
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'Wallet'} - Wallet`
  next()
})

export default router
