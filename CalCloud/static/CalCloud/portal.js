'use strict';

function displayDate(value) {
    return value ? `${value.slice(5, 7)}/${value.slice(8, 10)}/${value.slice(0, 4)}` : 'N/A';
}

function matchesFilters(row, filters) {
    return Object.entries(filters).every(([key, value]) => {
        if (!value) return true;
        if (key.endsWith('_min') || key.endsWith('_max')) {
            const date = row[key.slice(0, -4)];
            return !!date && (key.endsWith('_min') ? date >= value : date <= value);
        }
        if (key === 'active') return row.active === (value === 'yes');
        if (key === 'status' || key === 'condition') return row[key] === value;
        const text = Array.isArray(row[key]) ? row[key].join(' ') : String(row[key] ?? '');
        return text.toLowerCase().includes(value.trim().toLowerCase());
    });
}

function csvValue(value) {
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    const text = Array.isArray(value) ? value.join(', ') : String(value ?? '');
    return /^[=+\-@\t\r\n]/.test(text) ? "'" + text : text;
}

if (typeof module !== 'undefined') module.exports = {matchesFilters, displayDate, csvValue};
if (typeof document !== 'undefined') initializePortal();

function initializePortal() {
    const payload = JSON.parse(document.getElementById('portal-data').textContent);
    const assets = new Map((payload.assets || []).map(row => [row.barcode, row]));
    const dialog = document.getElementById('asset-dialog');
    const announce = text => { document.getElementById('live-message').textContent = text; };
    const textValue = value => typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value || 'N/A');

    function details(container, row, fields) {
        container.replaceChildren(...fields.map(([key, label]) => {
            const pair = document.createElement('div');
            const term = document.createElement('dt');
            const value = document.createElement('dd');
            term.textContent = label;
            value.textContent = key.endsWith('_date') ? displayDate(row[key]) : textValue(row[key]);
            pair.append(term, value);
            return pair;
        }));
    }

    function openAsset(barcode) {
        const row = assets.get(barcode);
        if (!row) return;
        document.getElementById('asset-identity').textContent = `Barcode ${row.barcode} · ${row.description}`;
        details(document.getElementById('asset-fields'), row, [
            ['active','Active'], ['disposition','Disposition'], ['barcode','Barcode'],
            ['legacy_barcode','Legacy Barcode'], ['status','Status'], ['description','Description'],
            ['brand','Brand'], ['model','Model #'], ['calibration_interval','Calibration Interval'],
            ['due_date','Due Date'], ['calibration_date','Calibration Date'],
            ['certificate_number','Current Calibration Certificate Number'], ['special_calibration','Special Calibration'],
            ['clean_due_date','Clean Due Date'], ['clean_date','Clean Date'], ['serial_number','Serial #'],
            ['asset_id','Asset ID'], ['location','Location'], ['sub_location','Sub-Location'], ['notes','Custom Notes'],
        ]);
        details(document.getElementById('asset-custom-fields'), row, [['operating_range','Operating Range'], ['condition','Condition']]);
        dialog.showModal();
    }

    document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('click', event => {
        const box = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
    });
    const mobileMenu = document.querySelector('.mobile-menu');
    mobileMenu.addEventListener('click', () => {
        const open = mobileMenu.getAttribute('aria-expanded') !== 'true';
        mobileMenu.setAttribute('aria-expanded', String(open));
        document.querySelector('.sidebar').classList.toggle('open', open);
    });
    document.addEventListener('click', event => document.querySelectorAll('details[open]').forEach(menu => {
        if (!menu.contains(event.target)) menu.open = false;
    }));
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') document.querySelectorAll('details[open]').forEach(menu => { menu.open = false; });
    });

    const tabs = [...document.querySelectorAll('[role="tab"]')];
    function selectTab(tab, focus = false) {
        tabs.forEach(item => {
            const selected = item === tab;
            item.setAttribute('aria-selected', String(selected));
            item.tabIndex = selected ? 0 : -1;
            document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
        });
        history.replaceState(null, '', '#' + tab.getAttribute('aria-controls'));
        if (focus) tab.focus();
    }
    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => selectTab(tab));
        tab.addEventListener('keydown', event => {
            if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
                event.preventDefault();
                const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + 1) % tabs.length;
                selectTab(tabs[next], true);
            }
        });
    });
    if (tabs.length && location.hash === '#faqs') selectTab(tabs[1]);

    const grid = document.getElementById('data-grid');
    if (grid) initializeGrid();
    if (document.getElementById('health-chart')) initializeCharts(payload);

    function initializeGrid() {
        const form = document.getElementById('filter-form');
        const query = new URLSearchParams(location.search);
        let applied = {};
        if (form) {
            for (const element of form.elements) {
                if (element.name && query.has(element.name)) element.value = query.get(element.name);
            }
            applied = Object.fromEntries(new FormData(form));
        }

        const col = (field, headerName, width = 145, options = {}) => ({field, headerName, width, ...options});
        const dateCol = (field, label) => col(field, label, 150, {
            cellDataType: 'dateString', filter: 'agDateColumnFilter',
            valueFormatter: params => displayDate(params.value),
        });
        const assetAction = {
            colId: 'actions', headerName: 'Actions', width: 90, minWidth: 80,
            filter: false, sortable: false, resizable: false, pinned: 'left',
            cellRenderer: params => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'grid-action';
                button.textContent = 'View';
                button.setAttribute('aria-label', `View asset ${params.data.barcode}`);
                button.addEventListener('click', () => openAsset(params.data.barcode));
                return button;
            },
        };
        const status = col('status', 'Status', 130, {
            valueFormatter: params => params.value?.toUpperCase() || 'N/A',
            cellClass: params => 'status-' + String(params.value).toLowerCase().replaceAll(' ', '-'),
        });
        const identifiers = [col('asset_id','Asset ID',135), col('barcode','Barcode',135)];
        const assetColumns = [assetAction, ...identifiers,
            col('legacy_barcode','Legacy Barcode',160), col('active','Active',95,{
                valueFormatter:p => textValue(p.value),filterValueGetter:p => textValue(p.data.active),cellDataType:false}),
            col('disposition','Disposition',140), status, dateCol('due_date','Due Date'), dateCol('calibration_date','Calibration Date'),
            col('calibration_interval','Calibration Interval',160), col('description','Description',260), col('brand','Brand',200),
            col('model','Model Number',150), col('serial_number','Serial #',140), col('location','Location',185),
            col('sub_location','Sub-Location',150), col('certificate_number','Calibration Certificate Number',225),
            dateCol('clean_due_date','Clean Due Date'), dateCol('clean_date','Clean Date'),
            col('operating_range','Operating Range',160), col('condition','Condition',185),
        ];
        let columns = assetColumns;
        if (payload.page === 'dashboard' || payload.page === 'recalls') {
            columns = [assetAction,...identifiers,status,dateCol('due_date','Due Date'),dateCol('calibration_date','Calibration Date')];
            if (payload.page === 'recalls') columns.push(...assetColumns.slice(9));
        } else if (payload.page === 'tracking_list') {
            columns = [{colId:'actions',headerName:'View',width:80,minWidth:70,pinned:'left',filter:false,sortable:false,
                cellRenderer: params => {
                    const link = document.createElement('a');
                    link.href = payload.tracker_base + encodeURIComponent(params.data.record_id) + '/';
                    link.className = 'grid-action';
                    link.textContent = 'View';
                    link.setAttribute('aria-label', `View tracking record ${params.data.record_id}`);
                    return link;
                }},
                col('record_id','Record #',120), col('ticket_number','Ticket #',130), col('contract','Contract #',145),
                col('item_number','Item #',120), col('paragraph','Paragraph',135), col('location','Shop/Location',215),dateCol('use_date','Use Date'),
            ];
        } else if (payload.page === 'changelog') {
            columns = [assetAction,col('barcode','Barcode',135),col('asset_id','Asset ID',140),col('serial_number','Serial Number',155),
                col('field','Field Changed',170),col('previous','Previous Value',220),col('new','New Value',310),
                dateCol('changed_at','Changed Date'),col('changed_by','Changed By',150)];
        } else if (payload.page === 'tracking_detail') {
            columns = [assetAction,...identifiers,col('description','Description',260),col('brand','Brand',190),col('model','Model Number',150),status];
        }
        const theme = agGrid.themeBalham.withParams({
            fontFamily:'Lato, Arial, sans-serif',fontSize:14,headerFontSize:14,rowHeight:40,headerHeight:44,
            foregroundColor:'#333333',backgroundColor:'#ffffff',headerBackgroundColor:'#f5f6f7',
            oddRowBackgroundColor:'#fafafa',borderColor:'#d5d8db',accentColor:'#e23b40',
        });
        const api = agGrid.createGrid(grid, {
            theme, rowData:payload.rows, columnDefs:columns,
            defaultColDef:{sortable:true,resizable:true,filter:'agTextColumnFilter',minWidth:85,
                valueFormatter:params => textValue(params.value)},
            getRowId:params => String(params.data.id || params.data.record_id || params.data.barcode),
            pagination:true,paginationPageSize:10,paginationPageSizeSelector:[10,25,50,100],
            // Small local exports are synchronous; avoid the 36.2 exporting-overlay wait.
            suppressOverlays:['exporting'],
            suppressCellFocus:false,animateRows:!matchMedia('(prefers-reduced-motion: reduce)').matches,
            isExternalFilterPresent:() => Object.values(applied).some(Boolean),
            doesExternalFilterPass:node => matchesFilters(node.data, applied),
            overlayNoRowsTemplate:'<span>No records match your filters.</span>',
            onFilterChanged:event => announce(`${event.api.getDisplayedRowCount()} matching records`),
        });
        if (Object.values(applied).some(Boolean)) api.onFilterChanged();

        if (form) {
            const toggle = document.getElementById('additional-filters');
            function expand(open) {
                toggle.setAttribute('aria-expanded', String(open));
                document.querySelectorAll('.advanced-field').forEach(field => { field.hidden = !open; });
            }
            if ([...document.querySelectorAll('.advanced-field input,.advanced-field select')].some(input => input.value)) expand(true);
            toggle.addEventListener('click', () => expand(toggle.getAttribute('aria-expanded') !== 'true'));
            function updateUrl() {
                const url = new URL(location.href);
                for (const [key,value] of Object.entries(applied)) {
                    if (value) url.searchParams.set(key,value); else url.searchParams.delete(key);
                }
                history.replaceState(null,'',url);
            }
            form.addEventListener('submit', event => {
                event.preventDefault();
                const filters = Object.fromEntries(new FormData(form));
                const error = document.getElementById('filter-error');
                const invalidRange = Object.keys(filters).find(key => key.endsWith('_min') && filters[key] && filters[key.slice(0,-4)+'_max'] && filters[key] > filters[key.slice(0,-4)+'_max']);
                error.hidden = !invalidRange;
                if (invalidRange) {
                    error.textContent = 'The start of a date range must be on or before its end.';
                    form.elements[invalidRange].focus();
                    return;
                }
                applied = filters;
                updateUrl();
                api.onFilterChanged();
                api.paginationGoToFirstPage();
            });
            form.addEventListener('reset', () => {
                applied = Object.fromEntries([...form.elements].filter(input => input.name).map(input => [input.name,'']));
                document.getElementById('filter-error').hidden = true;
                api.setFilterModel(null);
                api.onFilterChanged();
                api.paginationGoToFirstPage();
                updateUrl();
            });
        }
        const quickSearch = document.getElementById('quick-search');
        if (quickSearch) {
            quickSearch.addEventListener('input', () => api.setGridOption('quickFilterText',quickSearch.value));
            document.getElementById('reset-grid').addEventListener('click', () => {
                quickSearch.value='';api.setGridOption('quickFilterText','');api.setFilterModel(null);api.resetColumnState();api.paginationGoToFirstPage();
            });
        }
        document.querySelectorAll('[data-export]').forEach(button => button.addEventListener('click', () => {
            api.exportDataAsCsv({
                fileName:`calcloud-${payload.page.replaceAll('_','-')}-demo.csv`,
                columnKeys:columns.filter(column => column.field).map(column => column.field),
                exportedRows:'filteredAndSorted',
                processCellCallback:params => csvValue(params.column.getColDef().cellDataType === 'dateString' ? displayDate(params.value) : params.value),
            });
            announce(`Exported ${api.getDisplayedRowCount()} matching records.`);
        }));
    }
}

