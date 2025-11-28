/**
 * JournalSmart for QBO - Main JavaScript
 */

// ============================================
// Confirmation Modal System
// ============================================

/**
 * Show a confirmation modal
 * @param {object} options - Modal options
 * @param {string} options.title - Modal title
 * @param {string} options.message - Modal message
 * @param {string} options.confirmText - Confirm button text (default: 'Confirm')
 * @param {string} options.cancelText - Cancel button text (default: 'Cancel')
 * @param {string} options.type - Type: 'warning', 'danger', 'info' (default: 'warning')
 * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled
 */
window.showConfirm = function(options = {}) {
    return new Promise((resolve) => {
        const {
            title = 'Confirm Action',
            message = 'Are you sure you want to proceed?',
            confirmText = 'Confirm',
            cancelText = 'Cancel',
            type = 'warning'
        } = options;

        const iconColors = {
            warning: 'text-yellow-500 bg-yellow-100',
            danger: 'text-red-500 bg-red-100',
            info: 'text-blue-500 bg-blue-100'
        };

        const buttonColors = {
            warning: 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500',
            danger: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
            info: 'bg-primary-600 hover:bg-primary-700 focus:ring-primary-500'
        };

        const icons = {
            warning: `<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>`,
            danger: `<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>`,
            info: `<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
            </svg>`
        };

        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'fixed inset-0 z-50 overflow-y-auto';
        backdrop.setAttribute('aria-labelledby', 'modal-title');
        backdrop.setAttribute('role', 'dialog');
        backdrop.setAttribute('aria-modal', 'true');

        backdrop.innerHTML = `
            <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
                <!-- Backdrop overlay -->
                <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity modal-backdrop-overlay" aria-hidden="true"></div>

                <!-- Modal panel -->
                <div class="relative transform overflow-hidden rounded-xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg modal-panel">
                    <div class="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                        <div class="sm:flex sm:items-start">
                            <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full ${iconColors[type]} sm:mx-0 sm:h-10 sm:w-10">
                                ${icons[type]}
                            </div>
                            <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                                <h3 class="text-base font-semibold leading-6 text-gray-900" id="modal-title">${title}</h3>
                                <div class="mt-2">
                                    <p class="text-sm text-gray-500">${message}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6 gap-2">
                        <button type="button" class="inline-flex w-full justify-center rounded-lg px-4 py-2.5 text-sm font-semibold text-white shadow-sm ${buttonColors[type]} focus:outline-none focus:ring-2 focus:ring-offset-2 sm:w-auto modal-confirm-btn">
                            ${confirmText}
                        </button>
                        <button type="button" class="mt-3 inline-flex w-full justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 sm:mt-0 sm:w-auto modal-cancel-btn">
                            ${cancelText}
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(backdrop);

        // Get elements
        const panel = backdrop.querySelector('.modal-panel');
        const overlayEl = backdrop.querySelector('.modal-backdrop-overlay');
        const confirmBtn = backdrop.querySelector('.modal-confirm-btn');
        const cancelBtn = backdrop.querySelector('.modal-cancel-btn');

        // Animate in
        requestAnimationFrame(() => {
            overlayEl.classList.add('opacity-100');
            panel.classList.add('opacity-100', 'scale-100');
            panel.classList.remove('opacity-0', 'scale-95');
        });

        // Initial state for animation
        overlayEl.classList.add('opacity-0');
        panel.classList.add('opacity-0', 'scale-95');
        overlayEl.style.transition = 'opacity 200ms ease-out';
        panel.style.transition = 'opacity 200ms ease-out, transform 200ms ease-out';

        // Focus the confirm button
        setTimeout(() => confirmBtn.focus(), 100);

        // Close modal function
        const closeModal = (result) => {
            overlayEl.classList.remove('opacity-100');
            overlayEl.classList.add('opacity-0');
            panel.classList.remove('opacity-100', 'scale-100');
            panel.classList.add('opacity-0', 'scale-95');

            setTimeout(() => {
                backdrop.remove();
                resolve(result);
            }, 200);
        };

        // Event handlers
        confirmBtn.addEventListener('click', () => closeModal(true));
        cancelBtn.addEventListener('click', () => closeModal(false));

        // Close on backdrop click
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop || e.target === overlayEl) {
                closeModal(false);
            }
        });

        // Close on Escape key
        const handleKeydown = (e) => {
            if (e.key === 'Escape') {
                closeModal(false);
                document.removeEventListener('keydown', handleKeydown);
            }
            // Trap focus within modal
            if (e.key === 'Tab') {
                const focusableElements = [confirmBtn, cancelBtn];
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                } else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        };
        document.addEventListener('keydown', handleKeydown);
    });
};

// ============================================
// Toast Notification System
// ============================================

const toastIcons = {
    success: `<svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
    </svg>`,
    error: `<svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
    </svg>`,
    warning: `<svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
    </svg>`,
    info: `<svg class="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
    </svg>`
};

const toastColors = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    warning: 'bg-yellow-50 border-yellow-200',
    info: 'bg-blue-50 border-blue-200'
};

const toastTextColors = {
    success: 'text-green-800',
    error: 'text-red-800',
    warning: 'text-yellow-800',
    info: 'text-blue-800'
};

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in ms before auto-dismiss (default: 4000)
 */
window.showToast = function(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `flex items-center gap-3 p-4 rounded-lg border shadow-lg transform transition-all duration-300 ease-out translate-x-full ${toastColors[type] || toastColors.info}`;
    toast.setAttribute('role', 'alert');

    toast.innerHTML = `
        <div class="flex-shrink-0">
            ${toastIcons[type] || toastIcons.info}
        </div>
        <p class="text-sm font-medium ${toastTextColors[type] || toastTextColors.info}">${message}</p>
        <button type="button" class="ml-auto flex-shrink-0 rounded-lg p-1.5 inline-flex items-center justify-center h-8 w-8 ${toastTextColors[type] || toastTextColors.info} hover:bg-white/50 focus:ring-2 focus:ring-offset-2 transition-colors" aria-label="Close">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    `;

    // Close button handler
    const closeBtn = toast.querySelector('button');
    closeBtn.addEventListener('click', () => dismissToast(toast));

    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full');
        toast.classList.add('translate-x-0');
    });

    // Auto dismiss
    if (duration > 0) {
        setTimeout(() => dismissToast(toast), duration);
    }

    return toast;
};

function dismissToast(toast) {
    toast.classList.remove('translate-x-0');
    toast.classList.add('translate-x-full', 'opacity-0');
    setTimeout(() => toast.remove(), 300);
}

// ============================================
// Mobile Menu Toggle
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const menuIconOpen = document.getElementById('menu-icon-open');
    const menuIconClose = document.getElementById('menu-icon-close');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            const isExpanded = mobileMenuBtn.getAttribute('aria-expanded') === 'true';

            mobileMenuBtn.setAttribute('aria-expanded', !isExpanded);
            mobileMenu.classList.toggle('hidden');
            menuIconOpen.classList.toggle('hidden');
            menuIconClose.classList.toggle('hidden');
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!mobileMenuBtn.contains(event.target) && !mobileMenu.contains(event.target)) {
                mobileMenuBtn.setAttribute('aria-expanded', 'false');
                mobileMenu.classList.add('hidden');
                menuIconOpen.classList.remove('hidden');
                menuIconClose.classList.add('hidden');
            }
        });

        // Close menu on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                mobileMenuBtn.setAttribute('aria-expanded', 'false');
                mobileMenu.classList.add('hidden');
                menuIconOpen.classList.remove('hidden');
                menuIconClose.classList.add('hidden');
            }
        });
    }
});

// ============================================
// Form Utilities
// ============================================

/**
 * Set loading state on a button
 * @param {HTMLButtonElement} button - The button element
 * @param {boolean} loading - Whether to show loading state
 * @param {string} loadingText - Text to show while loading
 */
window.setButtonLoading = function(button, loading, loadingText = 'Loading...') {
    if (!button) return;

    const originalText = button.dataset.originalText || button.textContent;

    if (loading) {
        button.dataset.originalText = originalText;
        button.disabled = true;
        button.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${loadingText}
        `;
    } else {
        button.disabled = false;
        button.textContent = originalText;
        delete button.dataset.originalText;
    }
};

// ============================================
// API Utilities
// ============================================

/**
 * Make a fetch request with error handling
 * @param {string} url - The URL to fetch
 * @param {object} options - Fetch options
 * @returns {Promise<any>} - The response data
 */
window.apiFetch = async function(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    try {
        const response = await fetch(url, mergedOptions);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Request failed' }));
            throw new Error(error.message || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};

// ============================================
// Legacy Support (for existing inline scripts)
// ============================================

// Handle the confirmation and application of changes
async function applyChanges() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const changes = JSON.parse(decodeURIComponent(urlParams.get('changes')));

        const response = await fetch('/journals/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(changes)
        });

        if (!response.ok) {
            throw new Error('Failed to apply changes');
        }

        window.showToast('Changes applied successfully!', 'success');
        setTimeout(() => {
            window.location.href = '/journals?success=true';
        }, 1500);
    } catch (error) {
        console.error('Error:', error);
        window.showToast('Failed to apply changes. Please try again.', 'error');
    }
}

