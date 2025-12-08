*--------------------------------------------------------------------------
* Function: ConnectToDB
* Purpose:  Connects to various databases using SQLSTRINGCONNECT
* Parameters:
*   tcType     - "SQLSERVER", "ORACLE", "MYSQL", "POSTGRESQL", "MONGODB"
*   tcServer   - Server IP/Hostname (and Port if needed)
*   tcDatabase - Database Name (or Service Name for Oracle)
*   tcUser     - Username
*   tcPassword - Password
* Returns:  Connection Handle (Integer) - Positive if successful, -1 if failed
*--------------------------------------------------------------------------
FUNCTION ConnectToDB
    LPARAMETERS tcType, tcServer, tcDatabase, tcUser, tcPassword

    LOCAL lcConnectionString, lnHandle, laError[1], lcDriver
    
    * Normalize Input
    tcType = UPPER(ALLTRIM(tcType))
    
    * Default parameters if not provided
    IF VARTYPE(tcServer) <> "C"
        tcServer = "LOCALHOST"
    ENDIF
    IF VARTYPE(tcDatabase) <> "C"
        tcDatabase = ""
    ENDIF
    IF VARTYPE(tcUser) <> "C"
        tcUser = ""
    ENDIF
    IF VARTYPE(tcPassword) <> "C"
        tcPassword = ""
    ENDIF
    
    lcConnectionString = ""

    DO CASE
        CASE tcType == "SQLSERVER"
            * SQL Server Native Client or ODBC Driver
            lcDriver = "{SQL Server}" 
            * You might prefer {ODBC Driver 17 for SQL Server} in modern setups
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "SERVER=" + ALLTRIM(tcServer) + ";" + ;
                                 "DATABASE=" + ALLTRIM(tcDatabase) + ";" + ;
                                 "UID=" + ALLTRIM(tcUser) + ";" + ;
                                 "PWD=" + ALLTRIM(tcPassword) + ";"

        CASE tcType == "ORACLE"
            * Oracle ODBC Driver
            * Assumes Oracle Client is installed. 
            * tcDatabase here acts as the Service Name / TNS Name
            lcDriver = "{Oracle in OraClient11g_home1}" && Adjust based on installed client version
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "DBQ=" + ALLTRIM(tcServer) + "/" + ALLTRIM(tcDatabase) + ";" + ;
                                 "UID=" + ALLTRIM(tcUser) + ";" + ;
                                 "PWD=" + ALLTRIM(tcPassword) + ";"

        CASE tcType == "MYSQL"
            * MySQL ODBC Driver (e.g., 8.0)
            lcDriver = "{MySQL ODBC 8.0 Unicode Driver}" && Adjust version as needed
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "SERVER=" + ALLTRIM(tcServer) + ";" + ;
                                 "DATABASE=" + ALLTRIM(tcDatabase) + ";" + ;
                                 "USER=" + ALLTRIM(tcUser) + ";" + ;
                                 "PASSWORD=" + ALLTRIM(tcPassword) + ";" + ;
                                 "OPTION=3;"

        CASE tcType == "POSTGRESQL"
            * PostgreSQL ODBC Driver
            lcDriver = "{PostgreSQL Unicode}"
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "SERVER=" + ALLTRIM(tcServer) + ";" + ;
                                 "DATABASE=" + ALLTRIM(tcDatabase) + ";" + ;
                                 "UID=" + ALLTRIM(tcUser) + ";" + ;
                                 "PWD=" + ALLTRIM(tcPassword) + ";" + ;
                                 "PORT=5432;"

        CASE tcType == "MONGODB"
            * MongoDB ODBC Driver (BI Connector)
            * Note: Requires MongoDB BI Connector and ODBC Driver installed
            lcDriver = "{MongoDB ODBC Driver}"
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "SERVER=" + ALLTRIM(tcServer) + ";" + ;
                                 "DATABASE=" + ALLTRIM(tcDatabase) + ";" + ;
                                 "UID=" + ALLTRIM(tcUser) + ";" + ;
                                 "PWD=" + ALLTRIM(tcPassword) + ";" + ;
                                 "PORT=27017;"

        CASE tcType == "SQLITE"
            * SQLite ODBC Driver
            * tcDatabase should be the full path to the .db file
            lcDriver = "{SQLite3 ODBC Driver}"
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "Database=" + ALLTRIM(tcDatabase) + ";"

        CASE tcType == "MARIADB"
            * MariaDB ODBC Driver
            lcDriver = "{MariaDB ODBC 3.1 Driver}"
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "SERVER=" + ALLTRIM(tcServer) + ";" + ;
                                 "DATABASE=" + ALLTRIM(tcDatabase) + ";" + ;
                                 "UID=" + ALLTRIM(tcUser) + ";" + ;
                                 "PWD=" + ALLTRIM(tcPassword) + ";" + ;
                                 "PORT=3306;"

        CASE tcType == "FIREBIRD"
            * Firebird ODBC Driver
            lcDriver = "{Firebird/InterBase(r) driver}"
            * tcServer should be Host/Port, tcDatabase is the path/alias
            lcConnectionString = "DRIVER=" + lcDriver + ";" + ;
                                 "DBNAME=" + ALLTRIM(tcServer) + ":" + ALLTRIM(tcDatabase) + ";" + ;
                                 "UID=" + ALLTRIM(tcUser) + ";" + ;
                                 "PWD=" + ALLTRIM(tcPassword) + ";"

        CASE tcType == "GENERIC"
            * Raw Connection String passed in tcServer
            * tcDatabase, tcUser, tcPassword are ignored or can be appended if needed
            lcConnectionString = ALLTRIM(tcServer)

        OTHERWISE
            MESSAGEBOX("Unknown Database Type: " + tcType, 16, "Configuration Error")
            RETURN -1
    ENDCASE

    * Attempt Connection
    WAIT WINDOW "Connecting to " + tcType + "..." NOWAIT
    lnHandle = SQLSTRINGCONNECT(lcConnectionString)
    WAIT CLEAR

    * Check for success
    IF lnHandle > 0
        MESSAGEBOX("Successfully connected to " + tcType, 64, "Connection Success")
    ELSE
        AERROR(laError)
        MESSAGEBOX("Connection Failed to " + tcType + ":" + CHR(13) + ;
                   "Error: " + TRANSFORM(laError[1]) + CHR(13) + ;
                   "Message: " + laError[2] + CHR(13) + ;
                   "String: " + lcConnectionString, 16, "Connection Error")
        lnHandle = -1
    ENDIF

    RETURN lnHandle
