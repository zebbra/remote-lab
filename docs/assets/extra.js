/* Tab-aware TOC for pymdownx.tabbed (alternate_style: true).
 *
 * What this script does (and ONLY this — scope is intentionally small):
 *
 *   1. When a TOC entry points to a heading inside an inactive tab,
 *      clicking it activates the tab so the heading is visible. We
 *      restore the target's `id` synchronously in the capture phase
 *      so Material's bubble-phase scroll-into-view (and the browser's
 *      native anchor jump) find the live element with no race.
 *
 *   2. The flat TOC is restructured into synthetic per-tab parent
 *      entries: any consecutive run of TOC items whose targets live
 *      in the same tab gets grouped under a parent labelled with
 *      that tab's name. Clicking the parent activates the tab.
 *
 *   3. Synthetic group expansion (▾ active, ▸ inactive) tracks the
 *      currently active tab.
 *
 *   4. Material's scroll-spy is prevented from polluting the URL
 *      with fragments that point to inactive-tab headings via:
 *
 *        a. Stripping the `id` attribute of every element inside an
 *           inactive .tabbed-block (parked on `data-tab-id`); some
 *           Material codepaths walk live `[id]` and skip them.
 *
 *        b. A narrow filter on history.replaceState/pushState that
 *           drops calls whose fragment targets an element inside an
 *           inactive tab. Material caches `[id]` references at init
 *           time, so this is the necessary belt-and-braces.
 *
 * What this script intentionally does NOT do:
 *
 *   - No sticky positioning of the tab labels row. (CSS handles tab
 *     styling but the labels row scrolls naturally with content.)
 *   - No header-height tracking. Material's autohiding header is
 *     left alone.
 *   - No custom scrollIntoView. Material's instant-nav and the
 *     browser's native anchor jump handle scrolling. Activating the
 *     correct tab in the capture phase is enough — the live `id`
 *     restored there is what Material/browser scrolls to.
 *
 * Hooked into:
 *   - DOMContentLoaded                  (initial setup)
 *   - hashchange                        (URL fragment changes)
 *   - Material's document$ stream       (instant navigation)
 *   - radio change events               (tab switching)
 *   - capture-phase clicks              (TOC link interception)
 */
