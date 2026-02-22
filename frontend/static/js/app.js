document.addEventListener('DOMContentLoaded', () => {
    // 1. SCROLL REVEAL ANIMATION
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Optional: stop observing once revealed
                // observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    animatedElements.forEach(el => observer.observe(el));


    // 2. TYPING EFFECT FOR HERO SECTION
    const codeElement = document.getElementById('typing-code');
    if (codeElement) {
        const codeText = `import sdk from 'ai-memory-sdk'

// Initialize client
const memory = sdk.init({
  apiKey: 'sk_prod_5921...',
  context: 'user_992'
})

// Store memory
await memory.add(
  "User prefers dark mode"
)

// Retrieve context
const preferences = await memory.search(
  "What is the user's theme?"
)`;

        let i = 0;
        const speed = 25; // typing speed in ms

        function typeCode() {
            if (i < codeText.length) {
                codeElement.textContent += codeText.charAt(i);
                i++;
                setTimeout(typeCode, speed);
            }
        }

        // Start typing after a short delay
        setTimeout(typeCode, 800);
    }
});
