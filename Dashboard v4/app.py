from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import re
from pathlib import Path
import os
import sys

app = FastAPI()

# ========== CONFIGURATION ==========
EXCEL_FILENAME = "Innovations_Updated.xlsx"  # Your exact filename
IMAGES_FOLDER = "Images"  # Your images folder

# ========== DATA LOADING ==========
def load_data():
    """Load and process Excel data"""
    # Try multiple possible locations for the Excel file
    possible_paths = [
        Path.cwd() / EXCEL_FILENAME,
        Path(__file__).parent / EXCEL_FILENAME,
        Path("/app") / EXCEL_FILENAME,  # For Render
    ]
    
    excel_path = None
    for path in possible_paths:
        if path.exists():
            excel_path = path
            break
    
    if not excel_path:
        print(f"❌ Excel file not found. Tried: {[str(p) for p in possible_paths]}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   Files in directory: {list(Path.cwd().glob('*'))}")
        return None
    
    try:
        print(f"✅ Loading Excel from: {excel_path}")
        df = pd.read_excel(excel_path, engine="openpyxl")
        print(f"✅ Loaded Excel with {len(df)} rows, {len(df.columns)} columns")
        
        # Clean columns
        df.columns = [str(col).strip() for col in df.columns]
        
        # Find required columns
        cat_col = None
        brand_col = None
        proj_col = None
        status_col = None
        gm_col = None
        ito_col = None
        yr_col = None
        dp_col = None
        yr26_col = None
        fy_col = None
        trial_col = None
        site_col = None
        stability_col = None
        production_col = None
        primaries_col = None
        scope_col = None
        desc_col = None
        risks_col = None
        updates_col = None
        sku_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'category' in col_lower or 'type' in col_lower:
                cat_col = col
            elif 'brand' in col_lower:
                brand_col = col
            elif 'project' in col_lower:
                proj_col = col
            elif 'status' in col_lower:
                status_col = col
            elif 'gm' in col_lower and 'gm%' in col_lower:
                gm_col = col
            elif 'ito' in col_lower:
                ito_col = col
            elif 'yr' in col_lower and 'yr-26' not in col_lower and '1st' not in col_lower:
                yr_col = col
            elif 'dp vol' in col_lower:
                dp_col = col
            elif 'yr-26' in col_lower or 'yr 26' in col_lower:
                yr26_col = col
            elif '1st fy' in col_lower or '1st year' in col_lower:
                fy_col = col
            elif 'trial' in col_lower:
                trial_col = col
            elif 'site' in col_lower:
                site_col = col
            elif 'stability' in col_lower:
                stability_col = col
            elif 'production' in col_lower:
                production_col = col
            elif 'primaries' in col_lower:
                primaries_col = col
            elif 'scope' in col_lower:
                scope_col = col
            elif 'description' in col_lower or 'desciption' in col_lower:
                desc_col = col
            elif 'risk' in col_lower:
                risks_col = col
            elif 'update' in col_lower:
                updates_col = col
            elif 'sku' in col_lower:
                sku_col = col
        
        print(f"📊 Found columns: Category='{cat_col}', Brand='{brand_col}', Project='{proj_col}', Status='{status_col}'")
        
        if not cat_col or not brand_col or not proj_col:
            print("❌ Required columns not found")
            print(f"   Available columns: {list(df.columns)}")
            return None
        
        # Forward fill
        df[cat_col] = df[cat_col].ffill()
        df[brand_col] = df[brand_col].ffill()
        df[proj_col] = df[proj_col].ffill()
        
        # Status logic
        def get_status(val):
            if pd.isna(val) or val == "":
                return "No Status"
            s = str(val).lower().strip()
            if 'on-track' in s or 'on track' in s:
                return "On Track"
            elif 'landed' in s or 'done' in s:
                return "Launched"
            elif 'delayed' in s or 'delay' in s:
                return "Delayed"
            elif 'kick' in s or 'kick-off' in s:
                return "Upcoming"
            elif 'tbd' in s or 'not started' in s:
                return "Upcoming"
            else:
                return "Upcoming"
        
        if status_col:
            df['_status'] = df[status_col].apply(get_status)
        else:
            df['_status'] = "No Status"
        
        # Fill empty values
        df = df.fillna("")
        
        print(f"✅ Data processed successfully")
        
        return {
            'df': df,
            'cat_col': cat_col,
            'brand_col': brand_col,
            'proj_col': proj_col,
            'gm_col': gm_col,
            'ito_col': ito_col,
            'yr_col': yr_col,
            'dp_col': dp_col,
            'yr26_col': yr26_col,
            'fy_col': fy_col,
            'trial_col': trial_col,
            'site_col': site_col,
            'stability_col': stability_col,
            'production_col': production_col,
            'primaries_col': primaries_col,
            'scope_col': scope_col,
            'desc_col': desc_col,
            'risks_col': risks_col,
            'updates_col': updates_col,
            'sku_col': sku_col
        }
    except Exception as e:
        print(f"❌ Error loading Excel: {e}")
        return None

