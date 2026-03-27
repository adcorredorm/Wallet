/**
 * HandlerRegistry — dynamic entity handler registry for SyncManager.
 *
 * Instead of a switch statement in SyncManager.sendToServer(), each entity
 * type registers its own handler at module load time. SyncManager calls
 * registry.getHandler(entityType) to dispatch.
 *
 * Adding a new entity type becomes: (1) create handler file, (2) register it.
 * Zero changes to SyncManager.
 */

import type { PendingMutation } from './types'

export interface EntityHandler {
  create(mutation: PendingMutation, payload: Record<string, unknown>): Promise<unknown>
  update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<unknown>
  delete(mutation: PendingMutation, payload: Record<string, unknown>): Promise<unknown>
  delete_permanent?(mutation: PendingMutation, payload: Record<string, unknown>): Promise<unknown>
}

class HandlerRegistry {
  private handlers = new Map<string, EntityHandler>()

  register(entityType: string, handler: EntityHandler): void {
    this.handlers.set(entityType, handler)
  }

  getHandler(entityType: string): EntityHandler {
    const handler = this.handlers.get(entityType)
    if (!handler) {
      throw new Error(
        `[HandlerRegistry] No handler registered for entity type '${entityType}'. ` +
        `Registered types: ${[...this.handlers.keys()].join(', ')}`
      )
    }
    return handler
  }
}

export const handlerRegistry = new HandlerRegistry()
