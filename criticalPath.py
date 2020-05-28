## criticalpath.py - Rick Cottle, for GD-MS MUOS, May 2020.
## Expects Python3.  Usage: python criticalPath.py

## General library imports
import os
import sys
from subprocess import check_call
import io

## The critical path is determined for each Feature by using the criticalpath module
## Get from PyPI:  pip install criticalpath
from criticalpath import Node

## All of the spreadsheet parsing and data maniuplation is done with pandas
## Get from PyPI:  pip install pandas
import pandas as pd

## The template engine used to generate the .dot files is jinja2
## get from PyPI:  pip install Jinja2
import jinja2

# The next line is optional--useful for debugging pandas
pd.set_option('display.max_rows', None)

# Set up an environment for a jinja2 template, then load the template itself.
loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader = loader, trim_blocks = True, lstrip_blocks = True)
template = jenv.get_template('criticalpath.j2')

## Use Pandas to create data frames that relate all the features, stories and blocked stories.
##    The source for this data is a 'Feature_Rank_List.xlsm' and 'CriticalPath.csv' spreadsheet.
##    Feature_Rank_List is a copy of the current PI spreadsheet and CriticalPath comes from an RTC
##    shared query (download, open (in Excel), and save as .xlsx).

features = pd.read_excel('PI_15_Feature_Rank_List.xlsm',sheet_name='Feature_List',usecols='A,B,L,AP')
features['Id'] = features['Id'].fillna(0).astype(int)
features = features.loc[(features['Rank'].notnull()) & (features['Rank'] != 'Unranked') & (features['Id'] != 0)]
features['Rank'] = features['Rank'].astype(int)
features.rename(columns={'Id' : 'FeatureId'}, inplace=True)

rtc_data = pd.read_excel('CriticalPath.xlsx')
rtc_data.rename(columns={'Story Points (numeric)' : 'SP', 'Planned For' : 'PlannedFor'}, inplace=True)
rtc_data['Parent'] = rtc_data['Parent'].str.replace('#','')
rtc_data['Blocks'] = rtc_data['Blocks'].str.replace('#','')
rtc_data['SP'] = rtc_data['SP'].fillna(0)
rtc_data['SP'] = rtc_data['SP'].astype(int)
rtc_data['Parent'] = rtc_data['Parent'].fillna(0)
rtc_data['Parent'] = rtc_data['Parent'].astype(int)

stories = rtc_data.loc[(rtc_data.Type == 'Story') & (rtc_data['Parent'] > 0)].copy()
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
vectors = vectors.merge(rtc_data, how='left', left_on='BkdId', right_on='Id')
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
            story_cp_list = []
            story_cp_list_objects = proj_dict[FeatureId].get_critical_path()
            if story_cp_list_objects is not None:
                for object in story_cp_list_objects:
                    story_cp_list.append(int(str(object)))
            for StoryId in StoryIds:
                story_data = stories.loc[stories['Id'] == StoryId]
                StorySP = story_data['SP'].iloc[0]
                StoryCP = False
                if StoryId in story_cp_list:
                    StoryCP = True
                story_list.append((StoryId, StorySP, StoryCP))
            cluster_dict[PlannedFor] = story_list

        vector_list = []
        cp_tuples_list = []
        if len(story_cp_list) > 1:
            for cp_story in story_cp_list[1:]:
                cp_tuples_list.append((story_cp_list[story_cp_list.index(cp_story)-1],cp_story))
                
        vector_data = vectors.loc[vectors['FeatureId'] == FeatureId]
        for vector in vector_data.itertuples():
            vector_check_tuple = (vector.BkrId, vector.BkdId)
            VectorCP = False
            if vector_check_tuple in cp_tuples_list:
                VectorCP = True
            vector_list.append((vector.BkrId, vector.BkrSP, vector.BkdId, vector.BkdSP, VectorCP))
        feature_cp_duration = str(proj_dict[FeatureId].duration)
        chart_label = 'Team: ' + Team + ', Feature: ' + str(FeatureId) + ', Rank=' + str(Rank) + ', CP Duration='\
                      + feature_cp_duration + '\\n' + Summary.replace('"',"'")

        dot_data = template.render(chart_label = chart_label, clusters = cluster_dict, vectors = vector_list)
        dot_file = Team + '-' + str(FeatureId) + '.dot'
        png_file = Team + '-' + str(FeatureId) + '.png'

        with open(dot_file, mode='w') as file_object:
            print(dot_data, file=file_object)
        command = 'dot -Tpng ' + dot_file + ' -o ' + png_file
        print(command)
        os.system(command)
##            check_call(['dot','-Tpng',dot_file,'-o',png_file])
##        os.remove(dot_file)


