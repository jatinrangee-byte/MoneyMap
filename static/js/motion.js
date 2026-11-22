/**
 * MoneyMap — Motion Engine (dotrwt.in inspired)
 * Features: Smooth-scroll Lenis, staggered reveal, preloader,
 *           magnetic buttons, parallax cursor, text scramble
 * Pure vanilla JS — zero build step, Flask/Jinja compatible
 */

/* ================================================================
   1. PRELOADER — SVG draw animation (dotrwt.in signature style)
   ================================================================ */
(function initPreloader() {
  // Only run on the landing/auth screen
  if (document.getElementById('app-sidebar')) return;

  const preloader = document.createElement('div');
  preloader.id = 'mm-preloader';
  preloader.innerHTML = `
    <div class="mm-preloader-inner">
      <svg class="mm-preloader-svg" viewBox="0 0 320 90" fill="none" xmlns="http://www.w3.org/2000/svg">
        <text
          class="mm-draw-text"
          x="50%"
          y="68"
          text-anchor="middle"
          font-family="Georgia, serif"
          font-size="64"
          font-style="italic"
          font-weight="700"
          fill="transparent"
          stroke="#faf8f1"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >MoneyMap.</text>
      </svg>
      <div class="mm-preloader-bar">
        <div class="mm-preloader-fill" id="mm-preloader-fill"></div>
      </div>
      <span class="mm-preloader-label" id="mm-preloader-label">0%</span>
    </div>
    <div class="mm-preloader-noise" aria-hidden="true"></div>
  `;
  document.body.prepend(preloader);

  // Measure path length and animate
  requestAnimationFrame(() => {
    const textEl = preloader.querySelector('.mm-draw-text');
    if (textEl) {
      // Approximate stroke-dasharray via getBBox
      try {
        const len = textEl.getTotalLength ? textEl.getTotalLength() : 800;
        textEl.style.strokeDasharray = len;
        textEl.style.strokeDashoffset = len;
        textEl.style.animation = `mm-draw-text 1.4s cubic-bezier(0.45,0,0.15,1) forwards, mm-fill-text 0.7s ease-in 1s forwards`;
      } catch(e) {
        textEl.style.strokeDasharray = 800;
        textEl.style.strokeDashoffset = 800;
        textEl.style.animation = `mm-draw-text 1.4s cubic-bezier(0.45,0,0.15,1) forwards, mm-fill-text 0.7s ease-in 1s forwards`;
      }
    }

    // Fake progress bar
    let progress = 0;
    const fill = document.getElementById('mm-preloader-fill');
    const label = document.getElementById('mm-preloader-label');
    const interval = setInterval(() => {
      progress = Math.min(100, progress + (Math.random() * 12 + 3));
      if (fill) fill.style.width = progress + '%';
      if (label) label.textContent = Math.floor(progress) + '%';
      if (progress >= 100) clearInterval(interval);
    }, 80);
  });

  // Dismiss after 2.2s
  window.addEventListener('load', () => {
    setTimeout(() => {
      preloader.classList.add('mm-preloader-exit');
      setTimeout(() => preloader.remove(), 700);
    }, 1800);
  });
  // Safety dismiss
  setTimeout(() => {
    if (preloader && preloader.parentNode) {
      preloader.classList.add('mm-preloader-exit');
      setTimeout(() => { if (preloader.parentNode) preloader.remove(); }, 700);
    }
  }, 3500);
})();


/* ================================================================
   2. SMOOTH SCROLL — Lenis CDN with eased momentum
   ================================================================ */
(function initSmoothScroll() {
  if (typeof Lenis === 'undefined') return;
  const lenis = new Lenis({
    duration: 1.25,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    direction: 'vertical',
    smooth: true,
    smoothTouch: false,
  });
  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  // Anchor click smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        lenis.scrollTo(target, { offset: -100, duration: 1.4 });
      }
    });
  });
  window._moneyMapLenis = lenis;
})();


/* ================================================================
   3. SCROLL-REVEAL — IntersectionObserver stagger cascade
   ================================================================ */