ENDFUNC

*--------------------------------------------------------------------------
* Example Usage:
*--------------------------------------------------------------------------
* lnConn = ConnectToDB("MYSQL", "localhost", "my_db", "root", "password")
* lnConn = ConnectToDB("POSTGRESQL", "localhost", "postgres_db", "postgres", "password")
*--------------------------------------------------------------------------

*--------------------------------------------------------------------------
* Function: DB_Insert
* Purpose:  Generates and executes an INSERT statement
* Parameters:
*   tnHandle - Connection Handle
*   tcTable  - Table Name
*   toData   - Object containing data (Property Name = Column Name)
* Returns:  1 if successful, -1 if failed
*--------------------------------------------------------------------------
FUNCTION DB_Insert
    LPARAMETERS tnHandle, tcTable, toData

    LOCAL lcFields, lcValues, lnCount, laProps[1], i, lcProp, luValue, lnResult
    
    lcFields = ""
    lcValues = ""
    
    * Get properties of the data object
    lnCount = AMEMBERS(laProps, toData)
    
    IF lnCount = 0
        MESSAGEBOX("No data provided for INSERT", 16, "Error")
        RETURN -1
    ENDIF
    
    FOR i = 1 TO lnCount
        lcProp = laProps[i]
        luValue = GETPEM(toData, lcProp)
        
        * Build Field List
        lcFields = lcFields + IIF(EMPTY(lcFields), "", ", ") + lcProp
        
        * Build Value List (using parameters)
        lcValues = lcValues + IIF(EMPTY(lcValues), "", ", ") + "?" + "toData." + lcProp
    ENDFOR
    
    * Construct Query
    TEXT TO lcSQL NOSHOW TEXTMERGE PRETEXT 15
        INSERT INTO <<tcTable>> (<<lcFields>>) VALUES (<<lcValues>>)
    ENDTEXT
    
    * Execute
    lnResult = SQLEXEC(tnHandle, lcSQL)
    
    IF lnResult < 0
        LOCAL laError[1]
        AERROR(laError)
        MESSAGEBOX("DB_Insert Failed: " + laError[2], 16, "Database Error")
    ENDIF
    
    RETURN lnResult
ENDFUNC

