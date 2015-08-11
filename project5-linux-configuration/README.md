# Project 5: Linux Server Configuration

A baseline installation of a Linux distribution on a virtual machine and prepare it to host your web applications, to include installing updates, securing it from a number of attack vectors and installing/configuring web and database servers.

### 1 Launch your Virtual Machine with your Udacity account
1. Download the private key from https%3A//www.udacity.com/465ff463-7ef1-4197-b7bd-475c4bc6e2fe
2. Move the private key file into the folder ~/.ssh (where ~ is your environment's home directory). So if you downloaded the file to the Downloads folder,
   just execute the following command in your terminal.
   `mv ~/Downloads/udacity_key.rsa ~/.ssh/`
3. Open your terminal and type in
   `chmod 600 ~/.ssh/udacity_key.rsa`

### 2 Follow the instructions provided to SSH into your server
4. In your terminal, type in
   `ssh -i ~/.ssh/udacity_key.rsa root@52.27.212.246`

### 3 Create a new user named grader
1. In your terminal, type in
   `adduser grader`

### 4 Give the grader the permission to sudo
1. Edit sudo configuration
  `visudo`
2. Add the following line below `root    ALL=(ALL:ALL) ALL`
  `grader ALL=(ALL:ALL) ALL`

### 5 Update all currently installed packages
1. `sudo apt-get update`
2. `sudo apt-get upgrade`

### 6 Change the SSH port from 22 to 2200
1. Open the config file:  
   `vim /etc/ssh/sshd_config`
2. Change Port from 22 to 2200
3. Change PermitRootLogin from without-password to no
4. Change PasswordAuthentication from no to yes
5. Append UseDNS no
6. Append AllowUsers grader
7. Restart SSH Service:  
   `/etc/init.d/ssh restart`
8. Generate a SSH key pair on the local machine:  
   `$ ssh-keygen`
9. Copy the public id from local machine
   `pbcopy <  ~/.ssh/id_rsa.pub`
10. From root user change it to grader
  `su - grader`
11. Make the directory for authorized keys  
  `mkdir .ssh`
12. Change permissions of the folder
  `chmod 700 .ssh`
13. Paste the keys in the below file
  `vi .ssh/authorized_keys`
14. Change PasswordAuthentication from yes to no


### 7 Configure the Uncomplicated Firewall (UFW) to only allow incoming connections for SSH (port 2200), HTTP (port 80), and NTP (port 123)
1. Turn UFW on with the default set of rules:  
  `$ sudo ufw enable`
2. Allow incoming TCP packets on port 2200 (SSH)
  `$ sudo ufw allow 2200/tcp`
3. Allow incoming TCP packets on port 80 (HTTP)  
  `$ sudo ufw allow 80/tcp`
4. Allow incoming UDP packets on port 123 (NTP)  
  `$ sudo ufw allow 123/udp`  

### 8 Configure the local timezone to UTC
1. Type the below command and select the required time zone.
   `sudo dpkg-reconfigure tzdata`
2. It is already set to UTC.

### 9 Install and configure Apache to serve a Python mod_wsgi application
1. Install Apache
  `sudo apt-get install apache2`
2. Install mod_wsgi
   `sudo apt-get install python-setuptools libapache2-mod-wsgi`
3. Restart Apache
   `sudo service apache2 restart`
***************************

### 10 Install and configure PostgreSQL
1. Install PostgreSQL:  
  `sudo apt-get install postgresql postgresql-contrib`
2. Check that no remote connections are allowed (default):  
  `sudo vim /etc/postgresql/9.3/main/pg_hba.conf`
3. Edit database setup file  
  `sudo vim database_setup.py`
4. Update the postgres connection in database_setup.py and application.py
   create_engine('postgresql://catalog:<PWD>@localhost/catalog')
6. Rename catalog/application.py
  `mv application.py __init__.py`
7. Create needed linux user for psql
  `sudo adduser catalog`
8. Change to default user postgres
  `sudo su - postgre`
9. Connect
   `$ psql`
10. Add postgres user and allw user to create database
    `# CREATE USER catalog WITH PASSWORD 'PWD';`
    `# ALTER USER catalog CREATEDB;`
11. Create database  
  `# CREATE DATABASE catalog WITH OWNER catalog;`
12. Connect to the database catalog
  `# \c catalog`
13. Revoke all rights:  
  `# REVOKE ALL ON SCHEMA public FROM public;`
14. Grant only access to the catalog role:  
  `# GRANT ALL ON SCHEMA public TO catalog;`
15. Exit out of PostgreSQl and the postgres user:  
16. Create postgreSQL database schema:  
  $ python database_setup.py

### 11 Install git, clone and setup your Catalog App project (from your GitHub repository from earlier in the Nanodegree program) so that it functions correctly when visiting your server’s IP address in a browser. Remember to set this up appropriately so that your .git directory is not publicly accessible via a browser!

1. Install git  
  `sudo apt-get install git`
2. Enable Apache to serve flask applications
   `sudo apt-get install libapache2-mod-wsgi python-dev`
3. Enable mod_wsgi
  `sudo a2enmod wsgi`
4. Copy the folder from local machine.
   `cd /var/www`
   `sudo mkdir catalog`
   `scp -P 2200  catalog.zip grader@52.27.212.246:/var/www/catalog`
   `mv application.py __init__.py`
5. Install other packages required to run this app
   `ssudo apt-get -qqy update`
   `sudo apt-get -qqy install postgresql python-psycopg2`
   `sudo apt-get -qqy install python-flask python-sqlalchemy`
   `sudo apt-get -qqy install python-pip`
   `sudo pip install coverage Flask-Login flask-marshmallow Flask-SQLAlchemy Flask-WTF rauth marshmallow-sqlalchemy bleach oauth2client requests httplib2`
6. creating catalog db
   `createdb -U catalog --locale=en_US.utf-8 -E utf-8 -O catalog app -T template0`
7. sudo vi /etc/apache2/sites-available/catalog.conf
    <VirtualHost *:80>
     ServerName ec2-52-27-212-246.us-west-2.compute.amazonaws.com
     ServerAdmin grader@ec2-52-27-212-246.us-west-2.compute.amazonaws.com
     WSGIScriptAlias / /var/www/catalog/catalog.wsgi
     <Directory /var/www/catalog/catalog/>
         Order allow,deny
         Allow from all
     </Directory>
     Alias /static /var/www/catalog/catalog/static
     <Directory /var/www/catalog/catalog/static/>
         Order allow,deny
         Allow from all
     </Directory>
     ErrorLog /home/grader/catalog/logs/error.log
     LogLevel warn
     CustomLog /home/grader/catalog/logs/access.log combined
    </VirtualHost>
8. Create .wsgi file
   `sudo vi /etc/apache2/sites-available/catalog.conf`
   !/usr/bin/python
   import sys
   import logging
   logging.basicConfig(stream=sys.stderr)
   sys.path.insert(0,"/var/www/catalog")
   from app import app as application
   application.secret_key = <secret_key>

9. Restart apache server
   sudo service apache2 restart

10. Should be able to acesss the app here http://ec2-52-27-212-246.us-west-2.compute.amazonaws.com/

Resources
http://stackoverflow.com/
https://www.digitalocean.com/
https://wikipedia.org
http://askubuntu.com
http://blog.udacity.com/
https://help.ubuntu.com/
