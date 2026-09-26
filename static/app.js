(function () {
    function onReady(fn) {
        if (document.readyState === "complete" || document.readyState === "interactive") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    onReady(function () {
        const navToggle = document.querySelector(".nav-toggle");
        const nav = document.querySelector(".site-nav");
        const header = document.querySelector(".site-header");

        // Mobile navigation toggle
        if (navToggle && nav) {
            navToggle.addEventListener("click", function () {
                const isOpen = nav.classList.toggle("open");
                navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
            });

            // Close menu on nav link click (mobile)
            nav.addEventListener("click", function (event) {
                const target = event.target;
                if (target instanceof HTMLElement && target.closest("a")) {
                    nav.classList.remove("open");
                    navToggle.setAttribute("aria-expanded", "false");
                }
            });
        }

        // Smooth scrolling for in-page anchors and CTA buttons
        function handleScrollClick(event, targetSelector) {
            const target = document.querySelector(targetSelector);
            if (!target) return;
            event.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        document.addEventListener("click", function (event) {
            const target = event.target;
            if (!(target instanceof HTMLElement)) return;

            // Data-scroll-target buttons
            const scrollTarget = target.getAttribute("data-scroll-target");
            if (scrollTarget) {
                handleScrollClick(event, scrollTarget);
                return;
            }

            // In-page anchor links (e.g., #services)
            if (target.tagName === "A") {
                const href = target.getAttribute("href") || "";
                if (href.startsWith("#") && href.length > 1) {
                    handleScrollClick(event, href);
                }
            }
        });

        // Scope call link placeholder wiring
        const scopeCallLink = document.querySelector("[data-role='scope-call-link']");
        if (scopeCallLink instanceof HTMLAnchorElement) {
            scopeCallLink.addEventListener("click", function (event) {
                if (!scopeCallLink.getAttribute("href") || scopeCallLink.getAttribute("href") === "#") {
                    event.preventDefault();
                    window.location.href = "mailto:customaimodels@gmail.com?subject=" +
                        encodeURIComponent("Scope call: Custom AI Models") +
                        "&body=" +
                        encodeURIComponent(
                            "A short description of your project, current systems, and timeline will help us use our time well on the call."
                        );
                }
            });
        }

        // Dynamic year in footer
        const yearSpan = document.getElementById("year");
        if (yearSpan) {
            yearSpan.textContent = String(new Date().getFullYear());
        }

        // Optional: subtle header shadow on scroll
        if (header) {
            const toggleShadow = () => {
                if (window.scrollY > 4) {
                    header.style.boxShadow = "0 12px 30px rgba(15, 23, 42, 0.85)";
                } else {
                    header.style.boxShadow = "none";
                }
            };

            toggleShadow();
            window.addEventListener("scroll", toggleShadow, { passive: true });
        }
    });
})();
