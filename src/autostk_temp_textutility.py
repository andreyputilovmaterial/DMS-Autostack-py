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





def find_text_span(text,action,position=None):
    if action=='section-metadata':
        regex = r'(.*?\n\s*?\bMetadata\b\s*?(?:\([^\n]*?\)\s*?)?(?:\'[^\n]*?)?\s*?\n)((?:.*?\n)?)(\s*?\bEnd\b\s*?\bMetadata\b\s*?(?:\'[^\n]*?)?\s*?\n.*?)'
        find_regex_results = re.finditer(regex,text,flags=re.I|re.M|re.DOTALL)
        if not find_regex_results:
            return None
        captured_group_num = 2
        return [m for m in find_regex_results][0].span(captured_group_num)
    elif action=='section-onnextcase':
        regex = r'(.*?\n\s*?\bEvent\b\s*?(?:\(\s*?OnNextCase\s*?\)\s*?)(?:\'[^\n]*?)?\s*?\n)((?:.*?\n)?)(\s*?\bEnd\b\s*?\bEvent\b\s*?(?:\'[^\n]*?)?\s*?\n.*?)'
        find_regex_results = re.finditer(regex,text,flags=re.I|re.M|re.DOTALL)
        if not find_regex_results:
            return None
        captured_group_num = 2
        return [m for m in find_regex_results][0].span(captured_group_num)
    elif action=='insert':
        if position=='':
            regex = r'^((?:\s*?[^\n]*?\s*?\n)*?\s*?#include\b[^\n]*?\bGlobals\.mrs[^\n]*?\s*?\n(?:\s*?\'*?\s*?#(?:include|define)\b[^\n]*?\s*?\n)*)()(.*)$'
            find_regex_results = re.finditer(regex,text,flags=re.I|re.M|re.DOTALL)
            if not find_regex_results:
                regex = r'^((?:\s*?[^\n]*?\s*?\n)*?(?:\s*?\'*?\s*?#(?:include|define)\b[^\n]*?\s*?\n)*)()(.*)$'
                find_regex_results = re.finditer(regex,text,flags=re.I|re.M|re.DOTALL)
            if not find_regex_results:
                regex = r'^^(\s*\n)()(.*)$'
                find_regex_results = re.finditer(regex,text,flags=re.I|re.M|re.DOTALL)
            captured_group_num = 2
            return [m for m in find_regex_results][0].span(captured_group_num)
        else:
            raise ValueError('inserting code at other positions: not implemented (please add regex, it\'s simple')

    else:
        raise ValueError('patch position not found: {a}'.format(a=action))



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
        '--replace-mdata',
        help='Append metadata part',
        type=str,
        required=False
    )
    parser.add_argument(
        '--replace-edits',
        help='Append edits part',
        type=str,
        required=False
    )
    parser.add_argument(
        '--replace-defs',
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
    if args.replace_mdata:
        inserted_mdata_fname = Path(args.replace_mdata)
        inserted_mdata_fname = '{inserted_mdata_fname}'.format(inserted_mdata_fname=inserted_mdata_fname.resolve())
    
    inserted_edits_fname = None
    if args.replace_edits:
        inserted_edits_fname = Path(args.replace_edits)
        inserted_edits_fname = '{inserted_edits_fname}'.format(inserted_edits_fname=inserted_edits_fname.resolve())
    inserted_defs_list_fname = []
    if args.replace_defs:
        inserted_defs_list_fname = Path(args.replace_defs)
        inserted_defs_list_fname = '{inserted_defs_list_fname}'.format(inserted_defs_list_fname=inserted_defs_list_fname.resolve())

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
    if inserted_defs_list_fname:
        if not(Path(inserted_defs_list_fname).is_file()):
            raise FileNotFoundError('file not found: {fname}'.format(fname=inserted_defs_list_fname))

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
    inserted_defs_list = None
    if inserted_defs_list_fname:
        with open(inserted_defs_list_fname,'r',encoding='utf-8') as f_l:
            inserted_defs_list = json.load(f_l)
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
    print('{script_name}: template: "{t}"'.format(t=action,script_name=script_name))

    result = template
    # insert metadata
    if inserted_mdata:
        inserted_piece = inserted_mdata
        inserted_piece_span = find_text_span(result,'section-metadata')
        if inserted_piece_span:
            print('{script_name}: adding Metadata Section'.format(script_name=script_name))
            result = result[:inserted_piece_span[0]] + inserted_piece + result[inserted_piece_span[1]:]
        else:
            print('{script_name}: adding Metadata Section: not found'.format(script_name=script_name))
    # insert edits
    if inserted_edits:
        inserted_piece = inserted_edits
        inserted_piece_span = find_text_span(result,'section-onnextcase')
        if inserted_piece_span:
            print('{script_name}: adding OnNextCase Section'.format(script_name=script_name))
            result = result[:inserted_piece_span[0]] + inserted_piece + result[inserted_piece_span[1]:]
        else:
            print('{script_name}: adding OnNextCase Section: not found'.format(script_name=script_name))
    # insert defs
    if inserted_defs_list:
        for chunk in inserted_defs_list:
            inserted_piece = chunk['new_lines']
            inserted_piece_span = find_text_span(result,'insert',position=chunk['position'])
            if inserted_piece_span:
                print('{script_name}: adding lines to Section {s}'.format(s=chunk['position'] if chunk['position'] else 'top-level',script_name=script_name))
                result = result[:inserted_piece_span[0]] + inserted_piece + result[inserted_piece_span[1]:]
            else:
                print('{script_name}: adding lines to Section {s}: can\'t add, dest position not found'.format(s=chunk['position'] if chunk['position'] else 'top-level',script_name=script_name))
    
    print('{script_name}: saving as "{fname}"'.format(fname=result_final_fname,script_name=script_name))
    with open(result_final_fname, "w",encoding='utf-8') as outfile:
        outfile.write(result)

    time_finish = datetime.now()
    print('{script_name}: finished at {dt} (elapsed {duration})'.format(dt=time_finish,duration=time_finish-time_start,script_name=script_name))



if __name__ == '__main__':
    entry_point({'arglist_strict':True})
