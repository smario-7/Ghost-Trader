// Main Application - Alpine.js Initialization
// Główna funkcja inicjalizująca aplikację Trading Bot

// Informacje o modelach AI
const modelInfo = {
    'gpt-4o': 'GPT-4o: Najnowszy model. Doskonała analiza makro + news. ~$0.0025/request. Czas: 2-5s.',
    'gpt-4o-mini': 'GPT-4o Mini (Zalecany): Najlepszy stosunek jakości do ceny. Szybszy i 10x tańszy (~$0.0001/request). Doskonała analiza. Czas: 1-3s.',
    'gpt-4-turbo': 'GPT-4 Turbo: Głębsza analiza, więcej kontekstu. ~$0.01/request. Czas: 5-10s.',
    'gpt-4': 'GPT-4: Klasyczny model, sprawdzony. ~$0.03/request. Czas: 5-10s.',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo: Najtańszy (~$0.0005/request). Podstawowa analiza. Czas: 1-2s.'
};

// Główna funkcja Alpine.js
function tradingBot() {
    return {
        // ===== STAN GLOBALNY =====
        
        // Aktualny widok (dashboard, strategies, ai-analysis, charts)
        currentView: 'dashboard',
        
        // Dane aplikacji
        statistics: null,
        strategies: [],
        signals: [],
        activity: [],
        uniqueSymbols: [],
        technicalParams: null,
        macroData: null,
        
        // Stany ładowania
        loading: {
            statistics: false,
            strategies: false,
            signals: false,
            activity: false,
            aiAnalysis: false,
            tokenStats: false,
            analysisConfig: false
        },
        
        // Komunikaty
        errorMessage: '',
        successMessage: '',
        backendWarning: false,
        
        // Autoryzacja
        apiKey: null,
        showApiKeyModal: false,
        apiKeyInput: '',
        
        // UI state
        lastUpdate: '-',
        checkInterval: 15,
        currentTime: '',
        currentDate: '',
        refreshIndicators: {
            stats: '',
            signals: '',
            activity: '',
            aiAnalysis: ''
        },
        
        // ===== AI ANALYSIS =====
        
        aiModel: 'gpt-4o-mini',
        modelInfoText: modelInfo['gpt-4o-mini'],
        lastAnalysis: '-',
        apiCallsToday: 0,
        
        // Wyniki analiz AI
        aiAnalysisResults: [],
        aiAnalysisFilter: {
            symbol: '',
            signal: ''
        },
        currentAISignal: null,
        
        // Statystyki tokenów
        tokenStats: {
            total_tokens: 0,
            total_cost: 0,
            analyses_count: 0,
            avg_tokens_per_analysis: 0,
            today_tokens: 0,
            today_cost: 0,
            today_analyses: 0
        },
        
        // Konfiguracja analiz
        analysisConfig: {
            interval: 15,
            notificationThreshold: 60,
            isActive: true,
            enabledSymbols: []
        },
        
        // Symbole do wyboru
        allSymbols: {
            forex: ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 'USD/CAD', 'NZD/USD'],
            indices: ['SPX/USD', 'DJI/USD', 'IXIC/USD', 'RUT/USD'],
            stocks: ['AAPL/USD', 'MSFT/USD', 'GOOGL/USD', 'AMZN/USD', 'TSLA/USD', 'META/USD', 'NVDA/USD'],
            metals: ['XAU/USD', 'XAG/USD', 'XPT/USD', 'XPD/USD']
        },
        selectedSymbols: [],
        selectAllSymbols: false,
        
        // Modal szczegółów analizy
        analysisModal: {
            open: false,
            data: null,
            activeTab: 'ai'
        },
        
        // ===== STRATEGIES =====
        
        modal: {
            open: false,
            mode: 'add',
            strategyId: null,
            formData: {
                name: '',
                strategy_type: '',
                symbol: '',
                timeframe: '1h',
                is_active: true
            },
            formParameters: {}
        },
        
        // ===== CHARTS =====
        
        chartSettings: {
            symbol: 'EUR/USD',
            timeframe: '1h',
            period: '1mo',
            type: 'candlestick',
            indicators: {
                ma: false,
                rsi: false,
                macd: false,
                bollinger: false
            }
        },
        
        chartInstances: {
            main: null,
            rsi: null,
            macd: null,
            bollinger: null
        },
        
        chartSeries: {
            main: null,
            ma50: null,
            ma200: null
        },
        
        chartData: {
            candles: [],
            indicators: null,
            current_price: null
        },
        
        chartLoading: false,
        chartInitialized: false,
        
        // ===== SSE =====
        
        sseConnection: null,
        
        // ===== INICJALIZACJA =====
        
        async init() {
            try {
                // Uruchom zegar natychmiast
                this.updateClock();
                
                // Sprawdź czy jest API key
                const hasApiKey = localStorage.getItem('api_key') || sessionStorage.getItem('api_key');
                
                if (!hasApiKey) {
                    // Pokaż modal z prośbą o API key
                    console.log('Brak API Key - pokazuję modal');
                    this.showApiKeyModal = true;
                    
                    // Wymuś przerysowanie DOM
                    this.$nextTick(() => {
                        console.log('Modal powinien być widoczny, showApiKeyModal =', this.showApiKeyModal);
                        const modalElement = document.querySelector('.modal[x-show="showApiKeyModal"]');
                        if (modalElement) {
                            console.log('Element modala znaleziony, display:', window.getComputedStyle(modalElement).display);
                        } else {
                            console.warn('Element modala NIE został znaleziony!');
                        }
                    });
                    
                    // Zatrzymaj dalsze ładowanie
                    return;
                }
                
                // Załaduj wszystkie dane równolegle
                await Promise.all([
                    this.loadStatistics(),
                    this.loadStrategies(),
                    this.loadRecentSignals(),
                    this.loadBotActivity(),
                    this.loadAIAnalysisResults(),
                    this.loadTokenStatistics(),
                    this.loadAnalysisConfig(),
                    this.loadMacroData()
                ]);
                
                this.updateLastUpdate();
                
                // Połącz SSE dla real-time updates (DOPIERO po załadowaniu danych)
                // W tym momencie API key już jest w sessionStorage
                this.connectSSE();
                
                // Automatyczne odświeżanie co 30s
                setInterval(() => {
                    this.loadStatistics();
                    this.loadRecentSignals();
                    this.loadBotActivity();
                    this.updateLastUpdate();
                }, 30000);
                
                // Dodatkowe odświeżanie statystyk co 60s
                setInterval(() => {
                    this.loadStatistics();
                    this.updateLastUpdate();
                }, 60000);
                
                // Aktualizacja czasu ostatniej analizy AI
                setInterval(() => {
                    const now = new Date();
                    this.lastAnalysis = now.toLocaleTimeString('pl-PL');
                }, 1000);
                
                // Aktualizacja zegara co sekundę
                setInterval(() => {
                    this.updateClock();
                }, 1000);
                
            } catch (error) {
                if (error.message && error.message.includes('Backend nie jest dostępny')) {
                    this.showError(error.message);
                } else {
                    this.showError(`Błąd inicjalizacji: ${error.message}`);
                }
            }
        },
        
        // ===== ZEGAR =====
        
        updateClock() {
            try {
                // Pobierz aktualny czas w strefie Warsaw
                const now = new Date();
                
                // Użyj Intl.DateTimeFormat dla strefy Warsaw
                const timeFormatter = new Intl.DateTimeFormat('pl-PL', {
                    timeZone: 'Europe/Warsaw',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                });
                
                const dateFormatter = new Intl.DateTimeFormat('pl-PL', {
                    timeZone: 'Europe/Warsaw',
                    weekday: 'long',
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit'
                });
                
                // Formatuj czas (HH:MM:SS)
                this.currentTime = timeFormatter.format(now);
                
                // Formatuj datę (Dzień tygodnia, DD.MM.YYYY)
                const dateParts = dateFormatter.formatToParts(now);
                const weekday = dateParts.find(p => p.type === 'weekday').value;
                const day = dateParts.find(p => p.type === 'day').value;
                const month = dateParts.find(p => p.type === 'month').value;
                const year = dateParts.find(p => p.type === 'year').value;
                
                // Kapitalizuj pierwszą literę dnia tygodnia
                const weekdayCapitalized = weekday.charAt(0).toUpperCase() + weekday.slice(1);
                
                this.currentDate = `${weekdayCapitalized}, ${day}.${month}.${year}`;
            } catch (error) {
                console.error('Błąd aktualizacji zegara:', error);
                this.currentTime = '--:--:--';
                this.currentDate = 'Błąd';
            }
        },
        
        // ===== API KEY MANAGEMENT =====
        
        async submitApiKey() {
            if (this.apiKeyInput && this.apiKeyInput.trim()) {
                const key = this.apiKeyInput.trim();
                sessionStorage.setItem('api_key', key);
                localStorage.setItem('api_key', key);
                this.apiKey = key;
                this.showApiKeyModal = false;
                this.apiKeyInput = '';
                
                this.showSuccess('API Key zapisany pomyślnie!');
                
                // Załaduj dane
                try {
                    await Promise.all([
                        this.loadStatistics(),
                        this.loadStrategies(),
                        this.loadRecentSignals(),
                        this.loadBotActivity(),
                        this.loadAIAnalysisResults(),
                        this.loadTokenStatistics(),
                        this.loadAnalysisConfig()
                    ]);
                    
                    this.updateLastUpdate();
                    
                    // Połącz SSE
                    this.connectSSE();
                } catch (error) {
                    this.showError(`Błąd ładowania danych: ${error.message}`);
                }
            }
        },
        
        // ===== IMPORT METOD Z KOMPONENTÓW =====
        
        ...dashboardMethods,
        ...strategiesMethods,
        ...aiAnalysisMethods,
        ...chartsMethods,
        ...apiUtils
    };
}
