'''
Created on Apr 4, 2015

@author: mrhodes
'''

from bs4 import BeautifulSoup
import requests
import pandas
# from pandas.tools.merge import concat
from pandas.io import sql
# import numpy as np
from unidecode import unidecode
import time
import random
import re
import MySQLdb
import sqlalchemy


# MySQL Variables
the_host = "127.0.0.1"
the_db = "mikes_db"
the_user = "root"
the_pw = "Test123"
db = MySQLdb.connect(the_host, the_user, the_pw, the_db, use_unicode = True, charset = "utf8")
the_cursor = db.cursor()

# Add distinctive User-Agent header to let the server know who you are
headers = {
    'User-Agent': 'MikesBballAnalysisScript/Contact me: mrhodes262@gmail.com',
    'Accept-Encoding': 'gzip, deflate',
}

# Base URLs
espn_ncaa_bball_team_url = 'http://espn.go.com/mens-college-basketball/teams'
team_schedule_base_url = 'http://espn.go.com/mens-college-basketball/team/schedule/_/id/'
base_roster_url = 'http://espn.go.com/mens-college-basketball/team/roster/_/id/'
box_score_base_url = 'http://espn.go.com/ncb/boxscore?gameId='
play_by_play_base_url = 'http://espn.go.com/ncb/playbyplay?gameId='


def get_team_list():
    # Create an empty list that will contain school names and URLs to their ESPN profiles
    team_link_list = []
    
    # Request the HTML doc from ESPN's website
    bball_team_request = requests.get(espn_ncaa_bball_team_url, headers = headers)
    # Retrieve the contents and create beautiful soup object
    bball_team_request_content = BeautifulSoup(bball_team_request.content)
     
    # The school names are contained in unordered list tags named "medium-logos". Find each ul tag with that class name.
    blah = bball_team_request_content.findAll('ul', {'class': 'medium-logos'})
     
    # Each one of those ul tags represents a conference
    for unorderedlist in blah:
        # Within those conferences, find li tags, which will contain the names and links for each school in the conference
        conference = unorderedlist.findAll('li')
         
        # For each li that represents the school, get the schools name and ESPN profile link
        for school in conference:
            school_name = school.a.contents[0]
            school_name = unidecode(school_name)
            school_link = school.a.get('href')
            school_link = unidecode(school_link)
            school_id = school_link.split('/')
             
            # Create a list containing the school's info
            school_link = [school_name, school_link, school_id[7]]
            # Add that school's list to the master list
            team_link_list.append(school_link)
            
#     team_link_list_df = pandas.DataFrame(team_link_list, columns = ['school_name', 'espn_profile_link', 'espn_school_id'])
#     sql.to_sql(team_link_list_df, con=db, name='ncaa_team_lists_2015', if_exists='append', flavor='mysql')
    return team_link_list