# Load data on startup
print("=" * 50)
print("🚀 Innovation Dashboard Starting...")
print(f"📁 Current Directory: {Path.cwd()}")
print(f"📄 Looking for: {EXCEL_FILENAME}")
print(f"📁 Images folder: {IMAGES_FOLDER}")
print("=" * 50)

data = load_data()

if data:
    print("✅ Data loaded successfully!")
else:
    print("❌ Failed to load data - check Excel file")

# ========== SERVE IMAGES ==========
# Create images folder if it doesn't exist
images_path = Path(IMAGES_FOLDER)
if not images_path.exists():
    images_path.mkdir(exist_ok=True)
    print(f"📁 Created Images folder at: {images_path.absolute()}")

# Mount images folder for serving
if images_path.exists():
    app.mount("/images", StaticFiles(directory=str(images_path)), name="images")
    print(f"📁 Serving images from: {images_path.absolute()}")

# ========== API ENDPOINTS ==========
@app.get("/api/data")
def get_data():
    if not data:
        return {"error": "No data loaded. Please check Excel file."}
    
    df = data['df']
    cat_col = data['cat_col']
    brand_col = data['brand_col']
    proj_col = data['proj_col']
    
    # KPIs
    total = len(df[proj_col].dropna().unique())
    launched = len(df[df['_status'] == 'Launched'])
    on_track = len(df[df['_status'] == 'On Track'])
    upcoming = len(df[df['_status'] == 'Upcoming'])
    delayed = len(df[df['_status'] == 'Delayed'])
    
    # Categories
    categories = {}
    for cat in df[cat_col].dropna().unique():
        if pd.isna(cat) or cat == "":
            continue
        cat_df = df[df[cat_col] == cat]
        categories[cat] = {
            'total': len(cat_df[proj_col].dropna().unique()),
            'brands': cat_df[brand_col].dropna().unique().tolist(),
            'launched': len(cat_df[cat_df['_status'] == 'Launched']),
            'on_track': len(cat_df[cat_df['_status'] == 'On Track']),
            'upcoming': len(cat_df[cat_df['_status'] == 'Upcoming']),
            'delayed': len(cat_df[cat_df['_status'] == 'Delayed'])
        }
    
    # Projects
    projects = []
    for _, row in df.iterrows():
        proj_name = row[proj_col]
        if pd.isna(proj_name) or proj_name == "":
            continue
        
        # Try to find image
        image_name = None
        images_path = Path(IMAGES_FOLDER)
        if images_path.exists():
            # Try exact match with common extensions
            for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG', 'gif', 'GIF']:
                # Try exact match
                img_path = images_path / f"{proj_name}.{ext}"
                if img_path.exists():
                    image_name = f"{proj_name}.{ext}"
                    break
                # Try with underscores instead of spaces
                img_path = images_path / f"{proj_name.replace(' ', '_')}.{ext}"
                if img_path.exists():
                    image_name = f"{proj_name.replace(' ', '_')}.{ext}"
                    break
                # Try with hyphens instead of spaces
                img_path = images_path / f"{proj_name.replace(' ', '-')}.{ext}"
                if img_path.exists():
                    image_name = f"{proj_name.replace(' ', '-')}.{ext}"
                    break
                # Try with underscores and hyphens
                img_path = images_path / f"{proj_name.replace(' ', '_').replace('-', '_')}.{ext}"
                if img_path.exists():
                    image_name = f"{proj_name.replace(' ', '_').replace('-', '_')}.{ext}"
                    break
        
        # Get metrics
        gm = row.get(data['gm_col'], '') if data['gm_col'] else ''
        ito = row.get(data['ito_col'], '') if data['ito_col'] else ''
        
        projects.append({
            'name': proj_name,
            'category': row[cat_col] if not pd.isna(row[cat_col]) else "",
            'brand': row[brand_col] if not pd.isna(row[brand_col]) else "",
            'status': row['_status'],
            'image': f"/images/{image_name}" if image_name else None,
            'gm': str(gm) if gm else 'N/A',
            'ito': str(ito) if ito else 'N/A'
        })
    
    return {
        'kpis': {
            'total': total,
            'launched': launched,
            'on_track': on_track,
            'upcoming': upcoming,
            'delayed': delayed
        },
        'categories': categories,
        'projects': projects
    }

