// train_program.js - OOP VERSION WITHOUT SERVICE WORKER

// ===== CONFIGURATION =====
const CONFIG = {
    DEBOUNCE_DELAY: 300,
    THROTTLE_DELAY: 100,
    API_TIMEOUT: 10000,
    MAX_ROWS_VISIBLE: 50,
    MOBILE_BREAKPOINT: 768
};

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
}

// ===== STATE MANAGEMENT =====
class AppState {
    constructor() {
        this.data = {
            subjects: window.APP_DATA?.monHocData || [],
            departments: window.APP_DATA?.departments || [],
            subjectGroups: window.APP_DATA?.subjectGroups || [],
            curricula: window.APP_DATA?.curricula || [],
            courses: window.APP_DATA?.courses || [],
            subjectTypes: window.APP_DATA?.subjectTypes || [],
            majors: window.APP_DATA?.majors || []
        };
        
        this.filters = {
            departmentId: null,
            subjectGroupId: null,
            curriculumId: null,
            courseId: null
        };
        
        this.cache = new Map();
        this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        this.isInitialized = false;
    }
}

// ===== API SERVICE =====
class ApiService {
    constructor() {
        this.baseUrl = '';
    }
    
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            console.warn('Fetch error:', error.message);
            return [];
        }
    }
}

// ===== TABLE MANAGER =====
class TableManager {
    constructor(app) {
        this.app = app;
        this.container = document.querySelector('.table-container');
        this.tableBody = null;
    }
    
    init() {
        this.tableBody = this.container?.querySelector('tbody');
        if (!this.tableBody && this.container) {
            const table = this.container.querySelector('table');
            if (table) {
                this.tableBody = document.createElement('tbody');
                table.appendChild(this.tableBody);
            }
        }
    }
    
    render(data) {
        if (!this.tableBody) return;
        
        if (!data || data.length === 0) {
            this.showEmptyState();
            return;
        }
        
        // Sử dụng this.app.state thay vì appState
        const isMobile = this.app?.state?.isMobile || false;
        const displayData = isMobile ? 
            data.slice(0, CONFIG.MAX_ROWS_VISIBLE) : 
            data;
        
        // Dùng DocumentFragment cho hiệu suất
        const fragment = document.createDocumentFragment();
        
        displayData.forEach((item, index) => {
            const row = this.createRow(item, index);
            fragment.appendChild(row);
        });
        
        this.tableBody.innerHTML = '';
        this.tableBody.appendChild(fragment);
        
        // Nếu có nhiều dữ liệu trên mobile
        if (isMobile && data.length > CONFIG.MAX_ROWS_VISIBLE) {
            this.showLoadMoreButton(data.length - CONFIG.MAX_ROWS_VISIBLE);
        }
    }
    
    createRow(item, index) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';
        
        row.innerHTML = `
            <td class="px-2 py-2 text-center">${index + 1}</td>
            <td class="px-2 py-2">
                <span class="text-sm">${this.escapeHtml(item.ma_mon_hoc || item.code || '')}</span>
            </td>
            <td class="px-2 py-2 wrap-cell">
                <span class="text-sm">${this.escapeHtml(item.ten_mon_hoc || item.name || '')}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.so_tin_chi || item.credits || 0}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.tong_so_gio || item.total_hours || 0}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.ly_thuyet || item.theory_hours || 0}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.thuc_hanh || item.practice_hours || 0}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.kiem_tra || item.tests_hours || 0}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.thi || item.exam_hours || 0}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.hk1 || ''}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.hk2 || ''}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.hk3 || ''}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.hk4 || ''}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.hk5 || ''}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <span class="text-sm">${item.hk6 || ''}</span>
            </td>
            <td class="px-2 py-2">
                <span class="text-sm">${this.escapeHtml(item.don_vi || item.department_name || '')}</span>
            </td>
            <td class="px-2 py-2">
                <span class="text-sm">${this.escapeHtml(item.giang_vien || '')}</span>
            </td>
            <td class="px-2 py-2">
                <span class="text-sm">${this.getCourseName(item.course_id)}</span>
            </td>
            <td class="px-2 py-2 text-center">
                <button class="btn-sua text-blue-600 hover:text-blue-900 mr-2" 
                        data-id="${item.id || index}" title="Sửa">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-xoa text-red-600 hover:text-red-900" 
                        data-id="${item.id || index}" title="Xóa">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        return row;
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getCourseName(courseId) {
        if (!courseId) return '';
        const courses = this.app?.state?.data?.courses || [];
        const course = courses.find(c => c.id == courseId);
        return course ? (course.name || course.ten_khoa_hoc) : '';
    }
    
    showEmptyState() {
        if (!this.tableBody) return;
        this.tableBody.innerHTML = `
            <tr>
                <td colspan="19" class="px-4 py-8 text-center text-gray-500">
                    Không có dữ liệu môn học
                </td>
            </tr>
        `;
    }
    
    showLoadMoreButton(remaining) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td colspan="19" class="px-4 py-3 text-center">
                <button onclick="app.loadMoreRows()" 
                        class="text-blue-600 hover:text-blue-800 font-medium">
                    <i class="fas fa-chevron-down mr-1"></i>
                    Xem thêm ${remaining} môn học
                </button>
            </td>
        `;
        this.tableBody.appendChild(row);
    }
}

