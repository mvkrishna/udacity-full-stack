-- Table definitions for the tournament project.

-- Drop database tournament if exists.
DROP DATABASE IF EXISTS tournament;

-- Create database tournament
CREATE DATABASE tournament;

-- Connect to the tournament database
\c tournament


-- Drop view standings if exists
DROP VIEW IF EXISTS Standings_View CASCADE;

-- Drop view Winnings if exists
DROP VIEW IF EXISTS Winning_View CASCADE;

-- Drop view losses if exists
DROP VIEW IF EXISTS Matches_View CASCADE;

-- Drop Match table if exists.
DROP TABLE IF EXISTS Match CASCADE;

-- Drop Player table if exists.
DROP TABLE IF EXISTS Player CASCADE;

-- Create table Player
CREATE TABLE Player(
  ID serial NOT NULL,
  Name text,
  PRIMARY KEY (ID)
);

-- Create table Match
CREATE TABLE Match(
  ID serial NOT NULL,
  loser INTEGER,
  winner INTEGER,
  PRIMARY KEY (ID),
  FOREIGN KEY (loser) REFERENCES Player(ID),
  FOREIGN KEY (winner) REFERENCES Player(ID)
);

-- Create the "Winning_View"
CREATE VIEW Winning_View AS
    SELECT p.id , count(m.winner) AS won
    FROM player as p LEFT JOIN match as m
    ON p.id = m.winner
    GROUP BY p.id, m.winner
    ORDER BY p.id;

-- Create the "Matches_View"
CREATE VIEW Matches_View AS
    SELECT p.id, count(m) AS played
    FROM player as p LEFT JOIN match as m
    ON(p.id = m.winner)
    OR(p.id = m.loser)
    GROUP BY p.id
    ORDER BY p.id ASC;

--- Create the "Standings_View"
CREATE VIEW Standings_View AS
SELECT p.id, p.name, wv.won, mv.played
	FROM player as p
	LEFT JOIN Winning_view as wv ON p.id = wv.id
	LEFT JOIN Matches_View as mv ON p.id = mv.id
	GROUP BY p.id, p.name, wv.won, mv.played
	ORDER BY wv.won DESC;
