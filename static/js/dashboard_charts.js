const serviceChartCanvas = document.getElementById("serviceChart");

if (serviceChartCanvas) {
    const labels = JSON.parse(serviceChartCanvas.dataset.labels || "[]");
    const values = JSON.parse(serviceChartCanvas.dataset.values || "[]");

    new Chart(serviceChartCanvas, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    "#16a34a",
                    "#22c55e",
                    "#3b82f6",
                    "#f59e0b",
                    "#8b5cf6"
                ],
                borderWidth: 8,
                borderColor: "#ffffff",
                hoverOffset: 14
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "72%",
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: "#052e1b",
                    padding: 14,
                    titleFont: {
                        size: 14,
                        weight: "bold"
                    },
                    bodyFont: {
                        size: 13
                    }
                }
            }
        }
    });
}