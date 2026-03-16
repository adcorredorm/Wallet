/**
 * Declaración de tipos para Google Identity Services (GSI) SDK.
 *
 * El SDK se carga externamente via <script> en index.html, por lo que
 * TypeScript no lo conoce por defecto. Esta declaración minimal cubre
 * solo los métodos que useAuthStore y LoginView usan.
 *
 * Documentación completa: https://developers.google.com/identity/gsi/web/reference/js-reference
 */

interface GoogleAccountsId {
  initialize(config: {
    client_id: string
    callback: (response: { credential: string }) => void
    auto_select?: boolean
    cancel_on_tap_outside?: boolean
  }): void
  prompt(momentListener?: (notification: {
    isNotDisplayed(): boolean
    isSkippedMoment(): boolean
  }) => void): void
  renderButton(
    parent: HTMLElement,
    options: {
      theme?: 'outline' | 'filled_blue' | 'filled_black'
      size?: 'large' | 'medium' | 'small'
      text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
      shape?: 'rectangular' | 'pill' | 'circle' | 'square'
      width?: number
      locale?: string
    }
  ): void
  disableAutoSelect(): void
  revoke(hint: string, callback?: () => void): void
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: GoogleAccountsId
      }
    }
  }
}

export {}
