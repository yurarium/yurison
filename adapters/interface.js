/* Load kari/app.js as it is served and call its own rendering functions.
 *
 * WHY THIS EXISTS. check.py used to hold hand transcriptions of the interface: a `fold`, a
 * `render` that reimplemented the name lookup, a `joins` guessing at app.js's fallback order, and
 * `publisherOf`/`imprintOf` copied out by eye. Each was a second implementation of a rule that
 * already exists in JavaScript, and STANDING-INSTRUCTIONS §3 says a second implementation drifts.
 * It did. `English mode has no Japanese` went green over a title a reader could see in Japanese,
 * because the transcription had invented two fallbacks app.js does not have.
 *
 * So nothing here reimplements anything. app.js is read from disk, evaluated verbatim, and asked.
 *
 * HOW app.js LOADS WITH NO BROWSER. It is written for one and has DOM at the top level, so the
 * seam is a vm context holding a stub `document`, `window` and `localStorage` rather than a change
 * to app.js. The stub answers the shapes app.js touches while it loads: getElementById never
 * returns null, because `el('sq').addEventListener(...)` at the bottom of the file would throw,
 * and querySelectorAll returns an empty list. `fetch` rejects, so the boot at the end of app.js
 * takes its own catch branch and nothing is rendered until this file asks for it.
 *
 * Nothing about the browser's LOGIC is stubbed. The functions under test are app.js's own.
 *
 * WHY vm AND NOT require(). Top-level `const`, `let` and `function` declarations in a script run
 * by vm.runInContext live in that context's global lexical scope and persist, so a later script in
 * the same context reads and assigns them. app.js therefore needs no module system, no export
 * list and no build step, and the file GitHub Pages serves is the file this evaluates. A build
 * step producing a second copy of the logic would be the fault this exists to remove.
 *
 * OFFLINE. ./test.py blocks sockets in every PYTHON child and cannot reach a node grandchild, so
 * the block is made again here: the vm context is given no `require`, and this file's own network
 * entries are removed before app.js is evaluated. Reading a file is not a fetch, and the two files
 * read are named on the command line.
 *
 * Usage: node interface.js <path-to-app.js>   with a JSON request on stdin.
 *   { "names": {...} | null,
 *     "names_path": "…/names.json",      instead of `names`, to save serialising 3.8 MB
 *     "prefs": { "LANG": "en", "FURIGANA": false, … },
 *     "calls": [ ["workLabel", {"work": "…"}], … ] }
 * and a JSON reply on stdout:
 *   { "ok": true, "results": [ {"html": "…", "text": "…"}, … ] }
 */
'use strict';

// Before anything else. This process reads two files and talks to its parent, and a fetch from
// here would pass ./test.py's guard unnoticed because that guard is installed in Python.
delete globalThis.fetch;
delete globalThis.WebSocket;
delete globalThis.XMLHttpRequest;

const fs = require('fs');
const vm = require('vm');

/* An element that answers rather than throwing. app.js reaches for values (`el('sq').value`),
   attributes, a dataset and a classList while it loads, and a stub that returns undefined for one
   of them fails the load for a reason that has nothing to do with what is being checked. */
function stubEl(id) {
  const e = {
    id, dataset: {}, style: {}, value: '', textContent: '', innerHTML: '', hidden: false,
    options: [], children: [], checked: false, disabled: false, tagName: 'DIV',
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {}, removeEventListener() {}, setAttribute() {},
    getAttribute() { return null; }, removeAttribute() {}, appendChild() {}, append() {},
    insertAdjacentHTML() {}, click() {}, focus() {}, blur() {}, remove() {},
    closest() { return null; }, querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0 }; },
    scrollIntoView() {},
  };
  return e;
}

