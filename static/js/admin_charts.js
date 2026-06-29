function createAdminDoughnutChart(canvasId) {
    const canvas = document.getElementById(canvasId);

    if (!canvas) return;

    const labels = JSON.parse(canvas.dataset.labels || "[]");
    const values = JSON.parse(canvas.dataset.values || "[]");

    new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    "#22c55e",
                    "#f59e0b",
                    "#ef4444",
                    "#3b82f6",
                    "#8b5cf6"
                ],
                borderColor: "#ffffff",
                borderWidth: 8,
                hoverOffset: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}

function createAdminBarChart(canvasId) {
    const canvas = document.getElementById(canvasId);

    if (!canvas) return;

    const labels = JSON.parse(canvas.dataset.labels || "[]");
    const values = JSON.parse(canvas.dataset.values || "[]");

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Transactions",
                data: values,
                backgroundColor: "#22c55e",
                borderRadius: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

createAdminDoughnutChart("fundingChart");
createAdminDoughnutChart("transactionStatusChart");
createAdminBarChart("serviceUsageChart");