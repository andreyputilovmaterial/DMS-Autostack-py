# import os, time, re, sys
import os
from datetime import datetime, timezone
# from dateutil import tz
import argparse
from pathlib import Path
import re
import json



# if __name__ == '__main__':
#     # run as a program
#     import helper_utility_wrappers
# elif '.' in __name__:
#     # package
#     from . import helper_utility_wrappers
# else:
#     # included with no parent package
#     import helper_utility_wrappers




TEMPLATE_401 = """
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

'StackingLoop: Loop from R-files containing data we want stacked
#Define STACKINGLOOP "ChildLoop"

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

'Add new variables here. Add them as fields in the Loop below, and they will become top-level fields in the stacked output.

STACKINGLOOP
Loop
{
	'No need to define iterations if this is an existing Loop
}
fields
(
	STK_ID
	Text[..255];

	'Add new fields here, including banners for stacked data.
	
	'e.g.,
	'Banner3 "Banner3 - Stacked Banner"
	'categorical
	'{
	'	Total "Total",
	'	BannerPt2 "Some Banner Point Label",
	'	BannerPt3,
	'	BannerPt4,
	'	BannerPt5
	'} axis("{..,unweightedbase() [IsHidden=True], base() [IsHidden=True]}");

	'Populate variables in OnNextCase
)expand;

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

Dim Cat, oSL
'refer to overall loop as oSL for the rest of OnNextCase
execute("Set oSL = " +STACKINGLOOP)

'Populate variables inside stacking loop
For Each Cat in oSL.Categories
	With oSL[Cat.Name]
		'Create unique ID for each stacked record
		'Future versions of this script should probably use CodingID as the base, but that relies on Survey Shell 6.3.0+
		.STK_ID = Respondent.ID + "_" + Cat.Name
		
''		'.FieldOne = . . .
''		If .SomeVar is not null then
''			.Banner3 = {Total} + _
''				iif('!Some Condition!',{BannerPt2},{}) + _
''				iif('!Some Condition!',{BannerPt3},{}) + _
''				iif('!Some Condition!',{BannerPt4},{}) + _
''				iif('!Some Condition!',{BannerPt5},{})
''		end if
	End With
Next

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

TEMPLATE_402 = """
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
#Define STACKINGLOOP "ChildLoop"

'UnstackedVars: Respondent-level variables to include in stacked files
'    -Access Respondent-level variables with "^.Var"
'    -Use "^.Var as Var" naming for any variable not currently inside a block
'    -For Loops within Loops, add a carrot per level: "^.^.Var"
#Define UNSTACKEDVARS "^.Respondent.ID, ^.Respondent.Serial, ^.DataCollection.Status, ^.DataCollection.StartTime, ^.DataCollection.FinishTime, ^.Comp as Comp, ^.PrelimBanner as PrelimBanner, ^.Banner1 as Banner1, ^.Weight_Completes as Weight_Completes"

'WhichIterations: Used in the Where clause to determine which iterations to include
'    -We rarely want to include all iterations with any data at all ("TRUE")
'    -Usually depends on whether some variable inside the loop is populated ("ChildAge is not null")
'        -Syntax here is at the loop level: "ChildAge" not "ChildLoop.ChildAge"
#Define WHICHITERATIONS "ChildAge is not null"


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

' -----------------------------------------------------------------------
Metadata(ENU, Analysis, Label, Input)

'It is possible to add new variables here. Add them as fields in the Loop below, and they will become top-level fields in the stacked output.

''STACKINGLOOP
''Loop
''{
''}
''fields
''(
''	'Add new fields here.
''	
''	'Populate variables using expression logic: existing loop fields are available as top-level variables (ChildAge, Not ChildLoop[{_1}].ChildAge)
''	'e.g., ChildAge is a field inside ChildLoop
''	'ChildAgeNet
''	'categorical[1]
''	'{
''	'	_0_2 "0-2 yrs old" expression("ChildAge <= 2"),
''	'	_3_6 "3-6 yrs old" expression("ChildAge >= 3 and ChildAge <= 6"),
''	'	_7_10 "7-10 yrs old" expression("ChildAge >= 7 and ChildAge <= 10"),
''	'	_11_14 "11-14 yrs old" expression("ChildAge >= 11 and ChildAge <= 14")
''	'};
''
'')expand;

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

