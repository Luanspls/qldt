// ===== CONFIGURATION =====
const CONFIG = {
    DEBOUNCE_DELAY: 300,
    THROTTLE_DELAY: 100,
    API_TIMEOUT: 10000,
    LAZY_LOAD_DELAY: 100,
    CACHE_TTL: 5 * 60 * 1000, // 5 minutes
    MAX_ROWS_VISIBLE: 50,
    MOBILE_BREAKPOINT: 768
};

// ===== STATE MANAGEMENT =====
class AppState {
    constructor() {
        this.data = {
            subjects: window.APP_DATA.initialData || [],
            departments: window.APP_DATA.departments || [],
            subjectGroups: window.APP_DATA.subjectGroups || [],
            curricula: window.APP_DATA.curricula || [],
            courses: window.APP_DATA.courses || [],
            subjectTypes: window.APP_DATA.subjectTypes || [],
            majors: window.APP_DATA.majors || []
        };
        
        this.filters = {
            departmentId: null,
            subjectGroupId: null,
            curriculumId: null,
            courseId: null
        };
        
        this.cache = new Map();
        this.isMobile = window.APP_CONFIG.isMobile;
        this.isInitialized = false;
    }
    
    updateFilter(key, value) {
        this.filters[key] = value;
        this.saveToSessionStorage();
    }
    
    saveToSessionStorage() {
        try {
            sessionStorage.setItem('app_filters', JSON.stringify(this.filters));
        } catch (e) {
            console.warn('Failed to save to sessionStorage:', e);
        }
    }
    
    loadFromSessionStorage() {
        try {
            const saved = sessionStorage.getItem('app_filters');
            if (saved) {
                this.filters = JSON.parse(saved);
            }
        } catch (e) {
            console.warn('Failed to load from sessionStorage:', e);
        }
    }
}

