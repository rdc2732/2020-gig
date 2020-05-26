import jinja2
import os
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.file import File 
import io

import pandas as pd

ead_list = ['EA 15.1', 'EA 15.2', 'EA 15.3', 'EA 15.4' , 'EA 15.5', 'PI 16 - In Progress']

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)
template = jenv.get_template('cp4.j2')

## 1) Use Pandas to create a flat file that relates all the features, stories and blocked stories.
##    The source for this data is the 'CustomerReport.xlsx' spreadsheet.
##    Note: a future enhancement is to have the program read the file directly from SharePoint

cust = pd.read_excel('CustomerReport.xlsx',sheet_name='CustomerReport',usecols='A,B,C,D,F,G,H,O,AD')
cust.rename(columns={'Filed Against' : 'Team', 'Story Points (numeric)' : 'SP', 'Planned For' : 'PlannedFor'}, inplace=True)
cust['Parent'] = cust['Parent'].str.replace('#','')
cust['Team'] = cust['Team'].str.replace('MUOS/','')
cust['SP'] = cust['SP'].fillna(0)
cust['Parent'] = cust['Parent'].fillna(0)
cust['Parent'] = cust['Parent'].astype(int)

features = cust.loc[(cust['Type'] == 'Feature') & (cust['Status'] != 'Done') & \
    (cust['PlannedFor'].isin(ead_list))]
features = features.drop(['Parent', 'Type', 'PlannedFor', 'SP', 'Blocks', 'Status'], axis=1)
features = features[['Team','Id','Summary']]
features.sort_values(by = ['Team', 'Id'], inplace = True)
features.rename(columns={'Id' : 'FeatureId'}, inplace=True)

stories = cust[(cust.Type == 'Story') & (cust['Parent'] > 0)]
stories = stories.drop(['Type', 'Summary', 'Status', 'Team', 'Blocks'], axis=1)
stories.rename(columns={'Parent' : 'FeatureId'}, inplace=True)
stories = stories[['FeatureId', 'Id', 'PlannedFor', 'SP']]
stories.sort_values(by = ['FeatureId', 'Id'], inplace = True)

vectors = cust[(cust.Type == 'Story')]
vectors = vectors.drop(['Type', 'Parent', 'Summary', 'SP', 'Status', 'PlannedFor', 'Team'], axis=1)
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
vectors = vectors[(vectors['BlockedId'] > 0)]
vectors = vectors.merge(stories, how='right', left_on='BlockerId', right_on='Id')
vectors.sort_values(by = ['BlockerId'], inplace = True)
vectors.drop(columns=['FeatureId','Id','PlannedFor'], inplace=True)
vectors.rename(columns={'SP' : 'BlockedSP'}, inplace=True)

all_data = features.merge(stories, how='left', left_on='FeatureId', right_on='FeatureId').dropna()
all_data.rename(columns={'Id' : 'StoryId'}, inplace=True)
all_data = all_data.merge(vectors, how='left', left_on='StoryId', right_on='BlockerId')
all_data.drop(columns=['BlockerId'], inplace=True)
all_data['SP'] = all_data['SP'].astype(int)
all_data['BlockedId'] = all_data['BlockedId'].fillna(0).astype(int)
all_data['BlockedSP'] = all_data['BlockedSP'].fillna(0).astype(int)
all_data = all_data[['Team','FeatureId','Summary','PlannedFor','StoryId','SP','BlockedId','BlockedSP']]
all_data.sort_values(by = ['Team','FeatureId','PlannedFor','StoryId','BlockedId'], inplace = True)


## 2) Loop through the Pandas data.  Print each Feature's data to the template:
##    Team, FeatureId, Summary: goes to chart label
##      Sprint: goes to the cluster label
##          [(StoryId, SP)]: list of stories/SP goes to cluster
##      [(StoryId, SP, BlockedId, SP)] list of vectors goes to the chart
##

Teams = all_data['Team'].unique().tolist()
for Team in Teams:
    team_data = all_data[all_data['Team'] == Team]
    
    FeatureIds = team_data[team_data['Team'] == Team]['FeatureId'].unique().tolist()
    for FeatureId in FeatureIds:
        vectors = [] # For each Feature, build a list of vectors (story, SP, blocked, SP)
        clusters = {} # For each Feature, build a dictionary of clusters {PlannedFor: [(story, SP)]}
        feature_data = team_data[team_data['FeatureId'] == FeatureId]
        Summary = feature_data[feature_data['FeatureId'] == FeatureId]['Summary'].unique().tolist()[0]

        PlannedFors = feature_data[feature_data['FeatureId'] == FeatureId]['PlannedFor'].unique().tolist()
        for PlannedFor in PlannedFors:
            stories = [] # For each PlannedFor, build a list of stories [(story, SP)]
            plannedfor_data = feature_data[feature_data['PlannedFor'] == PlannedFor]

            StoryIds = plannedfor_data[plannedfor_data['PlannedFor'] == PlannedFor]['StoryId'].unique().tolist()
            for StoryId in StoryIds:
                story_data = plannedfor_data[plannedfor_data['StoryId'] == StoryId]
                StorySP = story_data[story_data['StoryId'] == StoryId]['SP'].unique().tolist()[0]
                stories.append((StoryId, StorySP))

                BlockedIds = story_data[story_data['StoryId'] == StoryId]['BlockedId'].unique().tolist()
                for BlockedId in BlockedIds:
                    blocked_data = story_data[story_data['BlockedId'] == BlockedId]
                    BlockedSP = blocked_data[blocked_data['BlockedId'] == BlockedId]['BlockedSP'].unique().tolist()[0]
                    if BlockedId != 0:
                        vectors.append((StoryId, StorySP, BlockedId, BlockedSP))
                    
            clusters[PlannedFor] = stories
    chart_label = '[' + Team + '] Feature ' + str(FeatureId) + ': ' + Summary

    print(template.render(chart_label = chart_label, clusters = clusters, vectors = vectors))



















