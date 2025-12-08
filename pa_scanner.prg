* pa_scanner.prg
* Price Action Scanner in Visual FoxPro (GUI Version with MT5 Bridge)
* Author: HackWarrior

PUBLIC oForm
oForm = CREATEOBJECT("ScannerForm")
oForm.Show()
READ EVENTS

DEFINE CLASS ScannerForm AS FORM
    Caption = "Price Action Scanner (MT5 Bridge)"
    Width = 850
    Height = 700
    AutoCenter = .T.
    FontName = "Segoe UI"
    FontSize = 9
    BackColor = RGB(240, 240, 240)
    
    * Properties to hold state
    IsScanning = .F.
    nConnHandle = -1
    
    * Header
    ADD OBJECT shpHeader AS SHAPE WITH ;
        Top = 0, Left = 0, Width = 850, Height = 50, ;
        BackColor = RGB(0, 120, 215), BorderStyle = 0
        
    ADD OBJECT lblTitle AS LABEL WITH ;
        Caption = "Price Action Scanner", Top = 10, Left = 10, ;
        FontName = "Segoe UI Semibold", FontSize = 14, ;
        ForeColor = RGB(255, 255, 255), BackStyle = 0
    
    * Controls
    ADD OBJECT lblSymbol AS LABEL WITH ;
        Caption = "Symbol:", Left = 20, Top = 65, AutoSize = .T., BackStyle = 0
        
    ADD OBJECT txtSymbol AS TEXTBOX WITH ;
        Value = "XAUUSD.m", Left = 70, Top = 62, Width = 100, ;
        FontName = "Segoe UI", FontSize = 9
        
    ADD OBJECT lblTF AS LABEL WITH ;
        Caption = "TF:", Left = 190, Top = 65, AutoSize = .T., BackStyle = 0
        
    ADD OBJECT cboTF AS COMBOBOX WITH ;
        Left = 220, Top = 62, Width = 60, Style = 2, ;
        FontName = "Segoe UI", FontSize = 9
        
    ADD OBJECT lblRefresh AS LABEL WITH ;
        Caption = "Refresh (s):", Left = 300, Top = 65, AutoSize = .T., BackStyle = 0
        
    ADD OBJECT txtRefresh AS TEXTBOX WITH ;
        Value = 60, Left = 370, Top = 62, Width = 40, InputMask = "999", ;
        FontName = "Segoe UI", FontSize = 9
        
    ADD OBJECT cmdStart AS COMMANDBUTTON WITH ;
        Caption = "Start Scanning", Left = 440, Top = 60, Height = 28, Width = 110, ;
        FontName = "Segoe UI", FontSize = 9
        
    ADD OBJECT cmdStop AS COMMANDBUTTON WITH ;
        Caption = "Stop", Left = 560, Top = 60, Height = 28, Width = 80, Enabled = .F., ;
        FontName = "Segoe UI", FontSize = 9
        
    ADD OBJECT lblStatus AS LABEL WITH ;
        Caption = "Status: Idle", Left = 660, Top = 65, AutoSize = .T., ;
        ForeColor = RGB(100, 100, 100), BackStyle = 0, FontName = "Segoe UI"
        
    ADD OBJECT grdResults AS GRID WITH ;
        Left = 10, Top = 100, Width = 830, Height = 480, ;
        RecordSource = "curResults", ReadOnly = .T., ;
        FontName = "Segoe UI", FontSize = 9, ;
        DeleteMark = .F., GridLines = 0, ;
        HeaderHeight = 25, RowHeight = 22, ;
        HighlightStyle = 2
        
    ADD OBJECT tmrScan AS TIMER WITH ;
        Interval = 0, Enabled = .F.

    * Database Controls
    ADD OBJECT lblDBSection AS LABEL WITH ;
        Caption = "Database Integration", Left = 10, Top = 590, ;
        FontName = "Segoe UI Semibold", FontSize = 10, AutoSize = .T., BackStyle = 0

    ADD OBJECT lblDBType AS LABEL WITH ;
        Caption = "Type:", Left = 10, Top = 620, AutoSize = .T., BackStyle = 0
    ADD OBJECT cboDBType AS COMBOBOX WITH ;
        Left = 50, Top = 617, Width = 100, Style = 2, ;
        FontName = "Segoe UI", FontSize = 9

    ADD OBJECT lblDBServer AS LABEL WITH ;
        Caption = "Server:", Left = 160, Top = 620, AutoSize = .T., BackStyle = 0
    ADD OBJECT txtDBServer AS TEXTBOX WITH ;
        Value = "localhost", Left = 210, Top = 617, Width = 100, ;
        FontName = "Segoe UI", FontSize = 9

    ADD OBJECT lblDBName AS LABEL WITH ;
        Caption = "DB:", Left = 320, Top = 620, AutoSize = .T., BackStyle = 0
    ADD OBJECT txtDBName AS TEXTBOX WITH ;
        Value = "trading_db", Left = 350, Top = 617, Width = 80, ;
        FontName = "Segoe UI", FontSize = 9

    ADD OBJECT lblDBUser AS LABEL WITH ;
        Caption = "User:", Left = 440, Top = 620, AutoSize = .T., BackStyle = 0
    ADD OBJECT txtDBUser AS TEXTBOX WITH ;
        Value = "root", Left = 480, Top = 617, Width = 80, ;
        FontName = "Segoe UI", FontSize = 9

    ADD OBJECT lblDBPass AS LABEL WITH ;
        Caption = "Pass:", Left = 570, Top = 620, AutoSize = .T., BackStyle = 0
    ADD OBJECT txtDBPass AS TEXTBOX WITH ;
        Value = "", Left = 610, Top = 617, Width = 80, PasswordChar = "*", ;
        FontName = "Segoe UI", FontSize = 9

    ADD OBJECT cmdConnectDB AS COMMANDBUTTON WITH ;
        Caption = "Connect", Left = 700, Top = 615, Height = 28, Width = 70, ;
        FontName = "Segoe UI", FontSize = 9

    ADD OBJECT cmdCreateTable AS COMMANDBUTTON WITH ;
        Caption = "Init DB", Left = 780, Top = 615, Height = 28, Width = 60, Enabled = .F., ;
        FontName = "Segoe UI", FontSize = 9

    PROCEDURE Init
        SET DEFAULT TO 'c:\tmp\101python'
        SET SAFETY OFF
        SET PROCEDURE TO vfp_utility.prg ADDITIVE
        * Setup Data
        CREATE CURSOR curCandles ( ;
            time T, symbol C(10), open N(10,5), high N(10,5), low N(10,5), close N(10,5) )
            
        CREATE CURSOR curResults ( ;
            time T, symbol C(10), pattern C(50), type C(4), price N(10,5) )
            
        * Setup Grid Columns
        WITH THIS.grdResults
            .ColumnCount = 5
            .Columns(1).ControlSource = "curResults.time"
            .Columns(1).Header1.Caption = "Time"
            .Columns(1).Width = 140
            .Columns(2).ControlSource = "curResults.symbol"
            .Columns(2).Header1.Caption = "Symbol"
            .Columns(2).Width = 80
            .Columns(3).ControlSource = "curResults.pattern"
            .Columns(3).Header1.Caption = "Pattern"
            .Columns(3).Width = 250
            .Columns(4).ControlSource = "curResults.type"
            .Columns(4).Header1.Caption = "Type"
            .Columns(4).Width = 80
            .Columns(5).ControlSource = "curResults.price"
            .Columns(5).Header1.Caption = "Price"
            .Columns(5).Width = 100
            
            * Dynamic Color
            .Columns(4).DynamicBackColor = "IIF(ALLTRIM(curResults.type)=='BUY', RGB(230,255,230), IIF(ALLTRIM(curResults.type)=='SELL', RGB(255,230,230), RGB(255,255,255)))"
        ENDWITH
            
        * Setup Combo
        THIS.cboTF.AddItem("M1")
        THIS.cboTF.AddItem("M5")
        THIS.cboTF.AddItem("H1")
        THIS.cboTF.AddItem("H4")
        THIS.cboTF.AddItem("D1")
        THIS.cboTF.ListIndex = 3 && Default H1

        * Setup DB Combo
        THIS.cboDBType.AddItem("MYSQL")
        THIS.cboDBType.AddItem("POSTGRESQL")
        THIS.cboDBType.AddItem("SQLSERVER")
        THIS.cboDBType.AddItem("SQLITE")
        THIS.cboDBType.AddItem("MARIADB")
        THIS.cboDBType.AddItem("FIREBIRD")
        THIS.cboDBType.AddItem("GENERIC")
        THIS.cboDBType.ListIndex = 1 && Default MYSQL
        
        * Bind Events
        BINDEVENT(THIS.cmdStart, "Click", THIS, "StartScanning")
        BINDEVENT(THIS.cmdStop, "Click", THIS, "StopScanning")
        BINDEVENT(THIS.tmrScan, "Timer", THIS, "OnTimer")
        BINDEVENT(THIS.cmdConnectDB, "Click", THIS, "ConnectDB")
        BINDEVENT(THIS.cmdCreateTable, "Click", THIS, "CreateTable")
    ENDPROC
    
    PROCEDURE Destroy
        CLEAR EVENTS
    ENDPROC
    
    PROCEDURE StartScanning
        LOCAL lnInterval
        lnInterval = VAL(TRANSFORM(THIS.txtRefresh.Value)) * 1000
        IF lnInterval < 1000
            lnInterval = 1000
        ENDIF
        
        THIS.IsScanning = .T.
        THIS.cmdStart.Enabled = .F.
        THIS.cmdStop.Enabled = .T.
        THIS.txtSymbol.Enabled = .F.
        THIS.cboTF.Enabled = .F.
        THIS.txtRefresh.Enabled = .F.
        
        THIS.lblStatus.Caption = "Status: Scanning " + ALLTRIM(THIS.txtSymbol.Value) + "..."
        THIS.tmrScan.Interval = lnInterval
        THIS.tmrScan.Enabled = .T.
        
        * Launch Bridge Script (Minimized)
        RUN /N7 python mt5_bridge.py
        
        * Run immediate scan
        THIS.OnTimer()
    ENDPROC
    
    PROCEDURE StopScanning
        THIS.IsScanning = .F.
        THIS.cmdStart.Enabled = .T.
        THIS.cmdStop.Enabled = .F.
        THIS.txtSymbol.Enabled = .T.
        THIS.cboTF.Enabled = .T.
        THIS.txtRefresh.Enabled = .T.
        
        THIS.lblStatus.Caption = "Status: Stopped"
        THIS.tmrScan.Enabled = .F.
    ENDPROC
    
    PROCEDURE OnTimer
        THIS.FetchData()
        THIS.ScanPatterns()
        THIS.grdResults.Refresh()
    ENDPROC
    
    PROCEDURE FetchData
        LOCAL lcFile, lcRequest
        lcFile = "candles.csv"
        lcRequest = "request.txt"
        
        * Write Request
        STRTOFILE(ALLTRIM(THIS.txtSymbol.Value) + "," + ALLTRIM(THIS.cboTF.Value), lcRequest)
        
        * Import Logic
        IF FILE(lcFile)
            * Use a temporary cursor for import to avoid type mismatch issues
            CREATE CURSOR curImport ( ;
                cTime C(30), cSymbol C(10), cOpen C(20), cHigh C(20), cLow C(20), cClose C(20) )
                
            * Try/Catch for safe import
            TRY
                APPEND FROM (lcFile) TYPE CSV
            CATCH TO oErr
                * Handle error (e.g., file locked)
                ACTIVATE SCREEN
                ? "Import Error: " + oErr.Message
            ENDTRY
            
            IF RECCOUNT("curImport") > 0
                SELECT curCandles
                ZAP
                
                SELECT curImport
                SCAN
                    INSERT INTO curCandles (time, symbol, open, high, low, close) VALUES ( ;
                        CTOT(curImport.cTime), ;
                        curImport.cSymbol, ;
                        VAL(curImport.cOpen), ;
                        VAL(curImport.cHigh), ;
                        VAL(curImport.cLow), ;
                        VAL(curImport.cClose) )
                ENDSCAN
            ENDIF
            
            USE IN curImport
        ENDIF
    ENDPROC
    
    PROCEDURE ScanPatterns
        LOCAL lnId, ldTime, lcSymbol, lnOpen, lnHigh, lnLow, lnClose
        LOCAL lnOpen1, lnHigh1, lnLow1, lnClose1
        LOCAL lnBodyTop, lnBodyBottom, lnBodySize, lnUpperWick, lnLowerWick
        
        LOCAL lnOpen2, lnHigh2, lnLow2, lnClose2
        
        SELECT curCandles
        GO BOTTOM
        
        IF RECCOUNT() < 5
            RETURN
        ENDIF
        
        * Get Current
        ldTime = time
        lcSymbol = symbol
        lnOpen = open
        lnHigh = high
        lnLow = low
        lnClose = close
        
        * Get Prev (1)
        SKIP -1
        lnOpen1 = open
        lnHigh1 = high
        lnLow1 = low
        lnClose1 = close
        
        * Get Prev (2)
        SKIP -1
        lnOpen2 = open
        lnHigh2 = high
        lnLow2 = low
        lnClose2 = close
        
        * Return to Current
        GO BOTTOM
        
        * Logic
        lnBodyTop = MAX(lnOpen, lnClose)
        lnBodyBottom = MIN(lnOpen, lnClose)
        lnBodySize = lnBodyTop - lnBodyBottom
        lnUpperWick = lnHigh - lnBodyTop
        lnLowerWick = lnBodyBottom - lnLow
        
        * Check Duplicate (Simple check by time)
        SELECT curResults
        LOCATE FOR time = ldTime
        IF FOUND()
            RETURN
        ENDIF
        
        * PATTERN 1: Rejection
        * Buy (Hammer)
        IF lnLowerWick > (2 * lnBodySize) AND lnUpperWick < lnBodySize
            THIS.AddResult(ldTime, lcSymbol, "BUY (Hammer)", "BUY", lnClose)
        ENDIF
        * Sell (Shooting Star)
        IF lnUpperWick > (2 * lnBodySize) AND lnLowerWick < lnBodySize
            THIS.AddResult(ldTime, lcSymbol, "SELL (Shooting Star)", "SELL", lnClose)
        ENDIF
        
        * PATTERN 2: Engulfing
        * Buy Engulfing: Prev Bearish, Curr Bullish, Engulfs
        IF lnClose1 < lnOpen1 AND lnClose > lnOpen AND lnClose > lnOpen1 AND lnOpen < lnClose1
             THIS.AddResult(ldTime, lcSymbol, "BUY (Engulfing)", "BUY", lnClose)
        ENDIF
        * Sell Engulfing: Prev Bullish, Curr Bearish, Engulfs
        IF lnClose1 > lnOpen1 AND lnClose < lnOpen AND lnClose < lnOpen1 AND lnOpen > lnClose1
             THIS.AddResult(ldTime, lcSymbol, "SELL (Engulfing)", "SELL", lnClose)
        ENDIF
        
        * PATTERN 3: Inside Bar Breakout
        * Inside Bar: Prev1 is inside Prev2
        IF lnHigh1 < lnHigh2 AND lnLow1 > lnLow2
            * Buy Breakout: Curr Close > Mother High
            IF lnClose > lnHigh2
                THIS.AddResult(ldTime, lcSymbol, "BUY (Inside Bar Breakout)", "BUY", lnClose)
            ENDIF
            * Sell Breakout: Curr Close < Mother Low
            IF lnClose < lnLow2
                THIS.AddResult(ldTime, lcSymbol, "SELL (Inside Bar Breakout)", "SELL", lnClose)
            ENDIF
        ENDIF
        
        * Helpers for complex patterns
        LOCAL llBullish, llBearish, llBullish1, llBearish1, llBullish2, llBearish2
        LOCAL lnBodySize1, lnBodySize2, lnMidpoint1, lnMidpoint2
        
        llBullish = lnClose > lnOpen
        llBearish = lnClose < lnOpen
        llBullish1 = lnClose1 > lnOpen1
        llBearish1 = lnClose1 < lnOpen1
        llBullish2 = lnClose2 > lnOpen2
        llBearish2 = lnClose2 < lnOpen2
        
        lnBodySize1 = ABS(lnOpen1 - lnClose1)
        lnBodySize2 = ABS(lnOpen2 - lnClose2)
        lnMidpoint1 = (lnOpen1 + lnClose1) / 2
        lnMidpoint2 = (lnOpen2 + lnClose2) / 2
        
        * PATTERN 4: Piercing / Dark Cloud
        * Buy (Piercing Line): Prev Bearish, Curr Bullish, Open < Prev Close, Close > Prev Midpoint
        IF llBearish1 AND llBullish AND lnOpen < lnClose1 AND lnClose > lnMidpoint1
            THIS.AddResult(ldTime, lcSymbol, "BUY (Piercing Line)", "BUY", lnClose)
        ENDIF
        * Sell (Dark Cloud Cover): Prev Bullish, Curr Bearish, Open > Prev Close, Close < Prev Midpoint
        IF llBullish1 AND llBearish AND lnOpen > lnClose1 AND lnClose < lnMidpoint1
            THIS.AddResult(ldTime, lcSymbol, "SELL (Dark Cloud Cover)", "SELL", lnClose)
        ENDIF
        
        * PATTERN 5: Morning / Evening Star
        * Buy (Morning Star): Bearish (2) -> Small (1) -> Bullish (0)
        * Check: Body2 > Body1*2 AND Body1 < Body2*0.3 AND Close > Midpoint2
        IF llBearish2 AND lnBodySize2 > (lnBodySize1 * 2) AND lnBodySize1 < (lnBodySize2 * 0.3) AND llBullish AND lnClose > lnMidpoint2
            THIS.AddResult(ldTime, lcSymbol, "BUY (Morning Star)", "BUY", lnClose)
        ENDIF
        * Sell (Evening Star): Bullish (2) -> Small (1) -> Bearish (0)
        IF llBullish2 AND lnBodySize2 > (lnBodySize1 * 2) AND lnBodySize1 < (lnBodySize2 * 0.3) AND llBearish AND lnClose < lnMidpoint2
            THIS.AddResult(ldTime, lcSymbol, "SELL (Evening Star)", "SELL", lnClose)
        ENDIF
        
    ENDPROC

    PROCEDURE AddResult
        LPARAMETERS tdTime, tcSymbol, tcPattern, tcType, tnPrice
        INSERT INTO curResults VALUES (tdTime, tcSymbol, tcPattern, tcType, tnPrice)
        THIS.LogPattern(tdTime, tcSymbol, tcPattern, tcType, tnPrice)
    ENDPROC

    PROCEDURE ConnectDB
        LOCAL lcType, lcServer, lcDB, lcUser, lcPass
        lcType = THIS.cboDBType.Value
        lcServer = THIS.txtDBServer.Value
        lcDB = THIS.txtDBName.Value
        lcUser = THIS.txtDBUser.Value
        lcPass = THIS.txtDBPass.Value
        
        THIS.nConnHandle = ConnectToDB(lcType, lcServer, lcDB, lcUser, lcPass)
        
        IF THIS.nConnHandle > 0
            THIS.cmdConnectDB.Enabled = .F.
            THIS.cmdCreateTable.Enabled = .T.
            THIS.lblStatus.Caption = "Status: Connected to DB"
        ENDIF
    ENDPROC
    
    PROCEDURE CreateTable
        LOCAL lcSQL, lnResult
        IF THIS.nConnHandle <= 0
            RETURN
        ENDIF
        
        * Generic SQL for creating table
        lcSQL = "CREATE TABLE pattern_logs (" + ;
                "id SERIAL PRIMARY KEY, " + ;
                "log_time TIMESTAMP, " + ;
                "symbol VARCHAR(20), " + ;
                "pattern VARCHAR(100), " + ;
                "type VARCHAR(10), " + ;
                "price DECIMAL(15,5))"
                
        lnResult = SQLEXEC(THIS.nConnHandle, lcSQL)
        
        IF lnResult > 0
            MESSAGEBOX("Table pattern_logs created successfully.", 64, "Success")
        ELSE
            LOCAL laError[1]
            AERROR(laError)
            MESSAGEBOX("Failed to create table: " + laError[2], 16, "Error")
        ENDIF
    ENDPROC
    
    PROCEDURE LogPattern
        LPARAMETERS tdTime, tcSymbol, tcPattern, tcType, tnPrice
        LOCAL lcSQL, lnResult, lcTimeStr
        
        IF THIS.nConnHandle <= 0
            RETURN
        ENDIF
        
        * Format Time YYYY-MM-DD HH:MM:SS
        lcTimeStr = ALLTRIM(STR(YEAR(tdTime))) + "-" + PADL(MONTH(tdTime),2,"0") + "-" + PADL(DAY(tdTime),2,"0") + " " + ;
                    PADL(HOUR(tdTime),2,"0") + ":" + PADL(MINUTE(tdTime),2,"0") + ":" + PADL(SEC(tdTime),2,"0")
        
        lcSQL = "INSERT INTO pattern_logs (log_time, symbol, pattern, type, price) VALUES (" + ;
                "'" + lcTimeStr + "', " + ;
                "'" + tcSymbol + "', " + ;
                "'" + tcPattern + "', " + ;
                "'" + tcType + "', " + ;
                TRANSFORM(tnPrice) + ")"
                
        lnResult = SQLEXEC(THIS.nConnHandle, lcSQL)
    ENDPROC

ENDDEFINE
