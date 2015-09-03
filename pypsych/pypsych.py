from time import time
from functools import partial
from collections import defaultdict
from itertools import combinations, starmap
from graph import Storage, View, Database

class UserView(View):
    "A view of users in the database."
    
    def map(self, doc):
        "Returns if the document is a user document."
        if doc['doc'].get("kind") == 'user':# and doc['doc'].get("verified"):
            return doc
    
    def reduce(self, docs):
        "No further processing is done."
        return docs

class MatchesView(UserView):
    "Used to generate a list of available matches."

    def reduce(self, docs):
        "Pairs members off in combinations of twos and calculates a score."
        f = lambda pair: pair[2]["overall"] >= max(pair[0]['doc']["match_requirement"], pair[1]['doc']["match_requirement"])
        return list(starmap(self.make_match, filter(f, starmap(self.score, combinations(docs, 2)))))

    def score(self, a, b):
        "scores two users on various aspects to obtain an overall compatibility scoring."
        score = {
            "aspects":{
                "test_property":1
            }
        }
        score["overall"] = sum(score["aspects"].values())
        return (a, b, score)

    def make_match(self, a, b, score):
        return [a['__id__'], b['__id__'], score]

class MessageView(View):
    "Sorts and organizes messages."
    
    def map(self, doc):
        "Ensures a document is a message."
        return doc if doc["doc"].get("kind") == 'msg' else None
    
    def reduce(self, docs):
        "Groubs messages into conversations between two users and sorts by timestamp."
        conversations = defaultdict(list)
        for msg in docs:
            a = min(msg["doc"]["from"], msg["doc"]["to"])
            b = max(msg["doc"]["from"], msg["doc"]["to"])
            content = msg["doc"]["content"]
            timestamp = msg["doc"]["timestamp"]
            conversations[(a, b)].append({
                "content":content,
                "timestamp":timestamp,
                "sender":msg["doc"]["from"]
            })
        for conversation in conversations.values():
            conversation.sort(key=lambda msg: msg["timestamp"])
        return list(starmap((lambda conversations, messages: {"participants":conversations, "messages":messages}), conversations.items()))

class ApiControl:
    "Abstracts database work into higher level operations."
    
    def __init__(self, db):
        "Stores database, registers proper views."
        self.db = db
        self.db.register_view("users", UserView())
        self.db.register_view("matches", MatchesView())
        self.db.register_view("messages", MessageView())
    
    def user_exists(self, uid):
        "Queries the users view to determine if a user with the given ID exists."
        for user in self.db.query_view("users"):
            if user['__id__'] == uid:
                return True
        return False
    
    def create_user(self, userinfo):
        "Inserts a user into the database, with an unverified status. Must include an email and username information. Returns user id."
        userinfo["email"] = userinfo["email"].lower()
        for user in self.db.query_view("users"):
            assert user["doc"]["email"] != userinfo["email"]
        userinfo["verified"] = False
        userinfo['kind'] = 'user'
        userinfo["match_requirement"] = 1
        return self.db.write(userinfo)
    
    def send_message(self, sender, receiver, content):
        "Inserts a message into the databse from sender to receiver containing the content. Returns message id."
        if self.user_exists(sender) and self.user_exists(receiver):
            return self.db.write({
                "kind":"msg",
                "content":content,
                "from":sender,
                "to":receiver,
                "timestamp":time()
            })
   
    def run_match_search(self, uid, filts=None, sorts=None):
        "Yields the results of a match search for the given user. Applies filters and sorts as provided in an iterable."
        base = self.db.query_view("matches")
        base.filter(lambda match: match[0] == uid or match[1] == uid)
        for f in (filts or []):
            base.filter(f)
        for s in (sorts or []):
            base.sort(s)
        yield from base
   
    def get_user_data(self, uid):
        "Obtains the complete document of a user of the given id."
        assert self.user_exists(uid)
        base = self.db.query_view("users")
        base.filter(lambda u: u['__id__'] == uid)
        base = list(base)
        assert len(base) > 0
        return base[0]

if __name__ == "__main__":
    app = ApiControl(Database(Storage()))
    tid = app.create_user({
        "email":"tyler9725@gmail.com",
        "username":"tyler.elric",
        "hobbies":["lol"],
    })
    xid = app.create_user({
        "email":"xlahr@facebook.com",
        "username":"firagastorm",
        "hobbies":["lol"]
    })
    app.send_message(tid, xid, "Yooooo")
    app.send_message(xid, tid, "Hey.")
    conversations = app.db.query_view("messages")
    def msg_filter(a, b, conversation):
        return a in conversation["participants"] and b in conversation["participants"]
    for match in app.db.query_view("matches"):
        a = app.get_user_data(match[0])
        b = app.get_user_data(match[1])
        print(a["doc"]["username"], "and", b["doc"]["username"], "have a score of", match[2]["overall"])
        print("The criteria for this is:")
        for aspect, contribution in match[2]["aspects"].items():
            print(aspect.title(), ":", contribution)
        conversations.filter(partial(msg_filter, match[0], match[1]))
        conversation = list(conversations)[0]
        if len(conversation):
            print("Conversation, to-date:")
            for msg in conversation["messages"]:
                print("{:10}: {}".format(msg["sender"][-10:], msg["content"]))
                print("          : Sent at {:}".format(msg["timestamp"]))