(function () {
  /* ──────────────────────────────────────────────────────────────
   *  Selectors
   * ────────────────────────────────────────────────────────────── */

  const SEL_TABBED_SET = ".tabbed-set";
  const SEL_TABBED_BLOCK = ".tabbed-block";
  const SEL_TABBED_LABELS = ".tabbed-labels";
  const SEL_SIDEBAR_SECONDARY = ".md-sidebar--secondary";
  const SEL_TOC_NAV = SEL_SIDEBAR_SECONDARY + " nav";

  const cssEscape =
    window.CSS && typeof CSS.escape === "function"
      ? CSS.escape.bind(CSS)
      : (s) => String(s).replace(/[^a-zA-Z0-9_-]/g, (c) => "\\" + c);

  /* ──────────────────────────────────────────────────────────────
   *  ID management for tabbed-blocks
   *
   *  When a tab is inactive, we move every descendant `id` onto
   *  `data-tab-id`. When the tab becomes active, we restore them.
   *  Idempotent on both sides.
   * ────────────────────────────────────────────────────────────── */

  function stripIdsInBlock(block) {
    for (const el of block.querySelectorAll("[id]")) {
      el.setAttribute("data-tab-id", el.id);
      el.removeAttribute("id");
    }
  }

  function restoreIdsInBlock(block) {
    for (const el of block.querySelectorAll("[data-tab-id]")) {
      const original = el.getAttribute("data-tab-id");
      if (original && !el.id) el.setAttribute("id", original);
      el.removeAttribute("data-tab-id");
    }
  }

  function syncIdsToActiveTab(tabbedSet) {
    const inputs = tabbedSet.querySelectorAll(
      ':scope > input[type="radio"]'
    );
    const blocks = tabbedSet.querySelectorAll(
      ":scope > .tabbed-content > " + SEL_TABBED_BLOCK
    );
    for (let i = 0; i < inputs.length; i++) {
      const block = blocks[i];
      if (!block) continue;
      if (inputs[i].checked) restoreIdsInBlock(block);
      else stripIdsInBlock(block);
    }
  }

  function syncAllTabbedSets() {
    for (const set of document.querySelectorAll(SEL_TABBED_SET)) {
      syncIdsToActiveTab(set);
    }
  }

  /* ──────────────────────────────────────────────────────────────
   *  Fragment → element lookup (id OR data-tab-id)
   * ────────────────────────────────────────────────────────────── */

  function findTargetByFragment(fragment) {
    if (!fragment || fragment === "#") return null;
    let id;
    try {
      id = decodeURIComponent(fragment.slice(1));
    } catch (e) {
      return null;
    }
    return (
      document.getElementById(id) ||
      document.querySelector('[data-tab-id="' + cssEscape(id) + '"]')
    );
  }

  /* ──────────────────────────────────────────────────────────────
   *  Tab activation
   *
   *  Clicking the label fires Material's indicator-animator (setting
   *  input.checked directly does NOT fire change). Synchronous in
   *  the capture phase: the target's id is live by the time
   *  Material/browser scroll in bubble phase.
   * ────────────────────────────────────────────────────────────── */

  function activateTab(tabbedSet, blockIndex) {
    const inputs = tabbedSet.querySelectorAll(
      ':scope > input[type="radio"]'
    );
    const labels = tabbedSet.querySelectorAll(
      ":scope > " + SEL_TABBED_LABELS + " > label"
    );
    const input = inputs[blockIndex];
    const label = labels[blockIndex];
    if (!input || input.checked) return;

    if (label) label.click();
    else input.checked = true;

    /* The radio change handler we install at the bottom of this
     * file runs syncIdsToActiveTab + syncTocVisibility. Defensively
     * call them here too in case the change event does not fire
     * (e.g., element detached at the time of the click). */
    syncIdsToActiveTab(tabbedSet);
    syncTocVisibility();
  }

  function activateTabForFragment(fragment) {
    if (!fragment || fragment === "#") return;
    const target = findTargetByFragment(fragment);
    if (!target) return;
    const block = target.closest(SEL_TABBED_BLOCK);
    if (!block) return;
    const tabbedSet = block.closest(SEL_TABBED_SET);
    if (!tabbedSet) return;
    const blocks = Array.from(
      tabbedSet.querySelectorAll(
        ":scope > .tabbed-content > " + SEL_TABBED_BLOCK
      )
    );
    const blockIndex = blocks.indexOf(block);
    if (blockIndex < 0) return;
    activateTab(tabbedSet, blockIndex);
  }

  function activateTabForHash() {
    activateTabForFragment(window.location.hash);
  }

  /* ──────────────────────────────────────────────────────────────
   *  TOC restructure — group entries by their parent tab
   * ────────────────────────────────────────────────────────────── */

  function tabInfoForFragment(fragment) {
    if (!fragment) return null;
    const target = findTargetByFragment(fragment);
    if (!target) return null;
    const block = target.closest(SEL_TABBED_BLOCK);
    if (!block) return null;
    const tabbedSet = block.closest(SEL_TABBED_SET);
    if (!tabbedSet) return null;
    const blocks = Array.from(
      tabbedSet.querySelectorAll(
        ":scope > .tabbed-content > " + SEL_TABBED_BLOCK
      )
    );
    const blockIndex = blocks.indexOf(block);
    if (blockIndex < 0) return null;
    const labels = tabbedSet.querySelectorAll(
      ":scope > " + SEL_TABBED_LABELS + " > label"
    );
    const labelText = labels[blockIndex]?.textContent.trim();
    if (!labelText) return null;
    return {
      tabbedSet,
      blockIndex,
      labelText,
      key:
        (tabbedSet.dataset.tabs || tabbedSet.id || "set") + ":" + blockIndex,
    };
  }

  function buildSyntheticParent(tabInfo) {
    const li = document.createElement("li");
    li.className = "md-nav__item md-nav__item--tab";
    li.dataset.tabSet = tabInfo.tabbedSet.dataset.tabs || "";
    li.dataset.tabIndex = String(tabInfo.blockIndex);

    const a = document.createElement("a");
    a.className = "md-nav__link md-nav__link--tab";
    a.href = "#";
    a.textContent = tabInfo.labelText;
    a.title = 'Open the "' + tabInfo.labelText + '" tab';

    a.addEventListener("click", (e) => {
      /* The href="#" + preventDefault + stopPropagation combo
       * deliberately keeps Material entirely out of this click:
       *
       *   - href="#" means there's no real fragment for Material's
       *     instant-nav to treat as a navigation.
       *   - preventDefault stops the browser's default "#" jump
       *     (which would put a stray "#" in the URL).
       *   - stopPropagation stops Material's bubble-phase click
       *     handler from running.
       *
       * With Material bypassed, NO ONE else is going to call
       * scrollTo on this click. Our requestAnimationFrame scroll
       * then runs unopposed — no race, no retry loop, robust in
       * every browser. This is exactly the "easy, race-free path"
       * for synthetic group clicks because we own the click in
       * full. (TOC sub-entries with real hash fragments still flow
       * through Material untouched by our generic handler.) */
      e.preventDefault();
      e.stopPropagation();
      activateTab(tabInfo.tabbedSet, tabInfo.blockIndex);
      requestAnimationFrame(() => {
        tabInfo.tabbedSet.scrollIntoView({ block: "start" });
      });
    });

    li.appendChild(a);

    const nestedNav = document.createElement("nav");
    nestedNav.className = "md-nav md-nav--secondary";
    nestedNav.setAttribute("aria-label", tabInfo.labelText);
    const nestedUl = document.createElement("ul");
    nestedUl.className = "md-nav__list";
    nestedNav.appendChild(nestedUl);
    li.appendChild(nestedNav);

    return { li, nestedUl };
  }

  function syncTocVisibility() {
    const groups = document.querySelectorAll(".md-nav__item--tab");
    for (const group of groups) {
      const setId = group.dataset.tabSet;
      const idx = parseInt(group.dataset.tabIndex, 10);
      if (Number.isNaN(idx)) continue;
      const tabbedSet = setId
        ? document.querySelector(
            SEL_TABBED_SET + '[data-tabs="' + cssEscape(setId) + '"]'
          )
        : null;
      if (!tabbedSet) continue;
      const inputs = tabbedSet.querySelectorAll(
        ':scope > input[type="radio"]'
      );
      const isActive = inputs[idx]?.checked === true;
      group.classList.toggle("md-nav__item--tab-active", isActive);
      group.classList.toggle("md-nav__item--tab-inactive", !isActive);
    }
  }

  function restructureTocList(navList) {
    const items = Array.from(navList.children).filter(
      (el) =>
        el.tagName === "LI" && !el.classList.contains("md-nav__item--tab")
    );
    if (items.length === 0) return 0;

    const infos = items.map((item) => {
      const link = item.querySelector(":scope > a.md-nav__link");
      /* link.hash returns just the fragment regardless of whether
       * the href is relative ("#foo") or absolute (Material rewrites
       * TOC hrefs to absolute form during instant nav). */
      const fragment = link?.hash;
      return tabInfoForFragment(fragment);
    });

    let group = null;
    const commits = [];
    for (let i = 0; i < items.length; i++) {
      const info = infos[i];
      if (!info) {
        if (group) commits.push(group);
        group = null;
        continue;
      }
      if (!group || group.key !== info.key) {
        if (group) commits.push(group);
        group = { ...info, items: [items[i]] };
      } else {
        group.items.push(items[i]);
      }
    }
    if (group) commits.push(group);

    for (const g of commits) {
      const first = g.items[0];
      const parent = first.parentNode;
      const { li, nestedUl } = buildSyntheticParent(g);
      parent.insertBefore(li, first);
      for (const item of g.items) nestedUl.appendChild(item);
    }
    return commits.length;
  }

  function restructureToc() {
    const tocRoot = document.querySelector(SEL_TOC_NAV);
    if (!tocRoot) return;
    if (tocRoot.dataset.tabRestructured === "done") return;
    const lists = tocRoot.querySelectorAll(".md-nav__list");
    for (const list of lists) restructureTocList(list);
    tocRoot.dataset.tabRestructured = "done";
    syncTocVisibility();
  }

  /* ──────────────────────────────────────────────────────────────
   *  URL pollution guard
   *
   *  Material's scroll-spy writes URL fragments that can point to
   *  inactive-tab headings (Material caches an `[id]` map at init
   *  time so DOM-level id stripping isn't enough on its own). We
   *  filter history.replaceState/pushState to drop calls whose
   *  fragment targets an inactive-tab element.
   *
   *  Pure DOM check at write time. No timing, no race. Idempotent
   *  install. Fails-open: if our predicate throws or finds nothing,
   *  the original call goes through.
   * ────────────────────────────────────────────────────────────── */

  function fragmentTargetsInactiveTab(url) {
    if (!url) return false;
    let parsed;
    try {
      parsed = new URL(url, document.baseURI);
    } catch (e) {
      return false;
    }
    if (!parsed.hash || parsed.hash === "#") return false;
    const target = findTargetByFragment(parsed.hash);
    if (!target) return false;
    const block = target.closest(SEL_TABBED_BLOCK);
    if (!block) return false;
    const tabbedSet = block.closest(SEL_TABBED_SET);
    if (!tabbedSet) return false;
    const blocks = Array.from(
      tabbedSet.querySelectorAll(
        ":scope > .tabbed-content > " + SEL_TABBED_BLOCK
      )
    );
    const blockIndex = blocks.indexOf(block);
    if (blockIndex < 0) return false;
    const inputs = tabbedSet.querySelectorAll(
      ':scope > input[type="radio"]'
    );
    return inputs[blockIndex] && !inputs[blockIndex].checked;
  }

  function installUrlGuard() {
    if (history.__neopsTabsGuard) return;
    history.__neopsTabsGuard = true;

    const wrap = (origName) => {
      const orig = history[origName].bind(history);
      history[origName] = function (state, title, url) {
        try {
          if (fragmentTargetsInactiveTab(url)) return;
        } catch (e) {
          /* Never break navigation because of us. */
        }
        return orig(state, title, url);
      };
    };

    wrap("replaceState");
    wrap("pushState");
  }

  /* ──────────────────────────────────────────────────────────────
   *  Sidebar rebuild observer — Material replaces the secondary
   *  sidebar on instant navigation. Our `done` flag lives on the
   *  tocRoot element, so a fresh <nav> from Material has no flag
   *  and our restructure re-applies.
   * ────────────────────────────────────────────────────────────── */

  function watchSidebarForRebuilds() {
    const sidebar = document.querySelector(SEL_SIDEBAR_SECONDARY);
    if (!sidebar) return;
    new MutationObserver(restructureToc).observe(sidebar, {
      childList: true,
      subtree: true,
    });
  }

  /* ──────────────────────────────────────────────────────────────
   *  Lifecycle wiring
   * ────────────────────────────────────────────────────────────── */

  function run() {
    syncAllTabbedSets();
    restructureToc();
    activateTabForHash();
  }

  function init() {
    /* Install the URL guard FIRST so it covers any subsequent
     * replaceState/pushState (ours and Material's). Idempotent. */
    installUrlGuard();
    run();
    watchSidebarForRebuilds();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.addEventListener("hashchange", activateTabForHash);

  /* Capture-phase click handler: when a TOC link points into an
   * inactive tab, activate the tab synchronously so the target's
   * `id` is live when Material's bubble-phase handler (and the
   * browser's native anchor jump) try to scroll to it. We do NOT
   * preventDefault, do NOT stopPropagation — the natural click
   * lifecycle handles URL update and scrolling. */
  document.addEventListener(
    "click",
    (e) => {
      if (e.defaultPrevented) return;
      if (e.button !== 0) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target.closest && e.target.closest("a");
      if (!a || !a.hash || a.hash === "#") return;
      if (a.pathname !== window.location.pathname) return;
      if (a.target && a.target !== "" && a.target !== "_self") return;
      activateTabForFragment(a.hash);
    },
    true
  );

  /* When the user clicks a tab label (or the tab radio changes for
   * any other reason), re-sync ID stripping and TOC visibility. */
  document.addEventListener(
    "change",
    (e) => {
      const target = e.target;
      if (
        target instanceof HTMLInputElement &&
        target.type === "radio" &&
        target.parentElement?.classList.contains("tabbed-set")
      ) {
        const tabbedSet = target.parentElement;
        syncIdsToActiveTab(tabbedSet);
        syncTocVisibility();
      }
    },
    true
  );

  /* Material's document$ Subject fires once on subscribe AND on
   * every instant navigation. Re-running run() is idempotent —
   * each step early-returns when its work is already done. */
  if (
    typeof document$ !== "undefined" &&
    typeof document$.subscribe === "function"
  ) {
    document$.subscribe(run);
  }
})();
