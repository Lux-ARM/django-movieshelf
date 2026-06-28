/**
 * MovieShelf — Main Vanilla JS
 * Midnight Violet Cinema Premium Interactions
 */

(function () {
    'use strict';

    // ===== Mobile Navigation Toggle =====
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function () {
            this.classList.toggle('active');
            navLinks.classList.toggle('open');
        });

        // Close menu on link click
        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                navToggle.classList.remove('active');
                navLinks.classList.remove('open');
            });
        });

        // Close menu on outside click
        document.addEventListener('click', function (e) {
            if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
                navToggle.classList.remove('active');
                navLinks.classList.remove('open');
            }
        });
    }


    // ===== Scroll Reveal (IntersectionObserver) =====
    const revealElements = document.querySelectorAll(
        '.movie-card, .genre-card, .stat-card, .comment, .recommendations-section, .section'
    );

    if (revealElements.length && 'IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -40px 0px'
        });

        revealElements.forEach(function (el) {
            el.classList.add('reveal');
            revealObserver.observe(el);
        });
    }


    // ===== Button Ripple Effect =====
    document.querySelectorAll('.btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            // Don't ripple for outline buttons or links
            if (this.classList.contains('btn-outline') || this.tagName === 'A') return;

            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            this.appendChild(ripple);

            ripple.addEventListener('animationend', function () {
                ripple.remove();
            });
        });
    });


    // ===== Stat Counter Animation =====
    const statNumbers = document.querySelectorAll('.stat-number');

    if (statNumbers.length && 'IntersectionObserver' in window) {
        const counterObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    counterObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        statNumbers.forEach(function (el) {
            counterObserver.observe(el);
        });
    }

    function animateCounter(el) {
        var text = el.textContent.trim();
        var match = text.match(/^(\d+(?:\.\d+)?)/);
        if (!match) return;

        var target = parseFloat(match[1]);
        var suffix = text.replace(match[1], '');
        var duration = 1200;
        var startTime = null;

        function easeOutExpo(t) {
            return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
        }

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var easedProgress = easeOutExpo(progress);
            var current = Math.round(easedProgress * target * 10) / 10;

            if (Number.isInteger(target)) {
                current = Math.round(easedProgress * target);
            }

            el.textContent = current + suffix;

            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }

        requestAnimationFrame(step);
    }


    // ===== Toast Auto-Dismiss =====
    var messages = document.querySelectorAll('.message');
    messages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'all 0.4s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(function () {
                msg.remove();
            }, 400);
        }, 5000);
    });


    // ===== Auto-resize Textarea in LLM Panel =====
    var llmTextarea = document.getElementById('llmQuery');
    if (llmTextarea) {
        llmTextarea.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }

})();
