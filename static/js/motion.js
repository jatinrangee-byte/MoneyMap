/**
 * MoneyMap — Full Scroll-Driven Motion Engine
 * Everything moves AS YOU SCROLL — parallax, translate, rotate, scale,
 * clip-path reveals, horizontal slides, counter rolls, 3D tilts.
 * Pure vanilla JS · zero build step · Flask/Jinja compatible
 */

/* ================================================================
   UTILS
   ================================================================ */
function clamp(val, min, max) { return Math.min(Math.max(val, min), max); }
function lerp(a, b, t) { return a + (b - a) * t; }
// Map a value from [inMin,inMax] → [outMin,outMax]
function mapRange(val, inMin, inMax, outMin, outMax) {
  return outMin + ((clamp(val, inMin, inMax) - inMin) / (inMax - inMin)) * (outMax - outMin);
}
// Get element's progress through viewport (0 = just entered bottom, 1 = leaving top)
function getScrollProgress(el, start = 0.0, end = 1.0) {
  const rect = el.getBoundingClientRect();
  const vh = window.innerHeight;
  const raw = (vh - rect.top) / (vh + rect.height);
  return clamp(mapRange(raw, start, end, 0, 1), 0, 1);
}

const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const TOUCH = window.matchMedia('(pointer: coarse)').matches;

/* ================================================================
   1. PRELOADER — SVG draw + fill
   ================================================================ */
(function initPreloader() {
  if (document.getElementById('app-sidebar')) return;

  const el = document.createElement('div');
  el.id = 'mm-preloader';
  el.innerHTML = `
    <div class="mm-preloader-inner">
      <svg class="mm-preloader-svg" viewBox="0 0 400 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <text class="mm-draw-text" x="50%" y="72" text-anchor="middle"
          font-family="Georgia,serif" font-size="68" font-style="italic" font-weight="700"
          fill="transparent" stroke="#faf8f1" stroke-width="1.5"
          stroke-linecap="round" stroke-linejoin="round">MoneyMap.</text>
      </svg>
      <div class="mm-preloader-bar"><div class="mm-preloader-fill" id="mm-pf"></div></div>
      <span class="mm-preloader-label" id="mm-pl">0%</span>
    </div>
    <div class="mm-preloader-noise" aria-hidden="true"></div>`;
  document.body.prepend(el);

  const txt = el.querySelector('.mm-draw-text');
  if (txt) {
    const len = 820;
    txt.style.cssText = `stroke-dasharray:${len};stroke-dashoffset:${len};
      animation:mm-draw-text 1.5s cubic-bezier(0.45,0,0.15,1) forwards,
                 mm-fill-text 0.7s ease-in 1.1s forwards`;
  }
  let p = 0;
  const pf = document.getElementById('mm-pf');
  const pl = document.getElementById('mm-pl');
  const iv = setInterval(() => {
    p = Math.min(100, p + Math.random() * 11 + 4);
    if (pf) pf.style.width = p + '%';
    if (pl) pl.textContent = Math.floor(p) + '%';
    if (p >= 100) clearInterval(iv);
  }, 75);

  const dismiss = () => {
    el.classList.add('mm-preloader-exit');
    setTimeout(() => el.remove(), 650);
    document.body.classList.remove('mm-loading');
    document.body.classList.add('mm-loaded');
  };
  window.addEventListener('load', () => setTimeout(dismiss, 1900));
  setTimeout(() => { if (el.parentNode) dismiss(); }, 3800);
})();


/* ================================================================
   2. SMOOTH SCROLL (Lenis)
   ================================================================ */
(function initLenis() {
  if (typeof Lenis === 'undefined') return;
  const lenis = new Lenis({
    duration: 1.3,
    easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smooth: true,
    smoothTouch: false,
  });
  (function raf(t) { lenis.raf(t); requestAnimationFrame(raf); })(0);
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const tgt = document.querySelector(a.getAttribute('href'));
      if (tgt) { e.preventDefault(); lenis.scrollTo(tgt, { offset: -100, duration: 1.5 }); }
    });
  });
  window._lenis = lenis;
})();