(function initScrollReveal() {
  const REVEAL_CLASS = 'mm-reveal';
  const VISIBLE_CLASS = 'mm-revealed';

  // Tag elements to animate
  const selectors = [
    '.builder-kicker',
    '.builder-title-line',
    '.builder-description',
    '.builder-actions',
    '.floating-glass-card',
    '.build-panel',
    '.feature-heading',
    '.route-step',
    '.simulator-section-head',
    '.wealth-sim-card',
    '.support-feature',
    '.pillars-grid > *',
    '.gist-quote',
    '.gist-points > *',
    '.section-desc-subtle',
    '.cta-block',
    '.footer-top',
    '.eyebrow',
    '.build-art-heading',
    '.vault-meter-display',
  ];

  selectors.forEach(sel => {
    document.querySelectorAll(sel).forEach((el, i) => {
      if (!el.classList.contains(REVEAL_CLASS)) {
        el.classList.add(REVEAL_CLASS);
        // Stagger within sibling groups
        const siblings = el.parentElement ? el.parentElement.querySelectorAll(`.${REVEAL_CLASS}`) : [];
        const index = Array.from(siblings).indexOf(el);
        el.style.setProperty('--mm-stagger', (index * 80) + 'ms');
      }
    });
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const delay = el.style.getPropertyValue('--mm-stagger') || '0ms';
        setTimeout(() => el.classList.add(VISIBLE_CLASS), parseInt(delay) || 0);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -48px 0px' });

  document.querySelectorAll(`.${REVEAL_CLASS}`).forEach(el => observer.observe(el));
})();


/* ================================================================
   4. MAGNETIC BUTTONS — hover repel/attract (dotrwt.in hero btns)
   ================================================================ */
(function initMagnetic() {
  const magneticSelectors = [
    '.builder-primary',
    '.builder-secondary',
    '.nyc-btn-register',
    '.nyc-theme-btn',
  ];

  function attachMagnetic(el) {
    const STRENGTH = 0.38;
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) * STRENGTH;
      const dy = (e.clientY - cy) * STRENGTH;
      el.style.transform = `translate(${dx}px, ${dy}px) scale(1.04)`;
      el.style.transition = 'transform 0.15s ease';
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = 'translate(0,0) scale(1)';
      el.style.transition = 'transform 0.45s cubic-bezier(0.33,1,0.68,1)';
    });
  }

  magneticSelectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => attachMagnetic(el));
  });
})();


/* ================================================================
   5. CUSTOM CURSOR — dot + ring trail (dotrwt.in style)
   ================================================================ */
(function initCursor() {
  // Don't run on touch devices
  if (window.matchMedia('(pointer: coarse)').matches) return;

  const dot = document.createElement('div');
  dot.id = 'mm-cursor-dot';
  const ring = document.createElement('div');
  ring.id = 'mm-cursor-ring';
  document.body.appendChild(dot);
  document.body.appendChild(ring);

  let mouseX = -100, mouseY = -100;
  let ringX = -100, ringY = -100;

  document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.transform = `translate(${mouseX}px, ${mouseY}px)`;
  });

  // Smooth ring follow
  function animateRing() {
    ringX += (mouseX - ringX) * 0.14;
    ringY += (mouseY - ringY) * 0.14;
    ring.style.transform = `translate(${ringX}px, ${ringY}px)`;
    requestAnimationFrame(animateRing);
  }
  animateRing();

  // Hover states
  const hoverEls = 'a, button, [role="button"], .build-panel, .floating-glass-card, input, textarea, select, label';
  document.addEventListener('mouseover', e => {
    if (e.target.closest(hoverEls)) {
      dot.classList.add('mm-cursor-hover');
      ring.classList.add('mm-cursor-hover');
    }
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest(hoverEls)) {
      dot.classList.remove('mm-cursor-hover');
      ring.classList.remove('mm-cursor-hover');
    }
  });

  // Click burst
  document.addEventListener('mousedown', () => {
    dot.classList.add('mm-cursor-click');
    ring.classList.add('mm-cursor-click');
  });
  document.addEventListener('mouseup', () => {
    dot.classList.remove('mm-cursor-click');
    ring.classList.remove('mm-cursor-click');
  });
})();


/* ================================================================
   6. TEXT SCRAMBLE — hero title letter scramble on page load
   ================================================================ */
