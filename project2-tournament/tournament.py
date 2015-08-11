#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2
import bleach
import sys


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def deleteMatches():
    """Remove all the match records from the database."""
    query = "delete from match;"
    # Execute delete match query and do not fetch results
    executeQuery(query, None, False)


def deletePlayers():
    """Remove all the player records from the database."""
    query = "delete from Player;"
    # Execute delete Player query and do not fetch results
    executeQuery(query, None, False)


def countPlayers():
    """Returns the number of players currently registered."""
    query = "select count(*) from Player limit 1;"
    # Execute select query and fetch results
    results = executeQuery(query, None, True)
    count = results[0][0]
    return count


def registerPlayer(name):
    """Adds a player to the tournament database.

    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)

    Args:
      name: the player's full name (need not be unique).
    """
    # Sanitize  passed in name field
    bleached_name = bleach.clean(name, strip=True)
    query = "insert into player (name) values (%s)"
    # Execute insert query and do not fetch results
    executeQuery(query, (bleached_name,), False)


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place,
    or a player tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
    """
    query = "SELECT * FROM Standings_View;"
    # Execute select query and fetch results.
    results = executeQuery(query, None, True)
    # return player standings.
    return results


def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    # Sanitize  passed in winner and loser field
    winner = bleach.clean(winner, strip=True)
    loser = bleach.clean(loser, strip=True)
    query = "INSERT INTO Match (winner, loser) VALUES (%s, %s)"
    # Execute insert query and do not fetch results
    executeQuery(query, (winner, loser,), False)


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.

    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.

    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    # Get standings using player standings method
    standings = playerStandings()
    # Get count players using count players method
    count = countPlayers()
    # Empty list to populate pairnings list
    pairings = []
    for i in range(0, count, 2):
        # Group ith element with i+1th element
        group = zip(standings[i], standings[i+1])
        # Append to pairning list in this format (id1, name1, id2, name2)
        pairings.append([group[0][0], group[1][0], group[0][1], group[1][1]])
    return pairings


# Execute the passed in query with values.
def executeQuery(query, values, fetchResults):
    """Execute the query"""
    results = []
    try:
        connection = connect()
        cursor = connection.cursor()
        # Execute query with passed in values
        cursor.execute(query, values)
        # Fetch results only when fetchResults is True
        if fetchResults:
            results = cursor.fetchall()
    except:
        print 'unexpected error occured', sys.exc_info()
    finally:
        if connection:
            connection.commit()
            connection.close()
    return results