def get_team_schedule_results(team_link_list):
    team_link_list = team_link_list
    all_schools_parsed_season_results = []

    pandas_df_column_headers = ['game_date', 'game_id', 'school_id', 'opponent_school_id', 'opponent_school_link', 'home_away_neutral', 'game_outcome', 
                            'team_score', 'opponent_score', 'overtime', 'team_overall_cuml_wins', 'team_overall_cuml_losses', 
                            'team_conf_cuml_wins', 'team_conf_cuml_losses']
    
    # For each school in "team_link_list"
    for school in team_link_list:
        
        # Empty list to put rows with HTML
        team_season_results = []
    
        team_schedule_url = team_schedule_base_url + str(school[2])
        the_team_schedule_request = requests.get(team_schedule_url, headers = headers)
        the_team_schedule = BeautifulSoup(the_team_schedule_request.content)
        bb = the_team_schedule.findAll('table', {'class': 'tablehead'})
    
        for table in bb:
            rows = table.findAll('tr', {'class': re.compile("team-41")})
            
            # The first two rows are the team name and column headers respectively. We dont want to parse those.
            for idx, row in enumerate(rows):
    
                team_season_results.append(row.findAll('td'))
            
            # Each element in the list now represents a game. Each game is a list with game info.
            for game in team_season_results:
                
                # If the game has been played and hasnt been postponed, continue
                if (str(game[2].find('li', {'class': 'score'})) != None and
                    game[2].find('li', {'class': re.compile('game-status')}) != None):
                    
                    game_date = game[0].contents[0]
                    try:
                        opponent_school_link  = game[1].a.get('href')
                        opponent_school_link = unidecode(opponent_school_link)
                        opponent_school_id = opponent_school_link.split('/')[7]
                    except AttributeError:
                        opponent_school_link  = None
                        opponent_school_id = None
                    
                    
                    # This yields a list of html elements about the team. We are interested in if there is a * (star), which indicates if the game was played at a
                    # neutral location. It will be the last element in the school list (if it exists).
                    opponent_name = game[1].find('li', {'class': 'team-name'}).contents
                    # if the list is > 1, it has some extra info about the school/game location (e.g. ranking, neutral location)
                    if len(opponent_name) > 1:
                        # Neutral location will always be at the end if it exists. Check for it and if it was at a neutral location, make "neutral_location" variable = True
                        if opponent_name[len(opponent_name)- 1] == '*':
                            neutral_location = True
                        else:
                            neutral_location = False
                    else:
                        neutral_location = False
                    
                    # If neutral_location == True, then give "home_away_neutral" vble a value of neutral
                    if neutral_location:
                        home_away_neutral = 'neutral'
                    # otherwise, look for the vs or @ symbol from the table and assign accordingly
                    else:
                        if game[1].find('li', {'class': 'game-status'}).contents[0] == 'vs':
                            home_away_neutral = 'home'
                        else:
                            home_away_neutral = 'away'
                    
                    
                    # Was it a Win or a Loss?
                    game_outcome = game[2].find('li', {'class': re.compile('game-status')}).span.contents[0]
                    # Game score will have score AND Overtime info (if relevant). We split on ' '. If the resulting list > 0, then there was an overtime.
                    game_outcome_detail = game[2].find('li', {'class': 'score'}).a.contents[0].split(' ')
                
                    # Was there overtime played?
                    if len(game_outcome_detail) > 1:
                        overtime = True
                    else:
                        overtime = False
                    
                    game_score = game_outcome_detail[0]
                    game_score_split = game_score.split("-")
                    
                    # ESPN always list the winning number of points first, the loosing second. If the team we are lookign at won, give them the first number of points.
                    if game_outcome == "W":
                        team_score = game_score_split[0]
                        opponent_score = game_score_split[1]
                    else:
                        team_score = game_score_split[1]
                        opponent_score = game_score_split[0]
                        
                    # Get the gameid so that we can use it to get play-by-play information about the game.
                    game_id = game[2].find('li', {'class': 'score'}).a.get('href').split("=")[1]
                    
                    if game[3].contents[0] != '--':
                        team_record = game[3].contents[0].replace('(', '')
                        team_record = team_record.replace(')', '').split(' ')
                        team_overall_cuml_wins = team_record[0].split('-')[0]
                        team_overall_cuml_losses = team_record[0].split('-')[1]
                        team_conf_cuml_wins = team_record[1].split('-')[0]
                        team_conf_cuml_losses = team_record[1].split('-')[1]
                    else:
                        team_record = None
                        team_record = None
                        team_overall_cuml_wins = None
                        team_overall_cuml_losses = None
                        team_conf_cuml_wins = None
                        team_conf_cuml_losses = None
        
                    game_results = [game_date, game_id, school[2], opponent_school_id, opponent_school_link, home_away_neutral, game_outcome, team_score, opponent_score, 
                                           overtime, team_overall_cuml_wins, team_overall_cuml_losses, team_conf_cuml_wins, team_conf_cuml_losses]
                    all_schools_parsed_season_results.append(game_results)
            print str(school[2])
                    
        team_parsed_season_results_pandas = pandas.DataFrame(all_schools_parsed_season_results, columns = pandas_df_column_headers)
#         team_parsed_season_results_pandas.to_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/AllSchools_Season_Results2.csv')
        sql.to_sql(team_parsed_season_results_pandas, con=db, name='ncaa_team_results_2015', if_exists='append', flavor='mysql')
        time.sleep(3)
    return all_schools_parsed_season_results