(function initTextScramble() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$%#@!';

  function scramble(el) {
    const original = el.textContent;
    let frame = 0;
    const totalFrames = 18;
    const interval = setInterval(() => {
      el.textContent = original.split('').map((ch, i) => {
        if (ch === ' ') return ' ';
        if (frame / totalFrames > i / original.length) return ch;
        return chars[Math.floor(Math.random() * chars.length)];
      }).join('');
      if (frame++ >= totalFrames) {
        el.textContent = original;
        clearInterval(interval);
      }
    }, 40);
  }

  // Run on the kicker text after preloader
  setTimeout(() => {
    const kicker = document.querySelector('.builder-kicker span:last-child');
    if (kicker) scramble(kicker);

    // Scramble each title line with a stagger
    document.querySelectorAll('.builder-title-line').forEach((line, i) => {
      setTimeout(() => scramble(line), i * 220);
    });
  }, 2200);
})();


/* ================================================================
   7. PARALLAX — subtle Y-shift for hero and floating cards
   ================================================================ */
(function initParallax() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const hero = document.querySelector('.builder-hero');
  const cards = document.querySelectorAll('.floating-glass-card');

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;
    if (hero) {
      hero.style.transform = `translateY(${scrollY * 0.08}px)`;
    }
    cards.forEach((card, i) => {
      const dir = i % 2 === 0 ? 1 : -1;
      card.style.transform = `translateY(${scrollY * 0.04 * dir}px)`;
    });
  }, { passive: true });
})();


/* ================================================================
   8. BENTO PANEL TILT — subtle 3D card tilt on mouse move
   ================================================================ */
(function initCardTilt() {
  if (window.matchMedia('(pointer: coarse)').matches) return;

  document.querySelectorAll('.build-panel').forEach(panel => {
    panel.addEventListener('mousemove', e => {
      const rect = panel.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 10;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * -10;
      panel.style.transform = `perspective(600px) rotateX(${y}deg) rotateY(${x}deg) translateY(-4px)`;
      panel.style.transition = 'transform 0.1s ease';
    });
    panel.addEventListener('mouseleave', () => {
      panel.style.transform = 'perspective(600px) rotateX(0deg) rotateY(0deg) translateY(0px)';
      panel.style.transition = 'transform 0.5s cubic-bezier(0.33,1,0.68,1)';
    });
  });
})();


/* ================================================================
   9. HEADER SHRINK — compact nav on scroll (dotrwt.in behavior)
   ================================================================ */
(function initHeaderShrink() {
  const header = document.querySelector('.nyc-site-header');
  if (!header) return;

  let lastY = 0;
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    if (y > 80) {
      header.classList.add('mm-header-scrolled');
    } else {
      header.classList.remove('mm-header-scrolled');
    }
    // Hide on scroll down, show on scroll up
    if (y > lastY + 8 && y > 200) {
      header.classList.add('mm-header-hidden');
    } else if (y < lastY - 4) {
      header.classList.remove('mm-header-hidden');
    }
    lastY = y;
  }, { passive: true });
})();


/* ================================================================
   10. COUNTER ANIMATION — number roll-up for stats
   ================================================================ */
function mmAnimateCounter(el, target, duration = 1200, prefix = '', suffix = '') {
  let start = null;
  const startVal = 0;
  function step(timestamp) {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(startVal + eased * (target - startVal));
    el.textContent = prefix + current.toLocaleString('en-IN') + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// Trigger counters when visible
(function initCounters() {
  const counterEls = document.querySelectorAll('[data-count]');
  if (!counterEls.length) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const val = parseInt(el.dataset.count);
        const prefix = el.dataset.prefix || '';
        const suffix = el.dataset.suffix || '';
        mmAnimateCounter(el, val, 1400, prefix, suffix);
        obs.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  counterEls.forEach(el => obs.observe(el));
})();


/* ================================================================
   11. FLOATING CARDS HOVER DEPTH (enhanced)
   ================================================================ */
(function initFloatingCardDepth() {
  document.querySelectorAll('.floating-glass-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
      card.style.boxShadow = '0 24px 48px -8px rgba(23,63,50,0.22), 0 0 0 1.5px #173f32';
      card.style.transition = 'all 0.3s cubic-bezier(0.33,1,0.68,1)';
    });
    card.addEventListener('mouseleave', () => {
      card.style.boxShadow = '';
    });
  });
})();
