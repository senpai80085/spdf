#!/usr/bin/env python3
"""
Generate admin.html with cosmic/galaxy theme
"""

html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPDF Admin Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        @keyframes starfield {
            0% { transform: translateY(0); }
            100% { transform: translateY(-100vh); }
        }
        
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(102, 126, 234, 0.5); }
            50% { box-shadow: 0 0 40px rgba(102, 126, 234, 0.8); }
        }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0a0e27;
            background-image: 
                radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e7ff;
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 200%;
            background-image: 
                radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.8), transparent),
                radial-gradient(2px 2px at 60px 70px, rgba(255,255,255,0.6), transparent),
                radial-gradient(1px 1px at 50px 50px, rgba(255,255,255,0.8), transparent),
                radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent),
                radial-gradient(2px 2px at 90px 10px, rgba(255,255,255,0.8), transparent);
            background-size: 200px 200px;
            animation: starfield 60s linear infinite;
            pointer-events: none;
            z-index: 0;
        }
        
        .dashboard {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(102, 126, 234, 0.2);
            overflow: hidden;
            position: relative;
            z-index: 1;
        }
        
        header {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
            border-bottom: 1px solid rgba(102, 126, 234, 0.3);
            color: #e0e7ff;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        h1 { 
            font-size: 24px;
            background: linear-gradient(135deg, #667eea 0%, #a78bfa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            filter: drop-shadow(0 0 10px rgba(102, 126, 234, 0.5));
        }
        
        .logout-btn {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }
        
        .logout-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
        }
        
        .tabs {
            display: flex;
            background: rgba(30, 41, 59, 0.6);
            border-bottom: 1px solid rgba(102, 126, 234, 0.2);
        }
        
        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 16px;
            color: #94a3b8;
            transition: all 0.3s;
            position: relative;
        }
        
        .tab:hover {
            color: #e0e7ff;
            background: rgba(102, 126, 234, 0.1);
        }
        
        .tab.active {
            color: #e0e7ff;
            background: rgba(15, 23, 42, 0.8);
            font-weight: 600;
        }
        
        .tab.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #667eea, #a78bfa, #667eea);
            animation: glow 2s infinite;
        }
        
        .content {
            padding: 30px;
            background: rgba(15, 23, 42, 0.5);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(51, 65, 85, 0.8) 100%);
            border: 1px solid rgba(102, 126, 234, 0.3);
            color: #e0e7ff;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #667eea, #a78bfa);
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
        }
        
        .stat-card h3 { font-size: 14px; opacity: 0.8; color: #a78bfa; }
        .stat-card p { font-size: 32px; font-weight: bold; margin-top: 10px; color: #e0e7ff; }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }
        
        .btn-danger { 
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }
        
        .btn-danger:hover { 
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(102, 126, 234, 0.2);
            color: #e0e7ff;
        }
        
        th {
            background: rgba(30, 41, 59, 0.6);
            font-weight: 600;
            color: #a78bfa;
        }
        
        tr:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .upload-zone {
            border: 2px dashed rgba(102, 126, 234, 0.5);
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: rgba(30, 41, 59, 0.3);
        }
        
        .upload-zone:hover {
            background: rgba(30, 41, 59, 0.5);
            border-color: rgba(167, 139, 250, 0.8);
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(5px);
            z-index: 1000;
        }
        
        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 1px solid rgba(102, 126, 234, 0.3);
            padding: 30px;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        
        .modal-content h2 {
            color: #e0e7ff;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #a78bfa;
        }
        
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 6px;
            background: rgba(15, 23, 42, 0.5);
            color: #e0e7ff;
            transition: all 0.3s;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            display: none;
            z-index: 2000;
            box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
        }
        
        .toast.show {
            display: block;
        }
        
        .toast.error {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
        }
        
        code {
            background: rgba(30, 41, 59, 0.6);
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            color: #a78bfa;
            border: 1px solid rgba(102, 126, 234, 0.2);
        }
        
        h2 {
            color: #e0e7ff;
            margin-bottom: 20px;
            font-size: 20px;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <header>
            <h1>🔒 SPDF Admin Dashboard</h1>
            <button class="logout-btn" onclick="logout()">Logout</button>
        </header>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('upload')">Upload PDF</button>
            <button class="tab" onclick="showTab('documents')">Documents</button>
            <button class="tab" onclick="showTab('users')">Users</button>
            <button class="tab" onclick="showTab('licenses')">Licenses</button>
        </div>
        
        <div class="content">
            <!-- Stats -->
            <div class="stats">
                <div class="stat-card">
                    <h3>Total Documents</h3>
                    <p id="stat-docs">0</p>
                </div>
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <p id="stat-users">0</p>
                </div>
                <div class="stat-card">
                    <h3>Active Licenses</h3>
                    <p id="stat-licenses">0</p>
                </div>
            </div>
            
            <!-- Upload Tab -->
            <div id="tab-upload" class="tab-content active">
                <h2>Upload & Convert PDF</h2>
                <div class="upload-zone" onclick="document.getElementById('pdf-file').click()">
                    <p style="font-size: 48px; margin-bottom: 10px;">📁</p>
                    <p id="file-name">Click or drag to upload PDF</p>
                    <input type="file" id="pdf-file" accept=".pdf" style="display:none" onchange="handleFileSelect(event)">
                </div>
                <form id="upload-form" style="margin-top: 20px; display: none;">
                    <div class="form-group">
                        <label>Document ID</label>
                        <input type="text" id="doc-id" required placeholder="e.g., DOC-001">
                    </div>
                    <div class="form-group">
                        <label>Title</label>
                        <input type="text" id="doc-title" required placeholder="Document title">
                    </div>
                    <div class="form-group">
                        <label>Max Devices</label>
                        <input type="number" id="max-devices" value="2" min="1">
                    </div>
                    <button type="submit" class="btn">Convert to SPDF</button>
                </form>
            </div>
            
            <!-- Documents Tab -->
            <div id="tab-documents" class="tab-content">
                <h2>Documents</h2>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Doc ID</th>
                            <th>Title</th>
                            <th>Org ID</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="documents-table"></tbody>
                </table>
            </div>
            
            <!-- Users Tab -->
            <div id="tab-users" class="tab-content">
                <h2>Users</h2>
                <button class="btn" onclick="showModal('user-modal')">Add User</button>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Email</th>
                            <th>Org ID</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="users-table"></tbody>
                </table>
            </div>
            
            <!-- Licenses Tab -->
            <div id="tab-licenses" class="tab-content">
                <h2>Licenses</h2>
                <button class="btn" onclick="showModal('license-modal')">Add License</button>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>User</th>
                            <th>Document</th>
                            <th>License Key</th>
                            <th>Max Devices</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="licenses-table"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <!-- Add User Modal -->
    <div id="user-modal" class="modal">
        <div class="modal-content">
            <h2>Add User</h2>
            <form id="user-form">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="user-email" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="user-password" required>
                </div>
                <div class="form-group">
                    <label>Org ID</label>
                    <input type="text" id="user-org" value="ORG-1" required>
                </div>
                <button type="submit" class="btn">Create User</button>
                <button type="button" class="btn btn-danger" onclick="hideModal('user-modal')">Cancel</button>
            </form>
        </div>
    </div>
    
    <!-- Add License Modal -->
    <div id="license-modal" class="modal">
        <div class="modal-content">
            <h2>Add License</h2>
            <form id="license-form">
                <div class="form-group">
                    <label>User ID</label>
                    <input type="number" id="license-user" required>
                </div>
                <div class="form-group">
                    <label>Document ID</label>
                    <input type="text" id="license-doc" required placeholder="e.g., DOC-001">
                </div>
                <div class="form-group">
                    <label>Max Devices</label>
                    <input type="number" id="license-max-devices" value="2" min="1">
                </div>
                <button type="submit" class="btn">Create License</button>
                <button type="button" class="btn btn-danger" onclick="hideModal('license-modal')">Cancel</button>
            </form>
        </div>
    </div>
    
    <!-- Toast -->
    <div id="toast" class="toast"></div>
    
    <script>
        const API_BASE = '';
        let token = localStorage.getItem('token');
        let selectedFile = null;
        
        // Check auth
        if (!token) {
            window.location.href = '/login.html';
        }
        
        // API helper
        async function api(endpoint, options = {}) {
            const headers = {
                'Authorization': `Bearer ${token}`,
                ...options.headers
            };
            
            if (options.body && !(options.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(options.body);
            }
            
            return fetch(API_BASE + endpoint, { ...options, headers });
        }
        
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
            
            if (tabName === 'documents') loadDocuments();
            if (tabName === 'users') loadUsers();
            if (tabName === 'licenses') loadLicenses();
        }
        
        // Toast
        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast show' + (isError ? ' error' : '');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
        
        // Modal
        function showModal(id) {
            document.getElementById(id).classList.add('show');
        }
        
        function hideModal(id) {
            document.getElementById(id).classList.remove('show');
        }
        
        // File upload
        function handleFileSelect(e) {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                document.getElementById('file-name').textContent = selectedFile.name;
                document.getElementById('upload-form').style.display = 'block';
            }
        }
        
        document.getElementById('upload-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!selectedFile) {
                showToast('Please select a file', true);
                return;
            }
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('doc_id', document.getElementById('doc-id').value);
            formData.append('title', document.getElementById('doc-title').value);
            formData.append('org_id', 'ORG-1');
            formData.append('max_devices', document.getElementById('max-devices').value);
            
            const res = await api('/admin/convert', { method: 'POST', body: formData });
            
            if (res.ok) {
                showToast('PDF converted successfully!');
                document.getElementById('upload-form').reset();
                document.getElementById('upload-form').style.display = 'none';
                document.getElementById('file-name').textContent = 'Click or drag to upload PDF';
                selectedFile = null;
                loadStats();
            } else {
                const data = await res.json();
                showToast(data.detail || 'Conversion failed', true);
            }
        });
        
        // Load stats
        async function loadStats() {
            const res = await api('/admin/stats');
            if (res.ok) {
                const stats = await res.json();
                document.getElementById('stat-docs').textContent = stats.total_documents;
                document.getElementById('stat-users').textContent = stats.total_users;
                document.getElementById('stat-licenses').textContent = stats.total_licenses;
            }
        }
        
        // Documents
        async function loadDocuments() {
            const res = await api('/admin/documents');
            if (res.ok) {
                const docs = await res.json();
                document.getElementById('documents-table').innerHTML = docs.map(doc => `
                    <tr>
                        <td>${doc.id}</td>
                        <td><code>${doc.doc_id}</code></td>
                        <td>${doc.title}</td>
                        <td>${doc.org_id}</td>
                        <td>
                            <button class="btn btn-danger" onclick="deleteDoc(${doc.id})">Delete</button>
                        </td>
                    </tr>
                `).join('');
            }
        }
        
        async function deleteDoc(id) {
            if (!confirm('Delete this document?')) return;
            const res = await api(`/admin/documents/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('Document deleted');
                loadDocuments();
                loadStats();
            }
        }
        
        // Users
        async function loadUsers() {
            const res = await api('/admin/users');
            if (res.ok) {
                const users = await res.json();
                document.getElementById ('users-table').innerHTML = users.map(user => `
                    <tr>
                        <td>${user.id}</td>
                        <td>${user.email}</td>
                        <td>${user.org_id}</td>
                        <td>
                            <button class="btn btn-danger" onclick="deleteUser(${user.id})">Delete</button>
                        </td>
                    </tr>
                `).join('');
            }
        }
        
        async function deleteUser(id) {
            if (!confirm('Delete this user?')) return;
            const res = await api(`/admin/users/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('User deleted');
                loadUsers();
                loadStats();
            }
        }
        
        document.getElementById('user-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                email: document.getElementById('user-email').value,
                password: document.getElementById('user-password').value,
                org_id: document.getElementById('user-org').value
            };
            
            const res = await api('/admin/users', { method: 'POST', body: data });
            if (res.ok) {
                showToast('User created');
                hideModal('user-modal');
                loadUsers();
                loadStats();
                e.target.reset();
            } else {
                const error = await res.json();
                showToast(error.detail || 'Failed to create user', true);
            }
        });
        
        // Licenses
        async function loadLicenses() {
            const res = await api('/admin/licenses');
            if (res.ok) {
                const licenses = await res.json();
                document.getElementById('licenses-table').innerHTML = licenses.map(lic => `
                    <tr>
                        <td>${lic.id}</td>
                        <td>${lic.user_email}</td>
                        <td><code>${lic.doc_id}</code></td>
                        <td>
                            <code>${lic.license_key || 'N/A'}</code>
                            ${lic.license_key ? `<button class="btn" onclick="copyKey('${lic.license_key}')">Copy</button>` : ''}
                        </td>
                        <td>${lic.max_devices}</td>
                        <td>
                            <button class="btn btn-danger" onclick="revokeLicense(${lic.id})">Revoke</button>
                        </td>
                    </tr>
                `).join('');
            }
        }
        
        function copyKey(key) {
            navigator.clipboard.writeText(key);
            showToast('License key copied!');
        }
        
        async function revokeLicense(id) {
            if (!confirm('Revoke this license?')) return;
            const res = await api(`/admin/licenses/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('License revoked');
                loadLicenses();
                loadStats();
            }
        }
        
        document.getElementById('license-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                user_id: parseInt(document.getElementById('license-user').value),
                doc_id: document.getElementById('license-doc').value,
                max_devices: parseInt(document.getElementById('license-max-devices').value)
            };
            
            const res = await api('/admin/licenses', { method: 'POST', body: data });
            if (res.ok) {
                const result = await res.json();
                hideModal('license-modal');
                loadLicenses();
                loadStats();
                e.target.reset();
                
                if (result.license_key) {
                    showToast(`License created! Key: ${result.license_key}`);
                    navigator.clipboard.writeText(result.license_key);
                } else {
                    showToast('License created');
                }
            } else {
                const error = await res.json();
                showToast(error.detail || 'Failed to create license', true);
            }
        });
        
        // Logout
        function logout() {
            localStorage.removeItem('token');
            window.location.href = '/login.html';
        }
        
        // Initialize
        loadStats();
    </script>
</body>
</html>'''

# Write file
with open('c:/Users/PRIYANSHU/OneDrive/Desktop/spdf/spdf-server/static/admin.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Generated admin.html with cosmic theme!")
