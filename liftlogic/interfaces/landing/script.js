/* ===================================
   ARPRO V2 Enhanced - Main JavaScript
   Combines AI-Aesthetic with Escalated Patterns
   =================================== */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {

    // Initialize all features
    initNavigation();
    initMobileMenu();
    initAOS();
    initLucideIcons();
    initContactForm();
    initSmoothScroll();

});

/* === NAVIGATION SCROLL EFFECT === */
function initNavigation() {
    const header = document.getElementById('header');
    const logo = document.querySelector('.logo-img');

    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
            // Switch to blue logo when header is white
            if (logo) {
                logo.src = 'assets/images/arpro-logo.png';
            }
        } else {
            header.classList.remove('scrolled');
            // Switch back to white logo when header is transparent/dark
            if (logo) {
                logo.src = 'assets/images/arpro-logo-white.png';
            }
        }
    });
}

/* === MOBILE MENU TOGGLE === */
function initMobileMenu() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navToggle.classList.toggle('active');
            navMenu.classList.toggle('active');
            document.body.classList.toggle('menu-open');
        });
    }

    // Close menu when clicking on a nav link
    const navLinks = document.querySelectorAll('.nav__link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navToggle.classList.remove('active');
            navMenu.classList.remove('active');
            document.body.classList.remove('menu-open');
        });
    });
}

/* === ANIMATE ON SCROLL (AOS) === */
function initAOS() {
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-in-out',
            once: true,
            offset: 100,
            delay: 100,
        });
    }
}

/* === LUCIDE ICONS === */
function initLucideIcons() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

/* === CONTACT FORM HANDLING === */
function initContactForm() {
    const form = document.getElementById('contact-form');

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            // Get form data
            const formData = new FormData(form);
            const data = {
                name: formData.get('name'),
                email: formData.get('email'),
                phone: formData.get('phone'),
                message: formData.get('message'),
            };

            // Log data (replace with actual API call)
            console.log('Form submitted:', data);

            // Show success message
            showFormMessage('success', 'Thank you! Your message has been sent successfully.');

            // Reset form
            form.reset();

            /*
            // Example: Send to API endpoint
            fetch('/api/contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })
            .then(response => response.json())
            .then(result => {
                showFormMessage('success', 'Thank you! Your message has been sent successfully.');
                form.reset();
            })
            .catch(error => {
                showFormMessage('error', 'Sorry, something went wrong. Please try again.');
            });
            */
        });
    }
}

/* === SHOW FORM MESSAGE === */
function showFormMessage(type, message) {
    // Create message element
    const messageEl = document.createElement('div');
    messageEl.className = `form-message form-message--${type}`;
    messageEl.textContent = message;

    // Style the message
    messageEl.style.cssText = `
        padding: 1rem;
        margin-top: 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
        text-align: center;
        animation: slideIn 0.3s ease-out;
    `;

    if (type === 'success') {
        messageEl.style.background = 'rgba(16, 185, 129, 0.1)';
        messageEl.style.color = '#10b981';
        messageEl.style.border = '1px solid rgba(16, 185, 129, 0.2)';
    } else {
        messageEl.style.background = 'rgba(239, 68, 68, 0.1)';
        messageEl.style.color = '#ef4444';
        messageEl.style.border = '1px solid rgba(239, 68, 68, 0.2)';
    }

    // Add to form
    const form = document.getElementById('contact-form');
    form.appendChild(messageEl);

    // Remove after 5 seconds
    setTimeout(() => {
        messageEl.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            messageEl.remove();
        }, 300);
    }, 5000);
}

/* === SMOOTH SCROLL === */
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');

            // Skip if href is just "#"
            if (href === '#') return;

            e.preventDefault();

            const target = document.querySelector(href);
            if (target) {
                const headerHeight = document.getElementById('header').offsetHeight;
                const targetPosition = target.offsetTop - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/* === UTILITY: DEBOUNCE === */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/* === INTERSECTION OBSERVER FOR ANIMATIONS === */
// Additional scroll-based animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
        }
    });
}, observerOptions);

// Observe all sections
document.querySelectorAll('section').forEach(section => {
    observer.observe(section);
});

/* === CONSOLE WELCOME MESSAGE === */
console.log('%c ARPRO V2 Enhanced ', 'background: #2563eb; color: white; font-size: 16px; padding: 8px;');
console.log('%c Next-Level Service ', 'background: #3b82f6; color: white; font-size: 14px; padding: 6px;');
console.log('%c Built with Escalated patterns + AI aesthetic ', 'color: #64748b; font-size: 12px;');
