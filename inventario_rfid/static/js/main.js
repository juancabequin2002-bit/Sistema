document.addEventListener("DOMContentLoaded", () => {
    const renderChart = (id, colors) => {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const labels = JSON.parse(canvas.dataset.labels || "[]");
        const values = JSON.parse(canvas.dataset.values || "[]");
        if (!labels.length) return;

        new Chart(canvas, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 8,
                }],
            },
            options: {
                cutout: "72%",
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
            },
        });
    };

    renderChart("categoryChart", ["#2563EB", "#16A34A", "#F59E0B", "#0EA5E9", "#8B5CF6", "#94A3B8"]);
    renderChart("statusChart", ["#16A34A", "#CBD5E1", "#F59E0B", "#DC2626"]);

    const rfidInput = document.querySelector(".rfid-input");
    if (rfidInput) {
        rfidInput.focus();
        setInterval(() => {
            if (document.activeElement !== rfidInput) {
                rfidInput.focus();
            }
        }, 1200);
    }

    const globalSearchInput = document.getElementById("globalSearchInput");
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
            event.preventDefault();
            if (globalSearchInput) {
                globalSearchInput.focus();
                globalSearchInput.select();
            }
        }
    });

    const topbarUserToggle = document.getElementById("topbarUserToggle");
    const topbarUserMenu = document.querySelector(".topbar-user-menu");
    if (topbarUserToggle && topbarUserMenu) {
        topbarUserToggle.addEventListener("click", () => {
            const isOpen = topbarUserMenu.classList.toggle("is-open");
            topbarUserToggle.setAttribute("aria-expanded", String(isOpen));
        });

        document.addEventListener("click", (event) => {
            if (!topbarUserMenu.contains(event.target)) {
                topbarUserMenu.classList.remove("is-open");
                topbarUserToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const themeToggleIcon = document.getElementById("themeToggleIcon");
    const body = document.body;
    const applyTheme = (theme) => {
        body.classList.remove("theme-soft", "theme-contrast");
        body.classList.add(theme);
        if (themeToggleIcon) {
            themeToggleIcon.className = theme === "theme-contrast" ? "bi bi-moon-stars" : "bi bi-sun";
        }
    };

    const savedTheme = localStorage.getItem("trazia-theme") || "theme-soft";
    applyTheme(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            const nextTheme = body.classList.contains("theme-contrast") ? "theme-soft" : "theme-contrast";
            applyTheme(nextTheme);
            localStorage.setItem("trazia-theme", nextTheme);
        });
    }
});