/* ================================================================
   3. SCROLL-DRIVEN PARALLAX ENGINE
      Runs every rAF frame — calculates scroll offsets and
      directly applies CSS transforms to every registered element.
   ================================================================ */
(function initScrollParallax() {
  if (REDUCED) return;

  /* ---- Register elements with [data-parallax] attrs ---- */
  // We'll set attrs from JS so we don't modify HTML
  const registry = [];

  function reg(selector, opts) {
    document.querySelectorAll(selector).forEach((el, i) => {
      registry.push({ el, i, ...opts });
    });
  }

  // Hero canvas drifts up slowly as you scroll away
  reg('.builder-hero', { type: 'yUp', speed: 0.22, start: 0, end: 0.6 });

  // Blobs drift in opposite directions
  reg('.blob-emerald', { type: 'yUp', speed: -0.18 });
  reg('.blob-gold',    { type: 'yDown', speed: 0.14 });
  reg('.blob-teal',    { type: 'xRight', speed: 0.1 });
  reg('.blob-forest',  { type: 'xLeft',  speed: 0.12 });

  // Floating glass cards fan apart as hero scrolls
  reg('.floating-glass-card', { type: 'fanCards', speed: 0.09 });

  // Kicker badge pops up slightly
  reg('.builder-kicker', { type: 'yUp', speed: 0.06 });

  // Title lines each move at slightly different rates
  reg('.builder-title-line', { type: 'titleLines', speed: 0.07 });

  // Bento panels slide in from alternating sides
  reg('.build-panel', { type: 'panelSlide', speed: 1 });

  // Feature headings zoom in gently
  reg('.feature-heading', { type: 'zoomIn', speed: 0.5 });

  // Section h2 elements drift up
  reg('.unimap-map-section h2', { type: 'yUp', speed: 0.08 });
  reg('.wealth-simulator-section h2', { type: 'yUp', speed: 0.08 });
  reg('.support-section h2', { type: 'yUp', speed: 0.08 });

  // Route steps slide from left
  reg('.route-step', { type: 'slideFromLeft', speed: 1 });

  // Simulator cards rotate in
  reg('.wealth-sim-card, .sim-output-card', { type: 'rotateIn', speed: 1 });

  // Support features rise with stagger
  reg('.support-feature, .pillars-grid > *', { type: 'staggerRise', speed: 1 });

  // The pixel divider stretches on scroll
  reg('.pixel-divider', { type: 'scaleX', speed: 0.5 });

  // Eyebrow labels slide from left
  reg('.eyebrow', { type: 'slideFromLeft', speed: 0.8 });

  // Showcase badge pulses scale
  reg('.showcase-status-badge', { type: 'scalePulse', speed: 1 });

  /* ---- RAF loop ---- */
  let currentScrollY = 0;
  let targetScrollY = 0;

  window.addEventListener('scroll', () => { targetScrollY = window.scrollY; }, { passive: true });

  function tick() {
    // Smooth scroll tracking
    currentScrollY = lerp(currentScrollY, targetScrollY, 0.1);
    const sy = currentScrollY;

    registry.forEach(({ el, i, type, speed }) => {
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const progress = getScrollProgress(el);

      // Skip if not near viewport
      if (rect.bottom < -vh || rect.top > vh * 2.5) return;

      switch (type) {

        case 'yUp': {
          const y = -(progress * vh * speed * 0.5);
          el.style.transform = `translateY(${y}px)`;
          break;
        }

        case 'yDown': {
          const y = progress * vh * speed * 0.5;
          el.style.transform = `translateY(${y}px)`;
          break;
        }

        case 'xRight': {
          const x = progress * vh * speed * 0.6;
          el.style.transform = `translateX(${x}px)`;
          break;
        }

        case 'xLeft': {
          const x = -(progress * vh * speed * 0.6);
          el.style.transform = `translateX(${x}px)`;
          break;
        }

        case 'fanCards': {
          // Cards fan out horizontally + rotate slightly as hero exits
          const heroProgress = clamp(sy / (vh * 0.8), 0, 1);
          const offset = (i - 1) * heroProgress * 32;
          const rot = (i - 1) * heroProgress * 3;
          const scale = 1 - heroProgress * 0.04;
          el.style.transform = `translateX(${offset}px) rotate(${rot}deg) scale(${scale})`;
          break;
        }

        case 'titleLines': {
          // Each line moves at increasing offset
          const p = getScrollProgress(el, 0, 0.7);
          const y = -(p * 60 * speed * (i + 1));
          el.style.transform = `translateY(${y}px)`;
          break;
        }

        case 'panelSlide': {
          // Panels slide from left for even index, right for odd
          const p = getScrollProgress(el, 0.05, 0.6);
          const eased = 1 - Math.pow(1 - p, 3);
          const fromX = i % 2 === 0 ? -60 : 60;
          const x = fromX * (1 - eased);
          const opacity = eased;
          el.style.transform = `translateX(${x}px)`;
          el.style.opacity = opacity;
          break;
        }

        case 'zoomIn': {
          const p = getScrollProgress(el, 0.1, 0.65);
          const eased = 1 - Math.pow(1 - p, 2);
          const scale = 0.88 + eased * 0.12;
          const opacity = 0.2 + eased * 0.8;
          el.style.transform = `scale(${scale})`;
          el.style.opacity = opacity;
          break;
        }

        case 'slideFromLeft': {
          const p = getScrollProgress(el, 0.1, 0.65);
          const eased = 1 - Math.pow(1 - p, 3);
          const x = -80 * (1 - eased) * (1 + i * 0.3);
          el.style.transform = `translateX(${x}px)`;
          el.style.opacity = eased;
          break;
        }

        case 'rotateIn': {
          const p = getScrollProgress(el, 0.1, 0.7);
          const eased = 1 - Math.pow(1 - p, 3);
          const rot = (1 - eased) * (i % 2 === 0 ? -6 : 6);
          const y = (1 - eased) * 50;
          const opacity = 0.1 + eased * 0.9;
          el.style.transform = `translateY(${y}px) rotate(${rot}deg)`;
          el.style.opacity = opacity;
          break;
        }

        case 'staggerRise': {
          const delay = i * 0.08;
          const p = clamp(getScrollProgress(el, 0.1 + delay, 0.7 + delay), 0, 1);
          const eased = 1 - Math.pow(1 - p, 3);
          const y = (1 - eased) * 70;
          const opacity = eased;
          el.style.transform = `translateY(${y}px)`;
          el.style.opacity = opacity;
          break;
        }

        case 'scaleX': {
          const p = getScrollProgress(el, 0, 1);
          el.style.transform = `scaleX(${p})`;
          el.style.transformOrigin = 'left center';
          break;
        }

        case 'scalePulse': {
          const p = getScrollProgress(el, 0.3, 0.7);
          const scale = 0.95 + Math.sin(p * Math.PI) * 0.08;
          el.style.transform = `scale(${scale})`;
          break;
        }
      }
    });

    requestAnimationFrame(tick);
  }

  tick();
})();


