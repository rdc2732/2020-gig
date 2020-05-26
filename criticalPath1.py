import jinja2
import os
import pandas as pd

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)
template = jenv.get_template('cp2.j2')

cust = pd.read_excel('CustomerReport.xlsx',sheet_name='CustomerReport',usecols='A,B,C,D,F,H,O,AD')
cust['Parent'] = cust['Parent'].str.replace('#','')
cust.rename(columns={'Filed Against' : 'Team', 'Story Points (numeric)' : 'SP', 'Planned For' : 'Sprint'}, inplace=True)
cust['SP'] = cust['SP'].fillna(0)
cust['SP'] = cust['SP'].astype(int)
cust['Team'] = cust['Team'].str.replace('MUOS/','')

stories = cust[(cust.Type == 'Story')]
stories = stories[['Id','Parent','Sprint','SP']]
stories.rename(columns={'Parent' : 'FeatureId'}, inplace=True)
stories.sort_values(by = ['Sprint', 'Id'], inplace = True)

features = cust[(cust.Type == 'Feature')]
features = features[['Id','Summary','Team']]
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

new_cust = stories.merge(blockers, how='left')
new_cust.rename(columns={'Blocks' : 'End', 'Id' : 'Start'}, inplace=True)
new_cust['FeatureId'] = new_cust['FeatureId'].fillna(0)
new_cust['FeatureId'] = new_cust['FeatureId'].astype(int)

vector_list = features.merge(new_cust, how='outer', left_on='Id', right_on='FeatureId')
vector_list = vector_list[(vector_list.Sprint.isin(['EA 14.1', 'EA 14.2', 'EA 14.3', 'EA 14.4' , 'EA 14.5', 'PI 14']))]
vector_list = vector_list.dropna(subset=['End'])
vector_list = vector_list[['Team', 'FeatureId', 'Summary', 'Start', 'End', 'Sprint', 'SP']]
vector_list.sort_values(by = ['Team', 'FeatureId', 'Start', 'End'], inplace = True)

vector_list['FeatureId'] = vector_list['FeatureId'].astype(int).astype(str)
##vector_list['Feature'] = vector_list['FeatureId'] + ' [' + vector_list['Team'] + '] ' + vector_list['Summary']
vector_list['Feature_Team'] = '"' + vector_list['Team'] + ' : ' + vector_list['FeatureId'] + '"'

vector_list['Start'] = vector_list['Start'].astype(int).astype(str)
vector_list['End'] = vector_list['End'].astype(int).astype(str)
vector_list['SP'] = ' (' +vector_list['SP'].astype(int).astype(str) + ')'
vector_list['Sprint'] = ' [' +vector_list['Sprint'] + ']'
vector_list['Start'] = vector_list['Start'] + vector_list['Sprint'] + vector_list['SP']
vector_list['End'] = vector_list['End'] + vector_list['Sprint'] + vector_list['SP']
vector_list['Vector'] = '"' + vector_list['Start'] + '" -> "' + vector_list['End'] + '"'
vector_list.drop(columns=['Team', 'FeatureId', 'Summary', 'Start', 'End', 'SP', 'Sprint'], inplace=True)


feature_dict = {}
feature_list = []

for index, row in vector_list.iterrows():
    feature_team = row['Feature_Team']
    vector = row['Vector']
    
    if feature_team not in feature_dict:
        vectors = [vector]
    else:
        vectors = feature_dict[feature_team]
        vectors.append(vector)

    feature_dict[feature_team] = vectors

for feature_team in feature_dict:
    feature_list.append({feature_team:feature_dict[feature_team]})
    
print(template.render(feature_teams = feature_list))


##feature_ids = sorted(features, key = lambda x: int(x))
##for fid in feature_ids:
##    feature_data.append({fid, features[fid]))
##
##print(features)



      







