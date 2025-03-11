# MDMAutoStacking
A fun attempt to automate stacking

Download files from the latest Release page:
[Releases](../../releases/latest)

To get it started, just edit the BAT file and insert the path to your MDD. Then just start the BAT file. Please note, there is no "pause" at the end. If it disappears, it means everything worked and finished successfully. 401_PreSTack and 402_Stack files will be generated (in the same folder as your MDD, or in the same folder as the BAT file, if you put "." as OUT_PATH inside the BAT file, so this can be configured - see inside the BAT file).

You don't even have to define what you are stacking on. The tool will decide everything for you.

Enjoy.

I tested it on a ~10 projects, it worked absolutely perfectly.

You need python installed and IBM/Unicom Professional to have this tool running. It is a requirement.

If some python packages are missing, just type
`python -m pip install xxx`
where xxx is a missing package.

The tool is distributed as a .py file, but you can't edit it. If you are not happy with the results, find the source codes (they are open) and re-generate the compiled bundle. Do NOT edit, as this bundle is a tricky file - python is reading and loading parts of self in runtime, and start and end positions of these parts are hardcoded. If you edit anything, block positions will be incorrect, and running the file will lead to undefined behaviour.

# Frequently asked questions
- Q: Can I use this tool, is it officially supported?<br />A: No, it was created entirely for fun. The codebase is quite complicated - I even separated some of its parts as separate repositories - the part that handles patching files, the part that reads MDD, etc... And I am using these repositories across several "fun" projects (diffing MDD, diffing Excel, or SPSS, prefill flatout map, and so on...) The complexisty of supporting these tools will be too high, given that I see that supporting smaller tasks takes years and years. So, no way, that's just for fun. But I am okay giving free support and updates while I am here. The quaity of code is good enough for me, and I don't care if someone else does not find it clean. So supporting it is not a problem for me.
- Q: The results look great, but I still need some adjustments in final scripts - change "PROCESSED_MDD" to "POSTMERGED_MDD", change path to some include files, change some parts in logic, and which iterations are stacked... Can this be done?<br />A: Yes, all of these modifications are possible, the tool is much more flexible than you might think. But I am not giving any guidance on how to configure it publically as it's too much engineering for you. And, to make it clear, all these updates are possible not modifying the python script.
- Q - Or, I see this is based on 401_PreStack and 402_Stack scripts from some shell version... Our shell was updated, can I have it started from newer template?<br />A: Yes, the template is generate as one of the steps in a BAT file, and then the template is patched. You can replace this step and take the template from elsewhere - just look inside the BAT file.
- Q - You are saying we "don't have to choose what we stack". How is that? We need to choose!<br />A: This tool was created for fun. Enjoy the free version. Yes, choosing what is stacked is not officially supported. You see some params for "priority" brands in the BAT file, in fact this param changes some of the weights but does not guarantee what is chosen. Or, you can look inside the BAT file, find a step where a list of variables and categories to stack is generated and saved in json. You can replace this step and give the program your own json, manually edited, with questions you need. Just follow the same pattern you see inside existing json.
- Q - I don't see anything generated. Where the results are?<br />The generated scripts should be R123456_401_PreStack.dms and R123456_402_Stack.dms files saved at some location. Look inside the BAT file, this param is one of the top config options. The default could be next to your MDD or the same location as the BAT file.

