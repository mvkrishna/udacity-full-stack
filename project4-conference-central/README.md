App Engine application for the Udacity training course.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## Setup Instructions
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][4].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting your local server's address (by default [localhost:8080][5].)
1. (Optional) Generate your client library(ies) with [the endpoints tool][6].
1. Deploy your application.


[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://console.developers.google.com/
[5]: https://localhost:8080/
[6]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool

## About Sessions
  1. Created Session as a separate entity which will be a sub entity of a Conference.
  2. Each Conference can have multiple sessions.
  3. A session can have a session type from a list of enum session types.
  4. New enum need to be added in case of adding a new session types
  5. Conference and Sessions are connected using conference key.

## About Speakers
  1. Created Speaker as a separate entity which will be a sub entity of a Session.
  2. Each Session can hava a Speaker
  3. Sessions and speakers are connected using speaker key
  4. It would have been better to have multiple speakers instead of one speaker.

## About additional queries
  1. List all the conferences in a passed in city
      * http://localhost:8080/_ah/api/conference/v1/conferences/London
  2. List all the conferences where attendees are greater than passed in value
      * http://localhost:8080/_ah/api/conference/v1/conferences/attendees/greaterthan/100

## About problematic query
  1. Multiple inequality filters are not supported.
    * https://cloud.google.com/appengine/docs/python/ndb/queries
  2. Fixed this by not passing the time constraint. Iterating the results to ignore sessions before 19 i.e 7pm
    * https://apis-explorer.appspot.com/apis-explorer/?base=http://localhost:8080/_ah/api#p/conference/v1/conference.getNotWorkshopSessionsBefore7pm

## Featured speaker
  1. Added a task to add the speaker to cache  if a speaker has more than one conference.

## API explorer
  1. https://apis-explorer.appspot.com/apis-explorer/?base=http://localhost:8080/_ah/api#p/conference/v1/

## Deployed application
  1. https://conference-central-1011.appspot.com/
