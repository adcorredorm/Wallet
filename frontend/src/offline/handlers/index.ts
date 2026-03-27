/**
 * Handler barrel — importing this file triggers self-registration of all
 * entity handlers into the handlerRegistry singleton.
 *
 * This file MUST be imported at app startup (via offline/index.ts) before
 * the first processQueue() call so all handlers are available.
 */

import './account'
import './transaction'
import './transfer'
import './category'
import './setting'
import './dashboard'
import './dashboard-widget'
