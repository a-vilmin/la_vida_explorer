SELECT pitcher_war.WAR as pitcher_war, 
       pitcher_war.team_ID as team,
       pitcher_war.year_ID as year_id,
       Master.nameFirst, Master.nameLast, Master.birthCountry
FROM Master	     
    INNER JOIN pitcher_war
    	  ON Master.playerID=pitcher_war.player_ID
WHERE Master.birthCountry = "P.R." or Master.birthCountry = "D.R." or
      Master.birthCountry = "Cuba" or Master.birthCountry = "Venezuela" or
      Master.birthCountry = "Mexico" or Master.birthCountry = "Panama" or
      Master.birthCountry = "Colombia" or Master.birthCountry = "Nicaragua" or
      Master.birthCountry = "Curacao" or Master.birthCountry = "Brazil"; 
