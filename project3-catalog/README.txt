--------------------------------------------
Catalog application
--------------------------------------------

What is it?
----------------------
web application that provides a list of items within a variety of categories and integrate third party user registration and authentication. Authenticated users should have the ability to post, edit, and delete their own items.

Features
----------------------
  * Add New Items
  * Update and existing Item
  * Delete an Item
  * Login using google credentials
  * Access items related to categories
  * Recently added items list
  * List all categories
  * Upload an image.

Prerequisites
----------------------
  * Install Vagrant http://vagrantup.com/
  * Install VirtualBox https://www.virtualbox.org/
  * Clone http://github.com/udacity/fullstack-nanodegree-vm
  * Python
  * sqlalchemy
  * flask
  * oauth2client

Installation & running
----------------------
  * Launch the Vagrant VM
  * Copy and unzip catalog.zip in /vagrant directory
  * cd /vagrant/catalog
  * Create catalog database using following commands
    - `vagrant ssh`
    - `python database_setup.py`
  * Test the application using following command
    - `python application.py`

End points to access after successfully running the app
----------------------
  * http://localhost:5000/
  * http://localhost:5000/catalog/Soccer/items
  * http://localhost:5000/catalog/Soccer/Jersey
  * http://localhost:5000/catalog/Soccer/Jersey/edit/1
  * http://localhost:5000/catalog.xml
  * http://localhost:5000/catalog.json