/* ================================================================
   4. AMBIENT BLOB PARALLAX — blobs drift with mouse + scroll
   ================================================================ */
(function initBlobParallax() {
  if (REDUCED) return;
  let mouseX = 0, mouseY = 0;
  document.addEventListener('mousemove', e => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  const blobs = [
    { el: document.querySelector('.blob-emerald'), mx: 30, my: 20 },
    { el: document.querySelector('.blob-gold'),    mx: -24, my: 32 },
    { el: document.querySelector('.blob-teal'),    mx: 20, my: -18 },
    { el: document.querySelector('.blob-forest'),  mx: -28, my: -24 },
  ];

  let bx = [0,0,0,0], by = [0,0,0,0];
  function animBlobs() {
    blobs.forEach(({ el, mx, my }, i) => {
      if (!el) return;
      const tx = mouseX * mx;
      const ty = mouseY * my;
      bx[i] = lerp(bx[i], tx, 0.05);
      by[i] = lerp(by[i], ty, 0.05);
      el.style.transform = `translate(${bx[i]}px, ${by[i]}px)`;
    });
    requestAnimationFrame(animBlobs);
  }
  animBlobs();
})();


/* ================================================================
   5. MAGNETIC BUTTONS
   ================================================================ */
(function initMagnetic() {
  if (TOUCH) return;
  ['.builder-primary','.builder-secondary','.nyc-btn-register','.nyc-theme-btn'].forEach(sel => {
    document.querySelectorAll(sel).forEach(el => {
      let tx = 0, ty = 0;
      el.addEventListener('mousemove', e => {
        const r = el.getBoundingClientRect();
        tx = (e.clientX - r.left - r.width / 2) * 0.4;
        ty = (e.clientY - r.top - r.height / 2) * 0.4;
        el.style.transform = `translate(${tx}px,${ty}px) scale(1.05)`;
        el.style.transition = 'transform 0.12s ease';
      });
      el.addEventListener('mouseleave', () => {
        el.style.transform = 'translate(0,0) scale(1)';
        el.style.transition = 'transform 0.5s cubic-bezier(0.33,1,0.68,1)';
      });
    });
  });
})();


/* ================================================================
   6. CUSTOM CURSOR — green dot + lagging ring
   ================================================================ */
(function initCursor() {
  if (TOUCH) return;
  const dot = document.createElement('div'); dot.id = 'mm-cursor-dot';
  const ring = document.createElement('div'); ring.id = 'mm-cursor-ring';
  document.body.append(dot, ring);

  let mx = -200, my = -200, rx = -200, ry = -200;
  document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    dot.style.transform = `translate(${mx}px,${my}px)`;
  }, { passive: true });

  (function loop() {
    rx = lerp(rx, mx, 0.13); ry = lerp(ry, my, 0.13);
    ring.style.transform = `translate(${rx}px,${ry}px)`;
    requestAnimationFrame(loop);
  })();

  const hoverable = 'a,button,[role="button"],.build-panel,.floating-glass-card,input,select,textarea,label';
  document.addEventListener('mouseover', e => {
    if (e.target.closest(hoverable)) { dot.classList.add('mm-cursor-hover'); ring.classList.add('mm-cursor-hover'); }
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest(hoverable)) { dot.classList.remove('mm-cursor-hover'); ring.classList.remove('mm-cursor-hover'); }
  });
  document.addEventListener('mousedown', () => { dot.classList.add('mm-cursor-click'); ring.classList.add('mm-cursor-click'); });
  document.addEventListener('mouseup', () => { dot.classList.remove('mm-cursor-click'); ring.classList.remove('mm-cursor-click'); });
})();


