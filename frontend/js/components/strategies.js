// Strategies Component Methods
// Metody związane z zarządzaniem strategiami tradingowymi (CRUD)

const strategiesMethods = {
    // Otwiera modal do dodawania/edycji strategii
    openModal(mode = 'add', id = null) {
        this.modal.open = true;
        this.modal.mode = mode;
        this.modal.strategyId = id;
        
        if (mode === 'add') {
            // Resetuj formularz dla nowej strategii
            this.modal.formData = {
                name: '',
                strategy_type: '',
                symbol: '',
                timeframe: '1h',
                is_active: true
            };
            this.modal.formParameters = {};
        } else if (mode === 'edit' && id) {
            // Załaduj dane strategii do edycji
            this.loadStrategyForEdit(id);
        }
    },

    // Ładuje dane strategii do formularza edycji
    async loadStrategyForEdit(id) {
        try {
            const data = await apiCall(`/strategies/${id}`);
            const strategy = data.strategy;
            
            this.modal.formData = {
                name: strategy.name,
                strategy_type: strategy.strategy_type,
                symbol: strategy.symbol,
                timeframe: strategy.timeframe,
                is_active: strategy.is_active
            };
            
            this.modal.formParameters = { ...strategy.parameters };
        } catch (error) {
            this.showError(`Błąd ładowania strategii: ${error.message}`);
        }
    },

    // Aktualizuje formularz parametrów w zależności od typu strategii
    updateParametersForm() {
        if (!this.modal.formData.strategy_type) {
            this.modal.formParameters = {};
            return;
        }
        
        const type = this.modal.formData.strategy_type;
        
        // Ustaw domyślne parametry dla każdego typu strategii
        if (type === 'RSI' && !this.modal.formParameters.period) {
            this.modal.formParameters = { 
                period: 14, 
                oversold: 30, 
                overbought: 70 
            };
        } else if (type === 'MACD' && !this.modal.formParameters.fast_period) {
            this.modal.formParameters = { 
                fast_period: 12, 
                slow_period: 26, 
                signal_period: 9 
            };
        } else if (type === 'BOLLINGER_BANDS' && !this.modal.formParameters.period) {
            this.modal.formParameters = { 
                period: 20, 
                std_dev: 2 
            };
        } else if (type === 'MOVING_AVERAGE' && !this.modal.formParameters.short_period) {
            this.modal.formParameters = { 
                short_period: 50, 
                long_period: 200 
            };
        }
    },

    // Zamyka modal i resetuje formularz
    closeModal() {
        this.modal.open = false;
        this.modal.formData = {
            name: '',
            strategy_type: '',
            symbol: '',
            timeframe: '1h',
            is_active: true
        };
        this.modal.formParameters = {};
    },

    // Zapisuje strategię (dodaje nową lub aktualizuje istniejącą)
    async saveStrategy() {
        try {
            const strategyData = {
                name: this.modal.formData.name,
                strategy_type: this.modal.formData.strategy_type,
                symbol: this.modal.formData.symbol,
                timeframe: this.modal.formData.timeframe,
                parameters: { ...this.modal.formParameters },
                is_active: this.modal.formData.is_active
            };
            
            if (this.modal.strategyId) {
                // Aktualizuj istniejącą strategię
                await apiCall(`/strategies/${this.modal.strategyId}`, 'PUT', strategyData);
                this.showSuccess('Strategia zaktualizowana pomyślnie');
            } else {
                // Dodaj nową strategię
                await apiCall('/strategies', 'POST', strategyData);
                this.showSuccess('Strategia utworzona pomyślnie');
            }
            
            this.closeModal();
            await this.loadStrategies();
            await this.loadStatistics();
        } catch (error) {
            this.showError(`Błąd zapisywania: ${error.message}`);
        }
    },

    // Usuwa strategię po potwierdzeniu
    async deleteStrategy(id) {
        if (!confirm('Czy na pewno chcesz usunąć tę strategię?')) {
            return;
        }
        
        try {
            await apiCall(`/strategies/${id}`, 'DELETE');
            this.showSuccess('Strategia usunięta pomyślnie');
            await this.loadStrategies();
            await this.loadStatistics();
        } catch (error) {
            this.showError(`Błąd usuwania: ${error.message}`);
        }
    },

    // Uruchamia analizę AI dla wybranej strategii
    async runAIAnalysis() {
        try {
            this.loading.strategies = true;
            
            // Znajdź pierwszą aktywną strategię
            const strategy = this.strategies.find(s => s.is_active);
            if (!strategy) {
                this.showError('Brak aktywnych strategii do analizy');
                return;
            }
            
            const key = await this.getApiKey();
            
            // Zbuduj URL
            const url = `/api/ai/analyze?symbol=${strategy.symbol}&timeframe=${strategy.timeframe}`;
            
            // Wywołaj endpoint AI
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-API-Key': key,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            this.showSuccess(`✅ Analiza AI zakończona: ${result.signal}`);
            this.apiCallsToday += 1;
            
            // Odśwież dane
            await this.loadRecentSignals();
            await this.loadBotActivity();
            
        } catch (error) {
            console.error('AI Analysis error:', error);
            this.showError(`❌ Błąd analizy AI: ${error.message}`);
        } finally {
            this.loading.strategies = false;
        }
    }
};
