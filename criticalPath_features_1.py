import jinja2
import os
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.file import File 
import io

import pandas as pd

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

new_features = rank.merge(cust, how='left', left_on='Id', right_on='Id')

vectors = new_features[(new_features['Type'] == 'Feature')]
vectors = vectors.drop(['Type', 'Rank', 'Parent', 'Summary', 'SP', 'ESP', 'Status', 'PlannedFor', 'Team'], axis=1)
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

vectors = vectors.merge(rank, how='left', left_on='BlockerId', right_on='Id')
vectors.rename(columns={'Rank' : 'BlockerRank'}, inplace=True)
vectors.drop(columns=['Id'], inplace=True)

vectors = vectors.merge(rank, how='left', left_on='BlockedId', right_on='Id')
vectors.rename(columns={'Rank' : 'BlockedRank'}, inplace=True)
vectors.drop(columns=['Id'], inplace=True)
vectors['BlockerId'] = vectors['BlockerId'].astype(str)
vectors['BlockedId'] = vectors['BlockedId'].astype(str)
vectors['BlockerRank'] = vectors['BlockerRank'].astype(str)
vectors['BlockedRank'] = vectors['BlockedRank'].astype(str)
vectors.loc[vectors['BlockedRank'].str.contains('nan'), 'BlockedRank'] = 'NR'
vectors['Blocker'] = '[' + vectors['BlockerRank'] + '] ' + vectors['BlockerId']
vectors['Blocked'] = '[' + vectors['BlockedRank'] + '] ' + vectors['BlockedId']
vectors.drop(columns=['BlockerId','BlockerRank','BlockedId','BlockedRank',], inplace=True)

new_features.drop(columns=['Parent','Type','Summary','Status','Team','SP','ESP','Blocks'], inplace=True)
                                  
## 2) Loop through the Pandas data.  Print each Feature's data to the template:
##    Team, FeatureId, Summary: goes to chart label
##      Sprint: goes to the cluster label
##          [(StoryId, SP)]: list of stories/SP goes to cluster
##      [(StoryId, SP, BlockedId, SP)] list of vectors goes to the chart
##

PlannedFors = new_features['PlannedFor'].unique().tolist()
PlannedFors.sort(reverse=True)

cluster_dict = {} # For each PlannedFor, build a dictionary of clusters {PlannedFor: [(FeatureId, Rank)]}
for PlannedFor in PlannedFors:
    feature_list = []
    plannedfor_data = new_features.loc[new_features['PlannedFor'] == PlannedFor]
    Features = plannedfor_data['Id'].unique().tolist()
    for Feature in Features:
        Rank = plannedfor_data[plannedfor_data['Id'] == Feature]['Rank'].unique().tolist()[0]
        Ranked_Feature = '[' + str(Rank).zfill(2) + '] ' + str(Feature)
        feature_list.append(Ranked_Feature)
    cluster_dict[PlannedFor] = feature_list

vector_list = []
print(vector_list)
for vector in vectors.itertuples():
    vector_list.append((vector.BkrId, vector.BkrSP, vector.BkdId, vector.BkdSP))
print(vector_list)
exit()
chart_label = 'MUOS PI 15 Features'
print(template.render(chart_label = chart_label, clusters = cluster_dict, vectors = vector_list))
