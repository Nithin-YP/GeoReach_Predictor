/**
 * CSRF Token Utility for GeoReach Predictor
 * =========================================
 * Add this to any page that needs to make POST requests via JavaScript
 */

/**
 * Get CSRF token from cookie
 * @param {string} name - Cookie name (default: 'csrftoken')
 * @returns {string|null} CSRF token value
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Get CSRF token (tries multiple methods)
 * @returns {string|null} CSRF token value
 */
function getCSRFToken() {
    // Method 1: From cookie
    let token = getCookie('csrftoken');
    if (token) return token;
    
    // Method 2: From meta tag
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) return metaTag.getAttribute('content');
    
    // Method 3: From hidden input in form
    const hiddenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (hiddenInput) return hiddenInput.value;
    
    return null;
}

/**
 * Make a POST request with CSRF token
 * @param {string} url - API endpoint
 * @param {object} data - Request body data
 * @param {object} options - Additional fetch options
 * @returns {Promise<Response>} Fetch promise
 */
async function postWithCSRF(url, data, options = {}) {
    const csrftoken = getCSRFToken();
    
    if (!csrftoken) {
        console.error('CSRF token not found! Make sure the page has loaded properly.');
        throw new Error('CSRF token not found');
    }
    
    const defaultOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(data)
    };
    
    // Merge with custom options
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    
    return fetch(url, finalOptions);
}

/**
 * Setup CSRF for jQuery AJAX (if using jQuery)
 */
function setupJQueryCSRF() {
    if (typeof $ !== 'undefined' && $.ajaxSetup) {
        const csrftoken = getCSRFToken();
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                // Only add CSRF token for local requests
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            }
        });
    }
}

/**
 * Setup CSRF for Axios (if using Axios)
 */
function setupAxiosCSRF() {
    if (typeof axios !== 'undefined') {
        const csrftoken = getCSRFToken();
        axios.defaults.headers.common['X-CSRFToken'] = csrftoken;
    }
}

/**
 * Initialize CSRF handling on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Auto-setup for popular libraries
    setupJQueryCSRF();
    setupAxiosCSRF();
    
    // Log CSRF token status for debugging
    const token = getCSRFToken();
    if (token) {
        console.log('✓ CSRF token loaded:', token.substring(0, 20) + '...');
    } else {
        console.warn('⚠ CSRF token not found. POST requests may fail.');
    }
});

// Export for ES6 modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getCookie,
        getCSRFToken,
        postWithCSRF,
        setupJQueryCSRF,
        setupAxiosCSRF
    };
}
