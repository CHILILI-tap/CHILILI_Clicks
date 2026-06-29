// =====================================
// CHILILI Analytics Center Animation
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    // -----------------------------
    // Animate Progress Bars
    // -----------------------------
    const progressBars = document.querySelectorAll(".analytics-progress-fill");

    progressBars.forEach((bar, index) => {

        const value = parseFloat(bar.dataset.value || 0);

        setTimeout(() => {

            bar.style.width = value + "%";

        }, 250 * index);

    });


    // -----------------------------
    // Card Hover Effect
    // -----------------------------
    const cards = document.querySelectorAll(
        ".analytics-progress-row, .fin-stat-card, .fin-panel"
    );

    cards.forEach(card => {

        card.addEventListener("mouseenter", () => {

            card.style.transform = "translateY(-6px)";
            card.style.transition = ".25s ease";

        });

        card.addEventListener("mouseleave", () => {

            card.style.transform = "translateY(0px)";

        });

    });


    // -----------------------------
    // Counter Animation
    // -----------------------------
    const counters = document.querySelectorAll(
        ".fin-stat-card h3, .analytics-bottom-grid strong"
    );

    counters.forEach(counter => {

        const originalText = counter.innerText;

        let numericValue = parseFloat(
            originalText.replace(/[^\d.]/g, "")
        );

        if (isNaN(numericValue)) return;

        let current = 0;
        const increment = numericValue / 40;

        const timer = setInterval(() => {

            current += increment;

            if (current >= numericValue) {

                counter.innerText = originalText;
                clearInterval(timer);

            } else {

                if (originalText.includes("₦")) {

                    counter.innerText =
                        "₦" + current.toLocaleString(undefined, {
                            maximumFractionDigits: 2
                        });

                } else if (originalText.includes("%")) {

                    counter.innerText =
                        current.toFixed(1) + "%";

                } else {

                    counter.innerText =
                        Math.floor(current);

                }

            }

        }, 25);

    });


    // -----------------------------
    // Analytics Glow
    // -----------------------------
    const analytics = document.querySelector(".analytics-center-pro");

    if (analytics) {

        setInterval(() => {

            analytics.classList.toggle("analytics-glow");

        }, 3000);

    }

});