/* ================================================================
   7. BENTO CARD 3D TILT
   ================================================================ */
(function initCardTilt() {
  if (TOUCH) return;
  document.querySelectorAll('.build-panel').forEach(el => {
    el.addEventListener('mousemove', e => {
      const r = el.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width - 0.5) * 14;
      const y = -((e.clientY - r.top) / r.height - 0.5) * 14;
      el.style.transform = `perspective(700px) rotateX(${y}deg) rotateY(${x}deg) translateY(-6px) scale(1.02)`;
      el.style.transition = 'transform 0.08s ease';
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
      el.style.transition = 'transform 0.6s cubic-bezier(0.33,1,0.68,1)';
    });
  });
})();


/* ================================================================
   8. FLOATING CARD TILT
   ================================================================ */
(function initFloatingTilt() {
  if (TOUCH) return;
  document.querySelectorAll('.floating-glass-card').forEach(el => {
    el.addEventListener('mousemove', e => {
      const r = el.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width - 0.5) * 10;
      const y = -((e.clientY - r.top) / r.height - 0.5) * 10;
      el.style.transform = `perspective(500px) rotateX(${y}deg) rotateY(${x}deg) scale(1.04)`;
      el.style.transition = 'transform 0.1s ease';
      el.style.boxShadow = '0 20px 48px -8px rgba(23,63,50,0.25), 0 0 0 1.5px #173f32';
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
      el.style.transition = 'transform 0.5s cubic-bezier(0.33,1,0.68,1)';
      el.style.boxShadow = '';
    });
  });
})();