// ===== PERFORMANCE UTILITIES =====
class PerformanceUtils {
    static debounce(func, wait = CONFIG.DEBOUNCE_DELAY) {
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
    
    static throttle(func, limit = CONFIG.THROTTLE_DELAY) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    static lazyLoad(callback, delay = CONFIG.LAZY_LOAD_DELAY) {
        return setTimeout(callback, delay);
    }
    
    static measurePerformance(label, callback) {
        const isDevelopment = window.location.hostname === 'localhost' || 
                         window.location.hostname === '127.0.0.1' ||
                         window.location.hostname.includes('local');
        
        if (isDevelopment) {
            console.time(label);
            const result = callback();
            console.timeEnd(label);
            return result;
        }
        return callback();
    }
}

// ===== API SERVICE =====
class ApiService {
    constructor() {
        this.baseUrl = '';
        this.csrfToken = window.APP_CONFIG.csrfToken;
    }
    
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    ...options.headers
                }
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }
    
    async getSubjects(filters = {}) {
        const cacheKey = `subjects_${JSON.stringify(filters)}`;
        
        // Check cache first
        if (appState.cache.has(cacheKey)) {
            const cached = appState.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < CONFIG.CACHE_TTL) {
                return cached.data;
            }
        }
        
        // Build query params
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });
        
        try {
            const data = await this.fetchWithTimeout(`/api/subjects/?${params}`);
            
            // Cache the result
            appState.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            return data;
        } catch (error) {
            console.error('Failed to fetch subjects:', error);
            return [];
        }
    }
    
    async updateSubject(id, changes) {
        try {
            return await this.fetchWithTimeout(`/train-program/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(changes)
            });
        } catch (error) {
            console.error('Failed to update subject:', error);
            throw error;
        }
    }
    
    async deleteSubject(id) {
        try {
            return await this.fetchWithTimeout(`/train-program/${id}/`, {
                method: 'DELETE'
            });
        } catch (error) {
            console.error('Failed to delete subject:', error);
            throw error;
        }
    }
}

// ===== TABLE MANAGER =====
class TableManager {
    constructor() {
        this.container = document.querySelector('.table-container');
        this.tableBody = null;
        this.visibleRows = new Set();
        this.observer = null;
    }
    
    init() {
        this.tableBody = this.container.querySelector('tbody');
        if (!this.tableBody) {
            this.tableBody = document.createElement('tbody');
            this.container.querySelector('table').appendChild(this.tableBody);
        }
        
        this.setupVirtualScroll();
    }
    
    render(data) {
        PerformanceUtils.measurePerformance('renderTable', () => {
            if (!data || data.length === 0) {
                this.showEmptyState();
                return;
            }
            
            // Limit rows for mobile performance
            const displayData = appState.isMobile 
                ? data.slice(0, CONFIG.MAX_ROWS_VISIBLE)
                : data;
            
            // Use DocumentFragment for better performance
            const fragment = document.createDocumentFragment();
            
            displayData.forEach((item, index) => {
                const row = this.createRow(item, index);
                fragment.appendChild(row);
                this.visibleRows.add(row);
            });
            
            // Clear and append
            this.tableBody.innerHTML = '';
            this.tableBody.appendChild(fragment);
            
            // Show load more button if needed
            if (appState.isMobile && data.length > CONFIG.MAX_ROWS_VISIBLE) {
                this.showLoadMoreButton(data.length - CONFIG.MAX_ROWS_VISIBLE);
            }
        });
    }
    
    createRow(item, index) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 transition-colors duration-150';
        row.dataset.id = item.id;
        
        // Create cells with optimized content
        const cells = [
            this.createCell(index + 1, 'text-center col-tt'),
            this.createEditableCell(item.ma_mon_hoc || '', 'code', item.id, 'col-ma'),
            this.createEditableCell(item.ten_mon_hoc || '', 'name', item.id, 'col-ten wrap-text'),
            this.createEditableCell(item.so_tin_chi || 0, 'credits', item.id, 'text-center col-tinchi', 'number'),
            this.createEditableCell(item.tong_so_gio || 0, 'total_hours', item.id, 'text-center col-gio', 'number'),
            // Add more cells as needed
        ];
        
        cells.forEach(cell => row.appendChild(cell));
        
        // Add action buttons
        const actionCell = this.createActionCell(item.id);
        row.appendChild(actionCell);
        
        return row;
    }
    
    createCell(content, className = '', type = 'text') {
        const cell = document.createElement('td');
        cell.className = `px-2 py-2 ${className}`;
        
        if (type === 'number') {
            const input = document.createElement('input');
            input.type = 'number';
            input.value = content;
            input.className = 'w-full bg-transparent border-none text-center';
            input.readOnly = true;
            cell.appendChild(input);
        } else {
            cell.textContent = content;
        }
        
        return cell;
    }
    
    createEditableCell(value, field, id, className = '', type = 'text') {
        const cell = document.createElement('td');
        cell.className = `px-2 py-2 ${className}`;
        
        const input = document.createElement('input');
        input.type = type;
        input.value = value;
        input.className = 'editable w-full bg-transparent border-none';
        input.dataset.field = field;
        input.dataset.id = id;
        input.dataset.original = value;
        input.readOnly = true;
        
        cell.appendChild(input);
        return cell;
    }
    
    createActionCell(id) {
        const cell = document.createElement('td');
        cell.className = 'px-2 py-2 text-center col-thaotac';
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn-edit text-blue-600 hover:text-blue-800 mr-2';
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.dataset.id = id;
        editBtn.title = 'Sửa';
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-delete text-red-600 hover:text-red-800';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.dataset.id = id;
        deleteBtn.title = 'Xóa';
        
        cell.appendChild(editBtn);
        cell.appendChild(deleteBtn);
        return cell;
    }
    
    showEmptyState() {
        this.tableBody.innerHTML = `
            <tr>
                <td colspan="19" class="px-4 py-8 text-center text-gray-500">
                    <i class="fas fa-inbox text-4xl mb-2 opacity-50"></i>
                    <p class="text-lg">Không có dữ liệu môn học</p>
                </td>
            </tr>
        `;
    }
    
    showLoadMoreButton(remaining) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td colspan="19" class="px-4 py-3 text-center">
                <button class="btn-load-more text-blue-600 hover:text-blue-800 font-medium">
                    <i class="fas fa-chevron-down mr-1"></i>
                    Xem thêm ${remaining} môn học
                </button>
            </td>
        `;
        this.tableBody.appendChild(row);
    }
    
    setupVirtualScroll() {
        if (!('IntersectionObserver' in window)) return;
        
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    this.observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '50px',
            threshold: 0.1
        });
    }
}

// ===== MODAL MANAGER =====
class ModalManager {
    constructor() {
        this.modals = new Map();
        this.currentModal = null;
    }
    
    async loadModal(name) {
        if (this.modals.has(name)) {
            return this.modals.get(name);
        }
        
        try {
            const response = await fetch(`/modals/${name}/`);
            const html = await response.text();
            
            const modal = document.createElement('div');
            modal.innerHTML = html;
            document.getElementById('modals-container').appendChild(modal);
            
            this.modals.set(name, modal);
            return modal;
        } catch (error) {
            console.error(`Failed to load modal ${name}:`, error);
            return null;
        }
    }
    
    show(name) {
        this.loadModal(name).then(modal => {
            if (!modal) return;
            
            // Hide current modal
            if (this.currentModal) {
                this.hide(this.currentModal);
            }
            
            // Show new modal
            modal.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
            this.currentModal = name;
            
            // Focus first input
            const firstInput = modal.querySelector('input, select, textarea');
            if (firstInput) firstInput.focus();
        });
    }
    
