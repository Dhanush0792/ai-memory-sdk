document.addEventListener('DOMContentLoaded', () => {
    const codeElement = document.getElementById('typing-code');
    const codeSnippet = `memory.ingest(
    user_id="user_123",
    conversation="I work at Microsoft."
)

context = memory.retrieve(user_id="user_123")

llm.generate(
    prompt="Explain OAuth.",
    context=context
)`;

    let i = 0;
    let isTyping = true;
    const typingSpeed = 30; // ms per char
    const pauseDuration = 3000; // ms to wait before looping

    function typeWriter() {
        if (i < codeSnippet.length) {
            codeElement.textContent += codeSnippet.charAt(i);
            i++;
            // Highlight syntax simply by wrapping in spans (basic implementation)
            // ideally we'd use a library like PrismJS, but for this constraint we keep it simple or adds classes
            // For now, let's just type plain text to match the "clean" requirement, 
            // or we can add basic syntax highlighting if needed. 
            // The CSS has colors for standard codeblocks, but for dynamic typing, plain text is safest to avoid jagged markup injection.
            setTimeout(typeWriter, typingSpeed);
        } else {
            isTyping = false;
            setTimeout(resetTyping, pauseDuration);
        }
    }

    function resetTyping() {
        codeElement.textContent = '';
        i = 0;
        isTyping = true;
        typeWriter();
    }

    // Start the animation
    typeWriter();

    // Smooth Scroll for Anchors
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.section, .feature-card, .step-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(el);
    });

    // Add visible class styling
    const style = document.createElement('style');
    style.innerHTML = `
        .visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);
});
