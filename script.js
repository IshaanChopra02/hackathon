// 1. Retrieve user_id from localStorage
const userId = localStorage.getItem('user_id');

// 2. Authentication Check
if (!userId) {
    console.warn("No user ID found. Redirecting to login...");
    window.location.href = '/index.html'; // Redirect to login if not authenticated
}

// 3. Fetch and Render Products
async function fetchProducts() {
    const tbody = document.getElementById('products-table-body');
    
    try {
        const res = await fetch(`/products/?user_id=${userId}`);
        
        if (!res.ok) throw new Error(`Products fetch failed: ${res.status}`);
        
        const products = await res.json();
        
        if (tbody) {
            tbody.innerHTML = ""; // Clear loading state

            if (products.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No products found.</td></tr>`;
                return;
            }

            products.forEach(product => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${product.id || 'N/A'}</td>
                    <td>${product.name || 'Unnamed Item'}</td>
                    <td>${product.category || 'N/A'}</td>
                    <td>${product.stock || 0}</td>
                    <td>$${product.price || '0.00'}</td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (err) {
        console.error("Products Error:", err);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Failed to load products.</td></tr>`;
        }
    }
}

// 4. Fetch and Render Dashboard Data
async function fetchDashboardData() {
    const container = document.getElementById('metrics-container');
    
    try {
        const res = await fetch(`/dashboard/?user_id=${userId}`);
        
        if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
        
        const data = await res.json();
        
        if (container) {
            container.innerHTML = `
                <div class="card">
                    <h3>Total Items</h3>
                    <p>${data.totalItems || 0}</p>
                </div>
                <div class="card">
                    <h3>Low Stock Alerts</h3>
                    <p style="color: ${data.lowStock > 0 ? 'red' : 'green'}">${data.lowStock || 0}</p>
                </div>
                <div class="card">
                    <h3>Total Inventory Value</h3>
                    <p>$${data.totalValue || 0}</p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Dashboard Error:", err);
        if (container) {
            container.innerHTML = `<p style="color: red;">Failed to load dashboard data.</p>`;
        }
    }
}

// 5. Initialize on Page Load
document.addEventListener('DOMContentLoaded', () => {
    // Only fetch data if the user is authenticated
    if (userId) {
        fetchDashboardData();
        fetchProducts();
    }
});