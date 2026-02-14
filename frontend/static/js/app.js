// AI Memory SDK - Neural Memory Space Frontend
// Subtle interactions and parallax effects

// ===== Mouse Parallax Effect =====
let mouseX = 0;
let mouseY = 0;
let currentX = 0;
let currentY = 0;

document.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 20; // Max 10px movement in each direction
    mouseY = (e.clientY / window.innerHeight - 0.5) * 20;
});

function animateParallax() {
    // Smooth interpolation for natural movement
    currentX += (mouseX - currentX) * 0.05;
    currentY += (mouseY - currentY) * 0.05;

    const nodeGroups = document.querySelectorAll('.node-group');

    nodeGroups.forEach((group, index) => {
        const depth = parseFloat(group.getAttribute('data-depth'));
        const multiplier = depth * 0.3; // Depth-based parallax strength

        group.style.transform = `translate(${currentX * multiplier}px, ${currentY * multiplier}px)`;
    });

    requestAnimationFrame(animateParallax);
}

// Start parallax animation
animateParallax();

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));

        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ===== Intersection Observer for Fade-in Animations =====
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe sections for fade-in
document.querySelectorAll('.process-step, .feature-card, .demo-input, .demo-output').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
    observer.observe(el);
});

// ===== Memory Demo Animation =====
const demoSection = document.querySelector('.memory-demo');
let demoAnimated = false;

const demoObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && !demoAnimated) {
            demoAnimated = true;
            animateMemoryDemo();
        }
    });
}, { threshold: 0.3 });

if (demoSection) {
    demoObserver.observe(demoSection);
}

function animateMemoryDemo() {
    const memoryItems = document.querySelectorAll('.memory-item');

    memoryItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        item.style.transition = 'opacity 0.5s ease, transform 0.5s ease';

        setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, index * 150 + 300);
    });

    // Subtle node rearrangement effect
    const nodes = document.querySelectorAll('.memory-node');
    nodes.forEach((node, index) => {
        setTimeout(() => {
            node.style.transition = 'transform 1s ease, opacity 0.5s ease';
            const randomX = (Math.random() - 0.5) * 10;
            const randomY = (Math.random() - 0.5) * 10;
            node.style.transform = `translate(${randomX}px, ${randomY}px)`;
            node.style.opacity = '0.8';
        }, index * 50);

        setTimeout(() => {
            node.style.transform = 'translate(0, 0)';
            node.style.opacity = '';
        }, 2000 + index * 50);
    });
}

// ===== Audience Section Staggered Animation =====
const audienceSection = document.querySelector('.audience');
let audienceAnimated = false;

// Check for reduced motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const audienceObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && !audienceAnimated) {
            audienceAnimated = true;

            // Skip animation if user prefers reduced motion
            if (prefersReducedMotion) {
                document.querySelectorAll('.audience-item').forEach(item => {
                    item.classList.add('animate-in');
                });
                return;
            }

            // Staggered reveal animation
            const audienceItems = document.querySelectorAll('.audience-item');
            audienceItems.forEach((item, index) => {
                setTimeout(() => {
                    item.classList.add('animate-in');
                }, index * 120); // 120ms delay between each item
            });
        }
    });
}, { threshold: 0.3 });

if (audienceSection) {
    audienceObserver.observe(audienceSection);
}

// ===== Process Step Hover Effect =====
const processSteps = document.querySelectorAll('.process-step');

processSteps.forEach((step, index) => {
    step.addEventListener('mouseenter', () => {
        // Highlight connecting lines
        const lines = document.querySelectorAll('.connection-lines line');
        lines.forEach(line => {
            line.style.opacity = '0.05';
        });

        // Highlight relevant connections
        if (index < lines.length) {
            lines[index].style.opacity = '0.4';
            lines[index].style.stroke = '#22D3EE';
        }
    });

    step.addEventListener('mouseleave', () => {
        const lines = document.querySelectorAll('.connection-lines line');
        lines.forEach(line => {
            line.style.opacity = '';
            line.style.stroke = '';
        });
    });
});

// ===== Feature Card Glow Effect =====
const featureCards = document.querySelectorAll('.feature-card');

featureCards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
    });
});

// Add glow effect CSS dynamically
const style = document.createElement('style');
style.textContent = `
    .feature-card::before {
        content: '';
        position: absolute;
        top: var(--mouse-y, 50%);
        left: var(--mouse-x, 50%);
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
        transform: translate(-50%, -50%);
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
        border-radius: 50%;
    }
    
    .feature-card:hover::before {
        opacity: 1;
    }
`;
document.head.appendChild(style);

// ===== Performance Optimization =====
// Reduce animations on low-performance devices
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.memory-node, .connection-lines line').forEach(el => {
        el.style.animation = 'none';
    });
}

// ===== Authentication Handling =====
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const API_BASE_URL = window.location.origin;

if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const submitBtn = loginForm.querySelector('button[type="submit"]');

        try {
            submitBtn.textContent = 'Logging in...';
            submitBtn.disabled = true;

            const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            localStorage.setItem('auth_token', data.access_token);
            window.location.href = 'chat.html';

        } catch (error) {
            alert(error.message);
            submitBtn.textContent = 'Login';
            submitBtn.disabled = false;
        }
    });
}

if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fullName = document.getElementById('fullName').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const submitBtn = signupForm.querySelector('button[type="submit"]');

        try {
            submitBtn.textContent = 'Creating Account...';
            submitBtn.disabled = true;

            const response = await fetch(`${API_BASE_URL}/api/v1/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name: fullName, email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Signup failed');
            }

            localStorage.setItem('auth_token', data.access_token);
            window.location.href = 'chat.html';

        } catch (error) {
            alert(error.message);
            submitBtn.textContent = 'Sign Up';
            submitBtn.disabled = false;
        }
    });
}

// ===== Console Easter Egg =====
console.log('%c🧠 AI Memory SDK', 'font-size: 20px; font-weight: bold; color: #6366F1;');
console.log('%cPersistent memory for AI applications', 'font-size: 12px; color: #22D3EE;');
console.log('%cGitHub: https://github.com/Dhanush0792/ai-memory-sdk', 'font-size: 10px; color: #9CA3AF;');