@app.get("/api/project/{project_name}")
def get_project_detail(project_name: str):
    """Get detailed information for a specific project"""
    if not data:
        return {"error": "No data loaded"}
    
    df = data['df']
    proj_col = data['proj_col']
    
    # Find the project
    project_row = None
    for _, row in df.iterrows():
        if row[proj_col] == project_name:
            project_row = row
            break
    
    if project_row is None:
        return {"error": "Project not found"}
    
    # Build project details
    details = {
        'name': project_name,
        'category': project_row.get(data['cat_col'], ''),
        'brand': project_row.get(data['brand_col'], ''),
        'status': project_row.get('_status', 'No Status'),
        'scope': project_row.get(data['scope_col'], '') if data['scope_col'] else '',
        'description': project_row.get(data['desc_col'], '') if data['desc_col'] else '',
        'sku_format': project_row.get(data['sku_col'], '') if data['sku_col'] else '',
        'risks': project_row.get(data['risks_col'], '') if data['risks_col'] else '',
        'updates': project_row.get(data['updates_col'], '') if data['updates_col'] else '',
        'metrics': {},
        'execution': {}
    }
    
    # Business metrics
    metric_fields = [
        ('GM', data['gm_col']),
        ('iTO(mn)', data['ito_col']),
        ('Yr', data['yr_col']),
        ('DP Vol', data['dp_col']),
        ('Yr-26', data['yr26_col']),
        ('1st FY', data['fy_col'])
    ]
    
    for label, col in metric_fields:
        if col:
            value = project_row.get(col, 'N/A')
            if pd.isna(value) or value == "":
                value = 'N/A'
            details['metrics'][label] = str(value)
    
    # Execution status
    exec_fields = [
        ('Trial Status', data['trial_col']),
        ('Site', data['site_col']),
        ('Stability', data['stability_col']),
        ('Production', data['production_col']),
        ('Primaries', data['primaries_col'])
    ]
    
    for label, col in exec_fields:
        if col:
            value = project_row.get(col, 'N/A')
            if pd.isna(value) or value == "":
                value = 'N/A'
            details['execution'][label] = str(value)
    
    # Find image
    image_name = None
    images_path = Path(IMAGES_FOLDER)
    if images_path.exists():
        for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG']:
            img_path = images_path / f"{project_name}.{ext}"
            if img_path.exists():
                image_name = f"{project_name}.{ext}"
                break
            img_path = images_path / f"{project_name.replace(' ', '_')}.{ext}"
            if img_path.exists():
                image_name = f"{project_name.replace(' ', '_')}.{ext}"
                break
    
    details['image'] = f"/images/{image_name}" if image_name else None
    
    return details

@app.get("/api/refresh")
def refresh_data():
    """Refresh data from Excel"""
    global data
    data = load_data()
    if data:
        return {"message": "Data refreshed successfully", "status": "success"}
    else:
        return {"error": "Failed to load data", "status": "error"}

@app.get("/api/status")
def get_status():
    """Check if the API is running"""
    return {
        "status": "running",
        "data_loaded": data is not None,
        "excel_file": EXCEL_FILENAME,
        "images_folder": IMAGES_FOLDER,
        "current_directory": str(Path.cwd())
    }

