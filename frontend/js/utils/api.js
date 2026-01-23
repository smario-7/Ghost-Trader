// API Helper Functions
// Funkcje pomocnicze do komunikacji z backendem i formatowania danych

const API_BASE = '/api';

// Główna funkcja do wykonywania zapytań API
// Automatycznie dodaje API key z localStorage i obsługuje błędy
async function apiCall(endpoint, method = 'GET', body = null) {
    try {
        let key = localStorage.getItem('api_key') || sessionStorage.getItem('api_key');
        
        // Jeśli brak klucza, zwróć cichy błąd (nie loguj)
        if (!key) {
            const silentError = new Error('API Key required');
            silentError.silent = true;
            throw silentError;
        }
        
        const options = {
            method,
            headers: {
                'X-API-Key': key,
                'Content-Type': 'application/json'
            }
        };
        
        if (body) options.body = JSON.stringify(body);
        
        const url = `${API_BASE}${endpoint}`;
        const response = await fetch(url, options);
        
        // Obsługa błędów autoryzacji
        if (response.status === 403) {
            sessionStorage.removeItem('api_key');
            localStorage.removeItem('api_key');
            throw new Error('Nieprawidłowy API Key. Podaj ponownie.');
        }
        
        // Obsługa błędów połączenia z backendem
        if (response.status === 502) {
            throw new Error('Backend nie jest dostępny. Sprawdź czy backend działa w Dockerze (docker-compose ps)');
        }
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        // Nie loguj błędów "cichych" (brak API key)
        if (error.silent) {
            throw error;
        }
        
        // Obsługa błędów sieciowych
        if (error.message.includes('Failed to fetch') || 
            error.message.includes('ERR_CONNECTION_REFUSED') ||
            error.message.includes('ERR_CONNECTION_RESET') ||
            error.message.includes('ERR_SOCKET_NOT_CONNECTED') ||
            error.message.includes('Bad Gateway') ||
            error.message.includes('502')) {
            const friendlyError = new Error('Backend nie jest dostępny. Sprawdź czy backend działa w Dockerze (docker-compose ps)');
            friendlyError.name = 'ConnectionError';
            throw friendlyError;
        }
        if (error.name !== 'ConnectionError') {
            console.error('API Error:', error);
        }
        throw error;
    }
}

// Formatuje datę do polskiego formatu w strefie czasowej Warsaw
function formatDate(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleString('pl-PL', { 
        timeZone: 'Europe/Warsaw' 
    });
}

// Skraca długie parametry JSON do 60 znaków
function formatParameters(params) {
    if (!params) return '';
    const str = JSON.stringify(params);
    return str.length > 60 ? str.substring(0, 60) + '...' : str;
}

// Formatuje wskaźniki techniczne do czytelnej formy
function formatIndicators(indicators) {
    if (!indicators) return '';
    return Object.entries(indicators)
        .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}`)
        .join(', ');
}

// Formatuje wartość walutową
function formatCurrency(value, decimals = 2) {
    if (value === null || value === undefined) return '';
    return typeof value === 'number' ? value.toFixed(decimals) : value;
}

// Eksport funkcji jako obiekt (dla Alpine.js spread operator)
const apiUtils = {
    apiCall,
    formatDate,
    formatParameters,
    formatIndicators,
    formatCurrency
};