/* ================================================================
   9. TEXT SCRAMBLE — hero title on load
   ================================================================ */
(function initScramble() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$%#@!';
  function scramble(el) {
    const original = el.textContent;
    let frame = 0, total = 20;
    const iv = setInterval(() => {
      el.textContent = original.split('').map((ch, i) => {
        if (ch === ' ') return ' ';
        return frame / total > i / original.length ? ch : chars[Math.floor(Math.random() * chars.length)];
      }).join('');
      if (++frame > total) { el.textContent = original; clearInterval(iv); }
    }, 38);
  }
  setTimeout(() => {
    const kicker = document.querySelector('.builder-kicker span:last-child');
    if (kicker) scramble(kicker);
    document.querySelectorAll('.builder-title-line').forEach((l, i) => setTimeout(() => scramble(l), i * 240));
  }, 2200);
})();


/* ================================================================
   10. HEADER SHRINK / HIDE ON SCROLL
   ================================================================ */
(function initHeader() {
  const h = document.querySelector('.nyc-site-header');
  if (!h) return;
  let lastY = 0;
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    h.classList.toggle('mm-header-scrolled', y > 80);
    if (y > lastY + 10 && y > 220) h.classList.add('mm-header-hidden');
    else if (y < lastY - 6) h.classList.remove('mm-header-hidden');
    lastY = y;
  }, { passive: true });
})();


/* ================================================================
   11. SCROLL PROGRESS BAR
   ================================================================ */
(function initProgressBar() {
  const bar = document.createElement('div');
  bar.id = 'mm-scroll-bar';
  document.body.appendChild(bar);
  window.addEventListener('scroll', () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (window.scrollY / max * 100) + '%';
  }, { passive: true });
})();


/* ================================================================
   12. COUNTER ROLL-UP on scroll-enter
   ================================================================ */
(function initCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const obs = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      let start; obs.unobserve(el);
      (function step(ts) {
        if (!start) start = ts;
        const p = Math.min((ts - start) / 1400, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = prefix + Math.floor(eased * target).toLocaleString('en-IN') + suffix;
        if (p < 1) requestAnimationFrame(step);
      })(performance.now());
    }, { threshold: 0.5 });
    obs.observe(el);
  });
})();


/* ================================================================
   13. HORIZONTAL SCROLL TICKER — marquee of stats
   ================================================================ */
(function initTicker() {
  const ticker = document.querySelector('.mm-ticker-track');
  if (!ticker) return;
  let pos = 0;
  const speed = 0.6;
  (function loop() {
    pos -= speed;
    if (pos < -ticker.scrollWidth / 2) pos = 0;
    ticker.style.transform = `translateX(${pos}px)`;
    requestAnimationFrame(loop);
  })();
})();


/* ================================================================
   14. CLIP-PATH REVEAL for section headings (wipe left→right)
   ================================================================ */
(function initClipReveal() {
  document.querySelectorAll('section h2').forEach(el => {
    el.style.clipPath = 'inset(0 100% 0 0)';
    el.style.transition = 'clip-path 0.9s cubic-bezier(0.33,1,0.68,1)';
    const obs = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      el.style.clipPath = 'inset(0 0% 0 0)';
      obs.unobserve(el);
    }, { threshold: 0.2 });
    obs.observe(el);
  });
})();


/* ================================================================
   15. SCROLL-LINKED NAV ACTIVE STATE
   ================================================================ */
(function initNavActive() {
  const sections = ['showcase','capital-map','simulator','pillars'].map(id => document.getElementById(id));
  const links = document.querySelectorAll('.nyc-nav-link');
  window.addEventListener('scroll', () => {
    const y = window.scrollY + 120;
    sections.forEach((sec, i) => {
      if (!sec || !links[i]) return;
      const inView = y >= sec.offsetTop && y < sec.offsetTop + sec.offsetHeight;
      links[i].classList.toggle('nyc-nav-link--active', inView);
    });
  }, { passive: true });
})();