function initializeCharts(payload) {
    Chart.defaults.font.family='Lato, Arial, sans-serif';
    Chart.defaults.color='#686868';
    const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
    const countLabels={
        id:'healthCounts',
        afterDatasetsDraw(chart) {
            const {ctx}=chart;
            ctx.save();ctx.font='bold 12px Lato, Arial';ctx.textAlign='center';ctx.textBaseline='middle';
            chart.getDatasetMeta(0).data.forEach((arc,index) => {
                const angle=(arc.startAngle+arc.endAngle)/2;
                const x=arc.x+Math.cos(angle)*(arc.outerRadius+3);
                const y=arc.y+Math.sin(angle)*(arc.outerRadius+3);
                ctx.beginPath();ctx.arc(x,y,16,0,Math.PI*2);ctx.fillStyle='#000';ctx.fill();
                ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle='#fff';
                ctx.fillText(payload.health[index].count,x,y);
            });ctx.restore();
        },
    };
    new Chart(document.getElementById('health-chart'),{
        type:'doughnut',data:{labels:payload.health.map(row=>row.label),datasets:[{data:payload.health.map(row=>row.count),backgroundColor:payload.health.map(row=>row.color),borderColor:'#fff',borderWidth:2}]},
        options:{responsive:true,maintainAspectRatio:false,cutout:'49%',layout:{padding:24},animation:reducedMotion?false:{duration:300},plugins:{legend:{display:false},tooltip:{enabled:true}}},plugins:[countLabels],
    });
    for (const name of ['services','tolerance']) {
        const canvas=document.getElementById(name+'-chart');
        if (!canvas) continue;
        const serviceLabels = {id:'serviceLabels',afterDatasetsDraw(chart) {
            if (name !== 'services') return;
            const {ctx}=chart;
            ctx.save();ctx.font='11px Lato, Arial';ctx.fillStyle='#686868';ctx.textAlign='center';
            chart.data.datasets.forEach((dataset,index) => chart.getDatasetMeta(index).data.forEach((bar,i) => {
                if (dataset.data[i] || chart.width > 600) ctx.fillText(dataset.data[i],bar.x,bar.y-8);
            }));
            ctx.restore();
        }};
        new Chart(canvas,{
            type:'bar',data:{labels:payload.charts.months,datasets:payload.charts[name]},
            plugins:[serviceLabels],
            options:{responsive:true,maintainAspectRatio:false,animation:reducedMotion?false:{duration:300},
                layout:{padding:{top:12}},plugins:{legend:{position:'bottom',labels:{boxWidth:32,font:{size:11}}}},
                scales:{y:{beginAtZero:true,title:{display:true,text:'Assets'},ticks:{precision:0},grid:{color:'#dedede'}},x:{ticks:{maxRotation:60,minRotation:25,font:{size:11}},grid:{color:'#e8e8e8'}}}},
        });
    }
}
