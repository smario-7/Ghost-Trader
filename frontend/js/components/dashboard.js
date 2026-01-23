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
            // Nie pokazuj błędu jeśli to "silent error" (brak API key)
            if (error && error.silent) {
                return;
            }
            if (error && error.message) {
                this.showError(error.message);
            }
            if (error.message && error.message.includes('Backend nie jest dostępny')) {
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
            if (error && error.silent) return;
            this.showError(error.message);
            if (error.message && error.message.includes('Backend nie jest dostępny')) {
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
            if (error && error.silent) return;
            this.showError(error.message);
            if (error.message && error.message.includes('Backend nie jest dostępny')) {
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
            if (error && error.silent) return;
            this.showError(error.message);
            if (error.message && error.message.includes('Backend nie jest dostępny')) {
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
            // Pobierz API key z sessionStorage (powinien już być ustawiony po załadowaniu danych)
            const apiKey = sessionStorage.getItem('api_key') || localStorage.getItem('api_key');
            if (!apiKey) {
                console.warn('No API key available for SSE - will retry after data loads');
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
        this.lastUpdate = now.toLocaleTimeString('pl-PL', {
            timeZone: 'Europe/Warsaw'
        });
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

    // Helper: formatuje timestamp w strefie czasowej Warsaw
    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleString('pl-PL', {
            timeZone: 'Europe/Warsaw'
        });
    },

    // Aktualizuje informacje o wybranym modelu AI
    updateModelInfo() {
        const modelInfo = {
            'gpt-4o': 'GPT-4o: Najnowszy model. Doskonała analiza makro + news. ~$0.0025/request. Czas: 2-5s.',
            'gpt-4o-mini': 'GPT-4o Mini (Zalecany): Najlepszy stosunek jakości do ceny. Szybszy i 10x tańszy (~$0.0001/request). Doskonała analiza. Czas: 1-3s.',
            'gpt-4-turbo': 'GPT-4 Turbo: Głębsza analiza, więcej kontekstu. ~$0.01/request. Czas: 5-10s.',
            'gpt-4': 'GPT-4: Klasyczny model, sprawdzony. ~$0.03/request. Czas: 5-10s.',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo: Najtańszy (~$0.0005/request). Podstawowa analiza. Czas: 1-2s.'
        };
        this.modelInfoText = modelInfo[this.aiModel] || modelInfo['gpt-4o-mini'];
    }
};