def get_team_rosters(team_list):
    player_info_headers = ['school_id', 'player_id', 'player_number', 'player_name', 'player_link', 'player_position', 'player_height_feet', 'player_height_inches',
                   'player_weight_lbs', 'player_year', 'player_hometown']
    player_list = []
    for team in team_list:
        team_roster_url = base_roster_url + str(team[2])
        team_roster_request = requests.get(team_roster_url, headers = headers)
        team_roster_request_content = BeautifulSoup(team_roster_request.content)
        player_table =  team_roster_request_content.find('table', {'class': 'tablehead'})
        players = player_table.findAll('tr', {'class': re.compile('row')})
        for player in players:
            school_id = team[2]
            player_info = player.findAll('td')
            player_number =  player_info[0].contents[0]
            player_name = player_info[1].a.contents[0]
            player_name = unidecode(player_name)
            player_link= player_info[1].a.get('href')
            player_link= unidecode(player_link)
            player_id = player_link.split('/')[7]
            player_position = player_info[2].contents[0]
            player_height = player_info[3].contents[0].split('-')
            player_height_feet = player_height[0]
            player_height_inches = player_height[1]
            player_weight_lbs = player_info[4].contents[0]
            player_year = player_info[5].contents[0]
            player_hometown = player_info[6].contents[0]
            player_hometown = unidecode(player_hometown)
            
            print school_id, player_id, player_number, player_name, player_link, player_position, player_height_feet, player_height_inches, player_weight_lbs, player_year, player_hometown
            print '\n'
            
            player_info = [school_id, player_id, player_number, player_name, player_link, player_position, player_height_feet, player_height_inches,
                           player_weight_lbs, player_year, player_hometown]
            player_list.append(player_info)

        player_info_df = pandas.DataFrame(player_list, columns = player_info_headers)
        player_info_df.to_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/AllSchools_Player_Info_alt.csv')
        # Sleep for x seconds before pulling the page for the next school
        time.sleep(2)

def get_game_play_by_play(sleep_time_min = 2, sleep_time_max = 5):
    
    random.seed()
    