// ===== APP CLASS =====
class App {
    constructor() {
        this.state = new AppState();
        this.api = new ApiService();
        this.tableManager = new TableManager(this);
        this.isLoading = false;
        
        // Tạo global reference để debug
        window.app = this;
    }
    
    async init() {
        try {
            console.log('App initializing...');
            
            // Initialize components
            this.tableManager.init();
            this.initEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            // Hide loading
            this.hideLoading();
            
            this.state.isInitialized = true;
            console.log('App initialized successfully');
            
        } catch (error) {
            console.error('App initialization failed:', error);
            this.showError('Không thể khởi tạo ứng dụng: ' + error.message);
            this.hideLoading(); // Vẫn ẩn loading dù có lỗi
        }
    }
    
    hideLoading() {
        const loadingEl = document.getElementById('app-loading');
        if (loadingEl) {
            loadingEl.style.transition = 'opacity 0.3s';
            loadingEl.style.opacity = '0';
            setTimeout(() => {
                loadingEl.classList.add('hidden');
                
                // Hiển thị nội dung chính
                const actualContent = document.getElementById('actual-content');
                if (actualContent) {
                    actualContent.classList.remove('hidden');
                    setTimeout(() => {
                        actualContent.style.opacity = '1';
                    }, 50);
                }
            }, 300);
        }
    }
    
    showError(message) {
        console.error('App Error:', message);
        // Hiển thị thông báo lỗi đơn giản
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
        // Filter changes với debounce
        $(document).on('change', '#khoa-dao-tao', 
            PerformanceUtils.debounce(() => this.loadFilteredData(), 500)
        );
        
        $(document).on('change', '#chuong-trinh-dao-tao', 
            PerformanceUtils.debounce(() => this.loadFilteredData(), 500)
        );
        
        $(document).on('change', '#khoa-hoc', 
            PerformanceUtils.debounce(() => this.loadFilteredData(), 500)
        );
        
        // Button clicks
        document.getElementById('btn-cap-nhat')?.addEventListener('click', () => {
            this.loadFilteredData();
        });
        
        document.getElementById('btn-them-mon-hoc')?.addEventListener('click', () => {
            this.openModal('them-mon-hoc');
        });
        
        // Table event delegation
        $(document).on('click', '.btn-sua', (e) => {
            const btn = e.currentTarget;
            const id = btn.dataset.id;
            this.editSubject(id);
        });
        
        $(document).on('click', '.btn-xoa', (e) => {
            const btn = e.currentTarget;
            const id = btn.dataset.id;
            this.deleteSubject(id);
        });
        
        // Window resize
        window.addEventListener('resize', 
            PerformanceUtils.throttle(() => this.handleResize(), 250)
        );
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }
    
    async loadInitialData() {
        // Sử dụng dữ liệu từ template nếu có
        if (this.state.data.subjects.length > 0) {
            this.tableManager.render(this.state.data.subjects);
            this.updateStatistics();
            return;
        }
        
        // Nếu không, thử load từ API
        await this.loadFilteredData();
    }
    
