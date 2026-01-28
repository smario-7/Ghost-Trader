const settingsMethods = {
    schedulerConfig: {
        signal_check_enabled: true,
        ai_analysis_enabled: true,
        signal_check_interval: 15,
        ai_analysis_interval: 30,
        signal_hours_start: '00:00',
        signal_hours_end: '23:59',
        ai_hours_start: '00:00',
        ai_hours_end: '23:59',
        signal_active_days: '1,2,3,4,5,6,7',
        ai_active_days: '1,2,3,4,5,6,7'
    },
    
    schedulerStatus: null,
    
    async loadSchedulerConfig() {
        try {
            this.loading.settings = true;
            const response = await apiCall('/scheduler/config');
            
            if (response && response.success) {
                // Upewnij się, że konfiguracja jest poprawnie przypisana
                if (response.config) {
                    // Zaktualizuj wszystkie pola konfiguracji
                    Object.assign(this.schedulerConfig, response.config);
                }
                if (response.status) {
                    this.schedulerStatus = response.status;
                }
                console.log('Scheduler config loaded:', this.schedulerConfig);
            } else {
                console.warn('Failed to load scheduler config:', response);
                // Nie pokazuj błędu jeśli to tylko brak odpowiedzi - użyj domyślnych wartości
            }
        } catch (error) {
            console.error('Error loading scheduler config:', error);
            // Nie pokazuj błędu użytkownikowi - użyj domyślnych wartości
            // this.showError('Nie udało się załadować konfiguracji');
        } finally {
            this.loading.settings = false;
        }
    },
    
    async saveSchedulerConfig() {
        try {
            this.loading.settings = true;
            
            const response = await apiCall('/scheduler/config', 'PUT', this.schedulerConfig);
            
            if (response && response.success) {
                // Zaktualizuj konfigurację z odpowiedzi serwera
                if (response.config) {
                    Object.assign(this.schedulerConfig, response.config);
                }
                this.showSuccess('Konfiguracja zapisana pomyślnie');
                
                // Odśwież status
                await this.loadSchedulerStatus();
                
                console.log('Scheduler config saved:', this.schedulerConfig);
            } else {
                this.showError('Błąd zapisu konfiguracji');
            }
        } catch (error) {
            console.error('Error saving scheduler config:', error);
            this.showError('Nie udało się zapisać konfiguracji');
        } finally {
            this.loading.settings = false;
        }
    },
    
    async loadSchedulerStatus() {
        try {
            const response = await apiCall('/scheduler/status');
            
            if (response && response.success && response.status) {
                this.schedulerStatus = response.status;
                console.log('Scheduler status loaded:', this.schedulerStatus);
            }
        } catch (error) {
            console.error('Error loading scheduler status:', error);
            // Nie pokazuj błędu - status jest opcjonalny
        }
    },
    
    async toggleSignalCheck() {
        try {
            // Zmień wartość lokalnie
            const oldValue = this.schedulerConfig.signal_check_enabled;
            const newValue = !oldValue;
            this.schedulerConfig.signal_check_enabled = newValue;
            
            // Wymuś aktualizację widoku
            this.$nextTick(() => {
                // Zapisz konfigurację
                this.saveSchedulerConfig().then(() => {
                    // Odśwież status po zapisaniu
                    this.loadSchedulerStatus();
                }).catch((error) => {
                    // W przypadku błędu przywróć poprzednią wartość
                    this.schedulerConfig.signal_check_enabled = oldValue;
                    console.error('Error toggling signal check:', error);
                });
            });
        } catch (error) {
            console.error('Error toggling signal check:', error);
        }
    },
    
    async toggleAIAnalysis() {
        try {
            // Zmień wartość lokalnie
            const oldValue = this.schedulerConfig.ai_analysis_enabled;
            const newValue = !oldValue;
            this.schedulerConfig.ai_analysis_enabled = newValue;
            
            // Wymuś aktualizację widoku
            this.$nextTick(() => {
                // Zapisz konfigurację
                this.saveSchedulerConfig().then(() => {
                    // Odśwież status po zapisaniu
                    this.loadSchedulerStatus();
                }).catch((error) => {
                    // W przypadku błędu przywróć poprzednią wartość
                    this.schedulerConfig.ai_analysis_enabled = oldValue;
                    console.error('Error toggling AI analysis:', error);
                });
            });
        } catch (error) {
            console.error('Error toggling AI analysis:', error);
        }
    },
    
    isDayActive(type, day) {
        if (!this.schedulerConfig || !this.schedulerConfig[`${type}_active_days`]) {
            return false;
        }
        const activeDays = this.schedulerConfig[`${type}_active_days`].split(',').map(d => d.trim());
        return activeDays.includes(String(day));
    },
    
    async toggleDay(type, day) {
        const key = `${type}_active_days`;
        if (!this.schedulerConfig[key]) {
            this.schedulerConfig[key] = '1,2,3,4,5,6,7';
        }
        let activeDays = this.schedulerConfig[key].split(',').map(d => d.trim());
        const dayStr = String(day);
        
        if (activeDays.includes(dayStr)) {
            activeDays = activeDays.filter(d => d !== dayStr);
        } else {
            activeDays.push(dayStr);
            activeDays.sort((a, b) => parseInt(a) - parseInt(b));
        }
        
        this.schedulerConfig[key] = activeDays.join(',');
        
        // Automatycznie zapisz zmianę
        await this.saveSchedulerConfig();
    },
    
    getDayName(day) {
        const names = {
            '1': 'Pn',
            '2': 'Wt',
            '3': 'Śr',
            '4': 'Cz',
            '5': 'Pt',
            '6': 'So',
            '7': 'Nd'
        };
        return names[String(day)] || day;
    },
    
    getStatusText(type) {
        // Jeśli nie ma statusu, sprawdź bezpośrednio w konfiguracji
        if (!this.schedulerStatus) {
            if (type === 'signal_check') {
                return this.schedulerConfig?.signal_check_enabled ? '✅ Aktywne' : '⏸️ Wyłączone';
            } else if (type === 'ai_analysis') {
                return this.schedulerConfig?.ai_analysis_enabled ? '✅ Aktywne' : '⏸️ Wyłączone';
            }
            return '';
        }
        
        const status = this.schedulerStatus[type];
        if (!status) {
            // Fallback do konfiguracji
            if (type === 'signal_check') {
                return this.schedulerConfig?.signal_check_enabled ? '✅ Aktywne' : '⏸️ Wyłączone';
            } else if (type === 'ai_analysis') {
                return this.schedulerConfig?.ai_analysis_enabled ? '✅ Aktywne' : '⏸️ Wyłączone';
            }
            return '';
        }
        
        if (!status.enabled) {
            return '⏸️ Wyłączone';
        }
        
        if (!status.in_active_days) {
            return '📅 Nieaktywny dzień';
        }
        
        if (!status.in_time_window) {
            return '🕐 Poza harmonogramem';
        }
        
        return '✅ Aktywne';
    },
    
    getStatusClass(type) {
        // Jeśli nie ma statusu, sprawdź bezpośrednio w konfiguracji
        if (!this.schedulerStatus) {
            if (type === 'signal_check') {
                return this.schedulerConfig?.signal_check_enabled ? 'status-active' : 'status-disabled';
            } else if (type === 'ai_analysis') {
                return this.schedulerConfig?.ai_analysis_enabled ? 'status-active' : 'status-disabled';
            }
            return '';
        }
        
        const status = this.schedulerStatus[type];
        if (!status) {
            // Fallback do konfiguracji
            if (type === 'signal_check') {
                return this.schedulerConfig?.signal_check_enabled ? 'status-active' : 'status-disabled';
            } else if (type === 'ai_analysis') {
                return this.schedulerConfig?.ai_analysis_enabled ? 'status-active' : 'status-disabled';
            }
            return '';
        }
        
        if (status.should_run) return 'status-active';
        if (status.enabled) return 'status-paused';
        return 'status-disabled';
    },
    
    // ===== ACTIVITY LOGS =====
    
    // Uwaga: zmienne activityLogs i activityLogsFilter są zdefiniowane w main.js
    // Nie definiujemy ich tutaj, aby uniknąć konfliktów
    activityLogsLastId: 0,
    activityLogsPollingInterval: null,
    
    async loadActivityLogs() {
        try {
            const response = await apiCall('/activity-logs?limit=100');
            
            if (response && response.logs && response.logs.length > 0) {
                this.activityLogs = response.logs;
                // Znajdź największe ID (najnowszy log)
                this.activityLogsLastId = Math.max(...response.logs.map(log => log.id || 0));
            } else {
                this.activityLogs = [];
                this.activityLogsLastId = 0;
            }
        } catch (error) {
            console.error('Error loading activity logs:', error);
            this.activityLogs = [];
            this.activityLogsLastId = 0;
        }
    },
    
    startActivityLogsPolling() {
        // Zatrzymaj istniejący polling jeśli jest
        this.stopActivityLogsPolling();
        
        // Rozpocznij polling co 2 sekundy
        this.activityLogsPollingInterval = setInterval(async () => {
            try {
                const filter = this.activityLogsFilter ? `&log_type=${this.activityLogsFilter}` : '';
                const response = await apiCall(`/activity-logs/new?last_id=${this.activityLogsLastId}${filter}`);
                
                if (response.logs && response.logs.length > 0) {
                    // Dodaj nowe logi na początku listy
                    this.activityLogs = [...response.logs.reverse(), ...(this.activityLogs || [])];
                    
                    // Ogranicz do 200 logów
                    if (this.activityLogs.length > 200) {
                        this.activityLogs = this.activityLogs.slice(0, 200);
                    }
                    
                    // Zaktualizuj last_id
                    this.activityLogsLastId = response.last_id;
                    
                    // Auto-scroll do góry (najnowsze logi)
                    this.$nextTick(() => {
                        const container = document.querySelector('.logs-container');
                        if (container) {
                            container.scrollTop = 0;
                        }
                    });
                }
            } catch (error) {
                console.error('Error polling activity logs:', error);
            }
        }, 2000);
    },
    
    stopActivityLogsPolling() {
        if (this.activityLogsPollingInterval) {
            clearInterval(this.activityLogsPollingInterval);
            this.activityLogsPollingInterval = null;
        }
    },
    
    getFilteredActivityLogs() {
        if (!this.activityLogs || !Array.isArray(this.activityLogs)) {
            return [];
        }
        if (!this.activityLogsFilter) {
            return this.activityLogs;
        }
        return this.activityLogs.filter(log => log && log.log_type === this.activityLogsFilter);
    },
    
    getLogTypeIcon(type) {
        const icons = {
            'llm': '🤖',
            'telegram': '📱',
            'market_data': '📊',
            'signal': '🔔',
            'analysis': '📈'
        };
        return icons[type] || '📝';
    },
    
    formatLogTime(timestamp) {
        if (!timestamp) return '';
        
        try {
            // Obsługa różnych formatów timestamp
            let date;
            if (typeof timestamp === 'string') {
                // Jeśli zawiera 'T' to ISO format, jeśli nie to może być SQLite format
                if (timestamp.includes('T')) {
                    date = new Date(timestamp);
                } else {
                    // SQLite format: "2026-01-23 12:45:53"
                    date = new Date(timestamp.replace(' ', 'T'));
                }
            } else {
                date = new Date(timestamp);
            }
            
            // Sprawdź czy data jest poprawna
            if (isNaN(date.getTime())) {
                return timestamp;
            }
            
            // Zawsze zwracaj konkretną datę i godzinę z sekundami
            return date.toLocaleString('pl-PL', {
                timeZone: 'Europe/Warsaw',
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (e) {
            console.error('Error formatting log time:', e, timestamp);
            return timestamp;
        }
    }
};
