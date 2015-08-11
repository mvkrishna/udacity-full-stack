import io
import os
import random
import string
import httplib2
import json
import requests
import bleach
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request
from flask import send_file, jsonify, flash

from database_setup import Base, Category, CategoryItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from flask import session as login_session

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from flask import make_response

app = Flask(__name__)

# initialize CLIENT_ID with client_secrets.json which is downloaded from google
# developer console: https://console.developers.google.com/
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# get the secret key from google developer console
app.secret_key = 'gH20vhAbDKgb-kWRtLaStRM0'
# Initialize database engine and session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
# Upload folder relative path for images
RELATIVE_PATH = os.path.join(os.path.dirname(__file__), 'static/uploads')
# Upload folder absolute path for images
UPLOAD_FOLDER = os.path.abspath(RELATIVE_PATH)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logged_in = False
        if 'username' in login_session:
            logged_in = True
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        login_session['logged_in'] = logged_in
        return f(*args, **kwargs)
    return decorated_function


# Main home page route
@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    # Fetch all the categories to display
    categories = session.query(Category).all()
    # Fetch latest items list based on latest inserted id's
    latest_items = session.query(CategoryItem).order_by(
        desc(CategoryItem.id)).all()
    # Render home page to using the passed in params
    return render_template('index.html', categories=categories,
                           latest_items=latest_items,
                           STATE=login_session['state'],
                           logged_in=login_session['logged_in'])


# signout route to clear the session
@app.route('/signout')
def signout():
    # Clear session
    login_session.clear()
    # redirect to home
    return redirect(url_for("home"))


# Google connect route to authenticate and authorize
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        # Return failure json when authorization code fails
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    # check the credentials which are stored in login_session
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    # login_session['email'] = data['email']

    output = ''
    flash("you are now logged in as %s" % login_session['username'])
    return output


# Display catalog as json response
@app.route('/catalog.json', methods=['GET', 'POST'])
def items_json():
    categories = session.query(CategoryItem).all()
    return jsonify(CategoryItem=[i.serialize for i in categories])


# Display catalog as xml response
@app.route('/catalog.xml')
def items_xml():
    items = session.query(CategoryItem).all()
    resp = make_response(render_template('catalog.xml', items=items))
    resp.headers['Content-type'] = 'text/xml; charset=utf-8'
    return resp


# Fetch binary and display image based on item id
@app.route("/images/<int:item_id>.jpg")
def getImage(item_id):
    item = session.query(CategoryItem).filter_by(id=item_id).one()
    return send_file(io.BytesIO(item.image),
                     attachment_filename='logo.png',
                     mimetype='image/png')


# Items route to display all categoris and  items for a specific category
@app.route('/catalog/<string:category_name>/items')
@login_required
def items(category_name):
    # Fetch all categories
    categories = session.query(Category).all()
    # Fetch selected category
    selected_category = session.query(
        Category).filter_by(name=category_name).one()
    # Fetch all items for the selected category
    latest_items = session.query(CategoryItem).filter_by(
        category_id=selected_category.id).all()
    return render_template('items.html', categories=categories,
                           latest_items=latest_items,
                           category_name=category_name,
                           STATE=login_session['state'],
                           logged_in=login_session['logged_in'])


# Item route to display item details based on item.
@app.route('/catalog/<string:category_name>/<string:item_name>')
@login_required
def item(category_name, item_name):
    # Fetch all categories
    categories = session.query(Category).all()
    # Fetch all items based on item name
    latest_items = session.query(CategoryItem).filter_by(name=item_name).all()
    return render_template('item.html', categories=categories,
                           latest_items=latest_items,
                           category_name=category_name,
                           STATE=login_session['state'],
                           logged_in=login_session['logged_in'])


# delete item route to delete an item based on item_id
@app.route('/catalog/<string:category_name>/<string:item_name>/delete/<int:item_id>')  # noqa
@login_required
def delete_item(category_name, item_name, item_id):
    # Fetch all categories
    categories = session.query(Category).all()
    # Fetch all items based on item name
    latest_items = session.query(CategoryItem).filter_by(name=item_name).all()
    # Delete an item only when valid item_id is present
    # More validations are required
    if item_id is not 0:
        session.query(CategoryItem).filter_by(id=item_id).delete()
        session.commit()
        flash("Deleted Successfully ")
        return redirect(url_for('items', category_name=category_name,
                                STATE=login_session['state'],
                                logged_in=logged_in))
    else:
        return render_template('delete.html', categories=categories,
                               latest_items=latest_items,
                               category_name=category_name,
                               STATE=login_session['state'],
                               logged_in=login_session['logged_in'])


# edit item route to edit an item based on item_id
@app.route('/catalog/<string:category_name>/<string:item_name>/edit/<int:item_id>', methods=['GET', 'POST'])  # noqa
@login_required
def edit_item(category_name, item_name, item_id):
    # Fetch the categories to edit
    categories = session.query(Category).all()
    # edit page is used for adding a new item also
    # Checking whether it is a new item or existing item
    if item_name == "new":
        if item_id is 0 and request.method == 'POST':
            selected_category = session.query(Category).filter_by(
                name=request.form['category']).one()
            # Create a new Category Item
            bleached_name = bleach.clean(request.form['name'], strip=True)
            bleached_des = bleach.clean(request.form['description'],
                                        strip=True)
            newItem = CategoryItem(name=bleached_name,
                                   description=bleached_des,
                                   category=selected_category)
            # get the image file
            file = request.files['file']
            # save it on the server and in the database
            if file:
                file.save(os.path.join(UPLOAD_FOLDER, file.filename))
                with open(UPLOAD_FOLDER + '/' + file.filename, "rb") as ifile:
                    image_blob = ifile.read()
                newItem.image = image_blob
            session.add(newItem)
            session.commit()
            flash("Added item Successfully ")
            return redirect(url_for('items',
                                    category_name=request.form['category']))
        else:
            latest_items = []
            selected_category = session.query(
                Category).filter_by(name=category_name).one()
            newItem = CategoryItem(
                name="", description="", category=selected_category, id=0)
            latest_items.append(newItem)
            return render_template('new.html', categories=categories,
                                   latest_items=latest_items,
                                   category_name=category_name,
                                   STATE=login_session['state'],
                                   logged_in=login_session['logged_in'])
    # Edit item flow
    elif item_id is not 0:
        if request.method == 'POST':
            selected_Item = session.query(
                CategoryItem).filter_by(id=item_id).one()
            # Get the name of the uploaded file
            file = request.files['file']
            # save it on the server and in the database
            if file:
                file.save(os.path.join(UPLOAD_FOLDER, file.filename))
                with open(UPLOAD_FOLDER + '/' + file.filename, "rb") as ifile:
                    image_blob = ifile.read()
                selected_Item.image = image_blob
            # Update all the other attributers
            selected_Item.name = request.form['name']
            selected_Item.description = request.form['description']
            category_name = request.form['category']
            selected_category = session.query(
                Category).filter_by(name=category_name).one()
            selected_Item.category = selected_category
            session.commit()
            flash("Updated Successfully ")
        return redirect(url_for('items', category_name=category_name))
    else:
        latest_items = session.query(
            CategoryItem).filter_by(name=item_name).all()
        return render_template('edit.html', categories=categories,
                               latest_items=latest_items,
                               category_name=category_name,
                               STATE=login_session['state'],
                               logged_in=login_session['logged_in'])


if __name__ == "__main__":
    # Enable this to debug
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
