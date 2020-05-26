import jinja2
import os
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.file import File 
import io

import pandas as pd

ead_list = ['EA 15.1', 'EA 15.2', 'EA 15.3', 'EA 15.4' , 'EA 15.5', 'EA 16 - In Progress', 'EA 17 - In Progress']

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)
template = jenv.get_template('cp_features.j2')

## 1) Use Pandas to create a flat file that relates all the features and the epics they block.
##    The source for this data is the 'CustomerReport.xlsx' spreadsheet.
##    Note: a future enhancement is to have the program read the file directly from SharePoint

rank = pd.read_excel('PI_15_Feature_Rank_List.xlsm',sheet_name='Feature_List',usecols='A,AP')

rank['Id'] = rank['Id'].fillna(0).astype(int)
rank = rank.loc[(rank['Rank'].notnull()) & (rank['Rank'] != 'Unranked') & (rank['Id'] != 0)]

rank['Rank'] = rank['Rank'].astype(int)
rank.rename(columns={'Id' : 'FeatureId'}, inplace=True)

cust = pd.read_excel('CustomerReport.xlsx',sheet_name='CustomerReport',usecols='A,B,C,D,F,G,H,L,O,AD')
cust.rename(columns={'Filed Against' : 'Team', 'Story Points (numeric)' : 'SP', 'Estimated Story Points' : 'ESP', 'Planned For' : 'PlannedFor'}, inplace=True)
cust['Parent'] = cust['Parent'].str.replace('#','')
cust['Team'] = cust['Team'].str.replace('MUOS/','')
cust['SP'] = cust['SP'].fillna(0)
cust['Parent'] = cust['Parent'].fillna(0)
cust['Parent'] = cust['Parent'].astype(int)
cust.loc[cust['Team'].apply(len) > 23, 'NewTeam'] = cust['Team'].str[:10] + '...' + cust['Team'].str[-10:]
cust.loc[cust['Team'].apply(len) <= 23, 'NewTeam'] = cust['Team']
cust = cust.drop(['Team'], axis=1)
cust.rename(columns={'NewTeam':'Team'}, inplace=True)

epics = cust.loc[(cust['Type'] == 'Program Epic')]
epics = epics.drop(['Parent', 'Type', 'PlannedFor', 'SP', 'Blocks', 'Status'], axis=1)
epics = epics[['Team','Id','Summary']]
      
epics.sort_values(by = ['Team', 'Id'], inplace = True)
epics.rename(columns={'Id' : 'EpicId'}, inplace=True)

features = cust[(cust.Type == 'Feature') & (cust['Parent'] > 0)]
features = features.drop(['Type', 'Summary', 'Status', 'Team', 'Blocks'], axis=1)
features.rename(columns={'Parent' : 'EpicId'}, inplace=True)
features = features[['EpicId', 'Id', 'PlannedFor', 'ESP']]
features.sort_values(by = ['EpicId', 'Id'], inplace = True)

vectors = cust[(cust['Type'] == 'Feature')]
vectors = vectors.drop(['Type', 'Parent', 'Summary', 'SP', 'ESP', 'Status', 'PlannedFor', 'Team'], axis=1)
vectors = \
(vectors.set_index(vectors.columns.drop('Blocks',1).tolist())
   .Blocks.str.split('\n', expand=True)
   .stack()
   .reset_index()
   .rename(columns={0:'Blocks'})
   .loc[:, vectors.columns]
)
vectors['Blocks'] = vectors['Blocks'].astype(int)
vectors.rename(columns={'Id' : 'BlockerId', 'Blocks' : 'BlockedId'}, inplace=True)
vectors = vectors.loc[(vectors['BlockedId'] > 0)]
vectors = vectors.merge(features, how='right', left_on='BlockerId', right_on='Id')
vectors.sort_values(by = ['BlockerId'], inplace = True)
vectors.drop(columns=['EpicId','Id','PlannedFor'], inplace=True)
vectors.rename(columns={'ESP' : 'BlockedESP'}, inplace=True)

