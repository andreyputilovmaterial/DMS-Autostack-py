TEMPLATE = """
' -----------------------------------------------------------------------
' IPS Table Shell Version 7.0.0
'
' -----------------------------------------------------------------------
' Run this script after unstacked Prep/Weight/etc. - creates a new inflated version of the R-data to prepare for stacking
'
' -----------------------------------------------------------------------
' Author Notes (optional): 
' - 
' -----------------------------------------------------------------------

#include "Includes/Globals.mrs"
#include "Includes/DMS/LoggingPrep.dms"
#define SCRIPT_NAME     "401_STKPrep.dms"

' -----------------------------------------------------------------------

'Note: By default only completes will be included in the stacking loop.  Please update WHERE clause below if contact stacking is needed
InputDatasource(Input)
	ConnectionString = "Provider = mrOleDB.Provider.2; Data Source = " + DIMENSIONS_DSC + "; Initial Catalog = '" + PROCESSED_MDD + "'; Location = " + PROCESSED_DATA + ";" 
	SelectQuery = "SELECT * FROM VDATA WHERE DataCollection.Status.ContainsAny({Completed})" 
End InputDatasource

OutputDatasource(Output)
    ConnectionString = "Provider = mrOleDB.Provider.2; Data Source = " + DIMENSIONS_DSC + "; Location = " + STK_PRE_DATA + ";"
    MetadataOutputName = STK_PRE_MDD
End OutputDatasource

' -----------------------------------------------------------------------

Event(OnBeforeJobStart)
	Debug.Echo("Beginning execution of " +SCRIPT_NAME + " at " + CText(now()))
	Debug.Log("Beginning execution of " +SCRIPT_NAME)

    Dim fso, directoryname, mainfolder, filecollection, file
    Dim deleteFSO    
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set deleteFSO = CreateObject("Scripting.FileSystemObject")
    
	' The outputs should be deleted to make sure that we don't append
	' to an existing file 

    If (fso.FileExists(STK_PRE_DATA)) Then
        fso.DeleteFile(STK_PRE_DATA)
    End If
    
    If (fso.FileExists(STK_PRE_MDD)) Then
        fso.DeleteFile(STK_PRE_MDD)
    End If
    
    ' Remove log files
	directoryname=".\Logs"
	Set mainfolder = fso.GetFolder(directoryname)
	Set filecollection = mainfolder.Files
	On Error Resume Next
	For Each file In filecollection
		If UCase(Left(file.Name)) = "DMP" Then
			file.Delete()
		End If
	Next
	
	'------------------------------------------------------------------------------------------------------------------------------------------------------
	' Delete old Bad Cases files
	#include "Includes\FileAccess.mrs"
	DeleteFileWithWild(GetCurrentPath() + "Bad Cases *.txt")
End Event

' -----------------------------------------------------------------------
Metadata(ENU, Analysis, Label, Input)

' ...

End Metadata
' -----------------------------------------------------------------------


Event(OnJobStart, "Do the set up")
	#include "Includes\DBadCaseFile\Create.mrs"	
	CreateBaseCaseFile(dmgrGlobal)
	
	'Scripters should add their work below here
	
End Event


''Event(OnAfterMetaDataTransformation, "")
'' 	
''End Event
' -----------------------------------------------------------------------

Event(OnBadCase, "" )
	#Include "Includes\DBadCaseFile\Write.mrs"
End Event

Event(OnNextCase)
#include "Includes/DMS/ONCFunctions.mrs"
#include "Includes/DMS/ONCCappingFunctions.mrs"

' ...

End Event

Event(OnJobEnd, "")
	Dim fso
	dim ErrorMessages[], WarningMessages[]
	
	Set fso = CreateObject("Scripting.FileSystemObject")
	
	#Include "Includes\DBadCaseFile\Report.mrs"
	
	ReportErrorsAndWarnings( dmgrGlobal, dmgrGlobal.MyFileName )
End Event

Event(OnAfterJobEnd)
	Debug.Echo("Ending execution of " +SCRIPT_NAME + " at " + CText(Now()))
	Debug.Log("Ending execution of " +SCRIPT_NAME)	
End Event
"""
