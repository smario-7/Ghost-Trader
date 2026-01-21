// Dashboard Component Methods
// Metody związane z głównym widokiem Dashboard: statystyki, sygnały, aktywność

const dashboardMethods = {
    // Pobiera API key z sessionStorage lub prompt
    async getApiKey() {
        if (!this.apiKey) {
            this.apiKey = sessionStorage.getItem('api_key') || prompt('Podaj API Key:');
            if (this.apiKey) {
                sessionStorage.setItem('api_key', this.apiKey);
            } else {
                throw new Error('API Key jest wymagany');
            }
        }
        return this.apiKey;
    },

    // Ładuje statystyki z backendu
    async loadStatistics() {
        try {
            this.loading.statistics = true;
            const stats = await apiCall('/statistics');
            this.backendWarning = false;
            this.statistics = stats;
            this.uniqueSymbols = await this.loadUniqueSymbols();
            this.refreshIndicators.stats = '✓';
            setTimeout(() => this.refreshIndicators.stats = '', 2000);
        } catch (error) {
            this.showError(error.message);
            if (error.message.includes('Backend nie jest dostępny')) {
                return;
            }
        } finally {
            this.loading.statistics = false;
        }
    },

    // Pobiera unikalne symbole z aktywnych strategii
    async loadUniqueSymbols() {
        try {
            const data = await apiCall('/strategies');
            return [...new Set(data.strategies.filter(s => s.is_active).map(s => s.symbol))];
        } catch {
            return [];
        }
    },

    // Ładuje listę strategii
    async loadStrategies() {
        try {
            this.loading.strategies = true;
            const data = await apiCall('/strategies');
            this.backendWarning = false;
            this.strategies = data.strategies || [];
        } catch (error) {
            this.showError(error.message);
            if (error.message.includes('Backend nie jest dostępny')) {
                return;
            }
        } finally {
            this.loading.strategies = false;
        }
    },

    // Ładuje ostatnie sygnały
    async loadRecentSignals() {
        try {
            this.loading.signals = true;
            const data = await apiCall('/signals/recent?limit=10');
            this.backendWarning = false;
            this.signals = data.signals || [];
            this.refreshIndicators.signals = '✓';
            setTimeout(() => this.refreshIndicators.signals = '', 2000);
        } catch (error) {
            this.showError(error.message);
            if (error.message.includes('Backend nie jest dostępny')) {
                return;
            }
        } finally {
            this.loading.signals = false;
        }
    },

    // Ładuje aktywność bota (sprawdzanie sygnałów)
    async loadBotActivity() {
        try {
            this.loading.activity = true;
            const data = await apiCall('/check-signals', 'POST');
            this.backendWarning = false;
            this.activity = data.results || [];
            this.refreshIndicators.activity = '✓';
            setTimeout(() => this.refreshIndicators.activity = '', 2000);
        } catch (error) {
            this.showError(error.message);
            if (error.message.includes('Backend nie jest dostępny')) {
                return;
            }
        } finally {
            this.loading.activity = false;
        }
    },

    // Łączy się z SSE (Server-Sent Events) dla real-time updates
    async connectSSE() {
        if (this.sseConnection) {
            console.log('SSE already connected');
            return; // już połączone
        }
        
        try {
            // Pobierz API key (SSE nie obsługuje custom headers, więc używamy query string)
            const apiKey = await this.getApiKey();
            if (!apiKey) {
                console.error('No API key available for SSE');
                return;
            }
            
            const url = `/api/stream/ai-updates?api_key=${encodeURIComponent(apiKey)}`;
            console.log('Connecting SSE to:', url.replace(apiKey, '***'));
            
            this.sseConnection = new EventSource(url);
            
            // Obsługa nowej analizy AI
            this.sseConnection.addEventListener('new_analysis', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    // Dodaj nową analizę do listy
                    this.aiAnalysisResults.unshift(data);
                    // Ogranicz listę do 50 elementów
                    if (this.aiAnalysisResults.length > 50) {
                        this.aiAnalysisResults = this.aiAnalysisResults.slice(0, 50);
                    }
                    // Aktualizuj statystyki
                    this.loadTokenStatistics();
                } catch (err) {
                    console.error('Error parsing SSE data:', err);
                }
            });
            
            // Obsługa błędów połączenia
            this.sseConnection.onerror = (error) => {
                console.error('SSE Error:', error);
                this.disconnectSSE();
                // Retry po 5 sekundach
                setTimeout(() => this.connectSSE(), 5000);
            };
            
            console.log('SSE connection established');
        } catch (error) {
            console.error('Error connecting SSE:', error);
        }
    },

    // Rozłącza SSE
    disconnectSSE() {
        if (this.sseConnection) {
            this.sseConnection.close();
            this.sseConnection = null;
            console.log('SSE connection closed');
        }
    },

    // Aktualizuje timestamp ostatniej aktualizacji
    updateLastUpdate() {
        const now = new Date();
        this.lastUpdate = now.toLocaleTimeString('pl-PL');
    },

    // Wyświetla komunikat błędu
    showError(message) {
        this.errorMessage = message;
        setTimeout(() => this.errorMessage = '', 5000);
    },

    // Wyświetla komunikat sukcesu
    showSuccess(message) {
        this.successMessage = message;
        setTimeout(() => this.successMessage = '', 3000);
    },

    // Helper: zwraca klasę CSS dla agreement score
    getAgreementClass(score) {
        if (!score) return 'low';
        if (score >= 75) return 'high';
        if (score >= 50) return 'medium';
        return 'low';
    },

    // Helper: formatuje timestamp
    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleString('pl-PL');
    }
};
