/**
 * PG Management System - Core Client JavaScript & Motion Design System
 * (Gate 2 / Gate 3 Frozen Core Architecture)
 */

document.addEventListener('DOMContentLoaded', () => {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // 1. Mobile Sidebar & Backdrop Toggle
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('open');
    if (backdrop) backdrop.classList.add('active');
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('active');
  }

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      if (sidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }

  // 2. Auto-dismiss Flash Alerts after 5 seconds with slide/fade-out
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // 3. Action Confirmation Modals / Prompts
  const confirmActions = document.querySelectorAll('[data-confirm]');
  confirmActions.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const message = btn.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // 4. Form Submissions - Micro-interaction spinner & double-submit prevention
  const forms = document.querySelectorAll('form:not([data-no-disable])');
  forms.forEach(form => {
    form.addEventListener('submit', () => {
      if (form.checkValidity && !form.checkValidity()) {
        return;
      }
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.disabled = true;
        submitBtn.dataset.originalHtml = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="btn-spinner"></span> Saving...';
      }
    });
  });

  // 5. Scroll-Based Motion Reveal (IntersectionObserver)
  const revealTargets = document.querySelectorAll(
    '.motion-reveal, .motion-reveal-left, .motion-reveal-right, .motion-scale, .motion-stagger'
  );

  if (revealTargets.length > 0) {
    if (prefersReduced || !('IntersectionObserver' in window)) {
      revealTargets.forEach(el => el.classList.add('is-visible'));
    } else {
      const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.12,
        rootMargin: '0px 0px -30px 0px'
      });

      revealTargets.forEach(el => observer.observe(el));
    }
  }

  // 6. Metric / Stat Count-Up Animation
  const statValues = document.querySelectorAll('.stat-value');
  if (statValues.length > 0 && !prefersReduced) {
    statValues.forEach(el => {
      const originalText = el.textContent.trim();
      // Match pattern like "₹ 15,250.00" or "₹15000.00" or "75.5%" or "42"
      // Skip non-numeric values like "Sunrise PG" or composite labels like "5 / 10"
      const match = originalText.match(/^([^\d.-]*)([\d,]+(?:\.\d+)?)([^\d]*)$/);
      if (!match) return;

      const prefix = match[1];
      const rawNumStr = match[2].replace(/,/g, '');
      const suffix = match[3];
      const targetVal = parseFloat(rawNumStr);

      if (isNaN(targetVal) || targetVal === 0) return;

      const hasDecimals = match[2].includes('.');
      const decimalPlaces = hasDecimals ? match[2].split('.')[1].length : 0;

      const duration = 850; // ms
      const startTime = performance.now();

      function updateCount(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Deceleration curve (cubic-bezier out)
        const ease = 1 - Math.pow(1 - progress, 3);
        const currentVal = targetVal * ease;

        let formattedVal;
        if (decimalPlaces > 0) {
          formattedVal = currentVal.toFixed(decimalPlaces);
        } else {
          formattedVal = Math.round(currentVal).toString();
        }

        if (match[2].includes(',')) {
          const parts = formattedVal.split('.');
          parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
          formattedVal = parts.join('.');
        }

        el.textContent = `${prefix}${formattedVal}${suffix}`;

        if (progress < 1) {
          requestAnimationFrame(updateCount);
        } else {
          el.textContent = originalText; // Guarantee exact precision on finish
        }
      }

      requestAnimationFrame(updateCount);
    });
  }
});