// Handle mapping form submission
document.addEventListener('DOMContentLoaded', function() {
    const mappingForm = document.getElementById('mapping-form');
    if (mappingForm) {
        mappingForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(mappingForm);
            const mappingData = {
                description_pattern: formData.get('description_pattern'),
                account_id: formData.get('account_id')
            };

            try {
                const response = await fetch('/mapping', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(mappingData)
                });

                if (!response.ok) {
                    throw new Error('Failed to save mapping');
                }

                window.showToast('Mapping saved successfully!', 'success');
                loadCurrentMappings();
                mappingForm.reset();
            } catch (error) {
                console.error('Error:', error);
                window.showToast('Failed to save mapping. Please try again.', 'error');
            }
        });
    }
});

// Load and display current mappings
async function loadCurrentMappings() {
    try {
        const response = await fetch('/mapping');
        if (!response.ok) {
            throw new Error('Failed to load mappings');
        }

        const mappings = await response.json();
        const mappingsContainer = document.getElementById('current-mappings');

        if (!mappingsContainer) return;

        mappingsContainer.innerHTML = mappings.map(mapping => `
            <div class="flex justify-between items-center py-3 border-b border-gray-200 last:border-0">
                <div>
                    <p class="text-sm font-medium text-gray-900">${mapping.description_pattern}</p>
                    <p class="text-sm text-gray-500">${mapping.account_name}</p>
                </div>
                <button onclick="deleteMapping('${mapping.id}')" class="text-red-600 hover:text-red-900 text-sm font-medium">
                    Delete
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error:', error);
        window.showToast('Failed to load mappings. Please refresh the page.', 'error');
    }
}

// Delete a mapping
async function deleteMapping(id) {
    if (!confirm('Are you sure you want to delete this mapping?')) {
        return;
    }

    try {
        const response = await fetch(`/mapping/${id}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Failed to delete mapping');
        }

        window.showToast('Mapping deleted successfully!', 'success');
        loadCurrentMappings();
    } catch (error) {
        console.error('Error:', error);
        window.showToast('Failed to delete mapping. Please try again.', 'error');
    }
}
