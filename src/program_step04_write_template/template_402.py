TEMPLATE = """
' -----------------------------------------------------------------------
' IPS Table Shell Version 7.0.0
'
' -----------------------------------------------------------------------
' Run this script after 401_STKPrep - creates a new stacked file
'
' -----------------------------------------------------------------------
' Author Notes (optional): 
' - 
' -----------------------------------------------------------------------

#include "Includes/Globals.mrs"
#include "Includes/DMS/LoggingPrep.dms"
#define SCRIPT_NAME     "402_STKCreate.dms"

' -----------------------------------------------------------------------

'StackingLoop: Loop from R-files containing data we want stacked
'    -For Loops within Loops, "ChildLoop.DayLoop"
'#define STACKINGLOOP "STKLoop"

'UnstackedVars: Respondent-level variables to include in stacked files
'    -Access Respondent-level variables with "^.Var"
'    -Use "^.Var as Var" naming for any variable not currently inside a block
'    -For Loops within Loops, add a carrot per level: "^.^.Var"
#define UNSTACKEDVARS "^.Respondent.ID, ^.Respondent.Serial, ^.DataCollection.Status, ^.DataCollection.StartTime, ^.DataCollection.FinishTime, ^.Comp as Comp, ^.PrelimBanner as PrelimBanner, ^.Banner1 as Banner1, ^.Weight_Completes as Weight_Completes"

'WhichIterations: Used in the Where clause to determine which iterations to include
'    -We rarely want to include all iterations with any data at all ("TRUE")
'    -Usually depends on whether some variable inside the loop is populated ("ChildAge is not null")
'        -Syntax here is at the loop level: "ChildAge" not "ChildLoop.ChildAge"
'#define WHICHITERATIONS "ChildAge is not null"
#define WHICHITERATIONS "true"


InputDatasource(Input)
	ConnectionString = "Provider = mrOleDB.Provider.2; Data Source = " + DIMENSIONS_DSC + "; Initial Catalog = '" + STK_PRE_MDD + "'; Location = " + STK_PRE_DATA + ";" 
	SelectQuery = "SELECT " + UNSTACKEDVARS + ", * FROM HDATA." + STACKINGLOOP + " Where ("+ WHICHITERATIONS +")" 
End InputDatasource

OutputDatasource(Output)
    ConnectionString = "Provider = mrOleDB.Provider.2; Data Source = " + DIMENSIONS_DSC + "; Location = " + STK_DATA + ";"
    MetadataOutputName = STK_MDD
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

    If (fso.FileExists(STK_DATA)) Then
        fso.DeleteFile(STK_DATA)
    End If
    
    If (fso.FileExists(STK_MDD)) Then
        fso.DeleteFile(STK_MDD)
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

'' -----------------------------------------------------------------------
'Metadata(ENU, Analysis, Label, Input)
'    STKLoop - loop
'    {
'        use SL_BrandListAssigned -
'    } fields -
'    (
'
'
'' Add your variables here, inside the loop
'' However, is STKCreate the right script, are you sure?
'' ...
'
'
'    ) expand;
'End Metadata
'' -----------------------------------------------------------------------

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

'Event(OnNextCase)
'
'' ...
'
'End Event

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
