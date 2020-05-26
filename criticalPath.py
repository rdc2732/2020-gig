import jinja2
import os

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)

template = jenv.get_template('cp.j2')
print(template.render(team_name = "Cyber",  feature_name = "Feature 123345", paths = ['abc','def','ghi']))


'''
let
    Source = CustomerReport,
    ReplacedValue = Table.ReplaceValue(Source,"MUOS/","",Replacer.ReplaceText,{"Filed Against"}),
    FilteredRows = Table.SelectRows(ReplacedValue, each ([Planned For] = "EA 14.1" or [Planned For] = "EA 14.2" or [Planned For] = "EA 14.3" or [Planned For] = "EA 14.4" or [Planned For] = "EA 14.5" or [Planned For] = "PI 14")),
    RemovedColumns = Table.RemoveColumns(FilteredRows,{"Type", "Summary", "Proposed", "Planned For", "Status", "Success Criteria", "Description", "Acceptance Criteria", "Estimated Story Points", "Feature Type", "SAFe Enabler Type", "Story Points (numeric)", "Tags", "Estimate", "Owned By", "Configuration Item", "Target Deployment", "Project Authorization", "SAFe Work Type", "Sustainment", "Level of Effort", "Priority", "Severity", "Actual Story Points", "Modified By", "Depends On"}),
    RenamedColumns = Table.RenameColumns(RemovedColumns,{{"Filed Against", "Team"}}),
    ReplacedValue1 = Table.ReplaceValue(RenamedColumns,"#","",Replacer.ReplaceText,{"Parent"}),
    FilteredRows1a = Table.SelectRows(ReplacedValue1, each ([Blocks] <> "")),
    SplitBlocks = Table.ExpandListColumn(Table.TransformColumns(FilteredRows1a, {{"Blocks", Splitter.SplitTextByDelimiter("#(lf)", QuoteStyle.Csv), let itemType = (type nullable text) meta [Serialized.Text = true] in type {itemType}}}), "Blocks"),
    ChangedType = Table.TransformColumnTypes(SplitBlocks,{{"Blocks", type text}, {"Id", type text}}),
    RenamedColumns1 = Table.RenameColumns(ChangedType,{{"Id", "Start"}, {"Blocks", "End"}, {"Parent", "Feature"}}),
    ReorderedColumns = Table.ReorderColumns(RenamedColumns1,{"Team", "Feature", "Start", "End"}),
    SortedRows = Table.Sort(ReorderedColumns,{{"Team", Order.Ascending}, {"Feature", Order.Ascending}, {"Start", Order.Ascending}}),
    AddedVectors = Table.AddColumn(SortedRows, "Vectors", each [Start] & " -> " & [End] & ";"),
    ChangedType1 = Table.TransformColumnTypes(AddedVectors,{{"Vectors", type text}}),
    RemovedColumns1 = Table.RemoveColumns(ChangedType1,{"Start", "End"})
in
    RemovedColumns1
'''