    hide(name) {
        const modal = this.modals.get(name);
        if (modal) {
            modal.classList.add('hidden');
        }
        
        if (this.currentModal === name) {
            this.currentModal = null;
            document.body.classList.remove('overflow-hidden');
        }
    }
}

// ===== APP INITIALIZATION =====
class App {
    constructor() {
        this.state = new AppState();
        this.api = new ApiService();
        this.tableManager = new TableManager();
        this.modalManager = new ModalManager();
        this.isLoading = false;
    }
    
    async init() {
        try {
            // Show loading state
            this.showLoading();
            
            // Load saved filters
            this.state.loadFromSessionStorage();
            
            // Initialize components
            this.initEventListeners();
            this.initSelect2();
            this.tableManager.init();
            
            // Load initial data
            await this.loadInitialData();
            
            // Hide loading, show content
            this.hideLoading();
            
            this.state.isInitialized = true;
            
            // Report performance
            this.reportPerformance();
            
        } catch (error) {
            console.error('App initialization failed:', error);
            this.showError('Không thể khởi tạo ứng dụng');
        }
    }
    
    showLoading() {
        document.getElementById('app-loading').classList.remove('hidden');
    }
    
    hideLoading() {
        const loadingEl = document.getElementById('app-loading');
        const mainContent = document.getElementById('main-content');
        const actualContent = document.getElementById('actual-content');
        
        loadingEl.style.opacity = '0';
        setTimeout(() => {
            loadingEl.classList.add('hidden');
            mainContent.classList.add('hidden');
            actualContent.classList.remove('hidden');
            actualContent.style.opacity = '1';
        }, 300);
    }
    
    showError(message) {
        const errorEl = document.createElement('div');
        errorEl.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
        errorEl.innerHTML = `
            <strong class="font-bold">Lỗi!</strong>
            <span class="block sm:inline"> ${message}</span>
        `;
        document.body.appendChild(errorEl);
        
        setTimeout(() => errorEl.remove(), 5000);
    }
    