# ========== SINGLE HTML PAGE ==========
@app.get("/", response_class=HTMLResponse)
def serve_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Innovation Portfolio Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Georgia, serif;
            background: #F4F7FB;
            color: #1A2A3A;
            padding: 20px;
        }
        .header {
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 28px;
            font-weight: 700;
        }
        .header p {
            color: #4A6A8A;
            font-size: 14px;
            margin-top: 4px;
        }
        
        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .refresh-btn {
            padding: 10px 24px;
            background: #245B82;
            color: white;
            border: none;
            border-radius: 6px;
            font-family: Georgia, serif;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .refresh-btn:hover {
            background: #2F80C0;
        }
        .refresh-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-online { background: #DCFCE7; color: #2E9B68; }
        .status-offline { background: #FEE2E2; color: #D9534F; }
        
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }
        .kpi-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #E5E7EB;
        }
        .kpi-card .label {
            font-size: 12px;
            color: #4A6A8A;
        }
        .kpi-card .value {
            font-size: 28px;
            font-weight: 700;
        }
        .kpi-card .accent {
            height: 3px;
            width: 40px;
            margin-top: 8px;
            border-radius: 2px;
        }
        
        .chart-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #E5E7EB;
        }
        .chart-card h3 {
            font-size: 16px;
            margin-bottom: 15px;
            font-weight: 700;
        }
        
        .bar-chart {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .bar-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .bar-label {
            min-width: 80px;
            font-size: 13px;
            font-weight: 600;
        }
        .bar-track {
            flex: 1;
            height: 20px;
            background: #F0F4F8;
            border-radius: 4px;
            overflow: hidden;
        }
        .bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s;
        }
        .bar-value {
            font-size: 13px;
            font-weight: 600;
            min-width: 30px;
            text-align: right;
        }
        
        .status-bar-group {
            margin-bottom: 12px;
        }
        .status-bar-group .label {
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 2px;
        }
        .status-stack {
            display: flex;
            height: 18px;
            border-radius: 4px;
            overflow: hidden;
        }
        .status-stack-item {
            height: 100%;
        }
        .status-legend {
            display: flex;
            gap: 12px;
            font-size: 10px;
            margin-top: 2px;
            color: #4A6A8A;
            flex-wrap: wrap;
        }
        
        .project-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 15px;
        }
        .project-card {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #E5E7EB;
            cursor: pointer;
            transition: all 0.2s;
        }
        .project-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        .project-card .image {
            width: 100%;
            height: 150px;
            object-fit: cover;
            background: #F8FAFC;
        }
        .project-card .image-placeholder {
            width: 100%;
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #F8FAFC;
            color: #CBD5E1;
            font-size: 40px;
        }
        .project-card .info {
            padding: 15px;
        }
        .project-card .name {
            font-weight: 700;
            font-size: 14px;
        }
        .project-card .meta {
            font-size: 12px;
            color: #4A6A8A;
            margin: 4px 0;
        }
        .project-card .status {
            font-size: 13px;
            font-weight: 600;
        }
        
        .loading {
            text-align: center;
            padding: 60px;
            color: #4A6A8A;
        }
        .error-box {
            text-align: center;
            padding: 40px;
            background: #FEF2F2;
            border: 1px solid #FEE2E2;
            border-radius: 8px;
            color: #D9534F;
        }
        
        .section-title {
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 18px;
            font-weight: 700;
        }
        
        @media (max-width: 768px) {
            .chart-grid { grid-template-columns: 1fr; }
            .top-bar { flex-direction: column; align-items: stretch; }
        }
    </style>