all_data = epics.merge(features, how='left', left_on='EpicId', right_on='EpicId').dropna()
all_data.rename(columns={'Id' : 'FeatureId'}, inplace=True)
all_data = all_data.merge(vectors, how='left', left_on='FeatureId', right_on='BlockerId')
all_data.drop(columns=['BlockerId'], inplace=True)
all_data['ESP'] = all_data['ESP'].astype(int)
all_data['BlockedId'] = all_data['BlockedId'].fillna(0).astype(int)
all_data['BlockedESP'] = all_data['BlockedESP'].fillna(0).astype(int)
all_data = all_data[['Team','EpicId','Summary','PlannedFor','FeatureId','ESP','BlockedId','BlockedESP']]
all_data = all_data.merge(rank, how='right', left_on='FeatureId', right_on='FeatureId').dropna()
all_data['FeatureId'] = all_data['FeatureId'].astype(int)
all_data.sort_values(by = ['Rank'], inplace = True)

## 2) Loop through the Pandas data.  Print each Feature's data to the template:
##    Team, FeatureId, Summary: goes to chart label
##      Sprint: goes to the cluster label
##          [(StoryId, SP)]: list of stories/SP goes to cluster
##      [(StoryId, SP, BlockedId, SP)] list of vectors goes to the chart
##

##Teams = all_data['Team'].unique().tolist()
##for Team in Teams:
##    team_data = all_data.loc[all_data['Team'] == Team]
##
##    EpicIds = team_data[team_data['Team'] == Team]['EpicId'].unique().tolist()
##    for EpicId in EpicIds:
##        vector_list = [] # For each Feature, build a list of vectors (story, SP, blocked, SP)
##        cluster_list = {} # For each Feature, build a dictionary of clusters {sprint: [(story, SP)]}
##        epic_data = team_data[team_data['EpicId'] == EpicId]
##        Summary = epic_data.loc[epic_data['EpicId'] == EpicId]['Summary'].unique().tolist()[0]
##    

#PlannedFors = epic_data.loc[epic_data['EpicId'] == EpicId]['PlannedFor'].unique().tolist()

##PlannedFors = all_data['PlannedFor'].unique().tolist()
##for PlannedFor in PlannedFors:
##    feature_list = [] # For each Sprint, build a list of stories [(story, SP)]
##    plannedfor_data = all_data.loc[all_data['PlannedFor'] == PlannedFor]
##    vector_list = [] # For each Feature, build a list of vectors (story, SP, blocked, SP)
##    cluster_list = {} # For each Feature, build a dictionary of clusters {sprint: [(story, SP)]}

##FeatureIds = plannedfor_data.loc[plannedfor_data['PlannedFor'] == PlannedFor]['FeatureId'].unique().tolist()
FeatureIds = all_data['FeatureId'].unique().tolist()
for FeatureId in FeatureIds:
    feature_data = plannedfor_data.loc[plannedfor_data['FeatureId'] == FeatureId]
    FeatureESP = feature_data.loc[feature_data['FeatureId'] == FeatureId]['ESP'].unique().tolist()[0]
    FeatureRank = feature_data.loc[feature_data['FeatureId'] == FeatureId]['Rank'].unique().tolist()[0]
    feature_list.append((FeatureId, FeatureESP, FeatureRank))

    BlockedIds = feature_data.loc[feature_data['FeatureId'] == FeatureId]['BlockedId'].unique().tolist()
    for BlockedId in BlockedIds:
        blocked_data = feature_data.loc[feature_data['BlockedId'] == BlockedId]
        BlockedESP = blocked_data[blocked_data['BlockedId'] == BlockedId]['BlockedESP'].unique().tolist()[0]
        if BlockedId != 0:
            vector_list.append((FeatureId, FeatureESP, BlockedId, BlockedESP))
        
cluster_list[FeatureId] = feature_list

chart_label = FeatureId

##    chart_label = '[' + Team + '] Epic ' + str(EpicId) + ': ' + Summary
##    print(template.render(chart_label = chart_label, clusters = cluster_list, vectors = vector_list))
print(chart_label, '\n', cluster_list, '\n', vector_list, '\n\n\n')

