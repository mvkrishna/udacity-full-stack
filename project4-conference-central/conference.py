#!/usr/bin/env python


from datetime import datetime

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import StringMessage
from models import BooleanMessage
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import TeeShirtSize

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId

from models import Session, SessionForm, SessionForms, SessionTypes
from models import Speaker, SpeakerForm, SpeakerForms

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
CACHE_FEATURED_SPEAKER_KEY = "FEATURED_SPEAKER"
CACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": ["Default", "Topic"],
}

OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }

FIELDS = {
         'CITY': 'city',
         'TOPIC': 'topics',
         'MONTH': 'month',
         'MAX_ATTENDEES': 'maxAttendees',
         }

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSIONS_BY_SPEAKER = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speakerKey=messages.StringField(1),
)

SESSIONS_BY_TYPE = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
    type=messages.StringField(2),
)

SESSION_WISH_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSessionKey=messages.StringField(1),
)

CONFERENCE_CITY_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    city=messages.StringField(1),
)

CONFERENCE_ATTENDEES_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    attendees=messages.IntegerField(1),
)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference', version='v1', audiences=[ANDROID_AUDIENCE],
               allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID,
               ANDROID_CLIENT_ID, IOS_CLIENT_ID],
               scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    def _createConferenceObject(self, request):
        """Create Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing
        # (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects;
        # set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10],
                                                  "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10],
                                                "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        ndb_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = ndb_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email')
        return request

    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        w_key = request.websafeConferenceKey
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % w_key)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            w_key = request.websafeConferenceKey
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % w_key)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf,
                   getattr(prof, 'displayName'))
                   for conf in confs]
        )

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"],
                                                   filtr["operator"],
                                                   filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name)
                     for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Invalid field \
                                                     or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been
                # used in previous filters
                # disallow the filter if inequality was
                # performed on a different field before
                # track the field on which the inequality
                # operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter \
                                                         is allowed on only \
                                                         one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences',
                      http_method='POST',
                      name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
                items=[self._copyConferenceToForm(conf,
                                                  names[conf.organizerUserId])
                       for conf in conferences]
        )

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name,
                            getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """Return user Profile from datastore, \
        creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email(),
                teeShirtSize=str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
                      path='profile',
                      http_method='GET',
                      name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile',
                      http_method='POST',
                      name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(CACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(CACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return StringMessage(data=memcache.get(CACHE_ANNOUNCEMENTS_KEY)or "")

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser()

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser()
        conf_keys = [ndb.Key(urlsafe=wsck)
                     for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId)
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(conf,
                                      names[conf.organizerUserId])
                                      for conf in conferences])

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='filterPlayground',
                      http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Playground"""
        q = Conference.query()
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
        q = q.filter(Conference.month == 6)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

    # To fix ProtocolBufferDecodeError
    # https://code.google.com/p/appengine-ndb-experiment/issues/detail?id=143
    def _getNdbKey(self, *args, **kwargs):
        try:
            key = ndb.Key(**kwargs)
        except Exception as e:
            if e.__class__.__name__ == 'ProtocolBufferDecodeError':
                key = 'Invalid Key'
        return key

    # Verify the passed in key is valid.
    def _verifyKey(self, key, websafeKey, kind):
        '''Check that key exists and is the right Kind'''
        if key == 'Invalid Key' or not key or key.kind() != kind:
            raise endpoints.NotFoundException(
                'Invalid key: %s' % websafeKey)

    # Copy session to form
    def _copySessionToForm(self, session, name=None):
        """Copy fields from Session to SessionForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(session, field.name):
                # convert typeOfSession to enum SessionTypes; just copy others
                if field.name == 'typeOfSession':
                    setattr(sf, field.name, getattr(SessionTypes,
                            str(getattr(session, field.name))))
                else:
                    setattr(sf, field.name, getattr(session, field.name))
            elif field.name == "websafeKey":
                setattr(sf, field.name, session.key.urlsafe())
            elif field.name == "speakerDisplayName":
                setattr(sf, field.name, name)

            # convert startDateTime from session
            # model to date and startTime for session Form
            startDateTime = getattr(session, 'startDateTime')
            if startDateTime:
                if field.name == 'date':
                    setattr(sf, field.name, str(startDateTime.date()))
                str_dt = startDateTime.time().strftime('%H:%M')
                f_nam = field.name
                if hasattr(session, 'startDateTime') and f_nam == 'startTime':
                    setattr(sf, field.name, str(str_dt))
        sf.check_initialized()
        return sf

    def _createSessionObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("'name' field is required")

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeConferenceKey']
        del data['websafeKey']

        # populate DEFAULT values
        session_defaults = {
            'highlights': 'TBD',
            'duration': 60,
        }
        for df in session_defaults:
            if data[df] in (None, []):
                data[df] = session_defaults[df]
                setattr(request, df, session_defaults[df])

        if data['typeOfSession'] is None:
            del data['typeOfSession']
        else:
            data['typeOfSession'] = str(data['typeOfSession'])

        # set start time and date to be next available if not specified
        # convert dates from strings to Date objects;
        if data['startTime'] and data['date']:
            data['startDateTime'] = datetime.strptime(data['date'][:10] +
                                                      ' ' +
                                                      data['startTime'][:5],
                                                      "%Y-%m-%d %H:%M")
        del data['startTime']
        del data['date']

        # get the conference for where the session will be added
        conf = self._getNdbKey(urlsafe=request.websafeConferenceKey).get()

        # check that conf.key is a Conference key and it exists
        self._verifyKey(conf.key, request.websafeConferenceKey, 'Conference')

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # generate Session key as child of Conference
        s_id = Session.allocate_ids(size=1, parent=conf.key)[0]
        s_key = ndb.Key(Session, s_id, parent=conf.key)
        data['key'] = s_key

        # get the speakerDisplayName from
        # Speaker entity if a speakerKey was provided
        if data['speakerKey']:
            speaker = self._getNdbKey(urlsafe=request.speakerKey).get()

            # check that speaker.key is a speaker key and it exists
            self._verifyKey(speaker.key, request.speakerKey, 'Speaker')

            data['speakerDisplayName'] = speaker.displayName

            taskqueue.add(
                params={
                    'sessionKey': s_key.urlsafe(),
                    'speakerKey': data['speakerKey'],
                    'speakerDisplayName': data['speakerDisplayName']
                    },
                url='/tasks/check_featuredSpeaker'
                )

        # create Session
        s = Session(**data)
        s.put()

        return self._copySessionToForm(s)

    # createSession(SessionForm, websafeConferenceKey)
    # open only to the organizer of the conference
    @endpoints.method(SESSION_POST_REQUEST, SessionForm,
                      path='conference/{websafeConferenceKey}/sessions',
                      http_method='POST', name='createSession')
    def createSession(self, request):
        """Create a new session"""
        return self._createSessionObject(request)

    # getConferenceSessions(websafeConferenceKey)
    # Given a conference, return all sessions
    @endpoints.method(CONF_GET_REQUEST, SessionForms,
                      path='conference/{websafeConferenceKey}/sessions',
                      http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Get list of all sessions for a conference."""

        ndb_key = self._getNdbKey(urlsafe=request.websafeConferenceKey)

        self._verifyKey(ndb_key, request.websafeConferenceKey, 'Conference')

        sessions = Session.query(ancestor=ndb_key)
        return SessionForms(items=[self._copySessionToForm(session)
                            for session in sessions])

    # getConferenceSessionsByType(websafeConferenceKey, typeOfSession)
    # Given a conference, return all sessions of a specified
    # type (eg lecture, keynote, workshop)
    @endpoints.method(SESSIONS_BY_TYPE, SessionForms,
                      path='conference/{websafeConferenceKey}/sessions/{type}',
                      http_method='GET', name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Get list of all sessions for a conference by type."""

        ndb_key = self._getNdbKey(urlsafe=request.websafeConferenceKey)

        self._verifyKey(ndb_key, request.websafeConferenceKey, 'Conference')

        r_type = request.type
        t_session = Session.typeOfSession
        s_types = SessionTypes
        sessions = Session.query(ancestor=ndb_key)\
                          .filter(t_session == str(getattr(s_types, r_type)))

        return SessionForms(items=[self._copySessionToForm(session)
                            for session in sessions])

    # getSessionsBySpeaker(speaker) --
    # Given a speaker, return all sessions given by this particular speaker,
    # across all conferences
    @endpoints.method(SESSIONS_BY_SPEAKER, SessionForms,
                      path='sessions/bySpeaker',
                      http_method='GET', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Get list of all sessions for a speaker accross all conferences.
           If no speakerKey is provided, all sessions are returned"""

        sessions = Session.query()
        sp_key = request.speakerKey
        if request.speakerKey:
            sessions = sessions.filter(Session.speakerKey == sp_key)
        return SessionForms(items=[self._copySessionToForm(session)
                            for session in sessions])

    def _copySpeakerToForm(self, speaker):
        """Copy relevant fields from Speaker to SpeakerForm."""
        sf = SpeakerForm()
        for field in sf.all_fields():
            if hasattr(speaker, field.name):
                setattr(sf, field.name, getattr(speaker, field.name))
            elif field.name == "websafeKey":
                setattr(sf, field.name, speaker.key.urlsafe())
        sf.check_initialized()
        return sf

    def _createSpeakerObject(self, request):
        user = endpoints.get_current_user()
        # Raise an exception if the user is not logged in
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # Raise an exception if the displayName is not provided
        if not request.displayName:
            raise endpoints.BadRequestException("dislayName field required")

        # Copy SpeakerForm into a dictionary
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeKey']

        # generate Speaker key
        sp_id = Speaker.allocate_ids(size=1)[0]
        sp_key = ndb.Key(Speaker, sp_id)
        data['key'] = sp_key

        # Create Speaker and save
        sp = Speaker(**data)
        sp.put()

        return self._copySpeakerToForm(sp)

    @endpoints.method(SpeakerForm, SpeakerForm,
                      path='speaker',
                      http_method='POST', name='addSpeaker')
    def addSpeaker(self, request):
        """Add a new Speaker"""
        return self._createSpeakerObject(request)

    # addSessionToWishlist(SessionKey) --
    # adds the session to the user's list of sessions
    # they are interested in attending
    @ndb.transactional(xg=True)
    def _sessionAddIt(self, request):
        """Add a session to the user Profile session wish list."""
        prof = self._getProfileFromUser()

        # get session key from the request
        web_session_key = request.websafeSessionKey
        s_key = ndb.Key(urlsafe=web_session_key)

        # check that session is a Session key and it exists
        self._verifyKey(s_key, web_session_key, 'Session')

        # check if user already added session otherwise add
        if web_session_key in prof.sessionKeysWishList:
            raise ConflictException(
                "This session is already in your wishlist")

        # add the session to the users session wish list
        prof.sessionKeysWishList.append(web_session_key)

        # Save the profile
        prof.put()
        return BooleanMessage(data=True)

    @endpoints.method(SESSION_WISH_REQUEST, BooleanMessage,
                      path='sessions/wishList/{websafeSessionKey}',
                      http_method='POST', name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Register user for selected conference."""
        return self._sessionAddIt(request)

    # getSessionsInWishlist() --
    # query for all the sessions in a conference that the user is interested in
    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='sessions/wishList',
                      http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Get list of sesions that user wishes to attend."""
        prof = self._getProfileFromUser()
        # Fetch all the session keys from profile
        session_keys = [ndb.Key(urlsafe=web_session_key)
                        for web_session_key in prof.sessionKeysWishList]
        # Fetch all the sessions based on passed in session keys
        sessions = ndb.get_multi(session_keys)

        # Fetch all the speaker keys from sessions
        speakerKeys = [ndb.Key(urlsafe=session.speakerKey)
                       for session in sessions]
        # Fetch all the speakers based on passed in speaker keys
        speakers = ndb.get_multi(speakerKeys)

        # put display names in a dict for easier fetching
        names = {}
        for speaker in speakers:
            names[speaker.key.id()] = speaker.displayName

        # return set of SessionForm objects per Session
        return SessionForms(items=[self._copySessionToForm(session,
                            names[speaker.key.id()]) for session in sessions])

    # 5. Work on indexes and queries
    #    Come up with 2 additional queries
    @endpoints.method(CONFERENCE_CITY_REQUEST, ConferenceForms,
                      path='conferences/{city}',
                      http_method='GET', name='getConferencesInCity')
    def getConferencesInCity(self, request):
        """Get list of conferences in city"""
        # Query to fetch conferences based on passed in city
        q = Conference.query(ndb.OR(
                Conference.city == request.city))
        items = [self._copyConferenceToForm(conf,
                 getattr(conf.key.parent().get(), 'displayName'))
                 for conf in q]

        return ConferenceForms(items=items)

    @endpoints.method(CONFERENCE_ATTENDEES_REQUEST, ConferenceForms,
                      path='conferences/attendees/greaterthan/{attendees}',
                      http_method='GET', name='getConferencesAttendeesGreater')
    def getConferencesAttendeesGreater(self, request):
        """Get list of conferences in city"""
        # Query to fetch conferences which are > passed in max attendees
        q = Conference.query(ndb.OR(
                Conference.maxAttendees >= request.attendees))
        items = [self._copyConferenceToForm(conf,
                 getattr(conf.key.parent().get(), 'displayName'))
                 for conf in q]

        return ConferenceForms(items=items)

    @endpoints.method(message_types.VoidMessage, SpeakerForms,
                      path='speakers',
                      http_method='GET', name='getSpeakers')
    def getSpeakers(self, request):
        """Get list of all speakers"""
        speakers = Speaker.query()
        return SpeakerForms(items=[self._copySpeakerToForm(speaker)
                            for speaker in speakers])

# 5. Work on indexes and queries
#    Solve the following query related problem: Lets say that you don't like
#    workshops and you don't like sessions after 7 pm. How would you handle a
#    query for all non-workshop sessions before 7 pm? What is the problem for
#    implementing this query? What ways to solve it did you think of?

    @endpoints.method(CONF_GET_REQUEST, SessionForms,
                      path='conference/{websafeConferenceKey}/NotWorkshopSessionsBefore7pm',  # noqa
                      http_method='GET', name='getNotWorkshopSessionsBefore7pm')  # noqa
    def getNotWorkshopSessionsBefore7pm(self, request):
        """Returns all conference non-workshop sessions before 7pm."""

        ndb_key = self._getNdbKey(urlsafe=request.websafeConferenceKey)

        self._verifyKey(ndb_key, request.websafeConferenceKey, 'Conference')
        # Do not fetch the sessions which are workshops and To be decided
        sessions = Session.query(ndb.AND(
                Session.typeOfSession != 'WORKSHOP',
                Session.typeOfSession != 'TBD'), ancestor=ndb_key)

        items = []
        for session in sessions:
            # Add the session to items only
            # if the start hour + minutes is before 7pm
            start_dt = session.startDateTime
            if start_dt and \
               start_dt + \
               start_dt/60.0 <= 19:
                items += [self._copySessionToForm(session)]
        return SessionForms(items=items)

# 6. Add a Task
#    * Define the following endpoints method: getFeaturedSpeaker()
    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='featuredSpeaker',
                      http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Get featured speakers from memcache"""
        # Get the featured speaker from memcache.
        # memcache is updated by the task
        speaker = memcache.get(CACHE_FEATURED_SPEAKER_KEY)
        return StringMessage(
               data=getattr(speaker, 'displayName') or "")

    # Method to set featured speaker in cache
    @staticmethod
    def _cacheFeaturedSpeaker(speakerKey, sessionKey):
        """cache speaker"""
        # get all sessions with speaker key
        sessions = Session.query().filter(Session.speakerKey == speakerKey)
        # get speaker
        speaker = ndb.Key(urlsafe=speakerKey).get()
        # if number of sessions greaterthan 1 cache the speaker
        if sessions.count() > 1:
            memcache.set(CACHE_FEATURED_SPEAKER_KEY, speaker)
        return speaker


api = endpoints.api_server([ConferenceApi])     # register API
