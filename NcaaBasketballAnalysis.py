'''
Created on Apr 19, 2015

@author: mrhodes
'''

import pandas
import numpy as np
import matplotlib.pyplot as plt
from pandas.io import sql
import MySQLdb
from numpy import histogram

# MySQL Variables
the_host = "127.0.0.1"
the_db = "mikes_db"
the_user = "root"
the_pw = "Test123"
db = MySQLdb.connect(the_host, the_user, the_pw, the_db, use_unicode = True, charset = "utf8")
the_cursor = db.cursor()

def calculate_lead_changes():
    
    # Query the database
    the_data = sql.read_sql_query("SELECT game_id, current_score_home, current_score_away FROM mikes_db.ncaa_pxp_detail_2015 where bool_non_play_event not in ('1');", db)
    
    # Get a uique list of the games
    unique_game_list = the_data.loc[:, 'game_id'].unique()
    
    all_lead_chg_summaries = []
    
    for game in unique_game_list:
        the_game_id = str(game)
        
        # Subset the data
        the_data_subset = the_data[the_data.game_id == str(the_game_id)]
        
        # If positive, the home team is ahead
        the_data_subset['current_score_diff'] = the_data_subset['current_score_home'].astype(int) - the_data_subset['current_score_away'].astype(int)
        # If positive, the home team is ahead
        the_data_subset['current_score_sign'] = np.sign(the_data_subset['current_score_diff'])
        # Get the sign of the previus play
        the_data_subset['prev_score_sign'] = np.sign(the_data_subset['current_score_diff'].shift())
        # There will be an NaN at the beginning, give it a value of 0
        the_data_subset['prev_score_sign'] = the_data_subset['prev_score_sign'].fillna(0)
        # if the sign of the current play and the last play are the same, then there was no lead change, otherwise there was
        the_data_subset['lead_change_bool'] = np.where(the_data_subset['prev_score_sign'] == the_data_subset['current_score_sign'], 0, 1)
        
        nLeadChanges = the_data_subset['lead_change_bool'].sum()
        
        print [the_game_id, nLeadChanges]
        
        all_lead_chg_summaries.append([the_game_id, nLeadChanges])
    
    all_lead_chg_summaries = pandas.DataFrame(all_lead_chg_summaries) 
    all_lead_chg_summaries.to_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/Sample_score_Diff.csv')
        
        
    return the_data_subset

lead_change_df = pandas.read_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/All_Lead_Changes.csv')
lead_change_df_summary = lead_change_df.groupby(lead_change_df['school_name']).mean()

lead_change_df_summary = lead_change_df_summary[lead_change_df_summary.in_tourney == True].sort_index(by = 'n_score_changes', ascending=False)

print lead_change_df_summary

# plt.figure();
lead_change_df_summary['n_score_changes'].plot(kind = 'bar')
plt.show()

