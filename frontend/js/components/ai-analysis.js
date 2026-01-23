// AI Analysis Component Methods
// Metody związane z analizą AI: wyniki, statystyki tokenów, konfiguracja

const aiAnalysisMethods = {
    // Ładuje wyniki analiz AI z backendu
    async loadAIAnalysisResults() {
        try {
            this.loading.aiAnalysis = true;
            const params = new URLSearchParams();
            
            // Filtruj po symbolu jeśli wybrano
            if (this.aiAnalysisFilter.symbol) {
                params.append('symbol', this.aiAnalysisFilter.symbol);
            }
            params.append('limit', '50');
            
            const data = await apiCall(`/ai/analysis-results?${params}`);
            this.aiAnalysisResults = data.results || [];
            
            // Filtruj po sygnale (frontend)
            if (this.aiAnalysisFilter.signal) {
                this.aiAnalysisResults = this.aiAnalysisResults.filter(
                    r => r.final_signal === this.aiAnalysisFilter.signal
                );
            }
            
            this.refreshIndicators.aiAnalysis = '✓';
            setTimeout(() => this.refreshIndicators.aiAnalysis = '', 2000);
        } catch (error) {
            if (error && error.silent) return;
            this.showError(error.message);
        } finally {
            this.loading.aiAnalysis = false;
        }
    },

    // Ładuje statystyki użycia tokenów OpenAI
    async loadTokenStatistics() {
        try {
            const data = await apiCall('/ai/token-statistics');
            this.tokenStats = data;
        } catch (error) {
            if (error && error.silent) return;
            console.error('Error loading token stats:', error);
        }
    },

    // Ładuje konfigurację automatycznych analiz
    async loadAnalysisConfig() {
        try {
            const data = await apiCall('/ai/analysis-config');
            this.analysisConfig = {
                interval: data.analysis_interval,
                notificationThreshold: data.notification_threshold,
                isActive: data.is_active
            };
            this.selectedSymbols = data.enabled_symbols || [];
            this.selectAllSymbols = this.selectedSymbols.length === this.getAllSymbolsList().length;
        } catch (error) {
            if (error && error.silent) return;
            console.error('Error loading analysis config:', error);
        }
    },

    // Aktualizuje konfigurację analiz
    async updateAnalysisConfig() {
        try {
            await apiCall('/ai/analysis-config', 'PUT', {
                analysis_interval: this.analysisConfig.interval,
                notification_threshold: this.analysisConfig.notificationThreshold,
                is_active: this.analysisConfig.isActive,
                enabled_symbols: this.selectedSymbols
            });
            this.showSuccess('Konfiguracja zaktualizowana');
        } catch (error) {
            if (error && error.silent) return;
            this.showError(error.message);
        }
    },

    // Uruchamia ręczną analizę dla wybranych symboli
    async triggerManualAnalysis() {
        try {
            this.loading.aiAnalysis = true;
            this.showSuccess('Uruchamiam analizę... To może potrwać kilka minut.');
            
            const result = await apiCall('/ai/trigger-analysis', 'POST', {
                symbols: this.selectedSymbols.length > 0 ? this.selectedSymbols : null
            });
            
            this.showSuccess(result.message);
            await this.loadAIAnalysisResults();
            await this.loadTokenStatistics();
        } catch (error) {
            if (error && error.silent) return;
            this.showError(error.message);
        } finally {
            this.loading.aiAnalysis = false;
        }
    },

    // Otwiera modal ze szczegółami analizy
    async showAnalysisDetails(analysisId) {
        try {
            const data = await apiCall(`/ai/analysis-results/${analysisId}`);
            this.analysisModal.data = data;
            this.analysisModal.activeTab = 'ai';
            this.analysisModal.open = true;
        } catch (error) {
            if (error && error.silent) return;
            this.showError(`Błąd ładowania szczegółów: ${error.message}`);
        }
    },

    // Zamyka modal szczegółów analizy
    closeAnalysisModal() {
        this.analysisModal.open = false;
        this.analysisModal.data = null;
        this.analysisModal.activeTab = 'ai';
    },

    // Przełącza zakładkę w modalu szczegółów
    switchAnalysisTab(tab) {
        this.analysisModal.activeTab = tab;
    },

    // Zwraca pełną listę wszystkich symboli
    getAllSymbolsList() {
        return [
            ...this.allSymbols.forex,
            ...this.allSymbols.indices,
            ...this.allSymbols.stocks,
            ...this.allSymbols.metals
        ];
    },

    // Zaznacza/odznacza wszystkie symbole
    toggleAllSymbols() {
        if (this.selectAllSymbols) {
            this.selectedSymbols = this.getAllSymbolsList();
        } else {
            this.selectedSymbols = [];
        }
    }
};
