from AlgorithmImports import *

class ROEThresholdAlgorithm(QCAlgorithm):
    def Initialize(self):
        # Set start date and cash amount
        self.SetStartDate(2015, 1, 1)  # Adjust the date as needed
        self.SetCash(100000)  # Set your initial capital
        
        # Add ETFs for allocation
        self.ivv = self.AddEquity("IVV", Resolution.Daily).Symbol
        self.moat = self.AddEquity("MOAT", Resolution.Daily).Symbol
        
        # List of allowed stocks (filtered from Wharton Investment Competition universe)
        self.allowed_symbols = [
            "AAPL", "ACHC", "ADBE", "AEHR", "AEP", "AMD", "AMGN", "AMTX", "AMZN", "ARCB", "AVGO", "BECN", "BIDU", "CMCSA", "COST", "CPRX", "CSCO", "CTSH", "CZR", "DBX", "DLTR", "ETSY", "FTNT", "GILD", "GMAB", "GOOGL", "ILMN", "INTC", "JBLU", "KDP", "LULU", "MANH", "META", "MSFT", "NFLX", "NTES", "NVDA", "NXPI", "ORCL", "PEP", "PYPL", "QCOM", "REGN", "SBUX", "SEDG", "TSLA", "TXN", "ULTA", "ABBV", "ABT", "CNC", "CRH", "CRM", "CTVA", "CVS", "DOW", "EMN", "FMC", "FTS", "GM", "GSK", "IMAX", "JNJ", "MCK", "MRK", "NVO", "NVS", "PFE", "PKX", "SAP", "SNOW", "SPOT", "T", "TGT", "TJX", "TSM", "UNH"
        ]
        
        # Filter out non-U.S. stock exchanges and stocks with market cap below $10 billion
        self.symbols = []
        for symbol in self.allowed_symbols:
            security = self.AddEquity(symbol, Resolution.Daily)
            if security.Symbol.ID.Market == "usa" and self.GetFundamentals(symbol).MarketCap >= 10e9:
                self.symbols.append(security.Symbol)
        
        # Focus only on four sectors: Materials, Communication Services, Information Technology, and Health Care
        self.symbols = [s for s in self.symbols if self.GetFundamentals(s).AssetClassification.MorningstarSectorCode in [101, 102, 103, 104]]
        
        # Set a maximum of 10 stocks in the portfolio
        self.max_portfolio_size = 10
        
        # Track the initial buying price of each stock
        self.buy_prices = {}
        
        # Schedule the method to check ROE, ensuring the date is a trading day
        self.Schedule.On(self.DateRules.MonthStart(self.symbols[0]), self.TimeRules.AfterMarketOpen(self.symbols[0], 30), self.Rebalance)

    def Rebalance(self):
        # Get the fundamentals for each symbol
        candidates = []
        for symbol in self.symbols:
            fundamentals = self.GetFundamentals(symbol)
            if fundamentals:
                sector_code = fundamentals.AssetClassification.MorningstarSectorCode
                
                # Filter based on sector-specific criteria
                if sector_code == 103 or sector_code == 104:  # IT & Healthcare
                    if (fundamentals.OperationRatios.ROE.Value >= 0.15 and
                        fundamentals.Profitability.ProfitMargin >= 0.20 and
                        fundamentals.ValuationRatios.PriceToBook <= 5 and
                        fundamentals.OperationRatios.OperatingMargin >= 0.25 and
                        fundamentals.OperationRatios.GrossMargin >= 0.50 and
                        fundamentals.OperationRatios.RevenueGrowth >= 0.10 and
                        fundamentals.OperationRatios.AssetTurnover >= 0.5 and
                        fundamentals.OperationRatios.ReturnOnAssets >= 0.07 and
                        fundamentals.CashFlowStatement.FreeCashFlow > 0 and
                        fundamentals.BalanceSheet.CashRatio >= 0.7):
                        candidates.append(symbol)
                elif sector_code == 101:  # Materials
                    if (fundamentals.OperationRatios.ROE.Value >= 0.12 and
                        fundamentals.Profitability.ProfitMargin >= 0.10 and
                        fundamentals.ValuationRatios.PriceToBook <= 2 and
                        fundamentals.OperationRatios.OperatingMargin >= 0.10 and
                        0.20 <= fundamentals.OperationRatios.GrossMargin <= 0.30 and
                        fundamentals.OperationRatios.RevenueGrowth >= 0.08 and
                        fundamentals.OperationRatios.AssetTurnover >= 1.0 and
                        fundamentals.OperationRatios.ReturnOnAssets >= 0.05 and
                        fundamentals.CashFlowStatement.FreeCashFlow > 0 and
                        fundamentals.BalanceSheet.CashRatio >= 0.5):
                        candidates.append(symbol)
                elif sector_code == 102:  # Communication Services
                    if (fundamentals.OperationRatios.ROE.Value >= 0.12 and
                        fundamentals.Profitability.ProfitMargin >= 0.15 and
                        fundamentals.ValuationRatios.PriceToBook <= 2 and
                        fundamentals.OperationRatios.OperatingMargin >= 0.17 and
                        0.20 <= fundamentals.OperationRatios.GrossMargin <= 0.30 and
                        fundamentals.OperationRatios.RevenueGrowth >= 0.08 and
                        fundamentals.OperationRatios.AssetTurnover >= 1.0 and
                        fundamentals.OperationRatios.ReturnOnAssets >= 0.05 and
                        fundamentals.CashFlowStatement.FreeCashFlow > 0 and
                        fundamentals.BalanceSheet.CashRatio >= 0.5):
                        candidates.append(symbol)
        
        # Sort candidates by ROE descending and select top 10
        candidates = sorted(candidates, key=lambda x: self.GetFundamentals(x).OperationRatios.ROE.Value, reverse=True)
        selected = candidates[:self.max_portfolio_size]
        
        # If less than 10 candidates, add the next best until we reach 10
        if len(selected) < self.max_portfolio_size:
            additional_candidates = [symbol for symbol in self.symbols if symbol not in selected]
            additional_candidates = sorted(additional_candidates, key=lambda x: self.GetFundamentals(x).OperationRatios.ROE.Value, reverse=True)
            selected += additional_candidates[:self.max_portfolio_size - len(selected)]
        
        # Liquidate stocks that are no longer in the top 10 or hit sell thresholds
        for holding in self.Portfolio.Values:
            if holding.Invested:
                current_price = self.Securities[holding.Symbol].Price
                initial_price = self.buy_prices.get(holding.Symbol, current_price)
                price_change = (current_price - initial_price) / initial_price
                
                # Sell if stock has dropped more than 10% or gained more than 25%
                if holding.Symbol not in selected and holding.Symbol not in [self.ivv, self.moat]:
                    self.Liquidate(holding.Symbol)
                elif price_change <= -0.10 or price_change >= 0.25:
                    self.Liquidate(holding.Symbol)
        
        # Set fixed allocations for ETFs
        self.SetHoldings(self.ivv, 0.10)  # 10% allocation to IVV ETF
        self.SetHoldings(self.moat, 0.15)  # 15% allocation to MOAT ETF
        
        # Allocate remaining weight to selected stocks
        remaining_weight = 0.75  # 100% - 10% (IVV) - 15% (MOAT)
        weight = remaining_weight / len(selected) if selected else 0
        for symbol in selected:
            self.SetHoldings(symbol, weight)
            # Track the initial buying price
            self.buy_prices[symbol] = self.Securities[symbol].Price

    def GetFundamentals(self, symbol):
        # Get the fundamentals data
        if symbol in self.Securities:
            return self.Securities[symbol].Fundamentals
        return None
