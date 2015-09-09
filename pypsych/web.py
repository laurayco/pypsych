import bottle
import pypsych
import graph
import json
import pystache
import os
from functools import partial

def json_dumper(f):
    def w(*a,**k):
        return json.dumps(f(*a,**k))
    return w

class API(bottle.Bottle):

    def __init__(self,storage):
        super().__init__()
        self.host = "http://dating.psych2go.net"
        self.data_interface = pypsych.ApiControl(graph.Database(storage))
        self.route("/",callback=self.index_page)
        self.route("/users/<uid>",callback=self.user_info)
        self.route("/users",callback=self.create_user,method="POST")
        self.route("/matches",callback=self.matches)
        self.route("/messages",callback=self.user_messages)
        self.route("/messages/<partner>",callback=self.conversation)
        self.route("/messages/<partner>", method="POST", callback=self.send_message)
        self.update_conversation_view()

    def index_page(self):
        return templates.Element("h1",templates.Element(None,text="Hello, world.")).render()

    @json_dumper
    def list_users(self):
        return list(self.data_interface.db.query_view("users"))

    def create_user(self):
        username = bottle.request.forms["username"]
        email = bottle.request.forms["email"]
        try:
            uid = self.data_interface.create_user({
                "email":email,
                "username":username
            })
            self.send_email(email, "Registration Confirmation", "Please confirm your email at {}/users/confirm?uid={}".format(self.host, uid))
            return uid
        except Exception as e:
            print(e)
            return "ERR"

    def update_conversation_view(self):
        self.conversations = self.data_interface.db.query_view("messages")

    def send_email(self, email, subject,  content):
        print("Sending an email to {}, subject: {}".format(email, subject))
        print(content, end='\n\n')

    @json_dumper
    def matches(self):
        return list(self.data_interface.run_match_search(bottle.request.headers["uid"]))

    @json_dumper
    def user_info(self, uid):
        return self.data_interface.get_user_data(uid)

    @json_dumper
    def user_messages(self):
        uid = bottle.request.headers["uid"]
        "returns a list of conversations, but not their contents."
        self.conversations.filter(lambda conversation: uid in conversation["participants"])
        return [conversation["participants"] for conversation in self.conversations]

    @json_dumper
    def conversation(self, partner):
        uid = bottle.request.headers["uid"]
        msg_filter = lambda conv: uid in conv["participants"] and partner in conv["participants"]
        self.conversations.filter(msg_filter)
        convs = list(self.conversations)
        convs = convs[0] if len(convs) else {'messages':[],"participant":[]}
        return convs

    def send_message(self, partner):
        sender = bottle.request.headers["uid"]
        content = bottle.request.forms["content"]
        r = self.data_interface.send_message(sender, partner, content)
        self.update_conversation_view()
        return r

class Interface(bottle.Bottle):
    
    def __init__(self):
        super().__init__()
        self.route("/", callback=self.index_page)
        self.route("/style/<style>", callback=self.stylesheet)
        self.route("/script/<script>", callback=self.script)
        self.route("/template/<templname>", callback=self.template)

    def pre_render(self):
        # will either be an ajax-data call
        # a pre-render call
        return False

    def index_page(self):
        scripts = list(map((lambda x:x[:-3]),filter((lambda x:x[-3:]==".js"),os.listdir("js"))))
        styles = list(map((lambda x:x[:-4]),filter((lambda x:x[-4:]==".css"),os.listdir("css"))))
        with open("templates/header.mustache") as f:
            if self.pre_render():
                return pystache.render(f.read(),{
                    "scripts":scripts,
                    "styles":styles,
                    "page_render":partial(pystache.render(self.template("home"),{}))
                })
            else:
                return pystache.render(f.read(),{
                    "scripts":scripts,
                    "styles":styles
                })

    def stylesheet(self,style):
        return bottle.static_file("{}.css".format(style), "css")

    def script(self, script):
        return bottle.static_file("{}.js".format(script), "js")

    def template(self, templname):
        return bottle.static_file("{}.mustache".format(templname), "templates")

if __name__=="__main__":
    api = API(graph.Storage())
    web = Interface()
    web.mount("/api",api)
    web.run()