</head>
<body>
    <div id="app">
        <div class="loading">Loading Dashboard...</div>
    </div>

    <script>
        let currentData = null;
        
        async function loadData() {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="loading">Loading Dashboard...</div>';
            
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                currentData = data;
                
                if (data.error) {
                    app.innerHTML = `
                        <div class="error-box">
                            <h2>⚠️ Error Loading Data</h2>
                            <p>${data.error}</p>
                            <p style="margin-top:10px;font-size:12px;color:#4A6A8A;">
                                Make sure 'Innovations_Updated.xlsx' is uploaded to the server.
                            </p>
                        </div>
                    `;
                    return;
                }
                
                renderDashboard(data);
            } catch (err) {
                app.innerHTML = `
                    <div class="error-box">
                        <h2>⚠️ Connection Error</h2>
                        <p>${err.message}</p>
                        <p style="margin-top:10px;font-size:12px;color:#4A6A8A;">
                            Make sure the server is running.
                        </p>
                    </div>
                `;
            }
        }
        
        async function refreshData() {
            const btn = document.querySelector('.refresh-btn');
            btn.disabled = true;
            btn.textContent = 'Refreshing...';
            
            try {
                await fetch('/api/refresh');
                await loadData();
            } catch (err) {
                alert('Refresh failed: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 Refresh Data';
            }
        }
        
        function renderDashboard(data) {
            const { kpis, categories, projects } = data;
            
            let html = `
                <div class="header">
                    <div class="top-bar">
                        <div>
                            <h1>📊 Innovation Portfolio Dashboard</h1>
                            <p>Real-time overview of all projects</p>
                        </div>
                        <div>
                            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
                        </div>
                    </div>
                </div>
            `;
            
            // KPI Cards
            html += `<div class="kpi-grid">`;
            const kpiData = [
                { label: 'Total Projects', value: kpis.total, color: '#2F80C0' },
                { label: 'Launched', value: kpis.launched, color: '#2E9B68' },
                { label: 'On Track', value: kpis.on_track, color: '#2F80C0' },
                { label: 'Upcoming', value: kpis.upcoming, color: '#D99A28' },
                { label: 'Delayed', value: kpis.delayed, color: '#D9534F' }
            ];
            kpiData.forEach(k => {
                html += `
                    <div class="kpi-card">
                        <div class="label">${k.label}</div>
                        <div class="value" style="color: ${k.color}">${k.value}</div>
                        <div class="accent" style="background: ${k.color}"></div>
                    </div>
                `;
            });
            html += `</div>`;
            
            // Category Charts
            html += `<div class="chart-grid">`;
            
            // Category Distribution
            html += `
                <div class="chart-card">
                    <h3>📊 Category Distribution</h3>
                    <div class="bar-chart">
            `;
            const maxCat = Math.max(...Object.values(categories).map(c => c.total), 1);
            const catColors = ['#2F80C0', '#2E9B68', '#D99A28', '#D9534F', '#8A9BA8'];
            let i = 0;
            for (const [name, cat] of Object.entries(categories)) {
                const pct = (cat.total / maxCat) * 100;
                const color = catColors[i % catColors.length];
                html += `
                    <div class="bar-row">
                        <span class="bar-label">${name}</span>
                        <div class="bar-track">
                            <div class="bar-fill" style="width: ${Math.max(5, pct)}%; background: ${color}"></div>
                        </div>
                        <span class="bar-value">${cat.total}</span>
                    </div>
                `;
                i++;
            }
            html += `</div></div>`;
            
            // Category Status
            html += `
                <div class="chart-card">
                    <h3>📈 Category Status Breakdown</h3>
            `;
            for (const [name, cat] of Object.entries(categories)) {
                const total = cat.total || 1;
                const launched = (cat.launched / total) * 100;
                const onTrack = (cat.on_track / total) * 100;
                const upcoming = (cat.upcoming / total) * 100;
                const delayed = (cat.delayed / total) * 100;
                html += `
                    <div class="status-bar-group">
                        <div class="label">${name}</div>
                        <div class="status-stack">
                            ${launched > 0 ? `<div class="status-stack-item" style="width: ${launched}%; background: #2E9B68;"></div>` : ''}
                            ${onTrack > 0 ? `<div class="status-stack-item" style="width: ${onTrack}%; background: #2F80C0;"></div>` : ''}
                            ${upcoming > 0 ? `<div class="status-stack-item" style="width: ${upcoming}%; background: #D99A28;"></div>` : ''}
                            ${delayed > 0 ? `<div class="status-stack-item" style="width: ${delayed}%; background: #D9534F;"></div>` : ''}
                        </div>
                        <div class="status-legend">
                            ${cat.launched > 0 ? `<span>✅ ${cat.launched}</span>` : ''}
                            ${cat.on_track > 0 ? `<span>🔵 ${cat.on_track}</span>` : ''}
                            ${cat.upcoming > 0 ? `<span>🟠 ${cat.upcoming}</span>` : ''}
                            ${cat.delayed > 0 ? `<span>🔴 ${cat.delayed}</span>` : ''}
                        </div>
                    </div>
                `;
            }
            html += `</div></div>`;
            html += `</div>`;
            
            // Projects
            html += `
                <div class="section-title">📋 All Projects (${projects.length})</div>
                <div class="project-grid">
            `;
            
            projects.forEach(p => {
                const status = p.status || 'No Status';
                const color = status === 'Launched' ? '#2E9B68' :
                             status === 'On Track' ? '#2F80C0' :
                             status === 'Upcoming' ? '#D99A28' :
                             status === 'Delayed' ? '#D9534F' : '#8A9BA8';
                
                const imageHtml = p.image ? 
                    `<img class="image" src="${p.image}" alt="${p.name}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">` :
                    '';
                const placeholderHtml = !p.image ? 
                    `<div class="image-placeholder">📷</div>` :
                    `<div class="image-placeholder" style="display:none;">📷</div>`;
                
                html += `
                    <div class="project-card">
                        ${imageHtml}
                        ${placeholderHtml}
                        <div class="info">
                            <div class="name">${p.name}</div>
                            <div class="meta">${p.category} • ${p.brand}</div>
                            <div class="status" style="color: ${color}">● ${status}</div>
                        </div>
                    </div>
                `;
            });
            
            html += `</div>`;
            
            document.getElementById('app').innerHTML = html;
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 5 minutes
        setInterval(loadData, 300000);
    </script>
</body>
</html>
    """

# ========== HEALTH CHECK FOR RENDER ==========
@app.get("/health")
def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "data_loaded": data is not None}

# ========== RUN THE APP ==========
if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 8000))
    
    print("=" * 50)
    print("🚀 Starting Innovation Dashboard...")
    print(f"📍 Port: {port}")
    print(f"📁 Directory: {Path.cwd()}")
    print(f"📄 Excel file: {EXCEL_FILENAME}")
    print(f"📁 Images folder: {IMAGES_FOLDER}")
    print("=" * 50)
    print("🌐 Open in browser: http://localhost:8000")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=port)