#     all_games_df = pandas.read_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/AllSchools_Season_Results.csv')
    all_games_df = pandas.read_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/NCAA Overtime Games.csv')
    
    pxp_column_names = ['game_id', 'play_id', 'half', 'game_time_minutes', 'game_time_seconds', 'cuml_time_seconds', 
                        'away_team_play', 'current_score_away', 'current_score_home', 'home_team_play', 'bool_non_play_event',
                        'away_action_player', 'away_action', 'away_assist_player', 'away_foul_player', 'away_turnover_player', 
                        'away_def_rebound_player', 'away_off_rebound_player', 'away_block_player', 'away_stl_player',
                        'home_action_player', 'home_action', 'home_assist_player', 'home_foul_player', 'home_turnover_player', 
                        'home_def_rebound_player', 'home_off_rebound_player', 'home_block_player', 'home_stl_player']
    
    
    
    # Get a unique list of all the games played in the current season.
    unique_game_list = all_games_df.loc[:,'game_id'].unique()
    
    #################################################
    # For each game in the unique list, pull the play by play info
    #################################################
    for idx, game_id in enumerate(unique_game_list):
        
        sleep_time = random.randint(sleep_time_min, sleep_time_max)
    
        # Append game ID to the base pxp URL and send request to server
        game_play_by_play_url = play_by_play_base_url + str(game_id)
        game_play_by_play_request = requests.get(game_play_by_play_url, headers = headers)
        game_play_by_play_content = BeautifulSoup(game_play_by_play_request.content)
        
        # List to store all the game information in
        game_plays = []
        # Set hald = 1 (first half) - will be changed to 2 for the second half
        half = 1
        # Set play_id = 0. First play will be indexed as 1
        play_id = 0
        
        #################################################
        # Determine if play-by-play exists - will throw IndexError if it doesn't
        #################################################
        try:
            # Navigate the HTML tree to the part that would contain the pxp info
            pbp_table = game_play_by_play_content.findAll('div', {'class': 'gp-body'})[0].findAll('table', {'class': 'mod-data mod-pbp'})[0]
            
            # Number of periods (regular is two - add 1 for each OT)
            num_periods = len(pbp_table.findAll('thead'))
            
            # Each play/event (e.g. timeout, etc) is contained in a "tr" (table row). Find all of them named "odd" or "even"
            for play in pbp_table.findAll('tr', {'class': re.compile('odd|even')}):
                
                # Increment the play_id by 1
                play_id += 1
                
                #################################################
                # If the tr is an event, it wont have a value for each column. So, catch the IndexError when it occurs
                #################################################
                try:
                    # Split the game clock to break up minutes and seconds
                    game_time =  play.findAll('td')[0].contents[0].split(':')
                    game_time_minutes = int(game_time[0])
                    game_time_seconds = int(game_time[1])
                    # Calculate the cumulative time on the fly
                    # If it is regular time, deal with it normally
                    if half <= 2:
                        # There are 1200 seconds in a half. Get the current amout of time played (in seconds) and subtract from 1200 seconds
                        cuml_time_seconds = 1200 - ((game_time_minutes * 60) + game_time_seconds)
                        # If it is the second half, add 1200 seconds to the calc above since that time was already played
                        if half == 2:
                            cuml_time_seconds = cuml_time_seconds + 1200
                    else:
                        # OT periods are 5 min (or 300 secs) a piece. Do a similar calc as above
                        cuml_time_seconds = 300 - ((game_time_minutes * 60) + game_time_seconds)
                        # For each OT period above the first OT, add 300 seconds to the time already played.
                        cuml_time_seconds = cuml_time_seconds + (2400 + (300 * (half - 3)))
                    
                    # Some plays are in bold characters, if so get the contents from the bold tags
                    try:
                        # This what to do if the play is in bold tags
                        away_team_play = play.findAll('td')[1].contents[0].contents[0]
                    except:
                        # Non bold tags
                        away_team_play = play.findAll('td')[1].contents[0]
                    # Fix non utf-8 chars
                    away_team_play = unidecode(away_team_play)
                    
                    # If there is a special event, it will be in the second td
                    if away_team_play == 'End of 1st half':
                        # Change to second half when you reach end of first half
                        half = 2
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds,
                                            away_team_play, None, None, away_team_play, True,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play]
                        
                    elif away_team_play == 'Official TV Timeout':
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds,
                                            away_team_play, None, None, away_team_play, True,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play]
                        
                    elif away_team_play.endswith('Timeout'):
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds, 
                                            away_team_play, None, None, away_team_play, True,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play]
                        
                    # If it says 'End of Second Half', then it is going into OT. Increment the "half" (an OT isn't a half but oh well) by one
                    elif away_team_play == 'End of 2nd half':
                        half = 3
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds,
                                            away_team_play, None, None, away_team_play, True,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play]
                        
                    # For each additional OT period played, increment the half by one
                    elif away_team_play.endswith('overtime'):
                        half += 1
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds,
                                            away_team_play, None, None, away_team_play, True,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play]
                                    
                    elif away_team_play == 'End of Game':
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds,
                                            away_team_play, None, None, away_team_play, True,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play,
                                            away_team_play, away_team_play, away_team_play, away_team_play, away_team_play, 
                                            away_team_play, away_team_play, away_team_play, away_team_play]
                        
                    else:
                        # Split the score to get the current score of each team after the play
                        current_score = play.findAll('td')[2].contents[0].split('-')
                        current_score_away = current_score[0]
                        current_score_home = current_score[1]
                        
                        # Some plays are in bold characters, if so get the contents from the bold tags
                        try:
                            home_team_play = play.findAll('td')[3].contents[0].contents[0]
                        except:
                            home_team_play = play.findAll('td')[3].contents[0]
                            
                        home_team_play = unidecode(home_team_play)
                        
                        #######################################################
                        # Home Team action breakdown
                        #######################################################
                        # If there was an assist, identify the assisting player
                        if 'Assisted' in home_team_play:
                            home_assist_player = home_team_play.split('. ')[1]
                            home_assist_player = home_assist_player.replace('Assisted by ', '')
                            home_assist_player = home_assist_player.replace('.', '')
        #                         print home_team_play, ' | ', assist_player
                        else:
                            home_assist_player = None
                        
                        if 'made' in home_team_play and home_assist_player == None:
                            home_action_player = home_team_play.split(' made ')[0]
                            home_action = home_team_play.split(' made ')[1].replace('.', '')
                        elif 'made' in home_team_play and home_assist_player != None:
                            home_action_player = str(home_team_play.split('. ')[0]).split(' made ')[0]
                            home_action = str(home_team_play.split('. ')[0]).split(' made ')[1].replace('.', '')
                        else:
                            home_action_player = None
                            home_action = None
                        
                        if 'Foul' in home_team_play:
                            home_foul_player = home_team_play.replace('Foul on ', '')
                            home_foul_player = home_foul_player.replace('.', '')
                        else:
                            home_foul_player = None
                            
                        if 'Turnover' in home_team_play:
                            home_turnover_player = home_team_play.replace(' Turnover.', '') 
                        else:
                            home_turnover_player = None
                            
                        if 'Defensive Rebound.' in home_team_play:
                            home_def_rebound_player = home_team_play.replace(' Defensive Rebound.', '') 
                        else:
                            home_def_rebound_player = None
                            
                        if 'Offensive Rebound.' in home_team_play:
                            home_off_rebound_player = home_team_play.replace(' Offensive Rebound.', '') 
                        else:
                            home_off_rebound_player = None
                        
                        if 'Block.' in home_team_play:
                            home_block_player = home_team_play.replace(' Block.', '') 
                        else:
                            home_block_player = None
                        
                        if 'Steal.' in home_team_play:
                            home_stl_player = home_team_play.replace(' Steal.', '') 
                        else:
                            home_stl_player = None
        
                        #######################################################
                        # AWAY Team action breakdown
                        #######################################################
                        # If there was an assist, identify the assisting player
                        if 'Assisted' in away_team_play:
                            away_assist_player = away_team_play.split('. ')[1]
                            away_assist_player = away_assist_player.replace('Assisted by ', '')
                            away_assist_player = away_assist_player.replace('.', '')
        #                         print away_team_play, ' | ', assist_player
                        else:
                            away_assist_player = None
                        
                        if 'made' in away_team_play and away_assist_player == None:
                            away_action_player = away_team_play.split(' made ')[0]
                            away_action = away_team_play.split(' made ')[1].replace('.', '')
                        elif 'made' in away_team_play and away_assist_player != None:
                            away_action_player = str(away_team_play.split('. ')[0]).split(' made ')[0]
                            away_action = str(away_team_play.split('. ')[0]).split(' made ')[1].replace('.', '')
                        else:
                            away_action_player = None
                            away_action = None
                        
                        if 'Foul' in away_team_play:
                            away_foul_player = away_team_play.replace('Foul on ', '')
                            away_foul_player = away_foul_player.replace('.', '')
                        else:
                            away_foul_player = None
                            
                        if 'Turnover' in away_team_play:
                            away_turnover_player = away_team_play.replace(' Turnover.', '') 
                        else:
                            away_turnover_player = None
                            
                        if 'Defensive Rebound.' in away_team_play:
                            away_def_rebound_player = away_team_play.replace(' Defensive Rebound.', '') 
                        else:
                            away_def_rebound_player = None
                            
                        if 'Offensive Rebound.' in away_team_play:
                            away_off_rebound_player = away_team_play.replace(' Offensive Rebound.', '') 
                        else:
                            away_off_rebound_player = None
                        
                        if 'Block.' in away_team_play:
                            away_block_player = away_team_play.replace(' Block.', '') 
                        else:
                            away_block_player = None
                        
                        if 'Steal.' in away_team_play:
                            away_stl_player = away_team_play.replace(' Steal.', '') 
                        else:
                            away_stl_player = None
                        
                        # Compile all results into a list
                        play_detail_list = [str(game_id), str(play_id), half, game_time_minutes, game_time_seconds, cuml_time_seconds, 
                                            away_team_play, current_score_away, current_score_home, home_team_play, False,
                                            away_action_player, away_action, away_assist_player, away_foul_player, away_turnover_player, 
                                            away_def_rebound_player, away_off_rebound_player, away_block_player, away_stl_player,
                                            home_action_player, home_action, home_assist_player, home_foul_player, home_turnover_player, 
                                            home_def_rebound_player, home_off_rebound_player, home_block_player, home_stl_player]
                        
                    # Add "play_detail_list" to the list of all plays
                    game_plays.append(play_detail_list)
                        
                #/////////////// END SPECIAL EVENT TRY BLOCK
                except IndexError:
                    pass
                
                
            
            # all_game_plays.append(game_plays)
            # print pandas.DataFrame(all_game_plays)
            # pbp_df = pandas.DataFrame(all_game_plays)
            # pbp_df.to_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/Test_PBP.csv')
            # print pbp_df.head(5)
        
        #/////////////// END PXP TRY BLOCK 
        except IndexError:
            pass
#             print "No play-by-play available"

        if len(game_plays) > 0:
            game_plays = pandas.DataFrame(game_plays, columns = pxp_column_names)
            sql.to_sql(game_plays, con=db, name='ncaa_pxp_detail_2015', if_exists='append', flavor='mysql')
#             print game_plays.head(5)
#             game_plays.to_csv('/home/mrhodes/Documents/Code/Eclipse_Workspaces/NCAABasketballAnalysis/Test_PBP.csv')

        
        print game_id, '|', sleep_time
        time.sleep(sleep_time)


def get_game_boxscore():
    pass

# # Set a list of all the D1 teams ESPN tracks.
# team_list = get_team_list()
# # Based on the above list, pull the rosters of each team.
# get_team_rosters(team_list)

# get_game_play_by_play()
    
    
team_link_list = get_team_list()
get_team_schedule_results(team_link_list)

    
    
    
    
    
    