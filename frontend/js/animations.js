/* ============================================================
   Rahmani Jewelry — Luxury Motion Controller (Cinematic Hero)
   Interactive particles, two-phase entrance, scroll exit
   Vanilla JS (no deps) · respects prefers-reduced-motion
   ============================================================ */
(function () {
    'use strict';

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ── Hero entrance: two-phase ────────────────────────── */
    const initHeroEntrance = () => {
        const hero = document.querySelector('.hero');
        if (!hero || reduceMotion) return;

        /* Phase 1: headline + copy rise from blur */
        const steps = hero.querySelectorAll('[data-entrance]');
        steps.forEach((el) => {
            const step = Number(el.dataset.entrance) || 0;
            el.style.transitionDelay = `${step * 0.13}s`;
        });

        requestAnimationFrame(() => {
            requestAnimationFrame(() => hero.classList.add('is-entered'));
        });

        /* Phase 2: background image fades in after 1.2s */
        setTimeout(() => {
            hero.classList.add('is-bg-visible');
        }, 1200);
    };

    /* ── Interactive gold dust particles ──────────────────── */
    const initParticles = () => {
        const host = document.querySelector('.hero-particles');
        if (!host || reduceMotion) return;

        const canvas = host.querySelector('canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        let width = 0;
        let height = 0;
        let particles = [];
        let sparkles = [];
        let rafId = null;
        const DPR = Math.min(window.devicePixelRatio || 1, 2);

        const mouse = { x: -9999, y: -9999 };
        const ATTRACT_RADIUS = 130;
        const ATTRACT_STRENGTH = 0.018;
        const RETURN_SPEED = 0.012;

        const rand = (min, max) => min + Math.random() * (max - min);

        const build = () => {
            width = host.clientWidth;
            height = host.clientHeight;
            canvas.width = width * DPR;
            canvas.height = height * DPR;
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
            ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

            const count = Math.min(Math.floor((width * height) / 20000), 100);
            particles = Array.from({ length: count }, () => ({
                x: rand(0, width),
                y: rand(0, height),
                restX: 0,
                restY: 0,
                r: rand(0.4, 2.0),
                vy: rand(0.04, 0.22),
                vx: rand(-0.06, 0.06),
                tw: rand(0.5, 2.2),
                p: rand(0, Math.PI * 2),
            }));
            /* Store rest positions for spring-back */
            particles.forEach((p) => { p.restX = p.x; p.restY = p.y; });
        };

        /* Spawn a small sparkle burst near cursor */
        const spawnSparkle = () => {
            if (mouse.x < 0) return;
            for (let i = 0; i < 3; i++) {
                sparkles.push({
                    x: mouse.x + rand(-20, 20),
                    y: mouse.y + rand(-20, 20),
                    r: rand(1.2, 2.8),
                    life: 1,
                    decay: rand(0.012, 0.025),
                });
            }
        };

        let sparkleTimer = 0;

        const draw = (t) => {
            ctx.clearRect(0, 0, width, height);

            /* Sparkle burst throttled */
            sparkleTimer++;
            if (sparkleTimer % 18 === 0) spawnSparkle();

            /* Draw sparkles */
            for (let i = sparkles.length - 1; i >= 0; i--) {
                const s = sparkles[i];
                s.life -= s.decay;
                if (s.life <= 0) { sparkles.splice(i, 1); continue; }
                ctx.beginPath();
                ctx.arc(s.x, s.y, s.r * s.life, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(243, 227, 189, ${s.life * 0.7})`;
                ctx.fill();
            }

            /* Draw particles with mouse attraction */
            for (const p of particles) {
                const alpha = 0.2 + 0.45 * (0.5 + 0.5 * Math.sin(t * 0.001 * p.tw + p.p));

                /* Mouse attraction */
                const dx = mouse.x - p.x;
                const dy = mouse.y - p.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < ATTRACT_RADIUS && dist > 1) {
                    const force = (1 - dist / ATTRACT_RADIUS) * ATTRACT_STRENGTH;
                    p.x += dx * force;
                    p.y += dy * force;
                } else {
                    /* Spring back toward rest position */
                    p.x += (p.restX - p.x) * RETURN_SPEED;
                    p.y += (p.restY - p.y) * RETURN_SPEED;
                }

                /* Natural drift */
                p.y -= p.vy;
                p.x += p.vx;

                /* Wrap vertically */
                if (p.y < -6) {
                    p.y = height + 6;
                    p.x = rand(0, width);
                    p.restX = p.x;
                    p.restY = p.y;
                }
                if (p.x < -6) p.x = width + 6;
                if (p.x > width + 6) p.x = -6;

                /* Draw main dot */
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(226, 195, 132, ${alpha})`;
                ctx.fill();

                /* Bloom halo for larger particles */
                if (p.r > 1.4) {
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.r * 2.8, 0, Math.PI * 2);
                    ctx.fillStyle = `rgba(226, 195, 132, ${alpha * 0.1})`;
                    ctx.fill();
                }

                /* Extra glow when near mouse */
                if (dist < ATTRACT_RADIUS && dist > 1) {
                    const glowAlpha = (1 - dist / ATTRACT_RADIUS) * 0.3;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2);
                    ctx.fillStyle = `rgba(243, 227, 189, ${glowAlpha})`;
                    ctx.fill();
                }
            }

            rafId = requestAnimationFrame(draw);
        };

        /* Mouse tracking */
        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
        });
        canvas.addEventListener('mouseleave', () => {
            mouse.x = -9999;
            mouse.y = -9999;
        });

        build();
        draw(0);

        /* Debounced resize */
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (host.clientWidth > 0) build();
            }, 160);
        });

        /* Pause when hero leaves viewport */
        const io = new IntersectionObserver((entries) => {
            const visible = entries[0].isIntersecting && entries[0].intersectionRatio > 0;
            if (visible && !rafId) {
                rafId = requestAnimationFrame(draw);
            } else if (!visible && rafId) {
                cancelAnimationFrame(rafId);
                rafId = null;
            }
        }, { threshold: 0.02 });
        io.observe(host);
    };

    /* ── Count-up stats ───────────────────────────────────── */
    const initCounters = () => {
        const meta = document.querySelector('.hero-meta');
        if (!meta) return;

        const animate = (el) => {
            const raw = el.dataset.count;
            if (raw == null) return;
            const target = parseInt(raw, 10);
            if (!Number.isFinite(target) || reduceMotion) return;

            const numEl = el.querySelector('.num') || el;
            const toPersian = (n) => String(n).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);

            const duration = 1600;
            const start = performance.now();
            const step = (now) => {
                const t = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - t, 3);
                numEl.textContent = toPersian(Math.round(target * eased));
                if (t < 1) requestAnimationFrame(step);
                else numEl.textContent = toPersian(target);
            };
            requestAnimationFrame(step);
        };

        const io = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    meta.classList.add('in-view');
                    meta.querySelectorAll('strong').forEach(animate);
                    io.unobserve(meta);
                }
            });
        }, { threshold: 0.5 });
        io.observe(meta);
    };

    /* ── Scroll reveal for every [data-reveal] element ────── */
    const initScrollReveal = () => {
        let targets = document.querySelectorAll('[data-reveal]');
        if (!targets.length) return;

        const reveal = (target) => {
            if (target.dataset.reveal === 'group') {
                target.className.includes('product-card') || target.parentElement?.classList.contains('products-grid')
                    ? revealGroup(target)
                    : target.classList.add('in-view');
                return;
            }
            target.classList.add('in-view');
        };

        const revealGroup = (container) => {
            const cards = container.querySelectorAll('.product-card, [data-reveal]');
            cards.forEach((card, i) => {
                card.style.transitionDelay = `${Math.min(i * 0.1, 0.6)}s`;
                card.classList.add('in-view');
            });
            container.parentElement?.classList.add('in-view');
            container.classList.add('in-view');
        };

        if ('IntersectionObserver' in window) {
            const io = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        reveal(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });

            targets.forEach((t) => io.observe(t));
        } else {
            targets.forEach((t) => t.classList.add('in-view'));
        }
    };

    /* ── Header scroll progress hairline ──────────────────── */
    const initProgressBar = () => {
        const bar = document.querySelector('.header-progress');
        if (!bar) return;
        const onScroll = () => {
            const doc = document.documentElement;
            const max = doc.scrollHeight - window.innerHeight;
            const ratio = max > 0 ? window.scrollY / max : 0;
            bar.style.width = `${Math.min(ratio * 100, 100)}%`;
            bar.classList.toggle('is-visible', window.scrollY > 200);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    };

    /* ── Hero scroll exit: cinematic parallax ─────────────── */
    const initHeroScrollExit = () => {
        const hero = document.querySelector('.hero');
        const center = document.querySelector('.hero-center');
        const bgImage = document.querySelector('.hero-bg-image');
        const particles = document.querySelector('.hero-particles');
        if (!hero || !center || reduceMotion) return;

        let ticking = false;
        const update = () => {
            const heroH = hero.offsetHeight;
            const scrollY = window.scrollY;
            const ratio = Math.min(scrollY / heroH, 1);

            /* Center text: drift up + fade out */
            center.style.transform = `translateY(${-(ratio * 100)}px)`;
            center.style.opacity = `${1 - ratio * 1.4}`;
            center.style.filter = `blur(${ratio * 6}px)`;

            /* Background image: scale up + brighten */
            if (bgImage) {
                bgImage.style.transform = `scale(${1 + ratio * 0.18})`;
                bgImage.style.opacity = `${0.5 + ratio * 0.4}`;
            }

            /* Particles: fade out */
            if (particles) {
                particles.style.opacity = `${1 - ratio * 1.6}`;
            }

            ticking = false;
        };

        window.addEventListener('scroll', () => {
            if (!ticking) {
                ticking = true;
                requestAnimationFrame(update);
            }
        }, { passive: true });
        update();
    };

    /* ── Card Stack (Collections) ─────────────────────────── */
    const initCardStack = () => {
        const stack = document.querySelector('.card-stack');
        if (!stack) return;
        const cards = [...stack.querySelectorAll('.stack-card')];
        const dots = [...stack.querySelectorAll('.stack-dot')];
        const prevBtn = stack.querySelector('.stack-arrow-prev');
        const nextBtn = stack.querySelector('.stack-arrow-next');
        if (cards.length === 0) return;

        let current = 0;
        const total = cards.length;
        let isDragging = false;
        let startX = 0;
        let deltaX = 0;

        const updateStack = (dir) => {
            if (dir === 'next') current = (current + 1) % total;
            else if (dir === 'prev') current = (current - 1 + total) % total;

            cards.forEach((card, i) => {
                const pos = (i - current + total) % total;
                card.classList.remove('is-pos-0', 'is-pos-1', 'is-pos-2', 'is-pos-3');
                card.classList.add(`is-pos-${pos}`);
                card.style.zIndex = 10 - pos;
            });

            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === current);
            });
        };

        /* Set initial positions */
        updateStack();

        /* Arrow navigation */
        if (prevBtn) prevBtn.addEventListener('click', () => updateStack('prev'));
        if (nextBtn) nextBtn.addEventListener('click', () => updateStack('next'));

        /* Dot navigation */
        dots.forEach((dot, i) => {
            dot.addEventListener('click', () => {
                if (i === current) return;
                updateStack(i > current ? 'next' : 'prev');
            });
        });

        /* Drag/swipe support */
        const onStart = (x) => {
            isDragging = true;
            startX = x;
            deltaX = 0;
        };
        const onMove = (x) => {
            if (!isDragging) return;
            deltaX = x - startX;
        };
        const onEnd = () => {
            if (!isDragging) return;
            isDragging = false;
            if (Math.abs(deltaX) > 50) {
                updateStack(deltaX > 0 ? 'prev' : 'next');
            }
        };

        /* Mouse events */
        stack.addEventListener('mousedown', (e) => {
            e.preventDefault();
            onStart(e.clientX);
        });
        window.addEventListener('mousemove', (e) => onMove(e.clientX));
        window.addEventListener('mouseup', onEnd);

        /* Touch events */
        stack.addEventListener('touchstart', (e) => onStart(e.touches[0].clientX), { passive: true });
        stack.addEventListener('touchmove', (e) => onMove(e.touches[0].clientX), { passive: true });
        stack.addEventListener('touchend', onEnd);

        /* Keyboard navigation */
        stack.setAttribute('tabindex', '0');
        stack.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') updateStack('next');
            if (e.key === 'ArrowRight') updateStack('prev');
        });
    };

    /* ── Showcase Drag Scrolling ──────────────────────────── */
    const initShowcaseDrag = () => {
        const track = document.querySelector('.showcase-track');
        if (!track) return;

        let isDragging = false;
        let startX = 0;
        let scrollLeft = 0;
        let velocity = 0;
        let lastX = 0;
        let lastTime = 0;
        let momentumId = null;

        const stopMomentum = () => {
            if (momentumId) { cancelAnimationFrame(momentumId); momentumId = null; }
        };

        const startDrag = (x) => {
            isDragging = true;
            startX = x;
            scrollLeft = track.scrollLeft;
            lastX = x;
            lastTime = Date.now();
            velocity = 0;
            stopMomentum();
            track.style.scrollBehavior = 'auto';
        };

        const moveDrag = (x) => {
            if (!isDragging) return;
            const dx = x - startX;
            track.scrollLeft = scrollLeft - dx;

            const now = Date.now();
            const dt = now - lastTime;
            if (dt > 0) velocity = (x - lastX) / dt;
            lastX = x;
            lastTime = now;
        };

        const endDrag = () => {
            if (!isDragging) return;
            isDragging = false;
            track.style.scrollBehavior = 'smooth';

            /* Apply momentum */
            if (Math.abs(velocity) > 0.3) {
                let vx = velocity * 600;
                const decelerate = () => {
                    vx *= 0.95;
                    track.scrollLeft -= vx * (1 / 60);
                    if (Math.abs(vx) > 0.5) {
                        momentumId = requestAnimationFrame(decelerate);
                    }
                };
                decelerate();
            }
        };

        /* Mouse events */
        track.addEventListener('mousedown', (e) => {
            if (e.target.closest('a, button')) return;
            e.preventDefault();
            startDrag(e.clientX);
        });
        window.addEventListener('mousemove', (e) => moveDrag(e.clientX));
        window.addEventListener('mouseup', endDrag);

        /* Touch events */
        track.addEventListener('touchstart', (e) => {
            if (e.target.closest('a, button')) return;
            startDrag(e.touches[0].clientX);
        }, { passive: true });
        track.addEventListener('touchmove', (e) => moveDrag(e.touches[0].clientX), { passive: true });
        track.addEventListener('touchend', endDrag);

        /* Arrow button navigation */
        document.querySelectorAll('[data-carousel="showcase"]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const dir = Number(btn.dataset.dir) || 1;
                track.scrollBy({ left: dir * 240, behavior: 'smooth' });
            });
        });
    };

    /* ── Boot ─────────────────────────────────────────────── */
    const init = () => {
        initHeroEntrance();
        initParticles();
        initCounters();
        initScrollReveal();
        initProgressBar();
        initHeroScrollExit();
        initCardStack();
        initShowcaseDrag();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();