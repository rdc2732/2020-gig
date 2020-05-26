import jinja2
import os
import sys
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.file import File 
from subprocess import check_call
import io
from criticalpath import Node
import pandas as pd

pd.set_option('display.max_rows', None)

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)
template = jenv.get_template('cp4.j2')

## 1) Use Pandas to create a flat file that relates all the features, stories and blocked stories.
##    The source for this data is the 'CustomerReport.xlsx' spreadsheet.
##    Note: a future enhancement is to have the program read the file directly from SharePoint

rank = pd.read_excel('PI_15_Feature_Rank_List.xlsm',sheet_name='Feature_List',usecols='A,L,AP')
rank['Id'] = rank['Id'].fillna(0).astype(int)
rank = rank.loc[(rank['Rank'].notnull()) & (rank['Rank'] != 'Unranked') & (rank['Id'] != 0)]
rank['Rank'] = rank['Rank'].astype(int)
rank.rename(columns={'Id' : 'FeatureId'}, inplace=True)

cust = pd.read_csv('Critical Path.csv', sep="\t")
cust.rename(columns={'Story Points (numeric)' : 'SP', 'Planned For' : 'PlannedFor'}, inplace=True)
cust['Parent'] = cust['Parent'].str.replace('#','')
cust['Blocks'] = cust['Blocks'].str.replace('#','')
cust['SP'] = cust['SP'].fillna(0)
cust['SP'] = cust['SP'].astype(int)
cust['Parent'] = cust['Parent'].fillna(0)
cust['Parent'] = cust['Parent'].astype(int)

features = cust.loc[(cust['Type'] == 'Feature')].copy()
features = features[['Id','Summary']]
features.rename(columns={'Id' : 'FeatureId'}, inplace=True)
features = features.merge(rank, how='right', left_on='FeatureId', right_on='FeatureId')

stories = cust.loc[(cust.Type == 'Story') & (cust['Parent'] > 0)].copy()
stories.rename(columns={'Parent' : 'FeatureId'}, inplace=True)
stories = stories[['FeatureId', 'Id', 'PlannedFor', 'SP', 'Blocks']]

vectors = stories.copy()
vectors = \
(vectors.set_index(vectors.columns.drop('Blocks',1).tolist())
   .Blocks.str.split('\n', expand=True)
   .stack()
   .reset_index()
   .rename(columns={0:'Blocks'})
   .loc[:, vectors.columns]
)

vectors['Blocks'] = vectors['Blocks'].fillna(0)
vectors['Blocks'] = vectors['Blocks'].astype(int)
vectors.rename(columns={'Id' : 'BkrId','PlannedFor' : 'BkrPf','SP' : 'BkrSP','Blocks' : 'BkdId'}, inplace=True)
vectors = vectors.merge(cust, how='left', left_on='BkdId', right_on='Id')
vectors.rename(columns={'FeatureId_x' : 'FeatureId','PlannedFor' : 'BkdPf','SP' : 'BkdSP'}, inplace=True)
vectors.drop(columns=['Id','Blocks','Parent','Type','Summary','Status'], inplace=True)

vectors['BkdPf'] = vectors['BkdPf'].fillna("")
vectors['BkdSP'] = vectors['BkdSP'].fillna(0)
vectors['BkdSP'] = vectors['BkdSP'].astype(int)

## 2) For each feature determine critical path nodes, links, and duration

proj_dict = {}  # Holds the critical path module's projects (features)
node_dict = {}  # Holds each features nodes

# First add all the nodes to each project, else key error
FeatureIds = features['FeatureId'].unique().tolist()
for FeatureId in FeatureIds:
    proj_dict[FeatureId] = Node(FeatureId)
    vector_data = vectors.loc[vectors['FeatureId'] == FeatureId]
    if len(vector_data) > 0:
        for vector in vector_data.itertuples():
            if vector.BkrId not in node_dict:
                node_dict[vector.BkrId] = proj_dict[FeatureId].add(Node(vector.BkrId, duration=vector.BkrSP))
            if vector.BkdId not in node_dict:
                node_dict[vector.BkdId] = proj_dict[FeatureId].add(Node(vector.BkdId, duration=vector.BkdSP))

# Then, add all the dependency links
for FeatureId in FeatureIds:
    vector_data = vectors.loc[vectors['FeatureId'] == FeatureId]
    if len(vector_data) > 0:
        for vector in vector_data.itertuples():
            proj_dict[FeatureId].link(node_dict[vector.BkrId], node_dict[vector.BkdId])
        proj_dict[FeatureId].update_all()

# And then, calculate the critical path and duration.
##feature_cp_node_dict = {}
##feature_cp_link_dict = {}
##feature_cp_link_dura = {}
##for FeatureId in FeatureIds:
##    print('FeatureId: ', FeatureId, proj_dict[FeatureId].get_critical_path(), proj_dict[FeatureId].duration)

## 3) Loop through the Pandas data.  Print each Feature's data to the template:
##    Team, FeatureId, Summary: goes to chart label
##      Sprint: goes to the cluster label
##          [(StoryId, SP)]: list of stories/SP goes to cluster
##      [(StoryId, SP, BlockedId, SP)] list of vectors goes to the chart
##
##        clusters = {} # For each Feature, build a dictionary of clusters {PlannedFor: [(story, SP)]}

Teams = features['Team'].unique().tolist()
for Team in Teams:
    team_data = features.loc[features['Team'] == Team]
    
    FeatureIds = team_data[team_data['Team'] == Team]['FeatureId'].unique().tolist()
    for FeatureId in FeatureIds:
        feature_data = features.loc[features['FeatureId'] == FeatureId]
        Rank = feature_data['Rank'].iloc[0].astype(int)
        Summary = feature_data['Summary'].iloc[0]
        PlannedFors = stories.loc[stories['FeatureId'] == FeatureId]['PlannedFor'].unique().tolist()
        PlannedFors.sort()

        cluster_dict = {}
        for PlannedFor in PlannedFors:
            StoryIds = stories.loc[(stories['FeatureId'] == FeatureId) & (stories['PlannedFor'] == PlannedFor)]['Id'].unique().tolist()
            StoryIds.sort()
            story_list = []
            for StoryId in StoryIds:
                story_data = stories.loc[stories['Id'] == StoryId]
                StorySP = story_data['SP'].iloc[0]
                story_list.append((StoryId, StorySP))
                    
            cluster_dict[PlannedFor] = story_list

        vector_list = []
        vector_data = vectors.loc[vectors['FeatureId'] == FeatureId]
        for vector in vector_data.itertuples():
            vector_list.append((vector.BkrId, vector.BkrSP, vector.BkdId, vector.BkdSP))

        chart_label = Team + '-' + str(FeatureId) + '[' + str(Rank) + ']: ' + Summary.replace('"',"'")

        dot_data = template.render(chart_label = chart_label, clusters = cluster_dict, vectors = vector_list)
        dot_file = Team + '-' + str(FeatureId) + '.dot'
        png_file = Team + '-' + str(FeatureId) + '.png'
        
        with open(dot_file, mode='w') as file_object:
            print(dot_data, file=file_object)

        check_call(['dot','-Tpng',dot_file,'-o',png_file])
        os.remove(dot_file)


