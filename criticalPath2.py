import jinja2
import os
import pandas as pd

ead_list = ['EA 14.1', 'EA 14.2', 'EA 14.3', 'EA 14.4' , 'EA 14.5']

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)
template = jenv.get_template('cp3.j2')

cust = pd.read_excel('CustomerReport.xlsx',sheet_name='CustomerReport',usecols='A,B,C,D,F,H,O,AD')
cust['Parent'] = cust['Parent'].str.replace('#','')
cust.rename(columns={'Filed Against' : 'Team', 'Story Points (numeric)' : 'SP', 'Planned For' : 'Sprint'}, inplace=True)
cust['SP'] = cust['SP'].fillna(0)
cust['SP'] = cust['SP'].astype(int)
cust['Team'] = cust['Team'].str.replace('MUOS/','')
cust['Parent'] = cust['Parent'].fillna(0)
cust['Parent'] = cust['Parent'].astype(int)


stories = cust[(cust.Type == 'Story')]
stories = stories[(stories.Sprint.isin(ead_list))]
stories = stories[['Id','Parent','Sprint','SP']]
stories.rename(columns={'Parent' : 'FeatureId'}, inplace=True)
stories.sort_values(by = ['Sprint', 'Id'], inplace = True)

feature_list = stories[['FeatureId']].drop_duplicates()
feature_list = feature_list[(feature_list.FeatureId > 0)]
feature_list.sort_values(by = ['FeatureId'], inplace = True)

features = cust[(cust.Type == 'Feature')].merge(feature_list, left_on = 'Id', right_on = 'FeatureId')
features = features[['Id','Summary','Team']]
features['Id'] = features['Id'].fillna(0)
features.sort_values(by = ['Team', 'Id'], inplace = True)


blockers = cust.drop(['Parent','Type','Summary','Sprint','Team','SP'], axis=1)
blockers = \
(blockers.set_index(blockers.columns.drop('Blocks',1).tolist())
   .Blocks.str.split('\n', expand=True)
   .stack()
   .reset_index()
   .rename(columns={0:'Blocks'})
   .loc[:, blockers.columns]
)

blockers.sort_values(by = ['Id', 'Blocks'], inplace = True)
blockers['Blocks'] = blockers['Blocks'].astype(int)
blockers.rename(columns={'Id':'BlockerId','Blocks':'BlockedId'}, inplace=True)
blockers = blockers.merge(stories, how='left', left_on='BlockerId', right_on='Id')
blockers['FeatureId'] = blockers['FeatureId'].fillna(0)
blockers['FeatureId'] = blockers['FeatureId'].astype(int)
blockers.rename(columns={'Sprint' : 'BlockerSprint', 'SP' : 'BlockerSP', 'FeatureId' : 'BlockerFeatureId'}, inplace=True)
blockers.drop(columns=['Id'], inplace=True)
blockers = blockers.merge(stories, how='left', left_on='BlockedId', right_on='Id')
blockers.rename(columns={'Sprint' : 'BlockedSprint', 'SP' : 'BlockedSP', 'FeatureId' : 'BlockedFeatureId'}, inplace=True)
blockers.drop(columns=['Id'], inplace=True)
blockers = blockers[['BlockerId', 'BlockerFeatureId', 'BlockerSprint', 'BlockerSP', 'BlockedId', 'BlockedFeatureId', 'BlockedSprint', 'BlockedSP']]
blockers['BlockedFeatureId'] = blockers['BlockedFeatureId'].astype('Int64')

## 1) Build Desired Data Structure from Pandas data:
##    {Team: {Feature: ({Sprint: [(Stories)]}, [(Vectors)])}}
##        Stories: (storyId, SP)
##        Vectors: (blockerId, SP, blockedId, SP) 
##
## 2) For each team, for each feature, pass team/feature plus data to template
##    chart_label = "Team" + ":" + "Feature"
##    chart_data ({Sprint: [(Stories)]}, [(Vectors)])}}

##vectors = blockers.copy()
##vectors.rename(columns={'BlockerFeatureId' : 'vectorFeatureId'}, inplace=True)
##vectors.drop(columns=['BlockerSprint', 'BlockedFeatureId', 'BlockedSprint'], inplace=True)
##vectors = vectors[['vectorFeatureId', 'BlockerId', 'BlockerSP', 'BlockedId', 'BlockedSP']].dropna()
##print(vectors)
##
##
##alldata = feature_list.merge(features, how='left', left_on='FeatureId', right_on='Id').dropna()
##print(alldata)
##
##alldata = alldata.merge(vectors, left_on='FeatureId', right_on='vectorFeatureId')
##print(alldata)
##


##new_cust = stories.merge(blockers, how='left')
##new_cust.rename(columns={'Blocks' : 'End', 'Id' : 'Start'}, inplace=True)
##new_cust['FeatureId'] = new_cust['FeatureId'].fillna(0)
##new_cust['FeatureId'] = new_cust['FeatureId'].astype(int)
##
##vector_list = features.merge(new_cust, how='outer', left_on='Id', right_on='FeatureId')
##vector_list = vector_list[(vector_list.Sprint.isin(['EA 14.1', 'EA 14.2', 'EA 14.3', 'EA 14.4' , 'EA 14.5', 'PI 14']))]
##vector_list = vector_list.dropna(subset=['End'])
##
##vector_list = vector_list[['Team', 'FeatureId', 'Summary', 'Start', 'End', 'Sprint', 'SP']]
##vector_list.sort_values(by = ['Team', 'FeatureId', 'Start', 'End'], inplace = True)
##
##vector_list['FeatureId'] = vector_list['FeatureId'].astype(int).astype(str)
##vector_list['Feature_Team'] = '"' + vector_list['Team'] + ' : ' + vector_list['FeatureId'] + '"'
##
##vector_list['Start'] = vector_list['Start'].astype(int).astype(str)
##vector_list['End'] = vector_list['End'].astype(int).astype(str)
##vector_list['SP'] = ' (' +vector_list['SP'].astype(int).astype(str) + ')'
##vector_list['Vector'] = '"' + vector_list['Start'] + '" -> "' + vector_list['End'] + '"'
##vector_list.drop(columns=['Team', 'FeatureId', 'Summary', 'Start', 'End', 'SP', 'Sprint'], inplace=True)
##
##

##feature_record = {}
##vectors = []
##feature_list = []
##
##for index, row in vector_list.iterrows():
##    feature_team = row['Feature_Team']
##    vector = row['Vector']
##    
##    if feature_team not in feature_dict:
##        vectors = [vector]
##    else:
##        vectors = feature_dict[feature_team]
##        vectors.append(vector)
##
##    feature_dict[feature_team] = vectors
##
##for feature_team in feature_dict:
##    feature_list.append({feature_team:feature_dict[feature_team]})
##    
##print(template.render(feature_name = feature_name, feature_records = feature_records, vectors = vectors)


##feature_ids = sorted(features, key = lambda x: int(x))
##for fid in feature_ids:
##    feature_data.append({fid, features[fid]))
##
##print(features)



      







