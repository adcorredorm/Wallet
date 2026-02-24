<script setup lang="ts">
/**
 * Account Card Component
 *
 * Displays account summary with balance
 * Mobile-optimized card layout
 */

import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
// Phase 5: SyncBadge shows per-item sync state (pending / error dot)
import SyncBadge from '@/components/sync/SyncBadge.vue'
import { formatAccountType } from '@/utils/formatters'
import type { Account } from '@/types'
import type { LocalAccount } from '@/offline/types'

interface Props {
  /**
   * Why accept LocalAccount | Account?
   * The store exposes LocalAccount[] (extends Account with _sync_status).
   * Downstream consumers that don't use offline mode can still pass a plain
   * Account — the badge simply won't render because _sync_status will be
   * undefined, which the v-if check below handles gracefully.
   */
  account: LocalAccount | Account
  balance?: number
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  balance: 0,
  clickable: true
})

const emit = defineEmits<{
  click: []
}>()

const accountTypeLabel = computed(() => formatAccountType(props.account.tipo))

// Icon for account type
const accountIcon = computed(() => {
  const icons: Record<string, string> = {
    debito: '💳',
    credito: '💳',
    efectivo: '💵'
  }
  return icons[props.account.tipo] || '💰'
})
</script>

<template>
  <BaseCard :clickable="clickable" @click="emit('click')">
    <div class="flex items-center justify-between">
      <!-- Left: Icon and info -->
      <div class="flex items-center gap-3 flex-1 min-w-0">
        <!-- Icon -->
        <div class="text-3xl flex-shrink-0">
          {{ accountIcon }}
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <!--
            Why flex + items-center on the title row?
            We need the account name and the SyncBadge dot to sit on the same
            baseline. flex + items-center achieves this without a table layout.
            gap-2 (8px) ensures the dot has breathing room from the name text.
          -->
          <div class="flex items-center gap-2">
            <h3 class="font-semibold truncate">
              {{ account.nombre }}
            </h3>
            <!--
              SyncBadge is only rendered when the account has a _sync_status
              field (i.e. it is a LocalAccount from the offline-first store).
              The 'in' operator checks for the key's existence at runtime.
              This makes AccountCard safe to use with plain Account objects too.
            -->
            <SyncBadge
              v-if="'_sync_status' in account"
              :status="(account as LocalAccount)._sync_status"
            />
          </div>
          <p class="text-sm text-dark-text-secondary">
            {{ accountTypeLabel }} • {{ account.divisa }}
          </p>
        </div>
      </div>

      <!-- Right: Balance -->
      <div class="flex-shrink-0 text-right ml-3">
        <CurrencyDisplay
          :amount="balance"
          :currency="account.divisa"
          size="lg"
          compact
        />
      </div>
    </div>

    <!-- Tags (if any) -->
    <div v-if="account.tags && account.tags.length > 0" class="flex gap-2 mt-3">
      <span
        v-for="tag in account.tags.slice(0, 3)"
        :key="tag"
        class="badge badge-primary text-xs"
      >
        {{ tag }}
      </span>
      <span v-if="account.tags.length > 3" class="text-xs text-dark-text-tertiary">
        +{{ account.tags.length - 3 }}
      </span>
    </div>
  </BaseCard>
</template>
