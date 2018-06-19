SELECT pitcher_war.WAR as pitcher_war, 
       pitcher_war.team_ID as pitcher_team,
       pitcher_war.year_ID as pitcher_year,
       Master.nameFirst, Master.nameLast
FROM Master	     
    INNER JOIN pitcher_war
    	  ON Master.playerID=pitcher_war.player_ID
WHERE Master.birthCountry = "P.R.";
