--------------------------------------------
Tournament application
--------------------------------------------

What is it?
----------------------
A database and an application that will store player and game data. When given an input of player match-ups and win/loss information for a round of games, the application will properly process this data and provide the following round of match-ups and current standings of each player.

Features
----------------------
  * Delete matches
  * Delete players
  * Count players
  * Register players
  * Get player standings
  * Report a match
  * Swiss pairing https://en.wikipedia.org/wiki/Swiss-system_tournament

Prerequisites
----------------------
  * Install Vagrant http://vagrantup.com/
  * Install VirtualBox https://www.virtualbox.org/
  * Clone http://github.com/udacity/fullstack-nanodegree-vm

Installation & running
----------------------
  * Launch the Vagrant VM
  * Copy and unzip tournament.zip in /vagrant directory
  * cd /vagrant/tournament
  * Create tournament database using following commands
    - `vagrant ssh`
    - `psql`
    - `\i tournament.sql`
    - exit database by pressing ctrl + D
  * Test the application using following command  
    - `python tournament_test.py`

Results after successful running of the application
----------------------
  1. Old matches can be deleted.
  2. Player records can be deleted.
  3. After deleting, countPlayers() returns zero.
  4. After registering a player, countPlayers() returns 1.
  5. Players can be registered and deleted.
  6. Newly registered players appear in the standings with no matches.
  7. After a match, players have updated standings.
  8. After one match, players with one win are paired.
  Success!  All tests pass!