    async loadFilteredData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        const btn = document.getElementById('btn-cap-nhat');
        if (btn) btn.classList.add('opacity-50', 'cursor-not-allowed');
        
        try {
            const params = new URLSearchParams();
            
            const curriculumId = document.getElementById('chuong-trinh-dao-tao')?.value;
            const departmentId = document.getElementById('khoa-dao-tao')?.value;
            const courseId = document.getElementById('khoa-hoc')?.value;
            
            if (curriculumId) params.append('curriculum_id', curriculumId);
            if (departmentId) params.append('department_id', departmentId);
            if (courseId) params.append('course_id', courseId);
            
            const url = `/api/subjects/${params.toString() ? '?' + params.toString() : ''}`;
            const data = await this.api.fetchWithTimeout(url);
            
            this.state.data.subjects = data;
            this.tableManager.render(data);
            this.updateStatistics();
            
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Không thể tải dữ liệu. Vui lòng thử lại.');
        } finally {
            this.isLoading = false;
            if (btn) btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
    
    updateStatistics() {
        const data = this.state.data.subjects;
        if (!data || data.length === 0) {
            this.setStatValue('tong-tin-chi', '0');
            this.setStatValue('tong-gio', '0');
            this.setStatValue('ty-le-ly-thuyet', '0%');
            this.setStatValue('ty-le-thuc-hanh', '0%');
            return;
        }
        
        const totalCredits = data.reduce((sum, item) => 
            sum + (parseFloat(item.so_tin_chi) || 0), 0
        );
        
        const totalHours = data.reduce((sum, item) => 
            sum + (parseInt(item.tong_so_gio) || 0), 0
        );
        
        this.setStatValue('tong-tin-chi', totalCredits.toFixed(1));
        this.setStatValue('tong-gio', totalHours);
        
        if (totalHours > 0) {
            const totalTheory = data.reduce((sum, item) => 
                sum + (parseInt(item.ly_thuyet) || 0), 0
            );
            
            const totalPractice = data.reduce((sum, item) => 
                sum + (parseInt(item.thuc_hanh) || 0), 0
            );
            
            const theoryPercent = ((totalTheory / totalHours) * 100).toFixed(1);
            const practicePercent = ((totalPractice / totalHours) * 100).toFixed(1);
            
            this.setStatValue('ty-le-ly-thuyet', `${theoryPercent}%`);
            this.setStatValue('ty-le-thuc-hanh', `${practicePercent}%`);
        }
    }
    
    setStatValue(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    handleResize() {
        const isNowMobile = window.innerWidth <= CONFIG.MOBILE_BREAKPOINT;
        if (isNowMobile !== this.state.isMobile) {
            this.state.isMobile = isNowMobile;
            this.tableManager.render(this.state.data.subjects);
        }
    }
    
    openModal(modalName) {
        const modal = document.getElementById(`modal-${modalName}`);
        if (modal) {
            modal.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
        }
    }
    
    closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
        document.body.classList.remove('overflow-hidden');
    }
    
    editSubject(id) {
        console.log('Edit subject:', id);
        this.showToast(`Chức năng sửa môn học ID: ${id} đang được phát triển`, 'info');
    }
    
    async deleteSubject(id) {
        if (!confirm('Bạn có chắc chắn muốn xóa môn học này?')) return;
        
        try {
            const csrfToken = this.getCSRFToken();
            const response = await fetch(`/train-program/${id}/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
            
            if (response.ok) {
                this.showToast('Đã xóa môn học thành công', 'success');
                await this.loadFilteredData();
            } else {
                throw new Error('Xóa không thành công');
            }
        } catch (error) {
            console.error('Error deleting subject:', error);
            this.showError('Không thể xóa môn học');
        }
    }
    
    getCSRFToken() {
        try {
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) return metaTag.getAttribute('content');
            
            const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfTokenInput) return csrfTokenInput.value;
            
            return '';
        } catch (error) {
            return '';
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
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    loadMoreRows() {
        // Implement load more functionality
        console.log('Loading more rows...');
        this.showToast('Đang tải thêm dữ liệu...', 'info');
    }
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');
    
    // Khởi tạo app
    const app = new App();
    window.app = app;
    
    // Bắt đầu khởi tạo
    app.init();
});

// KHÔNG CÓ Service Worker registration ở đây