    initEventListeners() {
        // Debounced filter changes
        document.querySelectorAll('#khoa-dao-tao, #chuong-trinh-dao-tao, #khoa-hoc').forEach(select => {
            select.addEventListener('change', PerformanceUtils.debounce((e) => {
                this.handleFilterChange(e.target.id, e.target.value);
            }));
        });
        
        // Button clicks
        document.getElementById('btn-them')?.addEventListener('click', () => {
            this.modalManager.show('them-chuong-trinh');
        });
        
        document.getElementById('btn-them-mon-hoc')?.addEventListener('click', () => {
            this.modalManager.show('them-mon-hoc');
        });
        
        document.getElementById('btn-cap-nhat')?.addEventListener('click', () => {
            this.refreshData();
        });
        
        // Table events (delegated)
        document.querySelector('.table-container').addEventListener('click', (e) => {
            const target = e.target.closest('button');
            if (!target) return;
            
            const id = target.dataset.id;
            
            if (target.classList.contains('btn-edit')) {
                this.toggleEditMode(id);
            } else if (target.classList.contains('btn-delete')) {
                this.deleteSubject(id);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.modalManager.currentModal) {
                    this.modalManager.hide(this.modalManager.currentModal);
                }
            }
            
            if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.refreshData();
            }
        });
        
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleResize();
            }, 100);
        });
        
        // Throttled resize handler
        window.addEventListener('resize', PerformanceUtils.throttle(() => {
            this.handleResize();
        }));
    }
    
    initSelect2() {
        // Lazy initialize Select2 only when needed
        const initSelect2ForElement = (element) => {
            if (!$(element).hasClass('select2-hidden-accessible')) {
                $(element).select2({
                    width: '100%',
                    dropdownAutoWidth: true,
                    minimumResultsForSearch: 10
                });
            }
        };
        
        // Initialize main filters
        ['#khoa-dao-tao', '#chuong-trinh-dao-tao', '#khoa-hoc'].forEach(selector => {
            const element = document.querySelector(selector);
            if (element) {
                initSelect2ForElement(element);
            }
        });
    }
    
    async loadInitialData() {
        // Load from cache first for instant display
        const cachedData = this.state.data.subjects;
        if (cachedData.length > 0) {
            this.tableManager.render(cachedData);
        }
        
        // Then fetch fresh data
        const freshData = await this.api.getSubjects(this.state.filters);
        if (freshData.length > 0) {
            this.state.data.subjects = freshData;
            this.tableManager.render(freshData);
            this.updateStatistics(freshData);
        }
    }
    
    async refreshData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        document.getElementById('btn-cap-nhat').classList.add('loading');
        
        try {
            const data = await this.api.getSubjects(this.state.filters);
            this.state.data.subjects = data;
            this.tableManager.render(data);
            this.updateStatistics(data);
            
            // Show success feedback
            this.showToast('Đã cập nhật dữ liệu thành công', 'success');
        } catch (error) {
            this.showError('Không thể cập nhật dữ liệu');
        } finally {
            this.isLoading = false;
            document.getElementById('btn-cap-nhat').classList.remove('loading');
        }
    }
    
    handleFilterChange(filterId, value) {
        let filterKey;
        
        switch(filterId) {
            case 'khoa-dao-tao':
                filterKey = 'departmentId';
                // Reset dependent filters
                this.state.updateFilter('subjectGroupId', null);
                this.state.updateFilter('curriculumId', null);
                this.state.updateFilter('courseId', null);
                break;
            case 'chuong-trinh-dao-tao':
                filterKey = 'curriculumId';
                this.state.updateFilter('courseId', null);
                break;
            case 'khoa-hoc':
                filterKey = 'courseId';
                break;
            default:
                return;
        }
        
        this.state.updateFilter(filterKey, value);
        this.refreshData();
    }
    
    handleResize() {
        const isNowMobile = window.innerWidth <= CONFIG.MOBILE_BREAKPOINT;
        
        if (isNowMobile !== this.state.isMobile) {
            this.state.isMobile = isNowMobile;
            this.tableManager.render(this.state.data.subjects);
        }
    }
    
    updateStatistics(data) {
        if (!data || data.length === 0) {
            this.updateStatElement('tong-tin-chi', '0');
            this.updateStatElement('tong-gio', '0');
            return;
        }
        
        const totalCredits = data.reduce((sum, item) => sum + (parseFloat(item.so_tin_chi) || 0), 0);
        const totalHours = data.reduce((sum, item) => sum + (parseInt(item.tong_so_gio) || 0), 0);
        
        this.updateStatElement('tong-tin-chi', totalCredits.toFixed(1));
        this.updateStatElement('tong-gio', totalHours);
    }
    
    updateStatElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    async toggleEditMode(subjectId) {
        const row = document.querySelector(`tr[data-id="${subjectId}"]`);
        if (!row) return;
        
        const isEditing = row.classList.contains('editing');
        
        if (isEditing) {
            // Save changes
            await this.saveEdits(row, subjectId);
            row.classList.remove('editing');
            row.querySelector('.btn-edit').innerHTML = '<i class="fas fa-edit"></i>';
        } else {
            // Enter edit mode
            row.classList.add('editing');
            row.querySelectorAll('.editable').forEach(input => {
                input.readOnly = false;
                input.classList.add('border', 'border-blue-300');
            });
            row.querySelector('.btn-edit').innerHTML = '<i class="fas fa-save"></i>';
        }
    }
    
    async saveEdits(row, subjectId) {
        const changes = {};
        row.querySelectorAll('.editable').forEach(input => {
            const field = input.dataset.field;
            const original = input.dataset.original;
            const current = input.value;
            
            if (current !== original) {
                changes[field] = current;
                input.dataset.original = current;
            }
            
            input.readOnly = true;
            input.classList.remove('border', 'border-blue-300');
        });
        
        if (Object.keys(changes).length > 0) {
            try {
                await this.api.updateSubject(subjectId, changes);
                this.showToast('Đã lưu thay đổi', 'success');
            } catch (error) {
                this.showError('Không thể lưu thay đổi');
            }
        }
    }
    
    async deleteSubject(subjectId) {
        if (!confirm('Bạn có chắc chắn muốn xóa môn học này?')) return;
        
        try {
            await this.api.deleteSubject(subjectId);
            this.showToast('Đã xóa môn học', 'success');
            this.refreshData();
        } catch (error) {
            this.showError('Không thể xóa môn học');
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 
                          ${type === 'success' ? 'bg-green-100 text-green-800' : 
                            type === 'error' ? 'bg-red-100 text-red-800' : 
                            'bg-blue-100 text-blue-800'}`;
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 
                               type === 'error' ? 'fa-exclamation-circle' : 
                               'fa-info-circle'} mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    reportPerformance() {
        if (window.performance && window.performance.timing) {
            const perf = window.performance.timing;
            const loadTime = perf.loadEventEnd - perf.navigationStart;
            
            console.log(`Page loaded in ${loadTime}ms`);
            
            // Send to analytics if needed
            if (loadTime > 3000) {
                console.warn('Slow page load detected');
            }
        }
    }
}


// Export for modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { App, AppState, ApiService };
}

// ===== INITIALIZE APP =====
let app;

document.addEventListener('DOMContentLoaded', () => {
    // Wait for critical resources
    if (document.readyState === 'complete') {
        initApp();
    } else {
        window.addEventListener('load', initApp);
    }
});

function initApp() {
    app = new App();
    app.init();
    
    // Register app for debugging
    window.app = app;
}

// Export for modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { App, AppState, ApiService };
}
