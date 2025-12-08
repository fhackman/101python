* test_db_ops.prg
* Purpose: Verify DB_Insert, DB_Update, DB_Delete

SET PROCEDURE TO vfp_utility.prg ADDITIVE

* 1. Connect (Adjust parameters for your DB)
* For testing, we assume a connection handle is available or we mock it.
* Since we can't easily mock a live DB connection without a driver, 
* this script demonstrates the usage pattern.

LOCAL lnHandle, loData, lnResult

* REPLACE THIS WITH YOUR ACTUAL CONNECTION
* lnHandle = ConnectToDB("SQLSERVER", "localhost", "TestDB", "sa", "password")
lnHandle = 1 && Mock handle for syntax checking if running offline

IF lnHandle > 0
    * 2. Test Insert
    loData = CREATEOBJECT("Empty")
    ADDPROPERTY(loData, "username", "jdoe")
    ADDPROPERTY(loData, "email", "jdoe@example.com")
    ADDPROPERTY(loData, "created_at", DATETIME())
    
    ? "Testing Insert..."
    * lnResult = DB_Insert(lnHandle, "users", loData)
    * ? "Insert Result:", lnResult
    
    * 3. Test Update
    loData = CREATEOBJECT("Empty")
    ADDPROPERTY(loData, "email", "john.doe@example.com")
    
    ? "Testing Update..."
    * lnResult = DB_Update(lnHandle, "users", loData, "username = 'jdoe'")
    * ? "Update Result:", lnResult
    
    * 4. Test Delete
    ? "Testing Delete..."
    * lnResult = DB_Delete(lnHandle, "users", "username = 'jdoe'")
    * ? "Delete Result:", lnResult
    
    * SQLDISCONNECT(lnHandle)
ELSE
    ? "Connection failed, cannot run live tests."
ENDIF
