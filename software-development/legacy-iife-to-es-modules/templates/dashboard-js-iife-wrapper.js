/* ============================================
   <APP_NAME> — Dashboard Application
   ============================================ */

// PR-N of the refactor: <APP>'s IIFE used to depend on the new
// lib modules loading before it (via <script type="module"
// src="..."> tags preceding it in <HTML>.html). That
// approach failed in some browser environments (Browser-Use
// sandboxes reject <script type="module" src="..."> in
// unpredictable ways, leaving globalThis.X undefined when this
// IIFE starts).
//
// The fix has two parts:
//   1. <HTML>.html no longer pre-loads the modules via
//      <script type="module" src="...">. See <HTML>.html for
//      why.
//   2. This file's IIFE body is now the .then() callback of a
//      dynamic-import() promise chain. We use a unique cache-
//      buster per page load to force the browser to actually
//      re-fetch the modules (even if it has them cached from
//      earlier this session) and re-run their top-level code,
//      so the globalThis.X side effects always run. (Without
//      the cache buster, the browser returns the cached module
//      object whose top-level code already ran — meaning
//      globalThis.X might be undefined if the cached module was
//      an older version that didn't have the side effect.)
const _modulePromises = [
  import('/js/config.js?cb=' + Date.now()),
  import('/js/lib/<MODULE_1>.js?cb=' + Date.now()),
  import('/js/lib/<MODULE_2>.js?cb=' + Date.now()),
  // ... one line per module
];
Promise.all(_modulePromises).then(() => {
  (function() {
   'use strict';

  // ============================================
  // CONFIG
  // ============================================
  const API_BASE = '';

  // PR-N of the refactor: alias the new modules' globalThis exports
  // to local consts so the rest of the IIFE body can keep using
  // bare-identifier references (`<helper1>`, `<helper2>`, etc.)
  // without every site being rewritten.
  //
  // The modules set these on globalThis via their dual-export
  // pattern (see lib/<helper>.js). Classic-script blocks (like
  // this one) wait for preceding <script type="module"> tags per
  // HTML spec, so by the time the IIFE runs, the modules have
  // already evaluated and the globals are populated.
  //
  // If a global is missing, we use a lazy globalThis lookup so
  // top-level statements like `els.content.addEventListener(...)`
  // don't throw ReferenceError if a module failed to load — they
  // throw at use-time instead, which is more debuggable.
  const _lookupGlobal = (key) => globalThis[key];
  const <HELPER_1> = _lookupGlobal('<helper1>');
  const <HELPER_2> = _lookupGlobal('<helper2>');
  // ... 38 lines like this for a 4,000-line IIFE

  // ... <INSERT 4,000 LINES OF LEGACY CODE HERE, UNCHANGED> ...

  // Start
  if (typeof document !== 'undefined' && document && document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else if (typeof init === 'function') {
    init();
  } else {
    init();
  }
  })();
}).catch(e => {
  if (typeof console !== 'undefined') console.error('PR-N: failed to load dashboard lib modules:', e);
});
