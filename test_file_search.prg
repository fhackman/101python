* test_file_search.prg
* Purpose: Verify File_Search function

SET PROCEDURE TO vfp_utility.prg ADDITIVE

LOCAL lnCount, lcStartDir

* Use current directory for testing
lcStartDir = FULLPATH(".")

? "Searching for *.prg in " + lcStartDir + " (Recursive)"

* Close cursor if open
IF USED("curSearchResults")
    USE IN curSearchResults
ENDIF

* Perform Search
lnCount = File_Search(lcStartDir, "*.prg", .T.)

? "Files Found: " + TRANSFORM(lnCount)

IF USED("curSearchResults")
    SELECT curSearchResults
    BROWSE NORMAL NOWAIT
    
    * Optional: List first 5 files
    GO TOP
    SCAN NEXT 5
        ? FilePath, FileSize, FileDate
    ENDSCAN
ELSE
    ? "Error: curSearchResults not created."
ENDIF