*--------------------------------------------------------------------------
* Function: DB_Update
* Purpose:  Generates and executes an UPDATE statement
* Parameters:
*   tnHandle - Connection Handle
*   tcTable  - Table Name
*   toData   - Object containing data to update
*   tcWhere  - WHERE clause (e.g., "id = 1")
* Returns:  1 if successful, -1 if failed
*--------------------------------------------------------------------------
FUNCTION DB_Update
    LPARAMETERS tnHandle, tcTable, toData, tcWhere

    LOCAL lcSet, lnCount, laProps[1], i, lcProp, luValue, lnResult, lcSQL
    
    lcSet = ""
    
    * Get properties of the data object
    lnCount = AMEMBERS(laProps, toData)
    
    IF lnCount = 0
        MESSAGEBOX("No data provided for UPDATE", 16, "Error")
        RETURN -1
    ENDIF
    
    FOR i = 1 TO lnCount
        lcProp = laProps[i]
        
        * Build Set List
        lcSet = lcSet + IIF(EMPTY(lcSet), "", ", ") + lcProp + " = ?" + "toData." + lcProp
    ENDFOR
    
    * Construct Query
    TEXT TO lcSQL NOSHOW TEXTMERGE PRETEXT 15
        UPDATE <<tcTable>> SET <<lcSet>> WHERE <<tcWhere>>
    ENDTEXT
    
    * Execute
    lnResult = SQLEXEC(tnHandle, lcSQL)
    
    IF lnResult < 0
        LOCAL laError[1]
        AERROR(laError)
        MESSAGEBOX("DB_Update Failed: " + laError[2], 16, "Database Error")
    ENDIF
    
    RETURN lnResult
ENDFUNC

*--------------------------------------------------------------------------
* Function: DB_Delete
* Purpose:  Generates and executes a DELETE statement
* Parameters:
*   tnHandle - Connection Handle
*   tcTable  - Table Name
*   tcWhere  - WHERE clause
* Returns:  1 if successful, -1 if failed
*--------------------------------------------------------------------------
FUNCTION DB_Delete
    LPARAMETERS tnHandle, tcTable, tcWhere

    LOCAL lcSQL, lnResult
    
    IF EMPTY(tcWhere)
        MESSAGEBOX("WHERE clause is required for DELETE to prevent accidental data loss.", 16, "Safety Error")
        RETURN -1
    ENDIF
    
    * Construct Query
    TEXT TO lcSQL NOSHOW TEXTMERGE PRETEXT 15
        DELETE FROM <<tcTable>> WHERE <<tcWhere>>
    ENDTEXT
    
    * Execute
    lnResult = SQLEXEC(tnHandle, lcSQL)
    
    IF lnResult < 0
        LOCAL laError[1]
        AERROR(laError)
        MESSAGEBOX("DB_Delete Failed: " + laError[2], 16, "Database Error")
    ENDIF
    
    RETURN lnResult
ENDFUNC

*--------------------------------------------------------------------------
* Function: File_Search
* Purpose:  Recursively searches for files matching a pattern
* Parameters:
*   tcStartDir - Starting Directory (e.g., "C:\MyData")
*   tcPattern  - File Pattern (e.g., "*.txt")
*   tlRecursive- .T. to search subdirectories
* Returns:  Number of files found
* Output:   Creates/Appends to cursor 'curSearchResults'
*--------------------------------------------------------------------------
FUNCTION File_Search
    LPARAMETERS tcStartDir, tcPattern, tlRecursive

    LOCAL lnFileCount, laFiles[1], i, lcFile, lcFullPath, lcSubDir
    LOCAL lnDirCount, laDirs[1], j, lcCurrentDir

    * Ensure Start Directory ends with backslash
    tcStartDir = ADDBS(tcStartDir)
    
    * Create Cursor if it doesn't exist (First call)
    IF !USED("curSearchResults")
        CREATE CURSOR curSearchResults (FilePath C(250), FileName C(100), FileSize N(12), FileDate T)
    ENDIF
    
    * 1. Search for Files in current directory
    lnFileCount = ADIR(laFiles, tcStartDir + tcPattern)
    
    FOR i = 1 TO lnFileCount
        lcFile = laFiles[i, 1]
        lcFullPath = tcStartDir + lcFile
        
        INSERT INTO curSearchResults (FilePath, FileName, FileSize, FileDate) ;
            VALUES (lcFullPath, lcFile, laFiles[i, 2], CTOT(DTOC(laFiles[i, 3]) + " " + laFiles[i, 4]))
    ENDFOR
    
    * 2. Recurse into Subdirectories if requested
    IF tlRecursive
        * Get all directories ("D" attribute)
        lnDirCount = ADIR(laDirs, tcStartDir + "*.*", "D")
        
        FOR j = 1 TO lnDirCount
            lcSubDir = laDirs[j, 1]
            
            * Skip "." and ".."
            IF lcSubDir != "." AND lcSubDir != ".." AND "D" $ laDirs[j, 5]
                File_Search(tcStartDir + lcSubDir, tcPattern, .T.)
            ENDIF
        ENDFOR
    ENDIF
    
    RETURN RECCOUNT("curSearchResults")
ENDFUNC
