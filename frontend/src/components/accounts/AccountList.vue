<script setup lang="ts">
/**
 * Account List Component
 *
 * Displays list of accounts with loading and empty states.
 * When reorderMode is true, active accounts become draggable via vuedraggable.
 * Archived accounts are always non-draggable and rendered below active ones.
 */

import { computed, ref, watch } from 'vue'
import draggable from 'vuedraggable'
import AccountCard from './AccountCard.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import type { Account } from '@/types'

interface Props {
  accounts: Account[]
  balances: Map<string, number>
  loading?: boolean
  reorderMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  reorderMode: false
})

const emit = defineEmits<{
  'account-click': [account: Account]
  'create-click': []
  'reorder': [orderedIds: string[]]
}>()

const hasAccounts = computed(() => props.accounts.length > 0)

// Separate active and archived — archived are always below and never draggable.
const activeAccounts = computed(() => props.accounts.filter(a => a.active !== false))
const archivedAccounts = computed(() => props.accounts.filter(a => a.active === false))

// vuedraggable needs a mutable ref it can reorder.
// We sync it whenever the parent list changes (e.g. after a successful store write).
const draggableList = ref<Account[]>([...activeAccounts.value])

watch(
  () => activeAccounts.value,
  (newVal) => {
    draggableList.value = [...newVal]
  }
)

function getBalance(accountId: string): number {
  return props.balances.get(accountId) || 0
}

function onDragEnd() {
  emit('reorder', draggableList.value.map(a => a.id))
}
</script>

<template>
  <div>
    <!-- Loading state -->
    <BaseSpinner v-if="loading" centered />

    <!-- Empty state -->
    <EmptyState
      v-else-if="!hasAccounts"
      title="No tienes cuentas"
      message="Crea tu primera cuenta para comenzar a registrar tus movimientos financieros"
      icon="💳"
      action-text="Crear cuenta"
      @action="emit('create-click')"
    />

    <!-- Account list -->
    <div v-else class="space-y-3">
      <!-- Active accounts — draggable when reorderMode is true -->
      <draggable
        v-if="reorderMode"
        v-model="draggableList"
        item-key="id"
        handle=".drag-handle"
        :animation="200"
        @end="onDragEnd"
      >
        <template #item="{ element: account }">
          <div class="relative mb-3">
            <AccountCard
              :account="account"
              :balance="getBalance(account.id)"
              :show-drag-handle="true"
              :clickable="false"
            />
          </div>
        </template>
      </draggable>

      <!-- Active accounts — normal clickable mode -->
      <template v-else>
        <div
          v-for="account in activeAccounts"
          :key="account.id"
          class="relative"
        >
          <AccountCard
            :account="account"
            :balance="getBalance(account.id)"
            @click="emit('account-click', account)"
          />
        </div>
      </template>

      <!-- Archived accounts — always below active, never draggable -->
      <div
        v-for="account in archivedAccounts"
        :key="account.id"
        class="relative opacity-50"
      >
        <AccountCard
          :account="account"
          :balance="getBalance(account.id)"
          @click="!reorderMode && emit('account-click', account)"
        />
      </div>
    </div>
  </div>
</template>
