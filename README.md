# MDMAutoStacking
A fun attempt to automate stacking

Download files from the latest Release page:
[Releases](../../releases/latest)

To get it started, just edit the BAT file and insert the path to your MDD. Then just start the BAT file. Please note, there is no "pause" at the end. If it disappears, it means everything worked and finished successfully. 401_PreSTack and 402_Stack files will be generated (in the same folder as the BAT file but this can be configured - see inside the BAT file).

You don't even have to define what you are stacking on. The tool will decide everything for you.

Enjoy.

I tested it on a ~10 projects, it worked absolutely perfectly.

You need python installed and IBM/Unicom Professional to have this tool running. It is a requirement.

If some python packages are missing, just type
`python -m pip install xxx`
where xxx is a missing package.

The tool is distributed as a .py file, but you can't edit it. If you are not happy with the results, find the source codes (they are open) and re-generate the compiled bundle. Do NOT edit, as this bundle is a tricky file - python is reading and loading parts of self in runtime, and start and end positions of these parts are hardcoded. If you edit anything, block positions will be incorrect, and running the file will lead to undefined behaviour.