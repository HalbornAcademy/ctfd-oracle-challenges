from CTFd.plugins import register_plugin_assets_directory, bypass_csrf_protection
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.challenges import (
    CTFdStandardChallenge,
    BaseChallenge,
    CHALLENGE_CLASSES,
)
from CTFd.models import (
    db,
    Solves,
    Fails,
    Flags,
    Challenges,
    ChallengeFiles,
    Tags,
    Hints,
)
from CTFd import utils
from CTFd.utils.user import get_ip, is_admin, get_current_team, get_current_user
from CTFd.utils.uploads import upload_file, delete_file
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.decorators import during_ctf_time_only, require_verified_emails, authed_only
from flask import Blueprint, abort, request, Response
from urllib.parse import urlparse

from sqlalchemy.sql import and_
import six
import json
import requests

def get_current_account_name():
    team = get_current_team()
    if team is not None:
        return team.name

    user = get_current_user()
    return user.name

class OracleChallenge(BaseChallenge):
    id = "oracle"  # Unique identifier used to register challenges
    name = "oracle"  # Name of a challenge type
    templates = {  # Templates used for each aspect of challenge editing & viewing
        "create": "/plugins/oracle_challenges/assets/create.html",
        "update": "/plugins/oracle_challenges/assets/update.html",
        "view": "/plugins/oracle_challenges/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/oracle_challenges/assets/create.js",
        "update": "/plugins/oracle_challenges/assets/update.js",
        "view": "/plugins/oracle_challenges/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/oracle_challenges/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "oracle_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @staticmethod
    def create(request):
        """
        This method is used to process the challenge creation request.

        :param request:
        :return:
        """
        data = request.form or request.get_json()

        challenge = OracleChallenges(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge

    @staticmethod
    def read(challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "description": challenge.description,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": OracleChallenge.id,
                "name": OracleChallenge.name,
                "templates": OracleChallenge.templates,
                "scripts": OracleChallenge.scripts,
            },
        }
        return data

    @staticmethod
    def update(challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()
        for attr, value in data.items():
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    @staticmethod
    def delete(challenge):
        """
        This method is used to delete the resources used by a challenge.

        :param challenge:
        :return:
        """
        Fails.query.filter_by(challenge_id=challenge.id).delete()
        Solves.query.filter_by(challenge_id=challenge.id).delete()
        Flags.query.filter_by(challenge_id=challenge.id).delete()
        files = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
        for f in files:
            delete_file(f.id)
        ChallengeFiles.query.filter_by(challenge_id=challenge.id).delete()
        Tags.query.filter_by(challenge_id=challenge.id).delete()
        Hints.query.filter_by(challenge_id=challenge.id).delete()
        OracleChallenges.query.filter_by(id=challenge.id).delete()
        Challenges.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @staticmethod
    def attempt(challenge, request):
        global CHALLENGE_TEAM_STATES
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.

        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """
        data = request.form or request.get_json()
        # submission = data["submission"].strip()
        # instance_id = submission
        # submission = data["submission"].strip()
        team_id = get_current_user().account_id
        team_name = get_current_account_name()
        challenge_id = challenge.challenge_id

        if challenge_id in CHALLENGE_TEAM_STATES and team_id in CHALLENGE_TEAM_STATES[challenge_id]:
            try:
                uuid = CHALLENGE_TEAM_STATES[challenge_id][team_id]['uuid']

                r = requests.post(
                    str(challenge_id) + "/{}/solved".format(uuid), json={}
                )
            except requests.exceptions.ConnectionError:
                return False, "Challenge oracle is not available. Talk to an admin."

            if r.status_code != 200:
                return False, "An error occurred when attempting to submit your flag. Talk to an admin."

            resp = r.json()
            return resp['result'], resp.get('message', 'Solved!' if resp['result'] else 'Not solved')

        else:
            return {"error":{"code":-32602,"message":"request new challenge"},"id":-1,"jsonrpc":"2.0"}

    @staticmethod
    def solve(user, team, challenge, request):
        """
        This method is used to insert Solves into the database in order to mark a challenge as solved.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        # submission = data['submission']
        submission = "No flags for this challenge"
        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(solve)
        db.session.commit()

    @staticmethod
    def fail(user, team, challenge, request):
        """
        This method is used to insert Fails into the database in order to mark an answer incorrect.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        # submission = data['submission']
        submission = "No flags for this challenge"
        wrong = Fails(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(wrong)
        db.session.commit()


def get_chal_class(class_id):
    """
    Utility function used to get the corresponding class from a class ID.

    :param class_id: String representing the class ID
    :return: Challenge class
    """
    cls = CHALLENGE_CLASSES.get(class_id)
    if cls is None:
        raise KeyError
    return cls


def get_domain_from_url(url):
    parsed_uri = urlparse(url)
    return '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)


class OracleChallenges(Challenges):
    __mapper_args__ = {"polymorphic_identity": "oracle"}
    id = db.Column(None, db.ForeignKey("challenges.id"), primary_key=True)
    # oracle = db.Column(db.String(255), default="")
    challenge_id = db.Column(db.String(255), default="")

    def __init__(self, *args, **kwargs):
        super(OracleChallenges, self).__init__(**kwargs)
        # self.oracle = kwargs["oracle"]
        self.challenge_id = kwargs['challenge_id']


def format_details(request, challenge_id, data):
    rpc = "{}/challenge/{}/{}".format(
        get_domain_from_url(request.base_url),
        challenge_id,
        data['uuid']
    )

    details = json.dumps(data['details'])
    return '''
<b>Deploy details</b>:
</br>
<pre>
{}
</pre>
</br>
<b>Your private RPC</b>:
</br>
<code>{}</code>
</br>

<b>Mnemonic</b>:
</br>
<code>{}</code>
'''.format(details, rpc, data['mnemonic'])
    # return data

CHALLENGE_TEAM_STATES = {}
# CHALLENGE_ORACLE_CACHE = {}

# def store_oracle_cache(challenge_id, oracle):
#     print('STORING', challenge_id, oracle)
#     global CHALLENGE_ORACLE_CACHE
#     CHALLENGE_ORACLE_CACHE[challenge_id] = oracle

# def invalidate_oracle_cache(challenge_id):
#     global CHALLENGE_ORACLE_CACHE
#     del CHALLENGE_ORACLE_CACHE[challenge_id]

# def get_oracle_cache(challenge_id):
#     global CHALLENGE_ORACLE_CACHE
#     return CHALLENGE_ORACLE_CACHE.get(challenge_id, None)


def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["oracle"] = OracleChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/oracle_challenges/assets/"
    )

    @check_challenge_visibility
    @during_ctf_time_only
    @require_verified_emails
    @app.route("/plugins/oracle_challenges/<challenge_id>", methods=["POST"])
    def request_new_challenge(challenge_id):
        global CHALLENGE_TEAM_STATES
        if is_admin():
            challenge = OracleChallenges.query.filter(
                Challenges.id == challenge_id
            ).first_or_404()
        else:
            challenge = OracleChallenges.query.filter(
                OracleChallenges.id == challenge_id,
                and_(Challenges.state != "hidden", Challenges.state != "locked"),
            ).first_or_404()

        data = request.form or request.get_json()

        team_id = get_current_user().account_id
        team_name = get_current_account_name()
        challenge_id = challenge.challenge_id

        if challenge_id not in CHALLENGE_TEAM_STATES:
            CHALLENGE_TEAM_STATES[challenge_id] = {}
            # store_oracle_cache(challenge_id, challenge.oracle)

        if data.get('force_new', False):
            if team_id in CHALLENGE_TEAM_STATES[challenge_id]:
                uuid = CHALLENGE_TEAM_STATES[challenge_id][team_id]['uuid']
                try:
                    r = requests.post(
                        str(challenge.oracle) + "/{}/kill".format(uuid),
                        json={},
                    )
                except requests.exceptions.ConnectionError:
                    pass

        else:
            if team_id in CHALLENGE_TEAM_STATES[challenge_id]:
                return format_details(request, challenge_id, CHALLENGE_TEAM_STATES[challenge_id][team_id])



        try:
            r = requests.post(
                str(challenge.oracle) + "/new",
                json={
                    "domain": get_domain_from_url(request.base_url),
                    # "team_name": team_name,
                    # "challenge_id": challenge_id,
                },
            )
            CHALLENGE_TEAM_STATES[challenge_id][team_id] = r.json()
        except requests.exceptions.ConnectionError:
            # invalidate_oracle_cache(challenge_id)
            return "ERROR: Challenge oracle is not available. Talk to an admin."

        if r.status_code != 200:
            return "ERROR: Challenge oracle is not available. Talk to an admin."

        if data.get('json', False):
            return r.json()
        else:
            return format_details(request, challenge_id, r.json())
        # return r.json().get('description', request.base_url)

    @bypass_csrf_protection
    @app.route("/challenge/<challenge_id>/<uuid>", methods=["POST"])
    def forward_challenge_request(challenge_id, uuid):
        if is_admin():
            challenge = OracleChallenges.query.filter(
                Challenges.challenge_id == challenge_id
            ).first_or_404()
        else:
            challenge = OracleChallenges.query.filter(
                OracleChallenges.challenge_id == challenge_id,
                and_(Challenges.state != "hidden", Challenges.state != "locked"),
            ).first_or_404()


        data = request.form or request.get_json()

        if uuid == 'new':
            return {"error":{"code":-32602,"message":"invalid uuid specified"},"id":data.get('id', -1),"jsonrpc":"2.0"}

        try:
            resp = requests.post(
                str(challenge_id) + "/{}".format(uuid),
                json=data
            )
        except requests.exceptions.ConnectionError:
            return "ERROR: Challenge oracle is not available. Talk to an admin."

        response = Response(resp.content, resp.status_code, resp.raw.headers.items())
        return response

