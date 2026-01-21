// Charts Component Methods
// Metody związane z wykresami tradingowymi (TradingView Lightweight Charts)

const chartsMethods = {
    // Inicjalizuje główny wykres
    initChart() {
        if (this.chartInitialized) {
            console.log('Chart already initialized');
            return;
        }
        
        console.log('Initializing chart...');
        
        const container = document.getElementById('main-chart');
        if (!container) {
            console.error('Chart container #main-chart not found');
            return;
        }

        // Sprawdź czy LightweightCharts jest dostępne
        if (typeof LightweightCharts === 'undefined') {
            console.error('LightweightCharts library not loaded');
            this.showError('Biblioteka wykresów nie została załadowana. Odśwież stronę.');
            return;
        }

        console.log('Creating chart instance...');
        
        // Utwórz instancję wykresu
        this.chartInstances.main = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 600,
            layout: {
                background: { color: '#0f172a' },
                textColor: '#e2e8f0'
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' }
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal
            },
            rightPriceScale: {
                borderColor: '#334155'
            },
            timeScale: {
                borderColor: '#334155',
                timeVisible: true,
                secondsVisible: false
            }
        });

        // Responsywność - dostosuj rozmiar wykresu do okna
        window.addEventListener('resize', () => {
            if (this.chartInstances.main) {
                this.chartInstances.main.applyOptions({
                    width: container.clientWidth
                });
            }
        });

        // Dodaj serię świecową jako domyślną
        this.updateChartType();
        
        this.chartInitialized = true;
        
        // Załaduj dane
        this.loadChartData();
    },

    // Zmienia typ wykresu (candlestick, line, bar)
    setChartType(type) {
        this.chartSettings.type = type;
        this.updateChartType();
    },

    // Aktualizuje typ serii na wykresie
    updateChartType() {
        if (!this.chartInstances.main) return;

        // Usuń poprzednią serię jeśli istnieje
        if (this.chartSeries.main) {
            this.chartInstances.main.removeSeries(this.chartSeries.main);
        }

        // Dodaj nową serię w zależności od typu
        if (this.chartSettings.type === 'candlestick') {
            this.chartSeries.main = this.chartInstances.main.addCandlestickSeries({
                upColor: '#10b981',
                downColor: '#ef4444',
                borderUpColor: '#10b981',
                borderDownColor: '#ef4444',
                wickUpColor: '#10b981',
                wickDownColor: '#ef4444'
            });
        } else if (this.chartSettings.type === 'line') {
            this.chartSeries.main = this.chartInstances.main.addLineSeries({
                color: '#667eea',
                lineWidth: 2
            });
        } else if (this.chartSettings.type === 'bar') {
            this.chartSeries.main = this.chartInstances.main.addBarSeries({
                upColor: '#10b981',
                downColor: '#ef4444'
            });
        }

        // Ponownie załaduj dane jeśli są dostępne
        if (this.chartData.candles && this.chartData.candles.length > 0) {
            this.renderChartData();
        }
    },

    // Pobiera dane wykresu z backendu
    async loadChartData() {
        try {
            this.chartLoading = true;
            
            const params = new URLSearchParams({
                symbol: this.chartSettings.symbol,
                timeframe: this.chartSettings.timeframe,
                period: this.chartSettings.period
            });
            
            const data = await this.apiCall(`/chart-data?${params}`);
            this.chartData = data;
            
            // Renderuj dane na wykresie
            this.renderChartData();
            
        } catch (error) {
            console.error('Error loading chart data:', error);
            this.showError(`Błąd ładowania danych wykresu: ${error.message}`);
        } finally {
            this.chartLoading = false;
        }
    },

    // Renderuje dane na wykresie
    renderChartData() {
        if (!this.chartSeries.main || !this.chartData.candles || !this.chartData.candles.length) {
            console.warn('Cannot render chart: missing series or data');
            return;
        }

        // Funkcja pomocnicza do konwersji Unix timestamp na format Lightweight Charts
        const convertTime = (timestamp) => {
            // Lightweight Charts akceptuje Unix timestamp (sekundy) dla większości timeframe'ów
            // Ale dla timeframe >= 1d może wymagać formatu {year, month, day}
            if (this.chartSettings.timeframe === '1d' || this.chartSettings.timeframe === '1w') {
                const date = new Date(timestamp * 1000);
                return {
                    year: date.getFullYear(),
                    month: date.getMonth() + 1,
                    day: date.getDate()
                };
            }
            // Dla mniejszych timeframe'ów używamy Unix timestamp
            return timestamp;
        };

        // Przygotuj dane w zależności od typu wykresu
        let chartData;
        
        if (this.chartSettings.type === 'candlestick' || this.chartSettings.type === 'bar') {
            // Dane OHLC dla świec i słupków
            chartData = this.chartData.candles.map(c => ({
                time: convertTime(c.time),
                open: parseFloat(c.open),
                high: parseFloat(c.high),
                low: parseFloat(c.low),
                close: parseFloat(c.close)
            }));
        } else {
            // Dane tylko z ceną zamknięcia dla linii
            chartData = this.chartData.candles.map(c => ({
                time: convertTime(c.time),
                value: parseFloat(c.close)
            }));
        }

        console.log('Rendering chart data:', chartData.length, 'points');
        this.chartSeries.main.setData(chartData);

        // Renderuj aktywne wskaźniki
        if (this.chartSettings.indicators.ma) {
            this.renderMovingAverages();
        }
        if (this.chartSettings.indicators.rsi) {
            this.renderRSI();
        }
        if (this.chartSettings.indicators.macd) {
            this.renderMACD();
        }
        if (this.chartSettings.indicators.bollinger) {
            this.renderBollinger();
        }
    },

    // Renderuje średnie kroczące (MA50, MA200) jako overlay
    renderMovingAverages() {
        if (!this.chartInstances.main || !this.chartData.indicators) return;

        // Usuń poprzednie serie MA jeśli istnieją
        if (this.chartSeries.ma50) {
            this.chartInstances.main.removeSeries(this.chartSeries.ma50);
        }
        if (this.chartSeries.ma200) {
            this.chartInstances.main.removeSeries(this.chartSeries.ma200);
        }

        // Dodaj MA50
        if (this.chartData.indicators.sma50) {
            this.chartSeries.ma50 = this.chartInstances.main.addLineSeries({
                color: '#f59e0b',
                lineWidth: 2,
                title: 'MA50'
            });
            this.chartSeries.ma50.setData(this.chartData.indicators.sma50);
        }

        // Dodaj MA200
        if (this.chartData.indicators.sma200) {
            this.chartSeries.ma200 = this.chartInstances.main.addLineSeries({
                color: '#3b82f6',
                lineWidth: 2,
                title: 'MA200'
            });
            this.chartSeries.ma200.setData(this.chartData.indicators.sma200);
        }
    },

    // Renderuje RSI w osobnym panelu
    renderRSI() {
        if (!this.chartData.indicators || !this.chartData.indicators.rsi) return;

        const container = document.getElementById('rsi-chart');
        if (!container) return;

        // Usuń poprzedni wykres jeśli istnieje
        if (this.chartInstances.rsi) {
            container.innerHTML = '';
        }

        // Utwórz nowy wykres RSI
        this.chartInstances.rsi = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 150,
            layout: {
                background: { color: '#0f172a' },
                textColor: '#e2e8f0'
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' }
            },
            rightPriceScale: {
                borderColor: '#334155'
            },
            timeScale: {
                borderColor: '#334155',
                visible: false
            }
        });

        // Dodaj linię RSI
        const rsiSeries = this.chartInstances.rsi.addLineSeries({
            color: '#a855f7',
            lineWidth: 2
        });
        rsiSeries.setData(this.chartData.indicators.rsi);

        // Dodaj poziomy oversold (30) i overbought (70)
        rsiSeries.createPriceLine({
            price: 30,
            color: '#10b981',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Oversold'
        });
        rsiSeries.createPriceLine({
            price: 70,
            color: '#ef4444',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Overbought'
        });

        // Synchronizuj oś czasu z głównym wykresem
        if (this.chartInstances.main) {
            this.chartInstances.main.timeScale().subscribeVisibleLogicalRangeChange((timeRange) => {
                this.chartInstances.rsi.timeScale().setVisibleLogicalRange(timeRange);
            });
        }
    },

    // Renderuje MACD w osobnym panelu
    renderMACD() {
        if (!this.chartData.indicators || !this.chartData.indicators.macd) return;

        const container = document.getElementById('macd-chart');
        if (!container) return;

        // Usuń poprzedni wykres jeśli istnieje
        if (this.chartInstances.macd) {
            container.innerHTML = '';
        }

        // Utwórz nowy wykres MACD
        this.chartInstances.macd = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 150,
            layout: {
                background: { color: '#0f172a' },
                textColor: '#e2e8f0'
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' }
            },
            rightPriceScale: {
                borderColor: '#334155'
            },
            timeScale: {
                borderColor: '#334155',
                visible: false
            }
        });

        // Dodaj histogram MACD
        const histogramSeries = this.chartInstances.macd.addHistogramSeries({
            color: '#667eea',
            priceFormat: {
                type: 'price',
                precision: 4,
                minMove: 0.0001
            }
        });
        
        // Przygotuj dane histogramu z kolorami
        const histogramData = this.chartData.indicators.macd.histogram.map(point => ({
            time: point.time,
            value: point.value,
            color: point.value >= 0 ? '#10b981' : '#ef4444'
        }));
        histogramSeries.setData(histogramData);

        // Dodaj linię MACD
        const macdLineSeries = this.chartInstances.macd.addLineSeries({
            color: '#3b82f6',
            lineWidth: 2
        });
        macdLineSeries.setData(this.chartData.indicators.macd.macd_line);

        // Dodaj linię sygnału
        const signalLineSeries = this.chartInstances.macd.addLineSeries({
            color: '#f59e0b',
            lineWidth: 2
        });
        signalLineSeries.setData(this.chartData.indicators.macd.signal_line);

        // Synchronizuj oś czasu z głównym wykresem
        if (this.chartInstances.main) {
            this.chartInstances.main.timeScale().subscribeVisibleLogicalRangeChange((timeRange) => {
                this.chartInstances.macd.timeScale().setVisibleLogicalRange(timeRange);
            });
        }
    },

    // Renderuje Bollinger Bands w osobnym panelu
    renderBollinger() {
        if (!this.chartData.indicators || !this.chartData.indicators.bollinger) return;

        const container = document.getElementById('bollinger-chart');
        if (!container) return;

        // Usuń poprzedni wykres jeśli istnieje
        if (this.chartInstances.bollinger) {
            container.innerHTML = '';
        }

        // Utwórz nowy wykres Bollinger
        this.chartInstances.bollinger = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 150,
            layout: {
                background: { color: '#0f172a' },
                textColor: '#e2e8f0'
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' }
            },
            rightPriceScale: {
                borderColor: '#334155'
            },
            timeScale: {
                borderColor: '#334155',
                visible: false
            }
        });

        // Dodaj górne pasmo
        const upperBandSeries = this.chartInstances.bollinger.addLineSeries({
            color: '#ef4444',
            lineWidth: 1
        });
        upperBandSeries.setData(this.chartData.indicators.bollinger.upper);

        // Dodaj środkowe pasmo (SMA)
        const middleBandSeries = this.chartInstances.bollinger.addLineSeries({
            color: '#667eea',
            lineWidth: 2
        });
        middleBandSeries.setData(this.chartData.indicators.bollinger.middle);

        // Dodaj dolne pasmo
        const lowerBandSeries = this.chartInstances.bollinger.addLineSeries({
            color: '#10b981',
            lineWidth: 1
        });
        lowerBandSeries.setData(this.chartData.indicators.bollinger.lower);

        // Synchronizuj oś czasu z głównym wykresem
        if (this.chartInstances.main) {
            this.chartInstances.main.timeScale().subscribeVisibleLogicalRangeChange((timeRange) => {
                this.chartInstances.bollinger.timeScale().setVisibleLogicalRange(timeRange);
            });
        }
    },

    // Włącza/wyłącza wskaźnik
    toggleIndicator(indicator) {
        this.chartSettings.indicators[indicator] = !this.chartSettings.indicators[indicator];
        
        if (this.chartSettings.indicators[indicator]) {
            // Włącz wskaźnik
            if (indicator === 'ma') this.renderMovingAverages();
            if (indicator === 'rsi') this.renderRSI();
            if (indicator === 'macd') this.renderMACD();
            if (indicator === 'bollinger') this.renderBollinger();
        } else {
            // Wyłącz wskaźnik
            if (indicator === 'ma') {
                if (this.chartSeries.ma50) {
                    this.chartInstances.main.removeSeries(this.chartSeries.ma50);
                    this.chartSeries.ma50 = null;
                }
                if (this.chartSeries.ma200) {
                    this.chartInstances.main.removeSeries(this.chartSeries.ma200);
                    this.chartSeries.ma200 = null;
                }
            }
            if (indicator === 'rsi' && this.chartInstances.rsi) {
                document.getElementById('rsi-chart').innerHTML = '';
                this.chartInstances.rsi = null;
            }
            if (indicator === 'macd' && this.chartInstances.macd) {
                document.getElementById('macd-chart').innerHTML = '';
                this.chartInstances.macd = null;
            }
            if (indicator === 'bollinger' && this.chartInstances.bollinger) {
                document.getElementById('bollinger-chart').innerHTML = '';
                this.chartInstances.bollinger = null;
            }
        }
    }
};