'Syntax in OnNextCase executes at Loop level. Access stacked variables directly. DO NOT attempt to iterate through original loop.
	'e.g., ChildAge is a field inside ChildLoop
	'Select Case ChildAge
	'	Case 0 to 2
	'		ChildAgeNet = {_0_2}
	'	Case 3 to 6
	'		ChildAgeNet = {_3_6}
	'	Case 7 to 10
	'		ChildAgeNet = {_7_10}
	'	Case 11 to 14
	'		ChildAgeNet = {_11_14}
	'End Select
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



def entry_point(runscript_config={}):

    time_start = datetime.now()
    script_name = 'mdmautostktoolsap mdd stk texttools'

    parser = argparse.ArgumentParser(
        description="MDD: produce text files",
        prog='mdd-autostk-text-utility'
    )
    parser.add_argument(
        '--action',
        help='Specify template name and action',
        type=str,
        required=True
    )
    parser.add_argument(
        '--mdata',
        help='Append metadata part',
        type=str,
        required=False
    )
    parser.add_argument(
        '--edits',
        help='Append edits part',
        type=str,
        required=False
    )
    parser.add_argument(
        '--output-filename',
        help='Set preferred output file name, with path',
        type=str,
        required=False
    )
    args = None
    args_rest = None
    if( ('arglist_strict' in runscript_config) and (not runscript_config['arglist_strict']) ):
        args, args_rest = parser.parse_known_args()
    else:
        args = parser.parse_args()
    
    inserted_mdata_fname = None
    if args.mdata:
        inserted_mdata_fname = Path(args.mdata)
        inserted_mdata_fname = '{inserted_mdata_fname}'.format(inserted_mdata_fname=inserted_mdata_fname.resolve())
    
    inserted_edits_fname = None
    if args.edits:
        inserted_edits_fname = Path(args.edits)
        inserted_edits_fname = '{inserted_edits_fname}'.format(inserted_edits_fname=inserted_edits_fname.resolve())

    config = {}

    action = None
    if args.action:
        if args.action=='template-401':
            action = 'template-401'
        elif args.action=='template-402':
            action = 'template-402'
        else:
            raise TypeError('mdd autostk texttools: this action is not implemented yet: "{a}"'.format(a=args.action))

    result_final_fname = None
    if args.output_filename:
        result_final_fname = Path(args.output_filename)
    else:
        raise FileNotFoundError('Inp source: file not provided; please use --inp-mdd-scheme option')
    

    if inserted_mdata_fname:
        if not(Path(inserted_mdata_fname).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=inserted_mdata_fname))
    if inserted_edits_fname:
        if not(Path(inserted_edits_fname).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=inserted_edits_fname))

    inserted_mdata = None
    if inserted_mdata_fname:
        with open(inserted_mdata_fname,'r',encoding='utf-8') as f_l:
            inserted_mdata = f_l.read()
            f_l.close()
    inserted_edits = None
    if inserted_edits_fname:
        with open(inserted_edits_fname,'r',encoding='utf-8') as f_l:
            inserted_edits = f_l.read()
            f_l.close()
    
    print('{script_name}: script started at {dt}'.format(dt=time_start,script_name=script_name))

    result = None
    template = ''
    if action=='template-401':
        template = TEMPLATE_401
    elif action=='template-402':
        template = TEMPLATE_402
    else:
        raise TypeError('mdd autostk texttools: this action is not implemented yet: "{a}"'.format(a=args.action))

    result = template
    result = re.sub(r'(.*?\n\s*?\bMetadata\b\s*?(?:\([^\n]*?\)\s*?)?(?:\'[^\n]*?)?\s*?\n)((?:.*?\n)?)(\s*?\bEnd\b\s*?\bMetadata\b\s*?(?:\'[^\n]*?)?\s*?\n.*?)',lambda m: '{begin}{ins}{_end}'.format(begin=m[1],_end=m[3],ins=inserted_mdata if inserted_mdata else m[2]),result,flags=re.I|re.M|re.DOTALL)
    result = re.sub(r'(.*?\n\s*?\bEvent\b\s*?(?:\(\s*?OnNextCase\s*?\)\s*?)(?:\'[^\n]*?)?\s*?\n)((?:.*?\n)?)(\s*?\bEnd\b\s*?\bEvent\b\s*?(?:\'[^\n]*?)?\s*?\n.*?)',lambda m: '{begin}{ins}{_end}'.format(begin=m[1],_end=m[3],ins=inserted_edits if inserted_edits else m[2]),result,flags=re.I|re.M|re.DOTALL)
    
    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w",encoding='utf-8') as outfile:
        outfile.write(result)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
