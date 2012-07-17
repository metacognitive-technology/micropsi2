#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MicroPsi server application.

This version of MicroPsi is meant to be deployed as a web server, and accessed through a browser.
For local use, simply start this server and point your browser to "http://localhost:6543".
The latter parameter is the default port and can be changed as needed.
"""

__author__ = 'joscha'
__date__ = '15.05.12'

VERSION = "0.1"

import micropsi_core.runtime
import micropsi_core.tools
import user
import config
import bottle
from bottle import route, post, run, request, response, template, static_file, redirect, error
import argparse, os, json, inspect


DEFAULT_PORT = 6543
DEFAULT_HOST = "localhost"

APP_PATH = os.path.dirname(__file__)
RESOURCE_PATH = os.path.join(os.path.dirname(__file__),"..","resources")

bottle.debug( True ) #devV
bottle.TEMPLATE_PATH.insert( 0, os.path.join(APP_PATH, 'view', ''))

def rpc(command, route_prefix = "/rpc/", method = "GET", permission_required = None):
    """Defines a decorator for accessing API calls. Use it by specifying the
    API method, followed by the permissions necessary to execute the method.
    Within the calling web page, use http://<url>/rpc/<method>(arg1="val1", arg2="val2", ...)
    Import these arguments into your decorated function:
        @rpc("my_method")
        def this_is_my_method(arg1, arg2):
            pass

    This will either return a JSON object with the result, or {"Error": <error message>}
    The decorated function can optionally import the following parameters (by specifying them in its signature):
        argument: the original argument string
        token: the current session token
        user_id: the id of the user associated with the current session token
        permissions: the set of permissions associated with the current session token

    Arguments:
        command: the command against which we want to match
        method (optional): the request method
        permission_required (optional): the type of permission necessary to execute the method;
            if omitted, permissions won't be tested by the decorator
    """
    def _decorator(func):
        @route(route_prefix + command + "()", method)
        @route(route_prefix + command + "(<argument>)", method)
        def _wrapper(argument = None):
            kwargs = {}
            if argument:
                try:
                    kwargs = dict((n.strip(),json.loads(v)) for n,v in (a.split('=') for a in argument.split(",")))
                except ValueError:
                    return {"Error": "Invalid arguments for remote procedure call"}
            if request.get_cookie("token"):
                token = request.get_cookie("token")
            else:
                token = None

            user_id = usermanager.get_user_id_for_session_token(token)
            permissions = usermanager.get_permissions_for_session_token(token)

            if permission_required and permission_required not in permissions:
                return {"Error": "Insufficient permissions for remote procedure call"}
            else:
                kwargs.update({"argument": argument, "permissions": permissions, "user_id": user_id, "token": token})
                try:
                    return json.dumps(func(**dict((name, kwargs[name]) for name in inspect.getargspec(func)[0])))
                except KeyError, err:
                    return {"Error": "Missing argument in remote procedure call: %s" %err}
        return _wrapper
    return _decorator

def page(path, route_prefix = "", method = "GET", permission_required = None):
    """Defines a decorator for accessing pages, similar to Bottle's @route, but adding user management.
    Simply supply the argument 'permission_required' with the required permission.

    It the permissions are insufficient, an error page will be shown.
    The decorated function can optionally import the following parameters (by specifying them in its signature):
        token: the current session token
        user_id: the id of the user associated with the current session token
        permissions: the set of permissions associated with the current session token
    """
    def _decorator(func):
        @route(route_prefix + path, method)
        def _wrapper():
            if request.get_cookie("token"):
                token = request.get_cookie("token")
            else:
                token = None

            user_id = usermanager.get_user_id_for_session_token(token)
            permissions = usermanager.get_permissions_for_session_token(token)

            if permission_required and permission_required not in permissions:
                return template("error", msg = "Insufficient access rights.")
            else:
                kwargs = {"permissions": permissions, "user_id": user_id, "token": token }
                return func(**dict((name, kwargs[name]) for name in inspect.getargspec(func)[0]))
        return _wrapper
    return _decorator

def submit(path, route_prefix = "/submit", method = "POST", permission_required = None):
    """Defines a decorator for submitting forms, similar to Bottle's @post, but adding user management.
    Simply supply the argument 'permission_required' with the required permission.

    It the permissions are insufficient, an error page will be shown.
    The decorated function can optionally import the following parameters (by specifying them in its signature):
        token: the current session token
        user_id: the id of the user associated with the current session token
        permissions: the set of permissions associated with the current session token
    """
    return page(path, route_prefix, method, permission_required)


# ----------------------------------------------------------------------------------

@route('/static/<filepath:path>')
def server_static(filepath): return static_file(filepath, root=os.path.join(APP_PATH, 'static'))

@page("/")
def index(user_id, permissions):
    return template("nodenet", version = VERSION, user = user_id, permissions = permissions)

@error(404)
def error_page(error):
    return template("error.tpl", error = error, msg = "Page not found.", img = "/static/img/brazil.gif")

@error(405)
def error_page(error):
    return template("error.tpl", error = error, msg = "Method not allowed.", img = "/static/img/strangelove.gif")

@error(500)
def error_page(error):
    return template("error.tpl", error = error, msg = "Internal server error.", img = "/static/img/brainstorm.gif")

@page("/about")
def about(user_id, permissions): return template("about", version = VERSION, user = user_id, permissions = permissions)

@route("/docs")
def documentation(): return template("documentation", version = VERSION)

@route("/contact")
def contact(): return template("contact", version = VERSION)

@page("/logout")
def logout(token):
    usermanager.end_session(token)
    response.delete_cookie("token")
    redirect("/")

@route("/login")
def login():
    if not usermanager.users:  # create first user
        return template("signup", version = VERSION, first_user = True, userid="admin")

    return template("login",
        version = VERSION,
        user = usermanager.get_user_id_for_session_token(None),
        permissions = usermanager.get_permissions_for_session_token(None))

@post("/login_submit")
def login_submit():
    user_id = request.forms.userid
    password = request.forms.password

    # log in new user
    token = usermanager.start_session(user_id, password, request.forms.get("keep_logged_in"))
    if token:
        response.set_cookie("token", token)
        # redirect to start page
        redirect("/")
    else:
        # login failed, retry
        if user_id in usermanager.users:
            return template("login", version = VERSION, userid=user_id, password=password,
                password_error="Re-enter the password",
                login_error="User name and password do not match",
                cookie_warning = (token is None),
                permissions = usermanager.get_permissions_for_session_token(token))
        else:
            return template("login", version = VERSION, userid=user_id, password=password,
                userid_error="Re-enter the user name",
                login_error="User unknown",
                cookie_warning = (token is None),
                permissions = usermanager.get_permissions_for_session_token(token))


@route("/signup")
def signup():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
    else:
        token = None

    if not usermanager.users:  # create first user
        return template("signup", version = VERSION, first_user = True, cookie_warning = (token is None))

    return template("signup", version = VERSION,
        permissions = usermanager.get_permissions_for_session_token(token),
        cookie_warning = (token is None))

@post("/signup_submit")
def signup_submit():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
    else:
        token = None
    user_id = request.forms.userid
    password = request.forms.password
    role = request.forms.get('permissions')
    (success, result) = micropsi_core.tools.check_for_url_proof_id(user_id, existing_ids = usermanager.users.keys())
    permissions = usermanager.get_permissions_for_session_token(token)

    if success:
        # check if permissions in form are consistent with internal permissions
        if ((role == "Administrator" and ("create admin" in permissions or not usermanager.users)) or
            (role == "Full" and "create full" in permissions) or
            (role == "Restricted" and "create restricted" in permissions)):
            if usermanager.create_user(user_id, password, role, uid = micropsi_core.tools.generate_uid()):
                # log in new user
                token = usermanager.start_session(user_id, password, request.forms.get("keep_logged_in"))
                response.set_cookie("token", token)
                # redirect to start page
                redirect('/')
            else:
                return template("error", msg = "User creation failed for an obscure internal reason.")
        else:
            return template("error", msg = "Permission inconsistency during user creation.")
    else:
        # something wrong with the user id, retry
        return template("signup", version = VERSION, userid=user_id, password=password, userid_error=result,
            permissions = permissions, cookie_warning = (token is None))

@route("/change_password")
def change_password():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        return template("change_password", version = VERSION,
            userid = usermanager.get_user_id_for_session_token(token),
            permissions = usermanager.get_permissions_for_session_token(token))
    else:
        return template("error", msg = "Cannot change password outside of a session")

@post("/change_password_submit")
def change_password_submit():
    if request.get_cookie("token"):
        token = request.get_cookie("token")

        old_password = request.forms.old_password
        new_password = request.forms.new_password
        user_id = usermanager.get_user_id_for_session_token(token)
        permissions = usermanager.get_permissions_for_session_token(token)

        if usermanager.test_password(user_id, old_password):
            usermanager.set_user_password(user_id, new_password)
            redirect('/')

        else:
            return template("change_password", version = VERSION, userid=user_id, old_password=old_password,
                permissions = permissions, new_password=new_password,
                old_password_error="Wrong password, please try again")
    else:
        return template("error", msg = "Cannot change password outside of a session")

@route("/user_mgt")
def user_mgt():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            return template("user_mgt", version = VERSION, permissions = permissions,
                user = usermanager.get_user_id_for_session_token(token),
                userlist = usermanager.list_users())
    return template("error", msg = "Insufficient rights to access user console")

@route("/set_permissions/<user_id>/<role>")
def set_permissions(user_id, role):
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            if user_id in usermanager.users.keys() and role in user.USER_ROLES.keys():
                usermanager.set_user_role(user_id, role)
            redirect('/user_mgt')
    return template("error", msg = "Insufficient rights to access user console")

@route("/create_user")
def create_user():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            return template("create_user", version = VERSION, user = usermanager.get_user_id_for_session_token(token),
                permissions = permissions)

    return template("error", msg = "Insufficient rights to access user console")


@post("/create_user_submit")
def create_user_submit():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)

        user_id = request.forms.userid
        password = request.forms.password
        role = request.forms.get('permissions')
        (success, result) = micropsi_core.tools.check_for_url_proof_id(user_id, existing_ids = usermanager.users.keys())

        if success:
            # check if permissions in form are consistent with internal permissions
            if ((role == "Administrator" and ("create admin" in permissions or not usermanager.users)) or
                (role == "Full" and "create full" in permissions) or
                (role == "Restricted" and "create restricted" in permissions)):
                if usermanager.create_user(user_id, password, role, uid = micropsi_core.tools.generate_uid()):
                    redirect('/user_mgt')
                else:
                    return template("error", msg = "User creation failed for an obscure internal reason.")
            else:
                return template("error", msg = "Permission inconsistency during user creation.")
        else:
            # something wrong with the user id, retry
            return template("create_user", version = VERSION, user = usermanager.get_user_id_for_session_token(token),
                permissions = permissions, userid_error = result)
    return template("error", msg = "Insufficient rights to access user console")

@route("/set_password/<user_id>")
def set_password(user_id):
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            return template("set_password", version = VERSION, permissions = permissions,
                user = usermanager.get_user_id_for_session_token(token),
                user_id=user_id)
    return template("error", msg = "Insufficient rights to access user console")

@post("/set_password_submit")
def set_password_submit():
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            user_id = request.forms.userid
            password = request.forms.password
            if user_id in usermanager.users.keys():
                usermanager.set_user_password(user_id, password)
            redirect('/user_mgt')
    return template("error", msg = "Insufficient rights to access user console")

@route("/delete_user/<user_id>")
def delete_user(user_id):
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            if user_id in usermanager.users.keys():
                usermanager.delete_user(user_id)
            redirect("/user_mgt")
    return template("error", msg = "Insufficient rights to access user console")

@route("/login_as/<user>")
def login_as_user(user):
    if request.get_cookie("token"):
        token = request.get_cookie("token")
        permissions = usermanager.get_permissions_for_session_token(token)
        if "manage users" in permissions:
            if user in usermanager.users.keys():
                usermanager.end_session(token)
                token = usermanager.start_session(user)
                response.set_cookie("token", token)
                # redirect to start page
                redirect('/')
    return template("error", msg = "Insufficient rights to access user console")


@route("/agent/import")
def import_agent():
    if 'file' in request.forms:
        # do stuff
        pass
    token = request.get_cookie("token")
    return template("upload.tpl", title='Import agent', message='Select a file to upload and use for importing', action='/agent/import',
        version = VERSION,
        userid = usermanager.get_user_id_for_session_token(token),
        permissions = usermanager.get_permissions_for_session_token(token))


@route("/agent/merge")
def merge_agent():
    if 'file' in request.forms:
        # do stuff
        pass
    token = request.get_cookie("token")
    return template("upload.tpl", title='Merge agent', message='Select a file to upload and use for merging', action='/agent/merge',
        version = VERSION,
        userid = usermanager.get_user_id_for_session_token(token),
        permissions = usermanager.get_permissions_for_session_token(token))


@route("/agent/export")
def export_agent():
    response.set_header('Content-type', 'application/json')
    response.set_header('Content-Disposition', 'attachment; filename="world.json"')
    return "{}"


@route("/agent/edit")
def edit_agent():
    token = request.get_cookie("token")
    id = request.params.get('id', None)
    title = 'Edit Blueprint' if id is not None else 'New Blueprint'
    return template("agent_form.tpl", title=title, agent={}, templates=[], worlds=[], worldadapters=[],
        version = VERSION,
        userid = usermanager.get_user_id_for_session_token(token),
        permissions = usermanager.get_permissions_for_session_token(token))


@route("/world/import")
def import_world():
    if 'file' in request.forms:
        # do stuff
        pass
    token = request.get_cookie("token")
    return template("upload.tpl", title='World import', message='Select a file to upload and use for importing',
        action='/world/import',
        version = VERSION,
        userid = usermanager.get_user_id_for_session_token(token),
        permissions = usermanager.get_permissions_for_session_token(token))


@route("/world/export")
def export_world():
    response.set_header('Content-type', 'application/json')
    response.set_header('Content-Disposition', 'attachment; filename="world.json"')
    return "{}"


@route("/world/edit")
def edit_world():
    token = request.get_cookie("token")
    id = request.params.get('id', None)
    title = 'Edit World' if id is not None else 'New World'
    return template("world_form.tpl", title=title, world={}, worldtypes=[],
        version = VERSION,
        userid = usermanager.get_user_id_for_session_token(token),
        permissions = usermanager.get_permissions_for_session_token(token))



@route("/agent_list/<current_agent>")
def agent_list(current_agent):
    print current_agent
    token = request.get_cookie("token")
    user_id = usermanager.get_user_id_for_session_token(token)
    agents = micropsi.get_available_agents()
    return template("agent_list", user_id = user_id,
        current_agent = current_agent,
        my_agents = { uid: agents[uid] for uid in agents if agents[uid]["owner"] == user_id},
        other_agents = { uid: agents[uid] for uid in agents if agents[uid]["owner"] != user_id})

@page("/select_agent")
def select_agent(agent_uid): pass

@rpc("generate_uid")
def generate_uid(): return micropsi_core.tools.generate_uid()

@rpc("get_available_agents")
def get_available_agents(user_id): return micropsi.get_available_agents(user_id)

@rpc("new_agent", permission_required="manage agents")
def new_agent(agent_name, agent_type, user_id, world_uid):
    return micropsi.new_agent(agent_name, agent_type, owner = user_id, world_uid = world_uid)

@rpc("delete_agent", permission_required="manage agents")
def delete_agent(self, agent_uid): return micropsi.delete_agent(self, agent_uid)

@rpc("set_agent_data", permission_required="manage agents")
def set_agent_data(self, agent_uid, agent_name = None, agent_type = None, world_uid = None, owner = None): return micropsi.set_agent_data(self, agent_uid, agent_name = None, agent_type = None, world_uid = None, owner = None)

@rpc("start_agentrunner", permission_required="manage agents")
def start_agentrunner(self, agent_uid): return micropsi.start_agentrunner

@rpc("set_agentrunner_timestep", permission_required="manage agents")
def set_agentrunner_timestep(self, timestep): return micropsi.set_agentrunner_timestep

@rpc("get_agentrunner_timestep", permission_required="manage server")
def get_agentrunner_timestep(self): return micropsi.get_agentrunner_timestep

@rpc("get_is_agent_running")
def get_is_agent_running(self, agent_uid): return micropsi.get_is_agent_running

@rpc("stop_agentrunner", permission_required="manage agents")
def stop_agentrunner(self, agent_uid): return micropsi.stop_agentrunner

@rpc("step_agent", permission_required="manage agents")
def step_agent(self, agent_uid, nodespace = None): return micropsi.step_agent

@rpc("revert_agent", permission_required="manage agents")
def revert_agent(self, agent_uid): return micropsi.revert_agent

@rpc("save_agent", permission_required="manage agents")
def save_agent(self, agent_uid): return micropsi.save_agent

@rpc("export_agent")
def export_agent(self, agent_uid): return micropsi.export_agent

@rpc("import_agent", permission_required="manage agents")
def import_agent(self, agent_uid, nodenet): return micropsi.import_agent

@rpc("merge_agent", permission_required="manage agents")
def merge_agent(self, agent_uid, nodenet): return micropsi.merge_agent

# World

@rpc("get_available_worlds")
def get_available_worlds(self, owner = None): return micropsi.get_available_worlds

@rpc("new_world", permission_required="manage worlds")
def new_world(self, world_name, world_type, owner = ""): return micropsi.new_world

@rpc("delete_world", permission_required="manage worlds")
def delete_world(self, world_uid): return micropsi.delete_world

@rpc("get_world_view")
def get_world_view(self, world_uid, step): return micropsi.get_world_view

@rpc("set_world_data", permission_required="manage worlds")
def set_world_data(self, world_uid, world_name = None, world_type = None, owner = None): return micropsi.set_world_data

@rpc("start_worldrunner", permission_required="manage worlds")
def start_worldrunner(self, world_uid): return micropsi.start_worldrunner

@rpc("get_worldrunner_timestep")
def get_worldrunner_timestep(self): return micropsi.get_worldrunner_timestep

@rpc("get_is_world_running")
def get_is_world_running(self, world_uid): return micropsi.get_is_world_running

@rpc("set_worldrunner_timestep", permission_required="manage server")
def set_worldrunner_timestep(self): return micropsi.set_worldrunner_timestep

@rpc("stop_worldrunner", permission_required="manage worlds")
def stop_worldrunner(self, world_uid): return micropsi.stop_worldrunner

@rpc("step_world", permission_required="manage worlds")
def step_world(self, world_uid, return_world_view = False): return micropsi.step_world

@rpc("revert_world", permission_required="manage worlds")
def revert_world(self, world_uid): return micropsi.revert_world

@rpc("save_world", permission_required="manage worlds")
def save_world(self, world_uid): return micropsi.save_world

@rpc("export_world")
def export_world(self, world_uid): return micropsi.export_world

@rpc("import_world", permission_required="manage worlds")
def import_world(self, world_uid, worlddata): return micropsi.import_world

# Monitor

@rpc("add_gate_monitor")
def add_gate_monitor(self, agent_uid, node_uid, gate_index): return micropsi.add_gate_monitor

@rpc("add_slot_monitor")
def add_slot_monitor(self, agent_uid, node_uid, slot_index): return micropsi.add_slot_monitor

@rpc("remove_monitor")
def remove_monitor(self, monitor_uid): return micropsi.remove_monitor

@rpc("clear_monitor")
def clear_monitor(self, monitor_uid): return micropsi.clear_monitor

@rpc("export_monitor_data")
def export_monitor_data(self, agent_uid): return micropsi.export_monitor_data

@rpc("get_monitor_data")
def get_monitor_data(self, agent_uid, step): return micropsi.get_monitor_data

# Nodenet

@rpc("get_nodespace")
def get_nodespace(self, agent_uid, nodespace, step): return micropsi.get_nodespace

@rpc("get_node")
def get_node(self, agent_uid, node_uid): return micropsi.get_node

@rpc("add_node", permission_required="manage agents")
def add_node(self, agent_uid, type, x, y, nodespace, uid = None, name = ""): return micropsi.add_node

@rpc("set_node_position", permission_required="manage agents")
def set_node_position(self, agent_uid, node_uid, x, y): return micropsi.set_node_position

@rpc("set_node_name", permission_required="manage agents")
def set_node_name(self, agent_uid, node_uid, name): return micropsi.set_node_name

@rpc("delete_node", permission_required="manage agents")
def delete_node(self, agent_uid, node_uid): return micropsi.delete_node

@rpc("get_available_node_types")
def get_available_node_types(self, agent_uid = None): return micropsi.get_available_node_types

@rpc("get_available_native_module_types")
def get_available_native_module_types(self, agent_uid = None): return micropsi.get_available_native_module_types

@rpc("get_node_function")
def get_node_function(self, agent_uid, node_type): return micropsi.get_node_function

@rpc("set_node_function", permission_required="manage agents")
def set_node_function(self, agent_uid, node_type, node_function = None): return micropsi.set_node_function

@rpc("set_node_parameters", permission_required="manage agents")
def set_node_parameters(self, agent_uid, node_uid, parameters = None): return micropsi.set_node_parameters

@rpc("add_node_type", permission_required="manage agents")
def add_node_type(self, agent_uid, node_type, slots = None, gates = None, node_function = None, parameters = None): return micropsi.add_node_type

@rpc("delete_node_type", permission_required="manage agents")
def delete_node_type(self, agent_uid, node_type): return micropsi.delete_node_type

@rpc("get_slot_types")
def get_slot_types(self, agent_uid, node_type): return micropsi.get_slot_types

@rpc("get_gate_types")
def get_gate_types(self, agent_uid, node_type): return micropsi.get_gate_types

@rpc("get_gate_function")
def get_gate_function(self, agent_uid, nodespace, node_type, gate_type): return micropsi.get_gate_function

@rpc("set_gate_function", permission_required="manage agents")
def set_gate_function(self, agent_uid, nodespace, node_type, gate_type, gate_function = None, parameters = None): return micropsi.set_gate_function

@rpc("set_gate_parameters", permission_required="manage agents")
def set_gate_parameters(self, agent_uid, node_uid, gate_type, parameters = None): return micropsi.set_gate_parameters

@rpc("get_available_datasources")
def get_available_datasources(self, agent_uid): return micropsi.get_available_datasources

@rpc("get_available_datatargets")
def get_available_datatargets(self, agent_uid): return micropsi.get_available_datatargets

@rpc("bind_datasource_to_sensor", permission_required="manage agents")
def bind_datasource_to_sensor(self, agent_uid, sensor_uid, datasource): return micropsi.bind_datasource_to_sensor

@rpc("bind_datatarget_to_actor", permission_required="manage agents")
def bind_datatarget_to_actor(self, agent_uid, actor_uid, datatarget): return micropsi.bind_datatarget_to_actor

@rpc("add_link", permission_required="manage agents")
def add_link(self, agent_uid, source_node_uid, gate_type, target_node_uid, slot_type, weight, certainty = 1, uid = None): return micropsi.add_link

@rpc("set_link_weight", permission_required="manage agents")
def set_link_weight(self, agent_uid, link_uid, weight, certainty = 1): return micropsi.set_link_weight

@rpc("get_link")
def get_link(self, agent_uid, link_uid): return micropsi.get_link

@rpc("delete_link", permission_required="manage agents")
def delete_link(self, agent_uid, link_uid): return micropsi.delete_link



# -----------------------------------------------------------------------------------------------

def main(host=DEFAULT_HOST, port=DEFAULT_PORT):
    global micropsi
    global usermanager
    global configs
    configs = config.ConfigurationManager(os.path.join(RESOURCE_PATH, "config.json"))
    micropsi = micropsi_core.runtime.MicroPsiRuntime(RESOURCE_PATH)
    usermanager = user.UserManager(os.path.join(RESOURCE_PATH, "user-db.json"))


    run(host=host, port=port) #devV

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the MicroPsi server.")
    parser.add_argument('-d', '--host', type=str, default=DEFAULT_HOST)
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    main(host = args.host, port = args.port)
