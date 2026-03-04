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

    // Pobiera unikalne symbole z aktywnych strategii (tylko poprawne formaty np. EUR/USD)
    async loadUniqueSymbols() {
        try {
            const data = await apiCall('/strategies');
            const strategies = Array.isArray(data.strategies) ? data.strategies : [];
            const symbols = strategies
                .filter(s => s.is_active && s.symbol)
                .map(s => typeof s.symbol === 'string' ? s.symbol.trim() : String(s.symbol))
                .filter(s => s.includes('/') && s.length >= 6);
            return [...new Set(symbols)];
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
            
            // Pobierz parametry techniczne z pierwszej aktywnej strategii
            this.updateTechnicalParams();
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

    // Aktualizuje parametry techniczne na podstawie aktywnych strategii
    updateTechnicalParams() {
        // Znajdź pierwszą aktywną strategię z parametrami technicznymi
        const activeStrategy = this.strategies.find(s => 
            s.is_active && 
            (s.strategy_type === 'RSI' || s.strategy_type === 'MACD' || 
             s.strategy_type === 'BOLLINGER_BANDS' || s.strategy_type === 'MOVING_AVERAGE')
        );
        
        if (activeStrategy) {
            this.technicalParams = {
                strategy_type: activeStrategy.strategy_type,
                symbol: activeStrategy.symbol,
                timeframe: activeStrategy.timeframe,
                parameters: activeStrategy.parameters
            };
        } else {
            // Ustaw domyślne wartości jeśli brak aktywnych strategii
            this.technicalParams = {
                strategy_type: 'DEFAULT',
                symbol: 'N/A',
                timeframe: 'N/A',
                parameters: {
                    rsi_period: 14,
                    rsi_oversold: 30,
                    rsi_overbought: 70,
                    macd_fast: 12,
                    macd_slow: 26,
                    macd_signal: 9,
                    bb_period: 20,
                    bb_std_dev: 2,
                    ma_short: 50,
                    ma_long: 200
                }
            };
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
            
            const apiBase = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
                ? 'http://localhost:8000' 
                : '';
            const url = `${apiBase}/stream/ai-updates?api_key=${encodeURIComponent(apiKey)}`;
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

    // Ładuje dane makroekonomiczne
    async loadMacroData() {
        try {
            const data = await apiCall('/macro-data');
            this.macroData = data;
        } catch (error) {
            if (error && error.silent) return;
            console.error('Error loading macro data:', error);
            // Nie pokazuj błędu użytkownikowi - dane makro są opcjonalne
        }
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
        // SQLite zwraca timestamp w UTC bez oznaczenia timezone
        // Dodajemy 'Z' aby JavaScript poprawnie zinterpretował jako UTC
        const utcString = timestamp.includes('Z') ? timestamp : timestamp + 'Z';
        return new Date(utcString).toLocaleString('pl-PL', {
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