function browser() {
  const els = new Map();
  const document = {
    documentElement: stubEl('html'),
    body: stubEl('body'),
    // NEVER NULL. app.js registers its listeners at the top level against elements by id, and a
    // null here would stop the file loading at line 3265 rather than at anything meaningful.
    getElementById(id) { if (!els.has(id)) els.set(id, stubEl(id)); return els.get(id); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {}, removeEventListener() {},
    createElement(tag) { return stubEl(tag); },
    createTextNode() { return { textContent: '' }; },
  };
  const ctx = {
    console,
    document,
    location: { search: '', pathname: '/kari/', href: 'https://example.invalid/kari/', hash: '' },
    history: { pushState() {}, replaceState() {}, state: null },
    // A reader's saved preferences are a browser's business. Every preference this harness cares
    // about is set explicitly below, so a store that always answers null is the honest default:
    // it is what a first visit looks like.
    localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    // The boot at the bottom of app.js is a Promise.all over five of these. Rejecting takes its
    // catch branch, which sets one element's text and stops, so nothing renders behind our back.
    fetch() { return Promise.reject(new Error('this harness is offline; data is handed in')); },
    URLSearchParams, URL, TextEncoder, TextDecoder,
    setTimeout, clearTimeout, setInterval, clearInterval,
    requestAnimationFrame() { return 0; },
    matchMedia() { return { matches: false, addEventListener() {}, addListener() {} }; },
    addEventListener() {}, removeEventListener() {},
    getComputedStyle() { return {}; },
    scrollTo() {},
  };
  ctx.window = ctx;
  ctx.globalThis = ctx;
  ctx.self = ctx;
  return vm.createContext(ctx);
}

/* What a reader would read. The lists build HTML, so a check asking whether a reader still meets
   Japanese has to look at the text inside it and not at the markup around it: a `title=` attribute
   on a tooltip is prose in its own right and is not the label. */
const TEXT = `(function (html) {
  const noTags = String(html).replace(/<[^>]*>/g, '');
  return noTags.replace(/&(amp|lt|gt|quot|#39|apos);/g,
    m => ({ '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&apos;': "'" }[m]));
})`;

function main() {
  const appPath = process.argv[2];
  if (!appPath) { process.stdout.write(JSON.stringify({ ok: false, error: 'no app.js given' })); return 1; }
  const req = JSON.parse(fs.readFileSync(0, 'utf8') || '{}');

  const ctx = browser();
  let src;
  try {
    src = fs.readFileSync(appPath, 'utf8');
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: `cannot read ${appPath}: ${e.message}` }));
    return 1;
  }
  try {
    vm.runInContext(src, ctx, { filename: appPath });
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false,
      error: `kari/app.js does not evaluate: ${e.message}`, stack: String(e.stack).split('\n').slice(0, 8) }));
    return 1;
  }

  // The name map, as the browser receives it. Read by path where one is given: it is 3.8 MB and
  // serialising it into this process's stdin on every call was most of the cost.
  let names = req.names || null;
  if (!names && req.names_path) names = JSON.parse(fs.readFileSync(req.names_path, 'utf8'));
  ctx.__in = { names, prefs: req.prefs || {}, calls: req.calls || [] };

  // The two globals the boot would have set, set the way the boot sets them. Everything else is a
  // preference, and each is assigned by name so a preference this harness forgets keeps app.js's
  // own default rather than becoming undefined.
  try {
    vm.runInContext(`
      NAMES = __in.names && __in.names.titles ? __in.names : null;
      PUBS  = (__in.names && __in.names.publishers) || null;
      for (const [k, v] of Object.entries(__in.prefs)) {
        // A NAME app.js DOES NOT HOLD IS REFUSED. Indirect eval assigning an unknown identifier
        // creates a global and reports nothing, so a caller asking for English by a name that has
        // been renamed would get a Japanese page and a passing check.
        if ((0, eval)('typeof ' + k) === 'undefined') throw new Error('no such preference in kari/app.js: ' + k);
        try { (0, eval)(k + ' = ' + JSON.stringify(v)); }
        catch (e) { throw new Error('kari/app.js will not take ' + k + ': ' + e.message); }
      }
    `, ctx);
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: `setting up: ${e.message}` }));
    return 1;
  }

  let results;
  try {
    results = vm.runInContext(`
      (() => {
        const text = ${TEXT};
        return __in.calls.map(([fn, arg]) => {
          const f = (0, eval)(fn);
          if (typeof f !== 'function') throw new Error('kari/app.js has no function ' + fn);
          const html = String(f(arg) ?? '');
          return { html, text: text(html) };
        });
      })()
    `, ctx);
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: `rendering: ${e.message}` }));
    return 1;
  }
  process.stdout.write(JSON.stringify({ ok: true, results }));
  return 0;
}

// `process.exitCode` and not `process.exit()`. Writing to a pipe is asynchronous, and exiting
// truncated the reply at 64 KB, which arrived as a JSON parse error rather than as anything
// resembling its cause.
process.exitCode = main();
