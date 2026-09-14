#!/usr/bin/env node
/**
 * Minimal CDP driver for web-app UI verification (Node 24 built-in fetch + WebSocket, zero deps).
 * Usage: node cdp-driver.mjs <action> [args...]   (actions run in sequence)
 *   open <url>          navigate + wait for load
 *   text                dump body innerText (first 4000) + URL
 *   click <innerText>   click first element whose trimmed innerText matches (or startsWith for row labels)
 *   fill <selector> <v> set value on first matching input/textarea (React-safe)
 *   press <key>         keydown/keyup on the active element
 *   wait <ms>
 *   eval <expr>         raw Runtime.evaluate, JSON-stringified result
 *
 * See the skill's Pitfalls: helpers MUST be re-injected after every navigation;
 * React controlled inputs need the native value setter; scope queries to the
 * outermost container you actually care about.
 */
const CDP_BASE = "http://localhost:9222";

async function connect() {
  const targets = await (await fetch(`${CDP_BASE}/json/list`)).json();
  let page = targets.find((t) => t.type === "page");
  if (!page) {
    page = await (await fetch(`${CDP_BASE}/json/new?about:blank`, { method: "PUT" })).json();
  }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result);
    }
  };
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const i = ++id;
      pending.set(i, { resolve, reject });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
  await send("Page.enable");
  await send("Runtime.enable");
  return {
    send,
    async eval(expression) {
      const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error("eval error: " + JSON.stringify(r.exceptionDetails).slice(0, 300));
      return r.result?.value;
    },
  };
}

const HELPERS = `
window.__setVal = (el, v) => {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
};
window.__setSelect = (el, v) => {
  Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(el, v);
  el.dispatchEvent(new Event('change', { bubbles: true }));
};
window.__clickByText = (t, exact) => {
  const els = [...document.querySelectorAll('button, a, [role="button"], input[type="submit"], input[type="button"]')];
  const el = els.find(e => {
    const text = (e.innerText || e.value || '').trim();
    return exact ? text === t : text.startsWith(t);
  });
  if (!el) return 'NOT_FOUND: ' + t;
  el.click();
  return 'clicked: ' + t;
};
`;

async function main() {
  const args = process.argv.slice(2);
  const cdp = await connect();
  let i = 0;
  while (i < args.length) {
    const action = args[i++];
    if (action === "open") {
      await cdp.send("Page.navigate", { url: args[i++] });
      await new Promise((r) => setTimeout(r, 5000));
    } else if (action === "text") {
      console.log("=== TEXT ===");
      console.log((await cdp.eval("document.body.innerText")).slice(0, 4000));
      console.log("=== URL ===", await cdp.eval("location.href"));
    } else if (action === "click") {
      await cdp.eval(HELPERS); // re-inject: navigation wipes helpers
      const target = args[i++];
      console.log(await cdp.eval(`window.__clickByText(${JSON.stringify(target)}, true)`));
      await new Promise((r) => setTimeout(r, 1500));
    } else if (action === "clickStart") {
      await cdp.eval(HELPERS);
      const target = args[i++];
      console.log(await cdp.eval(`window.__clickByText(${JSON.stringify(target)}, false)`));
      await new Promise((r) => setTimeout(r, 1500));
    } else if (action === "fill") {
      await cdp.eval(HELPERS);
      const selector = args[i++];
      const value = args[i++] ?? "";
      console.log(await cdp.eval(`(() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return 'NOT_FOUND: ' + ${JSON.stringify(selector)};
        if (el.tagName === 'SELECT') { window.__setSelect(el, ${JSON.stringify(value)}); }
        else { window.__setVal(el, ${JSON.stringify(value)}); }
        return 'filled ' + ${JSON.stringify(selector)};
      })()`));
    } else if (action === "press") {
      await cdp.eval(HELPERS);
      const key = args[i++] ?? "Enter";
      await cdp.eval(`(() => {
        const el = document.activeElement || document.body;
        el.dispatchEvent(new KeyboardEvent('keydown', { key: ${JSON.stringify(key)}, bubbles: true }));
        el.dispatchEvent(new KeyboardEvent('keyup', { key: ${JSON.stringify(key)}, bubbles: true }));
        return 'pressed ' + ${JSON.stringify(key)};
      })()`);
    } else if (action === "wait") {
      await new Promise((r) => setTimeout(r, Number(args[i++] ?? 2000)));
    } else if (action === "eval") {
      console.log(JSON.stringify(await cdp.eval(args[i++]), null, 2)?.slice(0, 3000));
    } else {
      console.log("unknown action:", action);
      break;
    }
  }
  process.exit(0);
}

main().catch((e) => {
  console.error("CDP ERROR:", e.message);
  process.exit(1);
});
